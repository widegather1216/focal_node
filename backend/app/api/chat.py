import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from services.indexing_service import get_gemma_adapter

from typing import List

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/critique", response_model=schemas.CritiqueResponse)
async def get_photo_critique(
    payload: schemas.CritiqueRequest
):
    """
    Generates a deep critique for a single photo using the VLM model and saves it to DB.
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
            get_gemma_adapter().generate_deep_critique, 
            file_path, 
            meta_data
        )
        
        now_utc = models.utcnow()
        with SessionLocal() as db:
            ai = db.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == payload.photo_id).first()
            if not ai:
                ai = models.AIAnalysis(
                    image_id=payload.photo_id,
                    critique=critique_text,
                    critique_updated_at=now_utc
                )
                db.add(ai)
            else:
                ai.critique = critique_text
                ai.critique_updated_at = now_utc
            db.commit()

        return {"critique": critique_text, "critique_updated_at": now_utc.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate critique: {str(e)}")


@router.get("/critiques", response_model=List[schemas.CritiqueItemResponse])
def get_all_critiques(db: Session = Depends(get_db)):
    """
    Returns list of all photos that have generated critiques, ordered by most recent critique date.
    """
    query = (
        db.query(models.AIAnalysis, models.Image, models.ImageMetadata)
        .join(models.Image, models.AIAnalysis.image_id == models.Image.id)
        .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
        .filter(models.AIAnalysis.critique.isnot(None))
        .filter(models.AIAnalysis.critique != "")
        .order_by(models.AIAnalysis.critique_updated_at.desc().nullslast())
    )
    results = query.all()
    items = []
    for ai, img, meta in results:
        cap_date = meta.capture_date.isoformat() if meta and meta.capture_date else None
        updated_at = ai.critique_updated_at.isoformat() if ai.critique_updated_at else None
        items.append(
            schemas.CritiqueItemResponse(
                photo_id=img.id,
                file_name=img.file_name,
                file_path=img.file_path,
                capture_date=cap_date,
                camera_model=meta.camera_model if meta else None,
                lens_model=meta.lens_model if meta else None,
                f_number=meta.f_number if meta else None,
                shutter_speed=meta.shutter_speed if meta else None,
                iso=meta.iso if meta else None,
                critique=ai.critique,
                critique_updated_at=updated_at,
            )
        )
    return items


@router.delete("/critique/{photo_id}")
def delete_photo_critique(photo_id: str, db: Session = Depends(get_db)):
    """
    Clears the stored critique for a photo.
    """
    ai = db.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    if ai:
        ai.critique = None
        ai.critique_updated_at = None
        db.commit()
    return {"status": "ok", "photo_id": photo_id}

