import os
import asyncio
from typing import Tuple, Dict, Any, Union
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Image as DBImage, ImageMetadata as DBImageMetadata, AIAnalysis as DBAIAnalysis
from services.ai_factory import get_siglip_adapter, get_gemma_adapter
from utils.image import extract_metadata
from repositories.vector_repository import VectorRepository
from services.indexer.scanner import calculate_sha256, scan_directory
from services.indexer.status import indexing_status, pause_event
from services.indexer.cleaner import delete_photo_atomic_sync, cleanup_zombie_records

vector_repo = VectorRepository()

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
            if existing_by_path.file_mtime == file_mtime and existing_by_path.file_size == file_size:
                return "skipped"
            else:
                print(f"[Indexer] File modified. Marking for re-indexing: {file_path}", flush=True)
                image_id_to_delete = existing_by_path.id

        image_id = calculate_sha256(file_path)
        
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
    import json
    from services.photo import _prepare_chroma_metadata
    
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
            
    metadata, embedding, ai_result = await asyncio.to_thread(run_ai_pipeline_sync, file_path)
    
    db = SessionLocal()
    try:
        db_img = db.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
             raise ValueError(f"Photo ID {photo_id} was deleted during re-indexing.")
             
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
        
        chroma_meta = _prepare_chroma_metadata(metadata)
        
        await asyncio.to_thread(
            vector_repo.upsert,
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

async def run_indexing_background(folder_paths: list[str]):
    """
    Main background scheduler executing the indexing lifecycle without blocking the main event loop.
    """
    from services.indexer.status import cancel_requested, pause_event
    import services.indexer.status as status_module

    status_module.cancel_requested = False
    pause_event.set()
    indexing_status["status"] = "processing"
    indexing_status["processed_files"] = 0
    indexing_status["total_files"] = 0
    indexing_status["current_file"] = ""
    
    try:
        files = await asyncio.to_thread(scan_directory, folder_paths)
        indexing_status["total_files"] = len(files)
        print(f"[Indexer] Starting background indexing. Found {len(files)} files.", flush=True)
        
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
            if status_module.cancel_requested:
                return "cancelled"
            async with semaphore:
                if status_module.cancel_requested:
                    return "cancelled"
                if not pause_event.is_set():
                    await pause_event.wait()
                if status_module.cancel_requested:
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
            if status_module.cancel_requested:
                break

            if not pause_event.is_set():
                print("[Indexer] Background indexing waiting for pause release...", flush=True)
                await pause_event.wait()
                if status_module.cancel_requested:
                    break

            chunk_files = files[i:i+chunk_size]
            tasks = [asyncio.create_task(process_file(f)) for f in chunk_files]
            results = await asyncio.gather(*tasks)
            
            raw_batch_data = [res for res in results if isinstance(res, dict)]
            
            if raw_batch_data:
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
            
        if status_module.cancel_requested:
            indexing_status["status"] = "cancelled"
            print("[Indexer] Background indexing cancelled.", flush=True)
        else:
            indexing_status["status"] = "idle"
            print("[Indexer] Background indexing completed.", flush=True)
            print("[Indexer] Sync completed.", flush=True)
    except Exception as e:
        print(f"[Indexer] Background task error: {e}", flush=True)
        indexing_status["status"] = "error"
