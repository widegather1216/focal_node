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

@router.get("/critique/status/{photo_id}", response_model=schemas.CritiqueStatusResponse)
def get_photo_critique_status(photo_id: str):
    """
    Returns real-time progress status for an ongoing critique request.
    """
    from services.critique_status import critique_status_manager
    return critique_status_manager.get(photo_id)


from repositories.photo_repository import PhotoRepository

@router.get("/critiques", response_model=List[schemas.CritiqueItemResponse])
def get_all_critiques(db: Session = Depends(get_db)):
    """
    Returns list of all photos that have generated critiques, ordered by most recent critique date.
    """
    photo_repo = PhotoRepository(db)
    results = photo_repo.list_critiques()
    items = []
    for ai, img, meta in results:
        capture_date_str = meta.capture_date.isoformat() if meta and meta.capture_date else None
        updated_at_str = ai.critique_updated_at.isoformat() if ai.critique_updated_at else None
        items.append(
            schemas.CritiqueItemResponse(
                photo_id=img.id,
                file_name=img.file_name,
                file_path=img.file_path,
                capture_date=capture_date_str,
                camera_model=meta.camera_model if meta else None,
                lens_model=meta.lens_model if meta else None,
                f_number=meta.f_number if meta else None,
                shutter_speed=meta.shutter_speed if meta else None,
                iso=meta.iso if meta else None,
                critique=ai.critique,
                critique_updated_at=updated_at_str,
            )
        )
    return items

@router.delete("/critique/{photo_id}")
def delete_photo_critique(photo_id: str, db: Session = Depends(get_db)):
    """
    Clears the stored critique for a photo.
    """
    photo_repo = PhotoRepository(db)
    photo_repo.delete_critique(photo_id)
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
