"""
Indexing Service Module

Coordinates directory scanning, single-file indexing, batch commit retries,
and background indexing scheduler orchestration while delegating folder/zombie
cleanup to folder_manager and single-photo reindexing to photo_reindex.
"""

import asyncio
import hashlib
import logging
import os
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Image as DBImage
from repositories.vector_repository import VectorRepository
from services.ai_factory import get_gemma_adapter, get_siglip_adapter
from services.folder_manager import (
    FolderDeletionConflictError,
    FolderNotRegisteredError,
    cleanup_zombie_records as _cleanup_zombie_records_impl,
    delete_photo_atomic_sync as _delete_photo_atomic_sync_impl,
    identify_zombie_photo_ids as _identify_zombie_photo_ids_impl,
    remove_folder_data as _remove_folder_data_impl,
)
from services.indexing_state import indexing_state_manager
from services.photo import get_thumbnail_path
from services.photo_reindex import reindex_single_photo_inplace as _reindex_single_photo_impl
from utils.image import extract_metadata

logger = logging.getLogger("focal_node.indexing_service")

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".rw2", ".pef", ".raf",
}

vector_repo = VectorRepository()


def pause_indexing() -> bool:
    """Pauses active background indexing."""
    return indexing_state_manager.pause()


def resume_indexing() -> bool:
    """Resumes paused background indexing."""
    return indexing_state_manager.resume()


def cancel_indexing() -> bool:
    """Cancels active or paused background indexing."""
    return indexing_state_manager.cancel()


def calculate_sha256(file_path: str) -> str:
    """Computes SHA-256 checksum of a file in chunks to bound memory usage."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def _collect_supported_folder_files(folder_path: str, seen_paths: set[str]) -> List[str]:
    """Walks a single folder recursively and collects unseen supported image paths."""
    collected_files: List[str] = []
    for root_dir, _, file_names in os.walk(folder_path):
        for file_name in file_names:
            if file_name.startswith(".") or file_name.startswith("._"):
                continue
            ext = os.path.splitext(file_name)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            full_path = os.path.join(root_dir, file_name)
            if full_path not in seen_paths:
                seen_paths.add(full_path)
                collected_files.append(full_path)
    return collected_files


def scan_directory(folder_paths: List[str]) -> List[str]:
    """Recursively scans targeted folders and extracts deduplicated supported image paths."""
    files_to_index: List[str] = []
    seen_paths: set[str] = set()
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            print(f"[Indexer] Target folder does not exist: {folder_path}", flush=True)
            continue
        files_to_index.extend(_collect_supported_folder_files(folder_path, seen_paths))
    return files_to_index


def delete_photo_atomic_sync(db: Session, image_id: str) -> None:
    """Delegates atomic photo deletion while keeping module-level patch hooks intact."""
    _delete_photo_atomic_sync_impl(
        db,
        image_id,
        vector_repository=vector_repo,
        thumbnail_path_fn=get_thumbnail_path,
    )


def _identify_zombie_photo_ids(db: Session, normalized_folder_prefixes: list) -> List[str]:
    """Delegates zombie photo identification to folder_manager."""
    return _identify_zombie_photo_ids_impl(db, normalized_folder_prefixes)


def cleanup_zombie_records(db: Session = None) -> None:
    """Delegates zombie record cleanup while keeping module-level patch hooks intact."""
    _cleanup_zombie_records_impl(
        db=db,
        session_factory=SessionLocal,
        vector_repository=vector_repo,
        thumbnail_path_fn=get_thumbnail_path,
    )


def remove_folder_data(folder_path: str, db: Session = None) -> None:
    """Delegates registered folder deletion while keeping module-level patch hooks intact."""
    _remove_folder_data_impl(
        folder_path,
        db=db,
        session_factory=SessionLocal,
        vector_repository=vector_repo,
        thumbnail_path_fn=get_thumbnail_path,
        state_manager=indexing_state_manager,
    )


def run_ai_pipeline_sync(file_path: str) -> Tuple[Dict[str, Any], list[float], Dict[str, Any]]:
    """Runs EXIF extraction, SigLIP embedding/hints, and Gemma captioning sequentially."""
    metadata = extract_metadata(file_path)
    siglip_adapter = get_siglip_adapter()
    embedding = siglip_adapter.get_image_embedding(file_path)
    siglip_hints = siglip_adapter.get_zero_shot_hints(embedding)
    ai_result = get_gemma_adapter().generate_caption_and_tags(
        file_path, metadata, siglip_hints=siglip_hints
    )
    return metadata, embedding, ai_result


def _find_existing_id_or_skip(
    file_path: str, file_size: int, file_mtime: float
) -> tuple[bool, Optional[str]]:
    """Checks SQLite by file_path and returns (should_skip, existing_image_id_if_modified)."""
    db_session: Optional[Session] = None
    try:
        db_session = SessionLocal()
        existing_by_path = db_session.query(DBImage).filter(DBImage.file_path == file_path).first()
        if existing_by_path is None:
            return False, None
        mtime_unchanged = abs(existing_by_path.file_mtime - file_mtime) < 0.01
        if mtime_unchanged and existing_by_path.file_size == file_size:
            return True, None
        print(f"[Indexer] File modified. Marking for re-indexing: {file_path}", flush=True)
        return False, existing_by_path.id
    finally:
        if db_session is not None:
            db_session.close()


def _safe_rollback_session(db_session: Session) -> None:
    """Rolls back a failed SQLAlchemy session without masking the original commit error."""
    try:
        db_session.rollback()
    except Exception as rollback_err:
        logger.warning("Failed to rollback batch session cleanly: %s", rollback_err)


def _resolve_hash_conflict(
    file_path: str, image_id: str, file_size: int, file_mtime: float
) -> Optional[str]:
    """Handles existing SHA-256 matches by updating mtime/size or reporting duplicate hash."""
    db_session: Optional[Session] = None
    try:
        db_session = SessionLocal()
        existing_by_id = db_session.query(DBImage).filter(DBImage.id == image_id).first()
        if existing_by_id is None:
            return None
        if existing_by_id.file_path == file_path:
            existing_by_id.file_mtime = file_mtime
            existing_by_id.file_size = file_size
            db_session.commit()
            return "skipped"
        print(f"[Indexer] Hash duplicate found. Skipping: {file_path}", flush=True)
        return "skipped_duplicate_hash"
    except Exception:
        if db_session is not None:
            _safe_rollback_session(db_session)
        raise
    finally:
        if db_session is not None:
            db_session.close()


def index_single_file_sync(file_path: str) -> Union[dict, str]:
    """Performs hashing, pipeline inference, and prepares atomic registration payload."""
    try:
        file_size = os.path.getsize(file_path)
        file_mtime = os.path.getmtime(file_path)
        should_skip, superseded_id = _find_existing_id_or_skip(file_path, file_size, file_mtime)
        if should_skip:
            return "skipped"

        image_id = calculate_sha256(file_path)
        conflict_status = _resolve_hash_conflict(file_path, image_id, file_size, file_mtime)
        if conflict_status is not None:
            return conflict_status

        from services.pipeline import IndexingPipeline
        pipeline_result = IndexingPipeline().run(file_path, image_id=image_id)
        if isinstance(pipeline_result, str):
            return pipeline_result

        new_image_id = pipeline_result.get("image_data", {}).get("id")
        if superseded_id and superseded_id != new_image_id:
            # Defer old record deletion until batch commit succeeds to avoid data loss on interrupt.
            pipeline_result["replaces_image_id"] = superseded_id
        return pipeline_result
    except Exception as index_err:
        logger.error("[Indexer] Error indexing file %s: %s", file_path, index_err)
        print(f"[Indexer] Error indexing file {file_path}: {index_err}", flush=True)
        return "error"


async def reindex_single_photo_inplace(photo_id: str) -> dict:
    """Delegates single-photo in-place reindexing while preserving module patch hooks."""
    return await _reindex_single_photo_impl(
        photo_id,
        ai_pipeline_fn=run_ai_pipeline_sync,
        session_factory=SessionLocal,
        vector_repository=vector_repo,
    )


def _deduplicate_batch_items(raw_items: list[dict]) -> list[dict]:
    """Filters duplicate photo records within a single chunk batch."""
    batch_items: list[dict] = []
    seen_ids: set[str] = set()
    for item in raw_items:
        image_id = item["image_data"]["id"]
        if image_id in seen_ids:
            print(f"[Indexer] In-batch duplicate found. Skipping: {item['image_data']['file_path']}", flush=True)
            continue
        seen_ids.add(image_id)
        batch_items.append(item)
    return batch_items


def _attempt_batch_commit(batch_items: list[dict]) -> Optional[Exception]:
    """Executes one batch upsert attempt and returns any caught exception after rollback."""
    from services.photo import register_photos_batch_atomic

    db_batch: Optional[Session] = None
    try:
        db_batch = SessionLocal()
        register_photos_batch_atomic(db_batch, batch_items)
        return None
    except Exception as commit_err:
        if db_batch is not None:
            _safe_rollback_session(db_batch)
        return commit_err
    finally:
        if db_batch is not None:
            db_batch.close()


def _handle_batch_commit_failure(
    commit_err: Exception, attempt: int, max_attempts: int, item_count: int
) -> None:
    """Logs batch commit failure and either sleeps for retry or re-raises on final attempt."""
    logger.error(
        "[Indexer] Batch DB Upsert attempt %d/%d failed for %d items: %s",
        attempt + 1, max_attempts, item_count, commit_err,
    )
    print(
        f"[Indexer] Batch DB Upsert attempt {attempt + 1}/{max_attempts} failed for {item_count} items: {commit_err}",
        flush=True,
    )
    if attempt < max_attempts - 1:
        time.sleep(0.3 * (attempt + 1))
        return
    traceback.print_exc()
    raise commit_err


def _commit_batch_with_retry(batch_items: list[dict], max_attempts: int = 3) -> None:
    """Saves indexed photos batch to SQLite and ChromaDB with exponential backoff retry."""
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1, got {max_attempts}")
    if not batch_items:
        return

    for attempt in range(max_attempts):
        commit_err = _attempt_batch_commit(batch_items)
        if commit_err is None:
            return
        _handle_batch_commit_failure(commit_err, attempt, max_attempts, len(batch_items))


_PROGRESS_STATUS_LABELS = {
    "skipped_duplicate_hash": "Skipped (Duplicate Hash)",
    "skipped": "Skipped (Already Indexed)",
}


def _log_indexing_progress(file_path: str, file_result: Any, count: int, total: int) -> None:
    """Formats and prints progress log for an indexed file."""
    if isinstance(file_result, dict):
        status_str = "Indexed with AI"
    else:
        status_str = _PROGRESS_STATUS_LABELS.get(file_result, f"Status: {file_result}")
    print(f"[Indexing] Progress: {count}/{total} - {file_path} ({status_str})", flush=True)


def _normalize_indexing_error(exc: BaseException) -> str:
    """Formats an indexing exception into a non-empty single-line error message."""
    single_line = " ".join(str(exc).split())
    return single_line[:500] if single_line else type(exc).__name__


async def _process_single_indexing_file(
    file_path: str,
    semaphore: asyncio.Semaphore,
    total_files: int,
    counter: list[int],
    run_id: Optional[int] = None,
) -> Any:
    """Handles concurrency, pause/cancel checking, and progress updates for a single file."""
    if indexing_state_manager.is_run_cancelled(run_id):
        return "cancelled"

    async with semaphore:
        if not await indexing_state_manager.wait_if_paused(run_id):
            return "cancelled"

        file_result = await asyncio.to_thread(index_single_file_sync, file_path)
        if indexing_state_manager.is_run_cancelled(run_id):
            return "cancelled"
        counter[0] += 1
        indexing_state_manager.update_progress(counter[0], total_files, file_path, run_id=run_id)
        _log_indexing_progress(file_path, file_result, counter[0], total_files)
        return file_result


async def _cancel_pending_chunk_tasks(tasks: list[asyncio.Task]) -> None:
    """Cancels any unfinished chunk tasks and awaits completion cleanly."""
    pending = [task for task in tasks if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def _process_indexing_chunk(
    chunk_files: list[str],
    semaphore: asyncio.Semaphore,
    total_files: int,
    counter: list[int],
    run_id: Optional[int],
) -> None:
    """Processes a single chunk of files concurrently and commits the batch atomically."""
    tasks = [
        asyncio.create_task(
            _process_single_indexing_file(file_path, semaphore, total_files, counter, run_id=run_id)
        )
        for file_path in chunk_files
    ]
    try:
        chunk_results = await asyncio.gather(*tasks)
    except BaseException:
        await _cancel_pending_chunk_tasks(tasks)
        raise

    if indexing_state_manager.is_run_cancelled(run_id):
        return

    raw_batch_items = [item for item in chunk_results if isinstance(item, dict)]
    if raw_batch_items:
        batch_items = _deduplicate_batch_items(raw_batch_items)
        await asyncio.to_thread(_commit_batch_with_retry, batch_items)


def _finalize_indexing_status(
    error_message: Optional[str] = None,
    run_id: Optional[int] = None,
) -> None:
    """Sets final indexing status and emits completion, cancellation, or error log."""
    final_status = indexing_state_manager.finalize_run(error_message=error_message, run_id=run_id)
    if final_status == "cancelled":
        print("[Indexer] Background indexing cancelled.", flush=True)
        return
    if final_status == "error":
        safe_run_id = run_id if run_id is not None else 0
        print(f"[Indexer] Background indexing failed [run={safe_run_id}]: {error_message}", flush=True)
        return
    if final_status == "idle":
        print("[Indexer] Background indexing completed.", flush=True)
        print("[Indexer] Sync completed.", flush=True)


async def _wait_if_paused(run_id: Optional[int]) -> bool:
    """Waits while indexing is paused; returns False if the run was cancelled."""
    if indexing_state_manager.is_run_cancelled(run_id):
        return False
    if not indexing_state_manager.pause_event.is_set():
        print("[Indexer] Background indexing waiting for pause release...", flush=True)
    return await indexing_state_manager.wait_if_paused(run_id)


async def _prepare_and_scan_for_run(
    folder_paths: list[str], active_run_id: int
) -> Optional[list[str]]:
    """Waits for pause release, scans folders, and runs zombie cleanup before indexing."""
    if not await _wait_if_paused(active_run_id):
        return None
    files = await asyncio.to_thread(scan_directory, folder_paths)
    total_files = len(files)
    indexing_state_manager.update_progress(0, total_files, "", run_id=active_run_id)
    print(f"[Indexer] Starting background indexing. Found {total_files} files.", flush=True)

    if not await _wait_if_paused(active_run_id):
        return None
    await asyncio.to_thread(cleanup_zombie_records)
    if not files:
        print("[Indexer] No files found for indexing.", flush=True)
        return None
    return files


async def _execute_indexing_chunks(files: list[str], active_run_id: int) -> None:
    """Executes chunked concurrent file indexing with pause checks between chunks."""
    semaphore = asyncio.Semaphore(4)
    counter = [0]
    chunk_size = 100
    total_files = len(files)
    for start_idx in range(0, total_files, chunk_size):
        if not await _wait_if_paused(active_run_id):
            break
        chunk_files = files[start_idx : start_idx + chunk_size]
        await _process_indexing_chunk(chunk_files, semaphore, total_files, counter, active_run_id)
        await asyncio.sleep(0.01)


async def run_indexing_background(folder_paths: list[str], run_id: Optional[int] = None) -> None:
    """Main background scheduler executing the indexing lifecycle without blocking the event loop."""
    active_run_id = indexing_state_manager.initialize_background_run(run_id=run_id)
    if active_run_id is None:
        logger.info("[Indexer] Skipping cancelled or superseded background run (run_id=%s).", run_id)
        return

    error_message: Optional[str] = None
    try:
        files = await _prepare_and_scan_for_run(folder_paths, active_run_id)
        if files:
            await _execute_indexing_chunks(files, active_run_id)
    except Exception as exc:
        error_message = _normalize_indexing_error(exc)
        logger.error("[Indexer] Background task error: %s", error_message, exc_info=True)
        print(f"[Indexer] Background task error: {error_message}", flush=True)
    except BaseException as exc:
        error_message = _normalize_indexing_error(exc)
        logger.error("[Indexer] Background task interrupted: %s", error_message)
        raise
    finally:
        _finalize_indexing_status(error_message=error_message, run_id=active_run_id)


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "indexing_state_manager",
    "pause_indexing",
    "resume_indexing",
    "cancel_indexing",
    "get_siglip_adapter",
    "get_gemma_adapter",
    "calculate_sha256",
    "scan_directory",
    "delete_photo_atomic_sync",
    "cleanup_zombie_records",
    "FolderNotRegisteredError",
    "FolderDeletionConflictError",
    "remove_folder_data",
    "run_ai_pipeline_sync",
    "index_single_file_sync",
    "reindex_single_photo_inplace",
    "run_indexing_background",
]
