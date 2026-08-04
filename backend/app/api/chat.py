from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/critique", response_model=schemas.CritiqueResponse)
async def get_photo_critique(payload: schemas.CritiqueRequest):
    """
    Generates a deep critique for a single photo using VLM models via ChatService.
    """
    try:
        return await ChatService.generate_photo_critique(payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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

@router.post("/critique-summary", response_model=schemas.CritiqueSummaryResponse)
async def generate_critique_summary(
    payload: schemas.CritiqueSummaryRequest = schemas.CritiqueSummaryRequest()
):
    """
    Generates an aggregated summary report for photo critiques via ChatService.
    """
    try:
        return await ChatService.generate_critique_summary(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate critique summary: {str(e)}")
