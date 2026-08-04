import asyncio
from typing import Dict, Any, List, Optional
from database import SessionLocal
import models
import schemas
from services.ai_factory import get_gemma_adapter

class ChatService:
    @staticmethod
    async def generate_photo_critique(payload: schemas.CritiqueRequest) -> Dict[str, Any]:
        """
        Generates deep photo critique using VLM (Gemma / UniPercept) and saves it to DB.
        """
        with SessionLocal() as db:
            img = db.query(models.Image).filter(models.Image.id == payload.photo_id).first()
            if not img:
                raise ValueError("Photo not found")
                
            meta = img.metadata_rel
            meta_data = {
                "camera_model": meta.camera_model if meta else None,
                "lens_model": meta.lens_model if meta else None,
                "f_number": meta.f_number if meta else None,
                "shutter_speed": meta.shutter_speed if meta else None,
                "iso": meta.iso if meta else None,
            }
            file_path = img.file_path

        # Inference outside DB session lock
        if payload.engine == "unipercept":
            from services.unipercept_adapter import get_unipercept_adapter
            res_dict = await asyncio.to_thread(
                get_unipercept_adapter().generate_full_ensemble_critique,
                file_path,
                meta_data
            )
            raw_en = res_dict.get("critique", "")
            scores_dict = res_dict.get("scores", {})
            quality_score = res_dict.get("quality_score")
            
            get_unipercept_adapter().unload_model()
            
            try:
                critique_text = await asyncio.to_thread(
                    get_gemma_adapter().translate_and_format_critique,
                    raw_en,
                    quality_score
                )
                if scores_dict and not critique_text.startswith("[📊"):
                    sb_header = (
                        f"[📊 4대 앙상블 비평 스코어보드]\n"
                        f"- 최종 종합 평점: {scores_dict.get('overall')}점 / 100점\n"
                        f"- 🎨 미학 & 구도 (IAA): {scores_dict.get('iaa')}점\n"
                        f"- 🔍 화질 & 기술 (IQA): {scores_dict.get('iqa')}점\n"
                        f"- 🧱 구조 & 질감 (ISTA): {scores_dict.get('ista')}점\n\n"
                    )
                    critique_text = f"{sb_header}{critique_text}"
            except Exception as tr_err:
                print(f"[ChatService] Gemma 4 translation fallback: {tr_err}", flush=True)
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

    @staticmethod
    async def generate_critique_summary(payload: Optional[schemas.CritiqueSummaryRequest] = None) -> Dict[str, Any]:
        """
        Generates an aggregated summary report for photo critiques using Gemma LLM.
        """
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
                raise ValueError("요약할 AI 비평 데이터가 존재하지 않습니다.")

            critiques_list = []
            for ai, img, meta in results:
                critiques_list.append({
                    "photo_id": img.id,
                    "file_name": img.file_name,
                    "camera_model": meta.camera_model if meta else None,
                    "lens_model": meta.lens_model if meta else None,
                    "critique": ai.critique
                })

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
