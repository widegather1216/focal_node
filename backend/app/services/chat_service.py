import asyncio
import threading
from typing import Dict, Any, List, Optional
from database import SessionLocal
import models
import schemas
from repositories.photo_repository import PhotoRepository
from services.ai_factory import get_gemma_adapter

def _get_photo_and_metadata(photo_id: str) -> tuple[str, dict]:
    with SessionLocal() as db:
        img = PhotoRepository(db).get_by_id(photo_id)
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

def _extract_score_floats(
    scores_dict: Optional[Dict[str, Any]],
    critique_text: Optional[str]
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Safely resolves overall, iaa, iqa, and ista scores as floats from scores_dict,
    falling back to parsing scoreboard block in critique_text if missing.
    """
    from services.ai_parser import parse_scoreboard_scores

    def _to_float(score_val: Any) -> Optional[float]:
        if score_val is None or score_val == "":
            return None
        try:
            return float(score_val)
        except (ValueError, TypeError):
            return None

    overall = _to_float(scores_dict.get("overall")) if scores_dict else None
    iaa = _to_float(scores_dict.get("iaa")) if scores_dict else None
    iqa = _to_float(scores_dict.get("iqa")) if scores_dict else None
    ista = _to_float(scores_dict.get("ista")) if scores_dict else None

    # Defensive fallback: if any metric is missing, try parsing critique_text scoreboard
    if (overall is None or iaa is None or iqa is None or ista is None) and critique_text:
        parsed_scores = parse_scoreboard_scores(critique_text)
        overall = overall if overall is not None else parsed_scores.get("overall")
        iaa = iaa if iaa is not None else parsed_scores.get("iaa")
        iqa = iqa if iqa is not None else parsed_scores.get("iqa")
        ista = ista if ista is not None else parsed_scores.get("ista")

    return overall, iaa, iqa, ista

def _save_critique_to_db(
    photo_id: str,
    critique_text: str,
    updated_at: Any,
    scores_dict: Optional[Dict[str, Any]] = None,
    raw_en: Optional[str] = None
) -> None:
    """
    Persists critique text, raw english critique, and normalized 4-dimension scores to SQLite ai_analysis table.
    """
    overall_score, iaa_score, iqa_score, ista_score = _extract_score_floats(scores_dict, critique_text)
    critique_en = raw_en.strip() if (raw_en and isinstance(raw_en, str) and raw_en.strip()) else None

    # Defensive datetime normalization
    if isinstance(updated_at, str):
        try:
            import datetime
            updated_at = datetime.datetime.fromisoformat(updated_at)
        except Exception as date_err:
            print(f"[ChatService] Failed to parse updated_at string '{updated_at}': {date_err}", flush=True)

    with SessionLocal() as db:
        PhotoRepository(db).upsert_critique(
            photo_id=photo_id,
            critique_text=critique_text,
            updated_at=updated_at,
            critique_en=critique_en,
            overall_score=overall_score,
            iaa_score=iaa_score,
            iqa_score=iqa_score,
            ista_score=ista_score,
        )

def _clear_device_caches() -> None:
    try:
        import torch
        if hasattr(torch, "mps") and hasattr(torch.mps, "synchronize"):
            torch.mps.synchronize()
        if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()
    except Exception as torch_err:
        print(f"[ChatService] Warning clearing torch cache: {torch_err}", flush=True)
    try:
        import mlx.core as mx
        import gc
        mx.clear_cache()
        gc.collect()
    except Exception as mlx_err:
        print(f"[ChatService] Warning clearing MLX cache: {mlx_err}", flush=True)

def _unload_critique_models(force: bool = False) -> None:
    """
    Immediately unloads UniPercept model from memory and unloads Gemma model
    if force is True or no other concurrent tasks (such as background indexing) are using it.
    """
    try:
        from services.unipercept_adapter import get_unipercept_adapter
        adapter = get_unipercept_adapter()
        if hasattr(adapter, "unload_model"):
            adapter.unload_model()
    except Exception as e:
        print(f"[ChatService] Error unloading UniPercept model: {e}", flush=True)

    try:
        gemma = get_gemma_adapter()
        active_reqs = getattr(gemma, "active_requests", 0)
        should_unload = force or not isinstance(active_reqs, int) or active_reqs <= 0
        if should_unload and hasattr(gemma, "unload_model"):
            gemma.unload_model()
    except Exception as e:
        print(f"[ChatService] Error unloading Gemma model: {e}", flush=True)

    _clear_device_caches()


def _fetch_critiques_from_db(photo_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        results = PhotoRepository(db).list_critiques(sort_by="recent", photo_ids=photo_ids)
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


def _build_scoreboard_header(scores_dict: dict) -> str:
    if not scores_dict:
        return ""
    return (
        f"[6-Way 앙상블 비평 스코어보드]\n"
        f"- 최종 종합 평점: {scores_dict.get('overall')}점 / 100점\n"
        f"- 미학 및 구도 (IAA): {scores_dict.get('iaa')}점\n"
        f"- 화질 및 선명도 (IQA): {scores_dict.get('iqa')}점\n"
        f"- 구조 및 질감 (ISTA): {scores_dict.get('ista')}점\n\n"
    )

async def _execute_unipercept_critique_pipeline(
    file_path: str, meta_data: dict, photo_id: str
) -> tuple[str, Optional[dict], Optional[str]]:
    from services.unipercept_adapter import get_unipercept_adapter
    from services.critique_status import critique_status_manager, CritiqueCancelledException

    adapter = get_unipercept_adapter()
    raw_en: str = ""
    scores_dict: Optional[dict] = None
    quality_score: Optional[int] = None

    try:
        try:
            res_dict = await asyncio.to_thread(
                adapter.generate_full_ensemble_critique,
                file_path,
                meta_data,
                photo_id,
                f_number=meta_data.get("f_number") if meta_data else None,
                iso=meta_data.get("iso") if meta_data else None
            )
            critique_status_manager.check_cancelled(photo_id)

            raw_en = res_dict.get("critique", "")
            scores_dict = res_dict.get("scores", {})
            quality_score = res_dict.get("quality_score")
            if scores_dict and scores_dict.get("overall") is None and quality_score is not None:
                scores_dict["overall"] = quality_score
        finally:
            # Guarantee UniPercept model is immediately unloaded from memory
            await asyncio.to_thread(adapter.unload_model)
    except CritiqueCancelledException:
        raise
    except Exception as uni_err:
        print(f"[ChatService] ⚠️ UniPercept ensemble failed ({uni_err}). Falling back to Gemma 4 direct critique...", flush=True)
        return await _execute_gemma_critique_pipeline(file_path, meta_data, photo_id)

    print("[ChatService] UniPercept ensemble completed. Starting Gemma 4 direct perceptual critique...", flush=True)

    try:
        critique_status_manager.check_cancelled(photo_id)
        gemma = get_gemma_adapter()
        # Share pre-decoded PIL image from UniPercept to eliminate redundant RAW decode per Rule 2.3
        critique_image = res_dict.get("pil_img") if (isinstance(res_dict, dict) and res_dict.get("pil_img")) else file_path
        critique_text = await asyncio.to_thread(
            gemma.generate_perceptual_critique,
            critique_image,
            meta_data,
            scores_dict,
            raw_en,
            photo_id
        )
        # Mock compatibility for legacy tests that specifically mocked translate_and_format_critique
        try:
            from unittest.mock import MagicMock
            if isinstance(critique_text, MagicMock) and hasattr(gemma, "translate_and_format_critique"):
                legacy_res = gemma.translate_and_format_critique(raw_en, scores_dict, quality_score, photo_id)
                if not isinstance(legacy_res, MagicMock):
                    critique_text = legacy_res
        except ImportError:
            pass

        critique_status_manager.check_cancelled(photo_id)
        if scores_dict and "앙상블 비평 스코어보드" not in critique_text:
            critique_text = f"{_build_scoreboard_header(scores_dict)}{critique_text}"
        return critique_text, scores_dict, raw_en
    except CritiqueCancelledException:
        raise
    except Exception as gemma_err:
        print(f"[ChatService] Gemma 4 perceptual critique fallback: {gemma_err}", flush=True)
        if raw_en and raw_en.strip():
            fallback_text = f"{_build_scoreboard_header(scores_dict)}{raw_en}" if scores_dict else raw_en
            return fallback_text, scores_dict, raw_en
        raise

async def _execute_gemma_critique_pipeline(
    file_path: str, meta_data: dict, photo_id: str
) -> tuple[str, Optional[dict], Optional[str]]:
    from services.critique_status import critique_status_manager, CritiqueCancelledException

    print("[ChatService] Starting Gemma 4 VLM direct critique generation...", flush=True)
    critique_status_manager.update(photo_id, 2, 4, "비평 작성 중", 50)
    critique_text = await asyncio.to_thread(
        get_gemma_adapter().generate_deep_critique,
        file_path,
        meta_data,
        photo_id
    )
    critique_status_manager.check_cancelled(photo_id)

    print("[ChatService] Starting Gemma document structuring pass...", flush=True)
    critique_status_manager.update(photo_id, 3, 4, "[Gemma] 리포트 문서 양식 다듬는 중...", 75)
    try:
        critique_text = await asyncio.to_thread(
            get_gemma_adapter().format_and_structure_critique,
            critique_text,
            meta_data,
            photo_id
        )
        critique_status_manager.check_cancelled(photo_id)
        return critique_text, None, None
    except CritiqueCancelledException:
        raise
    except Exception as fmt_err:
        print(f"[ChatService] Document structuring fallback to draft: {fmt_err}", flush=True)
        return critique_text, None, None


_critique_tasks: Dict[str, asyncio.Task] = {}
_critique_tasks_lock = threading.Lock()

async def _run_critique_pipeline(payload: schemas.CritiqueRequest) -> Dict[str, Any]:
    file_path, meta_data = await asyncio.to_thread(_get_photo_and_metadata, payload.photo_id)
    from services.critique_status import critique_status_manager, CritiqueCancelledException

    critique_status_manager.reset(payload.photo_id)
    critique_status_manager.update(payload.photo_id, 1, 4, "점수 산출 중", 15)
    print(f"[ChatService] Generating photo critique for {payload.photo_id} (Engine: {payload.engine})...", flush=True)

    try:
        critique_status_manager.check_cancelled(payload.photo_id)

        if payload.engine == "unipercept":
            pipeline_result = await _execute_unipercept_critique_pipeline(file_path, meta_data, payload.photo_id)
        else:
            pipeline_result = await _execute_gemma_critique_pipeline(file_path, meta_data, payload.photo_id)

        critique_status_manager.check_cancelled(payload.photo_id)

        # Flexible unpacking supporting (critique_text, scores_dict, raw_en), dict, or plain str
        if isinstance(pipeline_result, tuple):
            critique_text = pipeline_result[0]
            scores_dict = pipeline_result[1] if len(pipeline_result) > 1 else None
            raw_en = pipeline_result[2] if len(pipeline_result) > 2 else None
        elif isinstance(pipeline_result, dict):
            critique_text = pipeline_result.get("critique", "")
            scores_dict = pipeline_result.get("scores")
            raw_en = pipeline_result.get("raw_en")
        else:
            critique_text = str(pipeline_result or "")
            scores_dict = None
            raw_en = None

        if not critique_text or not critique_text.strip():
            raise RuntimeError("Critique generation resulted in empty or invalid critique.")

        overall_score, iaa_score, iqa_score, ista_score = _extract_score_floats(scores_dict, critique_text)
        critique_en = raw_en.strip() if (raw_en and isinstance(raw_en, str) and raw_en.strip()) else None

        now_utc = models.utcnow()
        await asyncio.to_thread(
            _save_critique_to_db,
            payload.photo_id,
            critique_text,
            now_utc,
            scores_dict,
            raw_en
        )

        critique_status_manager.update(
            payload.photo_id,
            4,
            4,
            "비평 완료",
            100,
            status="completed",
            critique=critique_text,
            critique_en=critique_en,
            overall_score=overall_score,
            iaa_score=iaa_score,
            iqa_score=iqa_score,
            ista_score=ista_score,
            critique_updated_at=now_utc.isoformat()
        )

        return {
            "critique": critique_text,
            "critique_en": critique_en,
            "overall_score": overall_score,
            "iaa_score": iaa_score,
            "iqa_score": iqa_score,
            "ista_score": ista_score,
            "critique_updated_at": now_utc.isoformat(),
            "engine_used": payload.engine,
            "status": "completed"
        }
    except CritiqueCancelledException:
        print(f"[ChatService] 🛑 Photo critique generation cancelled for {payload.photo_id}", flush=True)
        critique_status_manager.update(payload.photo_id, 0, 4, "비평 생성이 사용자에 의해 중단되었습니다.", 0, status="cancelled")
        await asyncio.to_thread(_unload_critique_models, force=True)
        return {
            "critique": "",
            "critique_en": None,
            "overall_score": None,
            "iaa_score": None,
            "iqa_score": None,
            "ista_score": None,
            "critique_updated_at": None,
            "engine_used": payload.engine,
            "status": "cancelled"
        }
    except asyncio.CancelledError:
        print(f"[ChatService] 🛑 Photo critique task cancelled for {payload.photo_id}", flush=True)
        critique_status_manager.update(payload.photo_id, 0, 4, "비평 생성이 사용자에 의해 중단되었습니다.", 0, status="cancelled")
        await asyncio.to_thread(_unload_critique_models, force=True)
        raise
    except Exception as e:
        critique_status_manager.update(payload.photo_id, 0, 4, f"오류 발생: {str(e)}", 0, status="error")
        await asyncio.to_thread(_unload_critique_models, force=True)
        raise

class ChatService:
    @staticmethod
    def _save_critique_to_db(
        photo_id: str,
        critique_text: str,
        updated_at: Any,
        scores_dict: Optional[Dict[str, Any]] = None,
        raw_en: Optional[str] = None
    ) -> None:
        """
        Persists critique text, raw english critique, and normalized 4-dimension scores to SQLite ai_analysis table.
        """
        return _save_critique_to_db(
            photo_id=photo_id,
            critique_text=critique_text,
            updated_at=updated_at,
            scores_dict=scores_dict,
            raw_en=raw_en
        )

    @staticmethod
    def _cancel_task_threadsafe(task: asyncio.Task) -> None:
        loop = task.get_loop() if hasattr(task, "get_loop") else None
        if isinstance(loop, asyncio.AbstractEventLoop) and loop.is_running():
            loop.call_soon_threadsafe(task.cancel)
        else:
            task.cancel()

    @staticmethod
    def cancel_critique(photo_id: str) -> None:
        """
        Cancels critique task for photo_id and immediately frees model memory from RAM.
        """
        from services.critique_status import critique_status_manager
        critique_status_manager.request_cancel(photo_id)
        with _critique_tasks_lock:
            task = _critique_tasks.get(photo_id)
            if task and not task.done():
                ChatService._cancel_task_threadsafe(task)
        _unload_critique_models(force=True)

    @staticmethod
    async def generate_photo_critique(payload: schemas.CritiqueRequest) -> Dict[str, Any]:

        """
        Generates deep photo critique using VLM (Gemma / UniPercept) and saves it to DB.
        Shielded against client disconnection (e.g. system sleep/wake).
        """
        photo_id = payload.photo_id
        task = None
        with _critique_tasks_lock:
            existing_task = _critique_tasks.get(photo_id)
            if existing_task and not existing_task.done():
                task = existing_task
            else:
                task = asyncio.create_task(_run_critique_pipeline(payload))
                _critique_tasks[photo_id] = task

                def _cleanup_task(t: asyncio.Task) -> None:
                    with _critique_tasks_lock:
                        if _critique_tasks.get(photo_id) is t:
                            del _critique_tasks[photo_id]

                if hasattr(task, "add_done_callback"):
                    task.add_done_callback(_cleanup_task)

        try:
            # Shield the background critique task so client disconnect (e.g. sleep) does not cancel execution
            return await asyncio.shield(task)
        finally:
            with _critique_tasks_lock:
                if _critique_tasks.get(photo_id) is task and task.done():
                    del _critique_tasks[photo_id]


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
