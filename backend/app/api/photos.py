import json
import os
import shutil
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import services.photo as photo_service
from database import get_db
import schemas

MAX_CONCURRENT_DECODES = 3
decode_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DECODES)

def _parse_ai_tags(ai_model) -> tuple[list[str], list[str]]:
    tags_list = []
    if ai_model and hasattr(ai_model, "tags") and ai_model.tags:
        try:
            tags_list = json.loads(ai_model.tags)
        except json.JSONDecodeError:
            pass
            
    aesthetic_tags_list = []
    if ai_model and hasattr(ai_model, "aesthetic_tags") and ai_model.aesthetic_tags:
        try:
            aesthetic_tags_list = json.loads(ai_model.aesthetic_tags)
        except json.JSONDecodeError:
            pass
            
    return tags_list, aesthetic_tags_list

router = APIRouter(prefix="/api/photos", tags=["photos"])

@router.get("", response_model=List[schemas.PhotoListResponse])
def get_photos(
    limit: int = 50,
    offset: int = 0,
    parent_dir: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns list of photos, supporting pagination and directory filtering.
    """
    query = db.query(models.Image).outerjoin(models.ImageMetadata)
    if parent_dir:
        query = query.filter(models.Image.parent_dir == parent_dir)
        
    query = query.order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
    images = query.offset(offset).limit(limit).all()
    
    result = [img.to_list_response_dict() for img in images]
    return result

@router.get("/{id}/thumbnail")
async def get_photo_thumbnail(id: str, db: Session = Depends(get_db)):
    """
    Serves the cached (or dynamically generated/cached) thumbnail for a photo.
    """
    db_image = db.query(models.Image).filter(models.Image.id == id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    try:
        # 1. Check cache first to avoid bottlenecking on semaphore
        cache_path = photo_service.get_thumbnail_path(id)
        if await asyncio.to_thread(os.path.exists, cache_path):
            try:
                # Fast path: read from cache via to_thread to prevent event loop blocking
                def _read_cache():
                    with open(cache_path, "rb") as f:
                        return f.read()
                thumb_bytes = await asyncio.to_thread(_read_cache)
                return Response(content=thumb_bytes, media_type="image/jpeg")
            except Exception:
                pass
                
        # 2. Cache miss: generate thumbnail with bounded concurrency (OOM protection)
        async with decode_semaphore:
            thumb_bytes = await asyncio.to_thread(
                photo_service.generate_and_cache_thumbnail, 
                db_image.file_path, 
                db_image.id
            )
        return Response(content=thumb_bytes, media_type="image/jpeg")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {str(e)}")

@router.get("/{id}/original")
async def get_photo_original(id: str, db: Session = Depends(get_db)):
    """
    Serves the original image. For RAW formats, decodes dynamically to sRGB JPEG.
    """
    db_image = db.query(models.Image).filter(models.Image.id == id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    try:
        from utils.image import is_raw_image
        if is_raw_image(db_image.file_path):
            async with decode_semaphore:
                original_bytes, content_type = await asyncio.to_thread(photo_service.get_original_image_bytes, db_image)
            return Response(content=original_bytes, media_type=content_type)
        else:
            if not os.path.exists(db_image.file_path):
                raise HTTPException(status_code=404, detail="Original file not found on disk")
            from fastapi.responses import FileResponse
            return FileResponse(db_image.file_path, media_type=db_image.mime_type)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream original image: {str(e)}")

@router.get("/{id}", response_model=schemas.PhotoDetailResponse)
def get_photo_detail(id: str, db: Session = Depends(get_db)):
    """
    Fetches full metadata and AI analysis details for a single photo.
    """
    img = db.query(models.Image).filter(models.Image.id == id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    return img.to_detail_dict()

@router.patch("/{id}/metadata", response_model=schemas.UpdateMetadataResponse)
def patch_photo_metadata(
    id: str,
    payload: schemas.UpdateMetadataRequest,
    db: Session = Depends(get_db)
):
    """
    Updates custom tags and caption editing state for a photo.
    """
    db_image = db.query(models.Image).filter(models.Image.id == id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    try:
        updated_ai = photo_service.update_photo_metadata(db, id, payload.caption, payload.tags)
        
        tags_list, aesthetic_tags_list = _parse_ai_tags(updated_ai)
                
        return {
            "status": "success",
            "id": id,
            "ai_analysis": {
                "caption": updated_ai.caption,
                "tags": tags_list,
                "aesthetic_tags": aesthetic_tags_list,
                "is_user_edited": updated_ai.is_user_edited
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")

@router.post("/export")
async def export_photos(
    payload: schemas.ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Exports selected photos to a destination folder via streaming to prevent timeouts.
    """
    dest_folder = payload.destination_folder
    
    if not os.path.exists(dest_folder) or not os.path.isdir(dest_folder):
        raise HTTPException(status_code=400, detail="Invalid destination folder")
        
    images = db.query(models.Image).filter(models.Image.id.in_(payload.photo_ids)).all()
    
    if not images:
        raise HTTPException(status_code=404, detail="No photos found to export")
        
    export_items = [{"file_path": img.file_path, "file_name": img.file_name} for img in images]
        
    async def export_generator():
        errors = []
        exported_count = 0
        total_count = len(export_items)
        
        yield f"event: start\ndata: {json.dumps({'total': total_count})}\n\n".encode('utf-8')
        
        for idx, item in enumerate(export_items):
            try:
                if os.path.exists(item["file_path"]):
                    base, ext = os.path.splitext(item["file_name"])
                    final_name = item["file_name"]
                    counter = 1
                    target_path = os.path.join(dest_folder, final_name)
                    while os.path.exists(target_path):
                        final_name = f"{base} ({counter}){ext}"
                        target_path = os.path.join(dest_folder, final_name)
                        counter += 1
                        
                    await asyncio.to_thread(shutil.copy2, item["file_path"], target_path)
                    exported_count += 1
                    
                    yield f"event: progress\ndata: {json.dumps({'processed': idx + 1, 'total': total_count, 'file': final_name})}\n\n".encode('utf-8')
                else:
                    errors.append(f"File not found: {item['file_path']}")
            except Exception as e:
                errors.append(f"Failed to copy {item['file_name']}: {str(e)}")
            
        final_result = {
            "status": "success" if exported_count > 0 else "failed",
            "exported_count": exported_count,
            "errors": errors if errors else None
        }
        yield f"event: done\ndata: {json.dumps(final_result)}\n\n".encode('utf-8')
        
    return StreamingResponse(export_generator(), media_type="text/event-stream")

from services.indexing_service import reindex_single_photo_inplace

@router.post("/{id}/reindex", response_model=schemas.PhotoDetailResponse)
async def reindex_photo(id: str):
    """
    Forces a re-indexing of a single photo (e.g. if previous AI analysis failed).
    """
    try:
        updated_data = await reindex_single_photo_inplace(id)
        return updated_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reindex photo: {str(e)}")

@router.post("/{id}/favorite", response_model=schemas.FavoriteToggleResponse)
def toggle_favorite(id: str, db: Session = Depends(get_db)):
    """
    Toggles the favorite status of a photo.
    """
    db_image = db.query(models.Image).filter(models.Image.id == id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    db_image.is_favorite = not db_image.is_favorite
    db.commit()
    db.refresh(db_image)
    
    return {"id": db_image.id, "is_favorite": db_image.is_favorite}

