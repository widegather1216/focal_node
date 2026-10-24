from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Literal, Optional
import models

import schemas
from database import get_db
from repositories.photo_repository import PhotoRepository
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

@router.post("/critique/cancel/{photo_id}", response_model=schemas.CritiqueCancelResponse)
@router.post("/critique/{photo_id}/cancel", response_model=schemas.CritiqueCancelResponse)
def cancel_photo_critique(photo_id: str):
    """
    Cancels an ongoing photo critique generation task safely and frees model memory.
    """
    ChatService.cancel_critique(photo_id)
    return schemas.CritiqueCancelResponse(
        photo_id=photo_id,
        status="cancelled",
        message="비평 생성이 사용자에 의해 중단되었습니다."
    )


def _to_critique_item_response(
    ai: models.AIAnalysis,
    img: models.Image,
    meta: Optional[models.ImageMetadata]
) -> schemas.CritiqueItemResponse:
    capture_date_str = meta.capture_date.isoformat() if meta and meta.capture_date else None
    updated_at_str = ai.critique_updated_at.isoformat() if ai.critique_updated_at else None
    return schemas.CritiqueItemResponse(
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
        critique_en=ai.critique_en,
        overall_score=ai.overall_score,
        iaa_score=ai.iaa_score,
        iqa_score=ai.iqa_score,
        ista_score=ai.ista_score,
        critique_updated_at=updated_at_str,
    )


@router.get("/critiques", response_model=List[schemas.CritiqueItemResponse])
def get_all_critiques(
    sort_by: Literal["recent", "overall_score", "iaa_score"] = Query(
        "recent",
        description="비평 목록 정렬 기준 (recent: 최신순, overall_score: 종합평점순, iaa_score: 미학점수순)"
    ),
    db: Session = Depends(get_db)
):
    """
    Returns list of all photos that have generated critiques, ordered by sort_by.
    """
    photo_repo = PhotoRepository(db)
    results = photo_repo.list_critiques(sort_by=sort_by)
    return [_to_critique_item_response(ai, img, meta) for ai, img, meta in results]

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
