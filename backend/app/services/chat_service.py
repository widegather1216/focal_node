"""Critique orchestration service coordinating UniPercept, Gemma 4, cancellation, and DB persistence."""

import asyncio
import gc
import threading
from typing import Any, Dict, List, Optional

import models
import schemas
from database import SessionLocal
from services.ai_factory import get_gemma_adapter
from services.base_model import clear_mlx_cache, clear_mps_cache
from services.critique_db_helpers import (
    extract_score_floats,
    fetch_critiques_with_session,
    get_photo_and_metadata_with_session,
    save_critique_with_session,
)

_extract_score_floats = extract_score_floats
_critique_tasks: Dict[str, asyncio.Task] = {}
_critique_tasks_lock = threading.Lock()


def _get_photo_and_metadata(photo_id: str) -> tuple[str, dict]:
    return get_photo_and_metadata_with_session(SessionLocal, photo_id)


def _save_critique_to_db(
    photo_id: str,
    critique_text: str,
    updated_at: Any,
    scores_dict: Optional[Dict[str, Any]] = None,
    raw_en: Optional[str] = None,
) -> None:
    save_critique_with_session(SessionLocal, photo_id, critique_text, updated_at, scores_dict, raw_en)


def _clear_device_caches() -> None:
    clear_mps_cache(synchronize=True)
    if clear_mlx_cache():
        gc.collect()


def _unload_critique_models(force: bool = False) -> None:
    """Safely unloads UniPercept and Gemma adapters and frees GPU caches."""
    try:
        from services.unipercept_adapter import get_unipercept_adapter

        adapter = get_unipercept_adapter()
        if hasattr(adapter, "unload_model"):
            adapter.unload_model()
    except Exception as err:
        print(f"[ChatService] Error unloading UniPercept model: {err}", flush=True)

    try:
        gemma = get_gemma_adapter()
        active_reqs = getattr(gemma, "active_requests", 0)
        should_unload = force or not isinstance(active_reqs, int) or active_reqs <= 0
        if should_unload and hasattr(gemma, "unload_model"):
            gemma.unload_model()
    except Exception as err:
        print(f"[ChatService] Error unloading Gemma model: {err}", flush=True)

    _clear_device_caches()


def _fetch_critiques_from_db(photo_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    return fetch_critiques_with_session(SessionLocal, photo_ids)


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


async def _run_unipercept_stage(file_path: str, meta_data: dict, photo_id: str) -> dict[str, Any]:
    from services.critique_status import critique_status_manager
    from services.unipercept_adapter import get_unipercept_adapter

    adapter = get_unipercept_adapter()
    try:
        ensemble_output = await asyncio.to_thread(
            adapter.generate_full_ensemble_critique,
            file_path,
            meta_data,
            photo_id,
            f_number=meta_data.get("f_number") if meta_data else None,
            iso=meta_data.get("iso") if meta_data else None,
        )
        critique_status_manager.check_cancelled(photo_id)
        return ensemble_output
    finally:
        await asyncio.to_thread(adapter.unload_model)


def _normalize_scores_dict(ensemble_output: dict[str, Any]) -> tuple[str, Optional[dict]]:
    raw_en = ensemble_output.get("critique", "")
    scores_dict = ensemble_output.get("scores", {})
    quality_score = ensemble_output.get("quality_score")
    if scores_dict and scores_dict.get("overall") is None and quality_score is not None:
        scores_dict["overall"] = quality_score
    return raw_en, scores_dict


def _format_fallback_critique(raw_en: str, scores_dict: Optional[dict]) -> str:
    return f"{_build_scoreboard_header(scores_dict)}{raw_en}" if scores_dict else raw_en


async def _run_gemma_perceptual_stage(
    file_path: str, meta_data: dict, photo_id: str, ensemble_output: dict[str, Any]
) -> tuple[str, Optional[dict], Optional[str]]:
    from services.critique_status import CritiqueCancelledException, critique_status_manager

    raw_en, scores_dict = _normalize_scores_dict(ensemble_output)
    try:
        critique_status_manager.check_cancelled(photo_id)
        gemma = get_gemma_adapter()
        critique_image = ensemble_output.get("pil_img") or file_path
        critique_text = await asyncio.to_thread(
            gemma.generate_perceptual_critique,
            image_path=critique_image,
            perceptual_anchor=raw_en,
            scores_dict=scores_dict,
            metadata=meta_data,
            photo_id=photo_id,
        )
        critique_status_manager.check_cancelled(photo_id)
        if scores_dict and "앙상블 비평 스코어보드" not in critique_text:
            critique_text = f"{_build_scoreboard_header(scores_dict)}{critique_text}"
        return critique_text, scores_dict, raw_en
    except CritiqueCancelledException:
        raise
    except Exception as gemma_err:
        print(f"[ChatService] ⚠️ Gemma perceptual critique failed ({gemma_err}), checking fallback...", flush=True)
        if raw_en and raw_en.strip():
            return _format_fallback_critique(raw_en, scores_dict), scores_dict, raw_en
        raise


async def _execute_unipercept_critique_pipeline(
    file_path: str,
    meta_data: dict,
    photo_id: str,
) -> tuple[str, Optional[dict], Optional[str]]:
    from services.critique_status import CritiqueCancelledException

    try:
        ensemble_output = await _run_unipercept_stage(file_path, meta_data, photo_id)
    except CritiqueCancelledException:
        raise
    except Exception as uni_err:
        print(f"[ChatService] ⚠️ UniPercept ensemble failed ({uni_err}). Falling back to Gemma 4 direct critique...", flush=True)
        return await _execute_gemma_critique_pipeline(file_path, meta_data, photo_id)

    print("[ChatService] UniPercept ensemble completed. Starting Gemma 4 direct perceptual critique...", flush=True)
    return await _run_gemma_perceptual_stage(file_path, meta_data, photo_id, ensemble_output)


async def _execute_gemma_critique_pipeline(
    file_path: str,
    meta_data: dict,
    photo_id: str,
) -> tuple[str, Optional[dict], Optional[str]]:
    from services.critique_status import CritiqueCancelledException, critique_status_manager

    print("[ChatService] Starting Gemma 4 VLM direct critique generation...", flush=True)
    critique_status_manager.update(photo_id, 2, 4, "비평 작성 중", 50)
    critique_text = await asyncio.to_thread(get_gemma_adapter().generate_deep_critique, file_path, meta_data, photo_id)
    critique_status_manager.check_cancelled(photo_id)

    print("[ChatService] Starting Gemma document structuring pass...", flush=True)
    critique_status_manager.update(photo_id, 3, 4, "[Gemma] 리포트 문서 양식 다듬는 중...", 75)
    try:
        structured = await asyncio.to_thread(
            get_gemma_adapter().format_and_structure_critique, critique_text, meta_data, photo_id
        )
        critique_status_manager.check_cancelled(photo_id)
        return structured, None, None
    except CritiqueCancelledException:
        raise
    except Exception as fmt_err:
        print(f"[ChatService] Document structuring fallback to draft: {fmt_err}", flush=True)
        return critique_text, None, None


def _unpack_pipeline_result(pipeline_result: Any) -> tuple[str, Optional[dict], Optional[str]]:
    if isinstance(pipeline_result, tuple):
        critique_text = pipeline_result[0]
        scores_dict = pipeline_result[1] if len(pipeline_result) > 1 else None
        raw_en = pipeline_result[2] if len(pipeline_result) > 2 else None
        return critique_text, scores_dict, raw_en
    if isinstance(pipeline_result, dict):
        return pipeline_result.get("critique", ""), pipeline_result.get("scores"), pipeline_result.get("raw_en")
    return str(pipeline_result or ""), None, None


async def _finalize_critique_success(
    payload: schemas.CritiqueRequest,
    critique_text: str,
    scores_dict: Optional[dict],
    raw_en: Optional[str],
) -> Dict[str, Any]:
    from services.critique_status import critique_status_manager

    overall_score, iaa_score, iqa_score, ista_score = _extract_score_floats(scores_dict, critique_text)
    critique_en = raw_en.strip() if (raw_en and isinstance(raw_en, str) and raw_en.strip()) else None
    updated_iso = models.utcnow().isoformat()
    await asyncio.to_thread(_save_critique_to_db, payload.photo_id, critique_text, updated_iso, scores_dict, raw_en)
    critique_status_manager.update(
        payload.photo_id, 4, 4, "비평 완료", 100, status="completed",
        critique=critique_text, critique_en=critique_en,
        overall_score=overall_score, iaa_score=iaa_score, iqa_score=iqa_score, ista_score=ista_score,
        critique_updated_at=updated_iso,
    )
    return {
        "critique": critique_text, "critique_en": critique_en,
        "overall_score": overall_score, "iaa_score": iaa_score,
        "iqa_score": iqa_score, "ista_score": ista_score,
        "critique_updated_at": updated_iso, "engine_used": payload.engine, "status": "completed",
    }


def _build_cancelled_response(engine_used: str) -> Dict[str, Any]:
    return {
        "critique": "",
        "critique_en": None,
        "overall_score": None,
        "iaa_score": None,
        "iqa_score": None,
        "ista_score": None,
        "critique_updated_at": None,
        "engine_used": engine_used,
        "status": "cancelled",
    }


async def _dispatch_engine_pipeline(payload: schemas.CritiqueRequest, file_path: str, meta_data: dict) -> Any:
    if payload.engine == "unipercept":
        return await _execute_unipercept_critique_pipeline(file_path, meta_data, payload.photo_id)
    return await _execute_gemma_critique_pipeline(file_path, meta_data, payload.photo_id)


async def _run_critique_pipeline(payload: schemas.CritiqueRequest) -> Dict[str, Any]:
    from services.critique_status import CritiqueCancelledException, critique_status_manager

    file_path, meta_data = await asyncio.to_thread(_get_photo_and_metadata, payload.photo_id)
    critique_status_manager.reset(payload.photo_id)
    critique_status_manager.update(payload.photo_id, 1, 4, "점수 산출 중", 5)
    print(f"[ChatService] Generating photo critique for {payload.photo_id} (Engine: {payload.engine})...", flush=True)
    try:
        critique_status_manager.check_cancelled(payload.photo_id)
        pipeline_result = await _dispatch_engine_pipeline(payload, file_path, meta_data)
        critique_status_manager.check_cancelled(payload.photo_id)
        critique_text, scores_dict, raw_en = _unpack_pipeline_result(pipeline_result)
        if not critique_text or not critique_text.strip():
            raise RuntimeError("Critique generation resulted in empty or invalid critique.")
        return await _finalize_critique_success(payload, critique_text, scores_dict, raw_en)
    except CritiqueCancelledException:
        critique_status_manager.update(payload.photo_id, 0, 4, "비평 생성이 사용자에 의해 중단되었습니다.", 0, status="cancelled")
        await asyncio.to_thread(_unload_critique_models, force=True)
        return _build_cancelled_response(payload.engine)
    except asyncio.CancelledError:
        critique_status_manager.update(payload.photo_id, 0, 4, "비평 생성이 사용자에 의해 중단되었습니다.", 0, status="cancelled")
        await asyncio.to_thread(_unload_critique_models, force=True)
        raise
    except Exception as err:
        critique_status_manager.update(payload.photo_id, 0, 4, f"오류 발생: {str(err)}", 0, status="error")
        await asyncio.to_thread(_unload_critique_models, force=True)
        raise


class ChatService:
    """Public critique service facade preserving task tracking and cancellation contracts."""

    @staticmethod
    def _save_critique_to_db(
        photo_id: str,
        critique_text: str,
        updated_at: Any,
        scores_dict: Optional[Dict[str, Any]] = None,
        raw_en: Optional[str] = None,
    ) -> None:
        return _save_critique_to_db(
            photo_id=photo_id,
            critique_text=critique_text,
            updated_at=updated_at,
            scores_dict=scores_dict,
            raw_en=raw_en,
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
        """Cancels critique task for photo_id and immediately frees model memory from RAM."""
        from services.critique_status import critique_status_manager

        critique_status_manager.request_cancel(photo_id)
        with _critique_tasks_lock:
            task = _critique_tasks.get(photo_id)
            if task and not task.done():
                ChatService._cancel_task_threadsafe(task)
        _unload_critique_models(force=True)

    @staticmethod
    def _get_or_create_critique_task(payload: schemas.CritiqueRequest) -> asyncio.Task:
        photo_id = payload.photo_id
        with _critique_tasks_lock:
            existing_task = _critique_tasks.get(photo_id)
            if existing_task and not existing_task.done():
                return existing_task

            task = asyncio.create_task(_run_critique_pipeline(payload))
            _critique_tasks[photo_id] = task

            def _cleanup_task(finished_task: asyncio.Task) -> None:
                with _critique_tasks_lock:
                    if _critique_tasks.get(photo_id) is finished_task:
                        del _critique_tasks[photo_id]

            if hasattr(task, "add_done_callback"):
                task.add_done_callback(_cleanup_task)
            return task

    @staticmethod
    async def generate_photo_critique(payload: schemas.CritiqueRequest) -> Dict[str, Any]:
        """Generates deep photo critique shielded against client sleep/disconnect."""
        photo_id = payload.photo_id
        task = ChatService._get_or_create_critique_task(payload)
        try:
            return await asyncio.shield(task)
        finally:
            with _critique_tasks_lock:
                if _critique_tasks.get(photo_id) is task and task.done():
                    del _critique_tasks[photo_id]

    @staticmethod
    async def generate_critique_summary(payload: Optional[schemas.CritiqueSummaryRequest] = None) -> Dict[str, Any]:
        """Generates an aggregated summary report for photo critiques using Gemma LLM."""
        critiques_list = await asyncio.to_thread(
            _fetch_critiques_from_db,
            payload.photo_ids if payload else None,
        )
        summary_text = await asyncio.to_thread(get_gemma_adapter().generate_critique_summary, critiques_list)
        now_utc = models.utcnow()
        return {
            "summary": summary_text,
            "total_critiques_analyzed": len(critiques_list),
            "created_at": now_utc.isoformat(),
        }
