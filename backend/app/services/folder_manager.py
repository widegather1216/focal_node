"""
Folder Manager Service Module

Handles path/Unicode normalization, zombie record garbage collection,
atomic photo deletion, and registered folder validation and removal.
"""

import logging
import os
import unicodedata
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Image as DBImage, IndexedFolder
from repositories.atomic_transaction import CompensatingTransactionManager
from repositories.vector_repository import VectorRepository
from services.indexing_state import indexing_state_manager
from services.photo import get_thumbnail_path

logger = logging.getLogger("focal_node.folder_manager")
_default_vector_repo = VectorRepository()


class FolderNotRegisteredError(ValueError):
    """Raised when attempting to remove a folder not registered in IndexedFolder."""


class FolderDeletionConflictError(RuntimeError):
    """Raised when folder deletion conflicts with an active indexing run."""


def remove_cached_thumbnail(
    image_id: str,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
) -> None:
    """Removes a cached JPEG thumbnail from disk if it exists."""
    thumbnail_path = thumbnail_path_fn(image_id)
    if not os.path.exists(thumbnail_path):
        return
    try:
        os.remove(thumbnail_path)
    except FileNotFoundError:
        logger.debug("Thumbnail cache file %s already removed", thumbnail_path)
    except OSError as os_err:
        logger.warning("Failed to remove thumbnail cache %s: %s", thumbnail_path, os_err)


def purge_photo_records_batch(
    db: Session,
    photo_ids: List[str],
    vector_repository: Optional[VectorRepository] = None,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
) -> None:
    """Deletes SQLite rows, disk thumbnails, and ChromaDB embeddings (before SQLite commit)."""
    if not photo_ids:
        return
    active_vector_repo = vector_repository or _default_vector_repo
    for offset in range(0, len(photo_ids), 900):
        id_chunk = photo_ids[offset : offset + 900]
        db.query(DBImage).filter(DBImage.id.in_(id_chunk)).delete(synchronize_session=False)
        for photo_id in id_chunk:
            remove_cached_thumbnail(photo_id, thumbnail_path_fn=thumbnail_path_fn)
    active_vector_repo.delete(photo_ids)


def delete_photo_atomic_sync(
    db: Session,
    image_id: str,
    vector_repository: Optional[VectorRepository] = None,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
) -> None:
    """Atomically deletes a photo from SQLite + ChromaDB and purges its cached thumbnail."""
    active_vector_repo = vector_repository or _default_vector_repo
    db_image = db.query(DBImage).filter(DBImage.id == image_id).first()
    if db_image:
        db.delete(db_image)

    tx_manager = CompensatingTransactionManager(db, active_vector_repo)
    tx_manager.delete_and_commit([image_id])
    remove_cached_thumbnail(image_id, thumbnail_path_fn=thumbnail_path_fn)


def normalize_path_for_comparison(path: str) -> str:
    """Resolves symlinks and normalizes Unicode (NFC) and case for path comparisons."""
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        resolved_path = os.path.realpath(path)
    except Exception as path_err:
        logger.debug("realpath failed for %s; falling back to normpath: %s", path, path_err)
        resolved_path = os.path.normpath(path)
    # macOS APFS stores filenames in NFD while UI/Tauri passes NFC strings; unify to NFC before comparing.
    return unicodedata.normalize("NFC", resolved_path).lower()


def to_folder_prefix_pair(folder_path: str) -> Optional[tuple[str, str]]:
    """Builds a normalized (root_path, prefix_with_sep) pair for folder boundary checks."""
    normalized_root = normalize_path_for_comparison(folder_path)
    if not normalized_root:
        return None
    folder_prefix = normalized_root if normalized_root.endswith(os.sep) else normalized_root + os.sep
    return normalized_root, folder_prefix


def belongs_to_any_folder(
    file_path: str,
    parent_dir: str,
    canonical_prefixes: list[tuple[str, str]],
) -> bool:
    """Returns True when the file or parent directory resides under any indexed folder."""
    if not canonical_prefixes:
        return False
    normalized_parent = normalize_path_for_comparison(parent_dir)
    normalized_file = normalize_path_for_comparison(file_path)
    for folder_root, folder_prefix in canonical_prefixes:
        if (
            normalized_parent == folder_root
            or normalized_parent.startswith(folder_prefix)
            or normalized_file.startswith(folder_prefix)
        ):
            return True
    return False


def identify_zombie_photo_ids(db: Session, normalized_folder_prefixes: list) -> List[str]:
    """Identifies photo IDs missing on disk or no longer belonging to any indexed folder."""
    canonical_prefixes = [
        pair
        for folder_root, _ in normalized_folder_prefixes
        if (pair := to_folder_prefix_pair(folder_root)) is not None
    ]
    all_images = db.query(DBImage.id, DBImage.file_path, DBImage.parent_dir).all()
    zombie_ids: List[str] = []
    for image_id, file_path, parent_dir in all_images:
        if not file_path or not os.path.exists(file_path):
            zombie_ids.append(image_id)
            continue
        if not belongs_to_any_folder(file_path, parent_dir, canonical_prefixes):
            zombie_ids.append(image_id)
    return zombie_ids


def cleanup_zombie_records(
    db: Session = None,
    session_factory: Callable[[], Session] = SessionLocal,
    vector_repository: Optional[VectorRepository] = None,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
) -> None:
    """Garbage-collects SQLite, ChromaDB, and thumbnails for missing or unindexed photos."""
    close_db = db is None
    active_db = session_factory() if close_db else db
    try:
        indexed_folders = active_db.query(IndexedFolder.path).all()
        folder_prefixes = [
            pair
            for folder_record in indexed_folders
            if (pair := to_folder_prefix_pair(folder_record.path)) is not None
        ]
        zombie_ids = identify_zombie_photo_ids(active_db, folder_prefixes)
        if zombie_ids:
            print(f"[Indexer] Found {len(zombie_ids)} unindexed/zombie records in SQLite. Cleaning up...", flush=True)
            purge_photo_records_batch(
                active_db, zombie_ids, vector_repository=vector_repository, thumbnail_path_fn=thumbnail_path_fn
            )
            active_db.commit()
        else:
            print("[Indexer] No SQLite zombie/unindexed records found.", flush=True)
        print("[Indexer] Zombie cleanup completed.", flush=True)
    finally:
        if close_db:
            active_db.close()


def resolve_path_without_leaf_symlink(path: str) -> str:
    """Normalizes path and resolves parent symlinks without expanding a leaf symlink."""
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith("//"):
        normalized_path = "/" + normalized_path.lstrip("/")
    if normalized_path == os.sep:
        return os.sep
    if os.path.islink(normalized_path):
        resolved_parent = os.path.realpath(os.path.dirname(normalized_path))
        return os.path.join(resolved_parent, os.path.basename(normalized_path))
    return os.path.realpath(normalized_path)


def normalize_folder_deletion_path(path: str) -> str:
    """Normalizes a path for folder deletion without expanding leaf symlinks."""
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        resolved_path = resolve_path_without_leaf_symlink(path)
    except Exception as path_err:
        logger.debug("Safe path resolution failed for %s; falling back to normpath: %s", path, path_err)
        resolved_path = os.path.normpath(path)
    return unicodedata.normalize("NFC", resolved_path).lower()


def validate_folder_deletion_pair(folder_path: str) -> tuple[str, str]:
    """Validates folder_path is a non-empty absolute path and returns its canonical (root, prefix)."""
    if not isinstance(folder_path, str) or not folder_path.strip() or "\x00" in folder_path:
        raise ValueError("Folder path must be a non-empty valid path.")
    if not os.path.isabs(folder_path):
        raise ValueError(f"Folder path must be an absolute path: {folder_path}")
    normalized_root = normalize_folder_deletion_path(folder_path)
    if not normalized_root:
        raise ValueError(f"Invalid folder path: {folder_path}")
    folder_prefix = normalized_root if normalized_root.endswith(os.sep) else normalized_root + os.sep
    return normalized_root, folder_prefix


def is_target_or_nested_folder(
    candidate_path: str,
    normalized_target: str,
    target_prefix: str,
) -> bool:
    """Returns True if candidate_path equals normalized_target or is nested beneath target_prefix."""
    normalized_candidate = normalize_folder_deletion_path(candidate_path)
    if not normalized_candidate:
        return False
    return normalized_candidate == normalized_target or normalized_candidate.startswith(target_prefix)


def find_matching_indexed_folders(
    db: Session,
    normalized_target: str,
    target_prefix: str,
    original_path: str,
) -> list[IndexedFolder]:
    """Requires an exact canonical IndexedFolder match, then returns it with nested subfolders."""
    all_indexed = db.query(IndexedFolder).all()
    exact_matches = [
        folder_record
        for folder_record in all_indexed
        if normalize_folder_deletion_path(folder_record.path) == normalized_target
    ]
    if not exact_matches:
        raise FolderNotRegisteredError(f"Folder is not registered: {original_path}")

    return [
        folder_record
        for folder_record in all_indexed
        if is_target_or_nested_folder(folder_record.path, normalized_target, target_prefix)
    ]


def belongs_to_deletion_target(
    file_path: str,
    parent_dir: str,
    target_pair: tuple[str, str],
) -> bool:
    """Checks if an image record belongs to target_pair without following leaf symlinks."""
    target_root, target_prefix = target_pair
    normalized_parent = normalize_folder_deletion_path(parent_dir)
    if normalized_parent == target_root or normalized_parent.startswith(target_prefix):
        return True
    if not isinstance(file_path, str) or not file_path.strip():
        return False
    file_dir_norm = normalize_folder_deletion_path(os.path.dirname(file_path))
    return file_dir_norm == target_root or file_dir_norm.startswith(target_prefix)


def find_folder_image_ids(db: Session, target_pair: tuple[str, str]) -> list[str]:
    """Collects unique IDs of images belonging to the deleted folder target."""
    all_images = db.query(DBImage.id, DBImage.file_path, DBImage.parent_dir).all()
    matched_ids: list[str] = []
    seen_ids: set[str] = set()
    for image_id, file_path, parent_dir in all_images:
        if image_id in seen_ids:
            continue
        if belongs_to_deletion_target(file_path, parent_dir, target_pair):
            seen_ids.add(image_id)
            matched_ids.append(image_id)
    return matched_ids


def execute_folder_deletion(
    active_db: Session,
    folder_path: str,
    target_pair: tuple[str, str],
    vector_repository: Optional[VectorRepository] = None,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
    state_manager=None,
) -> None:
    """Validates registration and active indexing state, then deletes folder records atomically."""
    normalized_target, target_prefix = target_pair
    folders_to_delete = find_matching_indexed_folders(
        active_db, normalized_target, target_prefix, folder_path
    )
    active_state_manager = state_manager or indexing_state_manager
    if active_state_manager.status in ("processing", "paused"):
        raise FolderDeletionConflictError("Cannot remove folder while indexing is in progress or paused.")

    image_ids = find_folder_image_ids(active_db, target_pair)
    if image_ids:
        print(f"[Indexer] Removing {len(image_ids)} images for folder {folder_path}", flush=True)
        purge_photo_records_batch(
            active_db, image_ids, vector_repository=vector_repository, thumbnail_path_fn=thumbnail_path_fn
        )
    for folder_record in folders_to_delete:
        active_db.delete(folder_record)
    active_db.commit()


def remove_folder_data(
    folder_path: str,
    db: Session = None,
    session_factory: Callable[[], Session] = SessionLocal,
    vector_repository: Optional[VectorRepository] = None,
    thumbnail_path_fn: Callable[[str], str] = get_thumbnail_path,
    state_manager=None,
) -> None:
    """Deletes a registered folder (and nested subfolders) plus all associated SQLite/Chroma/thumbnail records."""
    target_pair = validate_folder_deletion_pair(folder_path)
    close_db = db is None
    active_db = session_factory() if close_db else db
    try:
        execute_folder_deletion(
            active_db, folder_path, target_pair,
            vector_repository=vector_repository, thumbnail_path_fn=thumbnail_path_fn, state_manager=state_manager,
        )
    except (FolderNotRegisteredError, FolderDeletionConflictError, ValueError):
        active_db.rollback()
        raise
    except Exception as remove_err:
        active_db.rollback()
        logger.error("[Indexer] Error removing folder data for %s: %s", folder_path, remove_err)
        raise
    finally:
        if close_db:
            active_db.close()
