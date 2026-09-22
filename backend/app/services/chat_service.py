import asyncio
from typing import Dict, Any, List, Optional
from database import SessionLocal
import models
import schemas
from services.ai_factory import get_gemma_adapter

def _get_photo_and_metadata(photo_id: str) -> tuple[str, dict]:
    with SessionLocal() as db:
        img = db.query(models.Image).filter(models.Image.id == photo_id).first()
        if not img:
            raise ValueError("Photo not found")
            
        meta = img.metadata_rel
        meta_data = {
            "camera_model": meta.camera_model if meta else None,
            "lens_model": meta.lens_model if meta else None,
            "f_number": meta.f_number if meta else None,
            "focal_length": meta.focal_length if meta else None,
            "focal_length_35mm": meta.focal_length_35mm if meta else None,
            "sensor_format": meta.sensor_format if meta else None,
            "crop_factor": meta.crop_factor if meta else None,
            "shutter_speed": meta.shutter_speed if meta else None,
            "iso": meta.iso if meta else None,
        }
        return img.file_path, meta_data

def _save_critique_to_db(photo_id: str, critique_text: str, updated_at) -> None:
    with SessionLocal() as db:
        ai = db.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
        if not ai:
            ai = models.AIAnalysis(
                image_id=photo_id,
                critique=critique_text,
                critique_updated_at=updated_at
            )
            db.add(ai)
        else:
            ai.critique = critique_text
            ai.critique_updated_at = updated_at
        db.commit()

def _clear_device_caches() -> None:
    try:
        import torch
        if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()
    except Exception:
        pass
    try:
        import mlx.core as mx
        import gc
        mx.clear_cache()
        gc.collect()
    except Exception:
        pass

def _fetch_critiques_from_db(photo_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        query = (
            db.query(models.AIAnalysis, models.Image, models.ImageMetadata)
            .join(models.Image, models.AIAnalysis.image_id == models.Image.id)
            .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
            .filter(models.AIAnalysis.critique.isnot(None))
            .filter(models.AIAnalysis.critique != "")
        )
        if photo_ids:
            if len(photo_ids) > 900:
                from sqlalchemy import or_
                conditions = [
                    models.Image.id.in_(photo_ids[i:i+900])
                    for i in range(0, len(photo_ids), 900)
                ]
                query = query.filter(or_(*conditions))
            else:
                query = query.filter(models.Image.id.in_(photo_ids))
            
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
        return critiques_list


class ChatService:
    @staticmethod
    async def generate_photo_critique(payload: schemas.CritiqueRequest) -> Dict[str, Any]:
        """
        Generates deep photo critique using VLM (Gemma / UniPercept) and saves it to DB.
        """
        file_path, meta_data = await asyncio.to_thread(_get_photo_and_metadata, payload.photo_id)

        from services.critique_status import critique_status_manager, CritiqueCancelledException

        # Reset previous cancellation flag and initialize status
        critique_status_manager.reset(payload.photo_id)
        critique_status_manager.update(payload.photo_id, 1, 4, "점수 산출 중", 15)
        print(f"[ChatService] Generating photo critique for {payload.photo_id} (Engine: {payload.engine})...", flush=True)

        try:
            critique_status_manager.check_cancelled(payload.photo_id)

            if payload.engine == "unipercept":
                from services.unipercept_adapter import get_unipercept_adapter
                res_dict = await asyncio.to_thread(
                    get_unipercept_adapter().generate_full_ensemble_critique,
                    file_path,
                    meta_data,
                    payload.photo_id
                )
                critique_status_manager.check_cancelled(payload.photo_id)

                raw_en = res_dict.get("critique", "")
                scores_dict = res_dict.get("scores", {})
                quality_score = res_dict.get("quality_score")
                
                await asyncio.to_thread(get_unipercept_adapter().unload_model)
                print("[ChatService] UniPercept ensemble completed. Starting Gemma 4 translation...", flush=True)
                
                try:
                    critique_status_manager.check_cancelled(payload.photo_id)
                    critique_text = await asyncio.to_thread(
                        get_gemma_adapter().translate_and_format_critique,
                        raw_en,
                        scores_dict,
                        quality_score,
                        payload.photo_id
                    )
                    critique_status_manager.check_cancelled(payload.photo_id)
                    if scores_dict and "앙상블 비평 스코어보드" not in critique_text:
                        sb_header = (
                            f"[6-Way 앙상블 비평 스코어보드]\n"
                            f"- 최종 종합 평점: {scores_dict.get('overall')}점 / 100점\n"
                            f"- 미학 및 구도 (IAA): {scores_dict.get('iaa')}점\n"
                            f"- 화질 및 선명도 (IQA): {scores_dict.get('iqa')}점\n"
                            f"- 구조 및 질감 (ISTA): {scores_dict.get('ista')}점\n\n"
                        )
                        critique_text = f"{sb_header}{critique_text}"
                except CritiqueCancelledException:
                    raise
                except Exception as tr_err:
                    print(f"[ChatService] Gemma 4 translation fallback: {tr_err}", flush=True)
                    critique_text = raw_en
            else:
                print("[ChatService] Starting Gemma 4 VLM direct critique generation...", flush=True)
                critique_status_manager.update(payload.photo_id, 2, 4, "비평 작성 중", 50)
                critique_text = await asyncio.to_thread(
                    get_gemma_adapter().generate_deep_critique, 
                    file_path, 
                    meta_data,
                    payload.photo_id
                )
                critique_status_manager.check_cancelled(payload.photo_id)

                # Pass 2: Gemma Document Structuring Pass (Polish & Formatting) - Only for Gemma direct critique
                print("[ChatService] Starting Gemma document structuring pass...", flush=True)
                critique_status_manager.update(payload.photo_id, 3, 4, "[Gemma] 리포트 문서 양식 다듬는 중...", 75)
                try:
                    critique_text = await asyncio.to_thread(
                        get_gemma_adapter().format_and_structure_critique,
                        critique_text,
                        meta_data,
                        payload.photo_id
                    )
                    critique_status_manager.check_cancelled(payload.photo_id)
                except CritiqueCancelledException:
                    raise
                except Exception as fmt_err:
                    print(f"[ChatService] Document structuring fallback to draft: {fmt_err}", flush=True)
            
            critique_status_manager.check_cancelled(payload.photo_id)

            now_utc = models.utcnow()
            await asyncio.to_thread(_save_critique_to_db, payload.photo_id, critique_text, now_utc)

            critique_status_manager.update(payload.photo_id, 4, 4, "비평 완료", 100, status="completed")

            return {
                "critique": critique_text,
                "critique_updated_at": now_utc.isoformat(),
                "engine_used": payload.engine,
                "status": "completed"
            }
        except CritiqueCancelledException:
            print(f"[ChatService] 🛑 Photo critique generation cancelled for {payload.photo_id}", flush=True)
            critique_status_manager.update(payload.photo_id, 0, 4, "비평 생성이 사용자에 의해 중단되었습니다.", 0, status="cancelled")
            # Clear device caches safely in worker thread
            await asyncio.to_thread(_clear_device_caches)
            return {
                "critique": "",
                "critique_updated_at": None,
                "engine_used": payload.engine,
                "status": "cancelled"
            }
        except Exception as e:
            critique_status_manager.update(payload.photo_id, 0, 4, f"오류 발생: {str(e)}", 0, status="error")
            raise

    @staticmethod
    async def generate_critique_summary(payload: Optional[schemas.CritiqueSummaryRequest] = None) -> Dict[str, Any]:
        """
        Generates an aggregated summary report for photo critiques using Gemma LLM.
        """
        critiques_list = await asyncio.to_thread(
            _fetch_critiques_from_db,
            payload.photo_ids if payload else None
        )

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
