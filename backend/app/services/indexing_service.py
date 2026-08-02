import os
import hashlib
import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal
from services.photo import register_photo_atomic, generate_and_cache_thumbnail
from utils.image import extract_metadata
from models import Image as DBImage
import time

# Supported file extensions (Standard and RAW formats)
SUPPORTED_EXTENSIONS = {
    # Standard formats
    ".jpg", ".jpeg", ".png", ".webp",
    # RAW formats
    ".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".rw2", ".pef", ".raf"
}

# Thread-safe global status representation of background indexer
indexing_status = {
    "status": "idle",
    "total_files": 0,
    "processed_files": 0,
    "current_file": ""
}

pause_event = asyncio.Event()
pause_event.set()  # set() means running, clear() means paused
cancel_requested = False

def pause_indexing():
    global indexing_status
    if indexing_status["status"] == "processing":
        pause_event.clear()
        indexing_status["status"] = "paused"
        print("[Indexer] Background indexing paused.", flush=True)

def resume_indexing():
    global indexing_status
    if indexing_status["status"] == "paused":
        pause_event.set()
        indexing_status["status"] = "processing"
        print("[Indexer] Background indexing resumed.", flush=True)

def cancel_indexing():
    global indexing_status, cancel_requested
    if indexing_status["status"] in ["processing", "paused"]:
        cancel_requested = True
        pause_event.set()  # Unblock pause wait if currently paused
        indexing_status["status"] = "cancelled"
        print("[Indexer] Background indexing cancelled.", flush=True)

# Singleton adapters initialized on demand
_siglip_adapter = None
_gemma_adapter = None

def get_siglip_adapter():
    from services.ai_factory import get_siglip_adapter as factory_get_siglip
    return factory_get_siglip()

def get_gemma_adapter():
    from services.ai_factory import get_gemma_adapter as factory_get_gemma
    return factory_get_gemma()

def calculate_sha256(file_path: str) -> str:
    """
    Computes SHA-256 checksum of the file in chunks to optimize memory usage.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_directory(folder_paths: list[str]) -> list[str]:
    """
    Recursively scans the targeted folders and extracts supported image files.
    """
    files_to_index = []
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
                    files_to_index.append(os.path.join(root, file))
    return files_to_index

def delete_photo_atomic_sync(db: Session, image_id: str):
    """
    Atomically removes database records of an image from SQLite and ChromaDB.
    Maintains a compensation transaction style for deletion.
    """
    from chroma import get_chroma_collection
    
    # 1. Fetch from SQLite
    db_image = db.query(DBImage).filter(DBImage.id == image_id).first()
    if db_image:
        db.delete(db_image)
        
    # 2. Commit SQLite deletion
    db.commit()
    
    # 3. Delete from ChromaDB
    try:
        collection = get_chroma_collection()
        collection.delete(ids=[image_id])
    except Exception as chroma_err:
        print(f"[Compensating Tx Error] Failed to delete embedding from ChromaDB: {chroma_err}", flush=True)

def run_ai_pipeline_sync(file_path: str) -> tuple[dict, list[float], dict]:
    """
    Synchronous helper to run EXIF extraction, embedding generation, and caption generation sequentially.
    Returns: (metadata, embedding, ai_result)
    """
    metadata = extract_metadata(file_path)
    siglip_adapter = get_siglip_adapter()
    embedding = siglip_adapter.get_image_embedding(file_path)
    siglip_hints = siglip_adapter.get_zero_shot_hints(embedding)
    ai_result = get_gemma_adapter().generate_caption_and_tags(file_path, metadata, siglip_hints=siglip_hints)
    return metadata, embedding, ai_result


def index_single_file_sync(file_path: str) -> dict | str:
    """
    Performs hashing, EXIF extraction, thumbnail generation, embedding inference,
    caption inference, and atomic registration via IndexingPipeline.
    """
    file_size = os.path.getsize(file_path)
    file_mtime = os.path.getmtime(file_path)
    
    db: Session = SessionLocal()
    image_id_to_delete = None
    try:
        # 1. Incremental indexing check by file path
        existing_by_path = db.query(DBImage).filter(DBImage.file_path == file_path).first()
        if existing_by_path:
            if existing_by_path.file_mtime == file_mtime and existing_by_path.file_size == file_size:
                return "skipped"
            else:
                print(f"[Indexer] File modified. Marking for re-indexing: {file_path}", flush=True)
                image_id_to_delete = existing_by_path.id

        # 2. Calculate SHA-256 hash (primary key)
        image_id = calculate_sha256(file_path)
        
        # Check if the hash is already indexed under a different path (de-duplication)
        existing_by_id = db.query(DBImage).filter(DBImage.id == image_id).first()
        if existing_by_id:
            print(f"[Indexer] Hash duplicate found. Skipping: {file_path}", flush=True)
            return "skipped_duplicate_hash"
    finally:
        db.close()

    try:
        from services.pipeline import IndexingPipeline
        pipeline = IndexingPipeline()
        res = pipeline.run(file_path)
        if isinstance(res, str):
            return res
            
        # Delete old record ONLY IF new inference succeeded
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

async def reindex_single_photo_inplace(photo_id: str) -> dict:
    """
    Re-runs metadata, embedding, and caption inference for an existing photo,
    updating the database in-place without deleting the core Image record.
    """
    from models import ImageMetadata as DBImageMetadata, AIAnalysis as DBAIAnalysis
    import json
    from services.photo import _prepare_chroma_metadata
    from chroma import get_chroma_collection
    
    db: Session = SessionLocal()
    try:
        db_img = db.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
            raise ValueError(f"Photo ID {photo_id} not found in database.")
            
        file_path = db_img.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} no longer exists.")
    finally:
        db.close()
            
    # 1 & 2. Run AI pipeline sequentially inside a single background thread
    metadata, embedding, ai_result = await asyncio.to_thread(run_ai_pipeline_sync, file_path)
    
    db = SessionLocal()
    try:
        # Re-fetch image to return it later and verify it wasn't deleted
        db_img = db.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
             raise ValueError(f"Photo ID {photo_id} was deleted during re-indexing.")
             
        # 3. Update SQLite
        db_meta = db.query(DBImageMetadata).filter(DBImageMetadata.image_id == photo_id).first()
        if not db_meta:
            db_meta = DBImageMetadata(image_id=photo_id)
            db.add(db_meta)
        
        db_meta.width = metadata.get("width")
        db_meta.height = metadata.get("height")
        db_meta.color_space = metadata.get("color_space")
        db_meta.camera_model = metadata.get("camera_model")
        db_meta.lens_model = metadata.get("lens_model")
        db_meta.f_number = metadata.get("f_number")
        db_meta.focal_length = metadata.get("focal_length")
        db_meta.focal_length_35mm = metadata.get("focal_length_35mm")
        db_meta.crop_factor = metadata.get("crop_factor")
        db_meta.sensor_format = metadata.get("sensor_format")
        db_meta.shutter_speed = metadata.get("shutter_speed")
        db_meta.iso = metadata.get("iso")
        db_meta.capture_date = metadata.get("capture_date")
        
        db_ai = db.query(DBAIAnalysis).filter(DBAIAnalysis.image_id == photo_id).first()
        if not db_ai:
            db_ai = DBAIAnalysis(image_id=photo_id)
            db.add(db_ai)
            
        db_ai.caption = ai_result.get("caption", "")
        db_ai.tags = json.dumps(ai_result.get("tags", []))
        db_ai.aesthetic_tags = json.dumps(ai_result.get("aesthetic_tags", []))
        db_ai.is_user_edited = False
        
        # 4. Update Chroma
        collection = await asyncio.to_thread(get_chroma_collection)
        chroma_meta = _prepare_chroma_metadata(metadata)
        
        await asyncio.to_thread(
            collection.update,
            ids=[photo_id],
            embeddings=[embedding],
            metadatas=[chroma_meta]
        )
        
        db.commit()
        db.refresh(db_img)
        
        return db_img.to_detail_dict()
    except Exception as e:
        db.rollback()
        print(f"[Indexer] Re-index failed for {photo_id}: {e}", flush=True)
        raise e
    finally:
        db.close()

def cleanup_zombie_records(db: Session = None):
    """
    Checks all indexed images and batch deletes records if:
    1) Their physical files are missing from disk.
    2) Their parent folder is no longer in IndexedFolder list.
    Also acts as a Garbage Collector for ChromaDB and Thumbnail Cache.
    """
    from chroma import get_chroma_collection
    from models import IndexedFolder
    from services.photo import get_thumbnail_path
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        # Get all registered indexed folders
        indexed_folders = db.query(IndexedFolder.path).all()
        folder_paths = [f.path for f in indexed_folders]
        
        # Helper to check if file belongs to any registered folder
        def belongs_to_any_folder(file_path: str, parent_dir: str) -> bool:
            if not folder_paths:
                return False
            try:
                real_parent = os.path.realpath(parent_dir).lower()
                real_file = os.path.realpath(file_path).lower()
            except Exception:
                real_parent = os.path.normpath(parent_dir).lower()
                real_file = os.path.normpath(file_path).lower()

            for f_path in folder_paths:
                try:
                    real_f = os.path.realpath(f_path).lower()
                except Exception:
                    real_f = os.path.normpath(f_path).lower()
                f_prefix = real_f if real_f.endswith(os.sep) else real_f + os.sep
                if real_parent == real_f or real_parent.startswith(f_prefix) or real_file.startswith(f_prefix):
                    return True
            return False

        all_images = db.query(DBImage.id, DBImage.file_path, DBImage.parent_dir).all()
        sqlite_ids = set()
        zombie_ids = []
        
        for img_id, file_path, parent_dir in all_images:
            # Delete if file physically removed OR parent folder is no longer indexed
            if not os.path.exists(file_path) or not belongs_to_any_folder(file_path, parent_dir):
                zombie_ids.append(img_id)
            else:
                sqlite_ids.add(img_id)
                
        # 1. SQLite Zombie Cleanup
        if zombie_ids:
            print(f"[Indexer] Found {len(zombie_ids)} unindexed/zombie records in SQLite. Cleaning up...", flush=True)
            for i in range(0, len(zombie_ids), 900):
                chunk = zombie_ids[i:i+900]
                db.query(DBImage).filter(DBImage.id.in_(chunk)).delete(synchronize_session=False)
                for zid in chunk:
                    t_path = get_thumbnail_path(zid)
                    if os.path.exists(t_path):
                        try:
                            os.remove(t_path)
                        except Exception:
                            pass
            db.commit()
        else:
            print("[Indexer] No SQLite zombie/unindexed records found.", flush=True)

        # 2. ChromaDB Garbage Collection
        try:
            collection = get_chroma_collection()
            chroma_data = collection.get(include=[])
            if chroma_data and chroma_data.get('ids'):
                chroma_ids = set(chroma_data['ids'])
                orphaned_ids = list(chroma_ids - sqlite_ids)
                
                if orphaned_ids:
                    print(f"[Indexer] Found {len(orphaned_ids)} orphaned embeddings in ChromaDB. Cleaning up...", flush=True)
                    for i in range(0, len(orphaned_ids), 900):
                        chunk = orphaned_ids[i:i+900]
                        collection.delete(ids=chunk)
                else:
                    print("[Indexer] No ChromaDB garbage vectors found.", flush=True)
        except Exception as chroma_err:
            print(f"[Compensating Tx Error] Failed to access/clean ChromaDB: {chroma_err}", flush=True)
            
        print("[Indexer] Zombie cleanup completed.", flush=True)
    finally:
        if close_db:
            db.close()

def remove_folder_data(folder_path: str):
    """
    Deletes a folder from IndexedFolder and removes all associated photos
    from SQLite, ChromaDB, and Thumbnail cache using robust realpath & case-insensitive matching.
    """
    from chroma import get_chroma_collection
    from models import IndexedFolder
    from services.photo import get_thumbnail_path
    from sqlalchemy import or_, func
    
    db = SessionLocal()
    try:
        real_target = os.path.realpath(folder_path)
        search_prefix = real_target if real_target.endswith(os.sep) else real_target + os.sep
        path_without_sep = real_target.rstrip(os.sep)
        
        target_lower = real_target.lower()
        prefix_lower = search_prefix.lower()
        without_sep_lower = path_without_sep.lower()
        orig_lower = folder_path.lower()
        orig_prefix_lower = (folder_path if folder_path.endswith(os.sep) else folder_path + os.sep).lower()

        # Find all images under this folder or with matching parent_dir (case-insensitive & realpath aware)
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
            # 1. Delete from SQLite and remove thumbnail cache files
            for i in range(0, len(image_ids), 900):
                chunk = image_ids[i:i+900]
                db.query(DBImage).filter(DBImage.id.in_(chunk)).delete(synchronize_session=False)
                for img_id in chunk:
                    t_path = get_thumbnail_path(img_id)
                    if os.path.exists(t_path):
                        try:
                            os.remove(t_path)
                        except Exception:
                            pass

        # 2. Remove from IndexedFolder matching any case/realpath variant
        all_indexed = db.query(IndexedFolder).all()
        for f_rec in all_indexed:
            f_real = os.path.realpath(f_rec.path).lower()
            if f_real in [target_lower, without_sep_lower, orig_lower] or f_rec.path.lower() in [target_lower, without_sep_lower, orig_lower]:
                db.delete(f_rec)

        # 3. Commit SQLite Transaction
        db.commit()
        
        # 4. Delete from ChromaDB AFTER successful commit
        if image_ids:
            try:
                collection = get_chroma_collection()
                for i in range(0, len(image_ids), 900):
                    chunk = image_ids[i:i+900]
                    collection.delete(ids=chunk)
            except Exception as chroma_err:
                print(f"[Compensating Tx] Failed to delete some vectors from ChromaDB: {chroma_err}", flush=True)
    except Exception as e:
        db.rollback()
        print(f"[Indexer] Error removing folder data: {e}", flush=True)
    finally:
        db.close()

async def run_indexing_background(folder_paths: list[str]):
    """
    Main background scheduler executing the indexing lifecycle without blocking the main event loop.
    Supports non-blocking pause, resume, and cancel control.
    """
    global indexing_status, cancel_requested
    cancel_requested = False
    pause_event.set()
    indexing_status["status"] = "processing"
    indexing_status["processed_files"] = 0
    indexing_status["total_files"] = 0
    indexing_status["current_file"] = ""
    
    try:
        # Scan folders in non-blocking thread
        files = await asyncio.to_thread(scan_directory, folder_paths)
        indexing_status["total_files"] = len(files)
        print(f"[Indexer] Starting background indexing. Found {len(files)} files.", flush=True)
        
        # Cleanup zombie records before indexing
        await asyncio.to_thread(cleanup_zombie_records)
        
        if not files:
            indexing_status["status"] = "idle"
            indexing_status["processed_files"] = 0
            indexing_status["total_files"] = 0
            print("[Indexer] Background indexing completed.", flush=True)
            print("[Indexer] Sync completed.", flush=True)
            return
            
        semaphore = asyncio.Semaphore(4)
        
        async def process_file(f_path):
            if cancel_requested:
                return "cancelled"
            async with semaphore:
                if cancel_requested:
                    return "cancelled"
                if not pause_event.is_set():
                    await pause_event.wait()
                if cancel_requested:
                    return "cancelled"

                indexing_status["current_file"] = f_path
                res = await asyncio.to_thread(index_single_file_sync, f_path)
                indexing_status["processed_files"] += 1
                if isinstance(res, dict):
                    status_str = "Indexed with AI"
                elif res == "skipped_duplicate_hash":
                    status_str = "Skipped (Duplicate Hash)"
                elif res == "skipped":
                    status_str = "Skipped (Already Indexed)"
                else:
                    status_str = f"Status: {res}"
                    
                if indexing_status["processed_files"] % 1 == 0 or indexing_status["processed_files"] == indexing_status["total_files"]:
                    print(f"[Indexing] Progress: {indexing_status['processed_files']}/{indexing_status['total_files']} - {f_path} ({status_str})", flush=True)
                return res

        chunk_size = 100
        for i in range(0, len(files), chunk_size):
            if cancel_requested:
                break

            if not pause_event.is_set():
                print("[Indexer] Background indexing waiting for pause release...", flush=True)
                await pause_event.wait()
                if cancel_requested:
                    break

            chunk_files = files[i:i+chunk_size]
            tasks = [asyncio.create_task(process_file(f)) for f in chunk_files]
            results = await asyncio.gather(*tasks)
            
            raw_batch_data = [res for res in results if isinstance(res, dict)]
            
            if raw_batch_data:
                # Deduplicate within the batch to prevent SQLite IntegrityError
                batch_data = []
                seen_ids = set()
                for item in raw_batch_data:
                    img_id = item["image_data"]["id"]
                    if img_id not in seen_ids:
                        seen_ids.add(img_id)
                        batch_data.append(item)
                    else:
                        print(f"[Indexer] In-batch duplicate found. Skipping: {item['image_data']['file_path']}", flush=True)

                def _save_batch():
                    db_batch = SessionLocal()
                    try:
                        from services.photo import register_photos_batch_atomic
                        register_photos_batch_atomic(db_batch, batch_data)
                    except Exception as e:
                        import traceback
                        print(f"[Indexer] Batch DB Upsert Failed for {len(batch_data)} items: {e}", flush=True)
                        traceback.print_exc()
                    finally:
                        db_batch.close()
                await asyncio.to_thread(_save_batch)
            
            await asyncio.sleep(0.01)
            
        if cancel_requested:
            indexing_status["status"] = "cancelled"
            print("[Indexer] Background indexing cancelled.", flush=True)
        else:
            indexing_status["status"] = "idle"
            print("[Indexer] Background indexing completed.", flush=True)
            print("[Indexer] Sync completed.", flush=True)
    except Exception as e:
        print(f"[Indexer] Background task error: {e}", flush=True)
        indexing_status["status"] = "error"
