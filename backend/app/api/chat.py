import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from services.indexing_service import gemma_adapter

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/critique", response_model=schemas.CritiqueResponse)
async def get_photo_critique(
    payload: schemas.CritiqueRequest
):
    """
    Generates a deep critique for a single photo using the VLM model.
    """
    from database import SessionLocal
    with SessionLocal() as db:
        img = db.query(models.Image).filter(models.Image.id == payload.photo_id).first()
        if not img:
            raise HTTPException(status_code=404, detail="Photo not found")
            
        meta = img.metadata_rel
        
        meta_data = {
            "camera_model": meta.camera_model if meta else None,
            "lens_model": meta.lens_model if meta else None,
            "f_number": meta.f_number if meta else None,
            "shutter_speed": meta.shutter_speed if meta else None,
            "iso": meta.iso if meta else None,
        }
        file_path = img.file_path
    
    # DB session is closed here, connection is returned to pool BEFORE the long MLX inference.
    
    try:
        # We run the MLX inference in a background thread to prevent event loop blocking
        critique_text = await asyncio.to_thread(
            gemma_adapter.generate_deep_critique, 
            file_path, 
            meta_data
        )
        return {"critique": critique_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate critique: {str(e)}")
