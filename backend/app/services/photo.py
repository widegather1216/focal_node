import os
import io
import json
import uuid
import datetime
import time
from fastapi import HTTPException
from sqlalchemy.orm import Session
from PIL import Image
from models import Image as DBImage, ImageMetadata as DBImageMetadata, AIAnalysis as DBAIAnalysis
from utils.image import is_raw_image, decode_raw_to_pil
from chroma import get_chroma_collection

from config import THUMBNAILS_DIR

THUMBNAIL_CACHE_DIR = THUMBNAILS_DIR

def get_thumbnail_path(image_id: str) -> str:
    """
    Returns the absolute path to the cached thumbnail file.
    """
    return os.path.join(THUMBNAIL_CACHE_DIR, f"{image_id}.jpg")

def generate_and_cache_thumbnail(file_path: str, image_id: str) -> bytes:
    """
    Generates a thumbnail (width: 360px, aspect ratio preserved),
    saves it to the Hidden cache folder, and returns the JPEG bytes.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    cache_path = get_thumbnail_path(image_id)
    
    # 1. Load image (decode RAW dynamically if needed)
    try:
        if is_raw_image(file_path):
            img = decode_raw_to_pil(file_path)
        else:
            from PIL import ImageOps
            with Image.open(file_path) as raw_img:
                img_t = ImageOps.exif_transpose(raw_img)
                img = img_t.convert("RGB") if img_t.mode != "RGB" else img_t.copy()
    except Exception as e:
        print(f"[Photo Service] Corrupt image detected: {file_path}. Error: {e}", flush=True)
        raise HTTPException(status_code=422, detail="Unprocessable image file")
            
    # 2. Calculate aspect ratio dimensions (width 360px)
    width, height = img.size
    new_width = 360
    new_height = int((new_width / width) * height)
    
    # 3. Resize using high-quality filter
    resample_filter = getattr(Image, "Resampling", Image).LANCZOS
    img_thumb = img.resize((new_width, new_height), resample=resample_filter)
    
    # 4. Save to Cache folder atomically to prevent concurrent write corruption
    temp_path = f"{cache_path}.{uuid.uuid4().hex}.tmp"
    try:
        img_thumb.save(temp_path, format="JPEG", quality=85)
        
        # I/O Lock defense: Retry replacement up to 3 times
        for attempt in range(3):
            try:
                os.replace(temp_path, cache_path)
                break
            except OSError as e:
                if attempt == 2:
                    print(f"[Photo Service] Cache write failed after retries for {image_id}: {e}", flush=True)
                else:
                    time.sleep(0.05)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
    
    # 5. Return bytes
    buf = io.BytesIO()
    img_thumb.save(buf, format="JPEG", quality=85)
    return buf.getvalue()

def get_thumbnail_bytes(db_image: DBImage) -> bytes:
    """
    Returns the thumbnail image bytes. First searches in cache; on miss, decodes and caches it.
    """
    cache_path = get_thumbnail_path(db_image.id)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except Exception:
            # Fallback to generation if cache read fails
            pass
            
    return generate_and_cache_thumbnail(db_image.file_path, db_image.id)

def get_original_image_bytes(db_image: DBImage) -> tuple[bytes, str]:
    """
    Returns original photo bytes. For RAW images, decodes on-the-fly to JPEG.
    Returns a tuple of (bytes, content_type).
    """
    if not os.path.exists(db_image.file_path):
        raise HTTPException(status_code=404, detail=f"Original file not found: {db_image.file_path}")

    try:
        if is_raw_image(db_image.file_path):
            img = decode_raw_to_pil(db_image.file_path)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            return buf.getvalue(), "image/jpeg"
        else:
            with open(db_image.file_path, "rb") as f:
                return f.read(), db_image.mime_type
    except Exception as e:
        print(f"[Photo Service] Corrupt original image: {db_image.file_path}. Error: {e}", flush=True)
        raise HTTPException(status_code=422, detail="Unprocessable original image file")

def _prepare_photo_models(image_data: dict, metadata_data: dict, ai_data: dict) -> tuple[DBImage, DBImageMetadata, DBAIAnalysis]:
    image_id = image_data["id"]
    db_image = DBImage(**image_data)
    
    capture_date = metadata_data.get("capture_date")
    if isinstance(capture_date, str):
        try:
            metadata_data["capture_date"] = datetime.datetime.fromisoformat(capture_date)
        except ValueError:
            metadata_data["capture_date"] = None
            
    db_metadata = DBImageMetadata(image_id=image_id, **metadata_data)
    
    tags = ai_data.get("tags")
    if isinstance(tags, list):
        ai_data["tags"] = json.dumps(tags)
    
    aesthetic_tags = ai_data.get("aesthetic_tags")
    if isinstance(aesthetic_tags, list):
        ai_data["aesthetic_tags"] = json.dumps(aesthetic_tags)
        
    db_ai = DBAIAnalysis(image_id=image_id, **ai_data)
    return db_image, db_metadata, db_ai

def _prepare_chroma_metadata(metadata_data: dict) -> dict:
    iso_date = ""
    if metadata_data.get("capture_date"):
        if isinstance(metadata_data["capture_date"], datetime.datetime):
            iso_date = metadata_data["capture_date"].isoformat()
        else:
            iso_date = str(metadata_data["capture_date"])
            
    return {
        "capture_date": iso_date,
        "iso": metadata_data.get("iso") or 0,
        "camera_model": metadata_data.get("camera_model") or "",
        "lens_model": metadata_data.get("lens_model") or ""
    }

def _save_photos_atomic_internal(db: Session, items_data: list[dict]) -> list[DBImage]:
    """
    Unified function for atomic saves to SQLite and ChromaDB with compensating transactions.
    """
    if not items_data:
        return []

    db_images, db_metadatas, db_ais = [], [], []
    chroma_ids, chroma_embeddings, chroma_metadatas = [], [], []
    
    for item in items_data:
        image_data = item["image_data"]
        metadata_data = item["metadata_data"].copy()
        ai_data = item["ai_data"].copy()
        embedding = item.get("embedding")
        
        image_id = image_data["id"]
        db_image, db_metadata, db_ai = _prepare_photo_models(image_data, metadata_data, ai_data)
        
        db_images.append(db_image)
        db_metadatas.append(db_metadata)
        db_ais.append(db_ai)
        
        if embedding is not None:
            chroma_meta = _prepare_chroma_metadata(metadata_data)
            chroma_ids.append(image_id)
            chroma_embeddings.append(embedding)
            chroma_metadatas.append(chroma_meta)
            
    db.add_all(db_images)
    db.add_all(db_metadatas)
    db.add_all(db_ais)
    
    chroma_upserted = False
    if chroma_ids:
        try:
            collection = get_chroma_collection()
            collection.upsert(ids=chroma_ids, embeddings=chroma_embeddings, metadatas=chroma_metadatas)
            chroma_upserted = True
        except Exception as e:
            db.rollback()
            raise e
            
    try:
        db.commit()
        for img in db_images:
            db.refresh(img)
        return db_images
    except Exception as e:
        db.rollback()
        if chroma_upserted:
            try:
                collection = get_chroma_collection()
                collection.delete(ids=chroma_ids)
            except Exception as chroma_err:
                print(f"[Compensating Tx Error] ChromaDB delete failed after SQLite rollback: {chroma_err}")
        raise e

def register_photo_atomic(
    db: Session,
    image_data: dict,
    metadata_data: dict,
    ai_data: dict,
    embedding: list[float] | None = None
) -> DBImage:
    """
    Saves a single photo atomically in SQLite and ChromaDB vector store.
    """
    item = {
        "image_data": image_data,
        "metadata_data": metadata_data,
        "ai_data": ai_data,
        "embedding": embedding
    }
    return _save_photos_atomic_internal(db, [item])[0]

def register_photos_batch_atomic(db: Session, batch_data: list[dict]) -> None:
    """
    Saves multiple photos atomically in SQLite and ChromaDB vector store.
    """
    _save_photos_atomic_internal(db, batch_data)

def update_photo_metadata(db: Session, image_id: str, caption: str, tags: list[str]) -> DBAIAnalysis:
    """
    Updates the caption and tag metadata, setting is_user_edited to True.
    """
    db_ai = db.query(DBAIAnalysis).filter(DBAIAnalysis.image_id == image_id).first()
    if not db_ai:
        db_ai = DBAIAnalysis(image_id=image_id)
        db.add(db_ai)
        
    db_ai.caption = caption
    db_ai.tags = json.dumps(tags)
    # Note: aesthetic_tags are AI-generated, but if user edits them, we could add logic here.
    # We will assume update_photo_metadata only updates caption and general tags for now.
    db_ai.is_user_edited = True
    
    db.commit()
    db.refresh(db_ai)
    return db_ai
