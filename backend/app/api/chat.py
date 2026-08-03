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
        if payload.engine == "unipercept":
            from services.unipercept_adapter import get_unipercept_adapter
            res_dict = await asyncio.to_thread(
                get_unipercept_adapter().generate_unipercept_critique,
                file_path,
                meta_data
            )
            raw_en = res_dict.get("critique", "")
            quality_score = res_dict.get("quality_score")
            
            # Explicitly unload UniPercept 8B model to free ~16GB Mac RAM before loading Gemma 4!
            get_unipercept_adapter().unload_model()
            
            # Translate raw English VQA output to structured Korean using Gemma 4
            try:
                critique_text = await asyncio.to_thread(
                    get_gemma_adapter().translate_and_format_critique,
                    raw_en,
                    quality_score
                )
            except Exception as tr_err:
                print(f"[chat.py] Gemma 4 translation fallback: {tr_err}", flush=True)
                critique_text = raw_en
        else:
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

        return {
            "critique": critique_text,
            "critique_updated_at": now_utc.isoformat(),
            "engine_used": payload.engine
        }
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
    Generates an aggregated summary report for existing photo critiques using the Gemma LLM model.
    """
    from database import SessionLocal
    with SessionLocal() as db:
        query = (
            db.query(models.AIAnalysis, models.Image, models.ImageMetadata)
            .join(models.Image, models.AIAnalysis.image_id == models.Image.id)
            .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
            .filter(models.AIAnalysis.critique.isnot(None))
            .filter(models.AIAnalysis.critique != "")
        )
        if payload and payload.photo_ids:
            query = query.filter(models.Image.id.in_(payload.photo_ids))
            
        results = query.all()
        if not results:
            raise HTTPException(status_code=400, detail="요약할 AI 비평 데이터가 존재하지 않습니다.")

        critiques_list = []
        for ai, img, meta in results:
            critiques_list.append({
                "photo_id": img.id,
                "file_name": img.file_name,
                "camera_model": meta.camera_model if meta else None,
                "lens_model": meta.lens_model if meta else None,
                "critique": ai.critique
            })

    try:
        summary_text = await asyncio.to_thread(
            get_gemma_adapter().generate_critique_summary,
            critiques_list
        )
        now_utc = models.utcnow()
        return {
            "summary": summary_text,
            "total_critiques_analyzed": len(critiques_list),
            "created_at": now_utc.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate critique summary: {str(e)}")


