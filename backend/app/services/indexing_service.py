"""
Indexing Service Module

Consolidates directory scanning, indexer status state management, 
atomic cleaning routines, and background photo indexing pipelines.
"""

import os
import hashlib
import asyncio
from typing import List, Tuple, Dict, Any, Union, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database import SessionLocal
from models import Image as DBImage, ImageMetadata as DBImageMetadata, AIAnalysis as DBAIAnalysis, IndexedFolder
from repositories.vector_repository import VectorRepository
from services.ai_factory import get_siglip_adapter, get_gemma_adapter
from services.photo import get_thumbnail_path, _prepare_chroma_metadata
from utils.image import extract_metadata

# Supported file extensions (Standard and RAW formats)
SUPPORTED_EXTENSIONS = {
    # Standard formats
    ".jpg", ".jpeg", ".png", ".webp",
    # RAW formats
    ".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".rw2", ".pef", ".raf"
}

vector_repo = VectorRepository()

from services.indexing_state import indexing_state_manager

def pause_indexing():
    indexing_state_manager.pause()

def resume_indexing():
    indexing_state_manager.resume()

def cancel_indexing():
    indexing_state_manager.cancel()


# --- File Scanner Helpers ---
def calculate_sha256(file_path: str) -> str:
    """
    Computes SHA-256 checksum of the file in chunks to optimize memory usage.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(folder_paths: List[str]) -> List[str]:
    """
    Recursively scans targeted folders and extracts supported image file paths.
    Avoids duplicates from overlapping folders or symlinks.
    """
    files_to_index = []
    seen = set()
    for folder in folder_paths:
        if not os.path.exists(folder):
            print(f"[Indexer] Target folder does not exist: {folder}", flush=True)
            continue
        for root, _, files in os.walk(folder):
            for file in files:
                if file.startswith(".") or file.startswith("._"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    if full_path not in seen:
                        seen.add(full_path)
                        files_to_index.append(full_path)
    return files_to_index


# --- Database & Cache Cleanup Routines ---
def delete_photo_atomic_sync(db: Session, image_id: str):
    """
    Atomically removes database records of an image from SQLite and ChromaDB,
    and purges its cached thumbnail from disk.
    Uses CompensatingTransactionManager to ensure atomic multi-database consistency.
    """
    from repositories.atomic_transaction import CompensatingTransactionManager
    
    db_image = db.query(DBImage).filter(DBImage.id == image_id).first()
    if db_image:
        db.delete(db_image)
        
    tx_manager = CompensatingTransactionManager(db, vector_repo)
    tx_manager.delete_and_commit([image_id])
    
    # Clean up cached thumbnail
    t_path = get_thumbnail_path(image_id)
    if os.path.exists(t_path):
        try:
            os.remove(t_path)
        except Exception:
            pass


def _purge_photo_records_batch(db: Session, photo_ids: List[str]) -> None:
    """
    Deletes photo records from SQLite and ChromaDB, and removes cached thumbnails.
    Enforces ChromaDB deletion before SQLite commit (Rule 2.2).
    """
    if not photo_ids:
        return
    for i in range(0, len(photo_ids), 900):
        chunk = photo_ids[i : i + 900]
        db.query(DBImage).filter(DBImage.id.in_(chunk)).delete(synchronize_session=False)
        for pid in chunk:
            t_path = get_thumbnail_path(pid)
            if os.path.exists(t_path):
                try:
                    os.remove(t_path)
                except Exception:
                    pass
    vector_repo.delete(photo_ids)


def _identify_zombie_photo_ids(db: Session, normalized_folder_prefixes: list) -> List[str]:
    def belongs_to_any_folder(file_path: str, parent_dir: str) -> bool:
        if not normalized_folder_prefixes:
            return False
        try:
            real_parent = os.path.realpath(parent_dir).lower()
            real_file = os.path.realpath(file_path).lower()
        except Exception:
            real_parent = os.path.normpath(parent_dir).lower()
            real_file = os.path.normpath(file_path).lower()

        for real_f, f_prefix in normalized_folder_prefixes:
            if real_parent == real_f or real_parent.startswith(f_prefix) or real_file.startswith(f_prefix):
                return True
        return False

    all_images = db.query(DBImage.id, DBImage.file_path, DBImage.parent_dir).all()
    zombie_ids = []
    for img_id, file_path, parent_dir in all_images:
        if not os.path.exists(file_path) or not belongs_to_any_folder(file_path, parent_dir):
            zombie_ids.append(img_id)
    return zombie_ids


def cleanup_zombie_records(db: Session = None):
    """
    Checks all indexed images and batch deletes records if:
    1) Their physical files are missing from disk.
    2) Their parent folder is no longer in IndexedFolder list.
    Also acts as a Garbage Collector for ChromaDB and Thumbnail Cache.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        indexed_folders = db.query(IndexedFolder.path).all()
        normalized_folder_prefixes = []
        for f in indexed_folders:
            try:
                real_f = os.path.realpath(f.path).lower()
            except Exception:
                real_f = os.path.normpath(f.path).lower()
            f_prefix = real_f if real_f.endswith(os.sep) else real_f + os.sep
            normalized_folder_prefixes.append((real_f, f_prefix))

        zombie_ids = _identify_zombie_photo_ids(db, normalized_folder_prefixes)
        if zombie_ids:
            print(f"[Indexer] Found {len(zombie_ids)} unindexed/zombie records in SQLite. Cleaning up...", flush=True)
            _purge_photo_records_batch(db, zombie_ids)
            db.commit()
        else:
            print("[Indexer] No SQLite zombie/unindexed records found.", flush=True)

        print("[Indexer] Zombie cleanup completed.", flush=True)
    finally:
        if close_db:
            db.close()


def remove_folder_data(folder_path: str, db: Session = None):
    """
    Deletes a folder from IndexedFolder and removes all associated photos
    from SQLite, ChromaDB, and Thumbnail cache.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        real_target = os.path.realpath(folder_path)
        search_prefix = real_target if real_target.endswith(os.sep) else real_target + os.sep
        path_without_sep = real_target.rstrip(os.sep)

        target_lower = real_target.lower()
        prefix_lower = search_prefix.lower()
        without_sep_lower = path_without_sep.lower()
        orig_lower = folder_path.lower()
        orig_prefix_lower = (folder_path if folder_path.endswith(os.sep) else folder_path + os.sep).lower()

        images_to_delete = db.query(DBImage.id).filter(
            or_(
                func.lower(DBImage.parent_dir) == target_lower,
                func.lower(DBImage.parent_dir) == without_sep_lower,
                func.lower(DBImage.parent_dir) == orig_lower,
                func.lower(DBImage.parent_dir).startswith(prefix_lower),
                func.lower(DBImage.parent_dir).startswith(orig_prefix_lower),
                func.lower(DBImage.file_path).startswith(prefix_lower),
                func.lower(DBImage.file_path).startswith(orig_prefix_lower),
                func.lower(DBImage.file_path) == target_lower
            )
        ).all()
        image_ids = list(set(row.id for row in images_to_delete)) if images_to_delete else []

        if image_ids:
            print(f"[Indexer] Removing {len(image_ids)} images for folder {folder_path}", flush=True)
            _purge_photo_records_batch(db, image_ids)

        all_indexed = db.query(IndexedFolder).all()
        for f_rec in all_indexed:
            f_real = os.path.realpath(f_rec.path).lower()
            if (
                f_real in [target_lower, without_sep_lower, orig_lower]
                or f_rec.path.lower() in [target_lower, without_sep_lower, orig_lower]
                or f_real.startswith(prefix_lower)
            ):
                db.delete(f_rec)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Indexer] Error removing folder data: {e}", flush=True)
    finally:
        if close_db:
            db.close()


# --- Indexing Pipeline Workers ---
def run_ai_pipeline_sync(file_path: str) -> Tuple[Dict[str, Any], list[float], Dict[str, Any]]:
    """
    Synchronous helper to run EXIF extraction, embedding generation, and caption generation sequentially.
    """
    metadata = extract_metadata(file_path)
    siglip_adapter = get_siglip_adapter()
    embedding = siglip_adapter.get_image_embedding(file_path)
    siglip_hints = siglip_adapter.get_zero_shot_hints(embedding)
    ai_result = get_gemma_adapter().generate_caption_and_tags(file_path, metadata, siglip_hints=siglip_hints)
    return metadata, embedding, ai_result


def index_single_file_sync(file_path: str) -> Union[dict, str]:
    """
    Performs hashing, EXIF extraction, thumbnail generation, embedding inference,
    caption inference, and atomic registration via IndexingPipeline.
    """
    file_size = os.path.getsize(file_path)
    file_mtime = os.path.getmtime(file_path)
    
    db: Session = SessionLocal()
    image_id_to_delete = None
    try:
        existing_by_path = db.query(DBImage).filter(DBImage.file_path == file_path).first()
        if existing_by_path:
            if abs(existing_by_path.file_mtime - file_mtime) < 0.01 and existing_by_path.file_size == file_size:
                return "skipped"
            else:
                print(f"[Indexer] File modified. Marking for re-indexing: {file_path}", flush=True)
                image_id_to_delete = existing_by_path.id

        image_id = calculate_sha256(file_path)
        
        existing_by_id = db.query(DBImage).filter(DBImage.id == image_id).first()
        if existing_by_id:
            if existing_by_id.file_path == file_path:
                existing_by_id.file_mtime = file_mtime
                existing_by_id.file_size = file_size
                db.commit()
                return "skipped"
            print(f"[Indexer] Hash duplicate found. Skipping: {file_path}", flush=True)
            return "skipped_duplicate_hash"
    finally:
        db.close()

    try:
        from services.pipeline import IndexingPipeline
        pipeline = IndexingPipeline()
        res = pipeline.run(file_path, image_id=image_id)
        if isinstance(res, str):
            return res
            
        if image_id_to_delete:
            db_delete: Session = SessionLocal()
            try:
                delete_photo_atomic_sync(db_delete, image_id_to_delete)
            except Exception as e:
                print(f"[Indexer] Failed to delete old record {image_id_to_delete}: {e}", flush=True)
            finally:
                db_delete.close()
                
        return res
    except Exception as e:
        print(f"[Indexer] Error indexing file {file_path}: {e}", flush=True)
        return "error"


# --- Single Photo Reindexing Helpers ---
def _validate_photo_for_reindex(photo_id: str) -> str:
    """Verifies photo exists in DB and on disk before re-indexing."""
    db = SessionLocal()
    try:
        db_img = db.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
            raise ValueError(f"Photo ID {photo_id} not found in database.")
        file_path = db_img.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} no longer exists.")
        return file_path
    finally:
        db.close()


def _update_orm_photo_models(db: Session, photo_id: str, metadata: dict, ai_result: dict) -> None:
    """Updates ImageMetadata and AIAnalysis ORM entities with newly extracted values."""
    import json
    db_meta = db.query(DBImageMetadata).filter(DBImageMetadata.image_id == photo_id).first()
    if not db_meta:
        db_meta = DBImageMetadata(image_id=photo_id)
        db.add(db_meta)

    for field in [
        "width", "height", "color_space", "camera_model", "lens_model",
        "f_number", "focal_length", "focal_length_35mm", "crop_factor",
        "sensor_format", "shutter_speed", "iso", "capture_date"
    ]:
        setattr(db_meta, field, metadata.get(field))

    db_ai = db.query(DBAIAnalysis).filter(DBAIAnalysis.image_id == photo_id).first()
    if not db_ai:
        db_ai = DBAIAnalysis(image_id=photo_id)
        db.add(db_ai)

    db_ai.caption = ai_result.get("caption", "")
    db_ai.tags = json.dumps(ai_result.get("tags", []))
    db_ai.aesthetic_tags = json.dumps(ai_result.get("aesthetic_tags", []))
    db_ai.is_user_edited = False


def _rollback_chroma_embedding(photo_id: str, old_embedding: Optional[list[float]], chroma_meta: dict, err: Exception) -> None:
    """Restores previous ChromaDB embedding or deletes it if previously absent."""
    try:
        if old_embedding:
            vector_repo.upsert(ids=[photo_id], embeddings=[old_embedding], metadatas=[chroma_meta])
        else:
            vector_repo.delete([photo_id])
        print(f"[CompensatingTx] Successfully reverted ChromaDB after SQLite failure: {err}", flush=True)
    except Exception as comp_err:
        print(f"[CompensatingTx] Failed to execute compensating ChromaDB rollback: {comp_err}", flush=True)


def _commit_reindex_with_compensation(
    photo_id: str,
    metadata: dict,
    embedding: list[float],
    old_embedding: Optional[list[float]],
    db: Session,
    db_img: DBImage
) -> dict:
    """Upserts ChromaDB embedding, commits SQLite, and rolls back ChromaDB if commit fails."""
    chroma_meta = _prepare_chroma_metadata(metadata)
    vector_repo.upsert(
        ids=[photo_id],
        embeddings=[embedding],
        metadatas=[chroma_meta]
    )
    try:
        db.commit()
        db.refresh(db_img)
        return db_img.to_detail_dict()
    except Exception as commit_err:
        db.rollback()
        _rollback_chroma_embedding(photo_id, old_embedding, chroma_meta, commit_err)
        raise commit_err


async def reindex_single_photo_inplace(photo_id: str) -> dict:
    """
    Re-runs metadata, embedding, and caption inference for an existing photo,
    updating the database in-place without deleting the core Image record.
    """
    file_path = await asyncio.to_thread(_validate_photo_for_reindex, photo_id)
    metadata, embedding, ai_result = await asyncio.to_thread(run_ai_pipeline_sync, file_path)
    old_embedding = await asyncio.to_thread(vector_repo.get_embedding_by_id, photo_id)

    def _sync_db_update() -> dict:
        db = SessionLocal()
        try:
            db_img = db.query(DBImage).filter(DBImage.id == photo_id).first()
            if not db_img:
                raise ValueError(f"Photo ID {photo_id} was deleted during re-indexing.")
            _update_orm_photo_models(db, photo_id, metadata, ai_result)
            return _commit_reindex_with_compensation(photo_id, metadata, embedding, old_embedding, db, db_img)
        finally:
            db.close()

    return await asyncio.to_thread(_sync_db_update)


# --- Background Indexing Scheduler Helpers ---
def _deduplicate_batch_items(raw_items: list[dict]) -> list[dict]:
    """Filters duplicate photo records within a single chunk batch."""
    batch_data = []
    seen_ids = set()
    for item in raw_items:
        img_id = item["image_data"]["id"]
        if img_id not in seen_ids:
            seen_ids.add(img_id)
            batch_data.append(item)
        else:
            print(f"[Indexer] In-batch duplicate found. Skipping: {item['image_data']['file_path']}", flush=True)
    return batch_data


def _commit_batch_with_retry(batch_data: list[dict], max_attempts: int = 3) -> None:
    """Saves indexed photos batch to SQLite and ChromaDB with exponential backoff retry."""
    import time
    from services.photo import register_photos_batch_atomic
    for attempt in range(max_attempts):
        db_batch = SessionLocal()
        try:
            register_photos_batch_atomic(db_batch, batch_data)
            return
        except Exception as e:
            print(f"[Indexer] Batch DB Upsert attempt {attempt+1}/{max_attempts} failed for {len(batch_data)} items: {e}", flush=True)
            if attempt < max_attempts - 1:
                time.sleep(0.3 * (attempt + 1))
            else:
                import traceback
                traceback.print_exc()
        finally:
            db_batch.close()


def _log_indexing_progress(f_path: str, res: Any, count: int, total: int) -> None:
    """Formats and prints progress log for indexed file."""
    if isinstance(res, dict):
        status_str = "Indexed with AI"
    elif res == "skipped_duplicate_hash":
        status_str = "Skipped (Duplicate Hash)"
    elif res == "skipped":
        status_str = "Skipped (Already Indexed)"
    else:
        status_str = f"Status: {res}"
    print(f"[Indexing] Progress: {count}/{total} - {f_path} ({status_str})", flush=True)


async def _process_single_indexing_file(
    f_path: str,
    semaphore: asyncio.Semaphore,
    total_files: int,
    counter: list[int]
) -> Any:
    """Handles concurrency, pause/cancel checking, and progress updates for a single file."""
    if indexing_state_manager.cancel_requested:
        return "cancelled"

    async with semaphore:
        if indexing_state_manager.cancel_requested:
            return "cancelled"
        if not indexing_state_manager.pause_event.is_set():
            await indexing_state_manager.pause_event.wait()
        if indexing_state_manager.cancel_requested:
            return "cancelled"

        res = await asyncio.to_thread(index_single_file_sync, f_path)
        counter[0] += 1
        indexing_state_manager.update_progress(counter[0], total_files, f_path)
        _log_indexing_progress(f_path, res, counter[0], total_files)
        return res


def _finalize_indexing_status() -> None:
    """Sets final indexing status and emits completion log."""
    if indexing_state_manager.cancel_requested:
        indexing_state_manager.status = "cancelled"
        print("[Indexer] Background indexing cancelled.", flush=True)
    else:
        indexing_state_manager.status = "idle"
        indexing_state_manager.update_progress(0, 0, "")
        print("[Indexer] Background indexing completed.", flush=True)
        print("[Indexer] Sync completed.", flush=True)


async def run_indexing_background(folder_paths: list[str]):
    """
    Main background scheduler executing the indexing lifecycle without blocking the main event loop.
    Guarantees status reset to idle and completion log emission in all execution branches via finally.
    """
    indexing_state_manager.reset_status()
    indexing_state_manager.status = "processing"

    try:
        files = await asyncio.to_thread(scan_directory, folder_paths)
        total_files = len(files)
        indexing_state_manager.update_progress(0, total_files, "")
        print(f"[Indexer] Starting background indexing. Found {total_files} files.", flush=True)

        await asyncio.to_thread(cleanup_zombie_records)
        if not files:
            print("[Indexer] No files found for indexing.", flush=True)
            return

        semaphore = asyncio.Semaphore(4)
        counter = [0]
        chunk_size = 100

        for i in range(0, len(files), chunk_size):
            if indexing_state_manager.cancel_requested:
                break

            if not indexing_state_manager.pause_event.is_set():
                print("[Indexer] Background indexing waiting for pause release...", flush=True)
                await indexing_state_manager.pause_event.wait()
                if indexing_state_manager.cancel_requested:
                    break

            chunk_files = files[i:i+chunk_size]
            tasks = [_process_single_indexing_file(f, semaphore, total_files, counter) for f in chunk_files]
            results = await asyncio.gather(*tasks)

            raw_batch_data = [res for res in results if isinstance(res, dict)]
            if raw_batch_data:
                batch_data = _deduplicate_batch_items(raw_batch_data)
                await asyncio.to_thread(_commit_batch_with_retry, batch_data)

            await asyncio.sleep(0.01)

    except Exception as e:
        print(f"[Indexer] Background task error: {e}", flush=True)
    finally:
        _finalize_indexing_status()


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
    "remove_folder_data",
    "run_ai_pipeline_sync",
    "index_single_file_sync",
    "reindex_single_photo_inplace",
    "run_indexing_background",
]
