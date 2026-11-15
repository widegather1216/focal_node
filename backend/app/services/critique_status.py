"""Thread-safe critique status tracker and cancellation registry."""

import threading
from typing import Any, Dict, Optional, Set


class CritiqueCancelledException(Exception):
    """Raised when photo critique generation is cancelled by user request."""


def _build_idle_status(photo_id: str) -> Dict[str, Any]:
    return {
        "photo_id": photo_id,
        "step": 0,
        "total_steps": 4,
        "message": "준비 중...",
        "progress": 0,
        "status": "idle",
        "critique": None,
        "critique_en": None,
        "overall_score": None,
        "iaa_score": None,
        "iqa_score": None,
        "ista_score": None,
        "critique_updated_at": None,
    }


def _query_db_critique_fallback(photo_id: str) -> Optional[Dict[str, Any]]:
    try:
        from database import SessionLocal
        from repositories.photo_repository import PhotoRepository

        with SessionLocal() as db:
            ai_row = PhotoRepository(db).get_ai_analysis(photo_id)
            if not ai_row or not ai_row.critique:
                return None
            updated_at_str = ai_row.critique_updated_at.isoformat() if ai_row.critique_updated_at else None
            return {
                "photo_id": photo_id,
                "step": 4,
                "total_steps": 4,
                "message": "비평 완료",
                "progress": 100,
                "status": "completed",
                "critique": ai_row.critique,
                "critique_en": ai_row.critique_en,
                "overall_score": ai_row.overall_score,
                "iaa_score": ai_row.iaa_score,
                "iqa_score": ai_row.iqa_score,
                "ista_score": ai_row.ista_score,
                "critique_updated_at": updated_at_str,
            }
    except Exception as err:
        print(f"[CritiqueStatus] DB fallback query notice: {err}", flush=True)
        return None


class CritiqueStatusManager:
    """In-memory progress and cancellation status cache with bounded history eviction."""

    def __init__(self, max_history: int = 100):
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._cancelled_ids: Set[str] = set()
        self._lock = threading.Lock()
        self._max_history = max_history

    def _evict_stale_statuses_locked(self) -> None:
        """Evicts oldest terminal statuses when exceeding max_history."""
        while len(self._statuses) >= self._max_history:
            evict_key = next(
                (key for key, val in self._statuses.items() if val.get("status") in ("completed", "cancelled", "error")),
                next(iter(self._statuses)),
            )
            del self._statuses[evict_key]
            self._cancelled_ids.discard(evict_key)

        if len(self._cancelled_ids) > self._max_history * 2:
            stale_cancel = next(iter(self._cancelled_ids))
            self._cancelled_ids.discard(stale_cancel)

    def update(self, photo_id: str, step: int, total_steps: int, message: str, progress: int, status: str = "processing", **extra: Any) -> None:
        with self._lock:
            if photo_id in self._cancelled_ids and status != "cancelled":
                return
            if photo_id not in self._statuses:
                self._evict_stale_statuses_locked()
            self._statuses[photo_id] = {
                "photo_id": photo_id,
                "step": step,
                "total_steps": total_steps,
                "message": message,
                "progress": progress,
                "status": status,
                "critique": extra.get("critique"),
                "critique_en": extra.get("critique_en"),
                "overall_score": extra.get("overall_score"),
                "iaa_score": extra.get("iaa_score"),
                "iqa_score": extra.get("iqa_score"),
                "ista_score": extra.get("ista_score"),
                "critique_updated_at": extra.get("critique_updated_at"),
            }

    def get(self, photo_id: str) -> Dict[str, Any]:
        with self._lock:
            if photo_id in self._statuses:
                return dict(self._statuses[photo_id])
        db_fallback = _query_db_critique_fallback(photo_id)
        return db_fallback if db_fallback is not None else _build_idle_status(photo_id)

    def request_cancel(self, photo_id: str) -> None:
        with self._lock:
            if photo_id not in self._statuses:
                self._evict_stale_statuses_locked()
            self._cancelled_ids.add(photo_id)
            self._statuses[photo_id] = {
                "photo_id": photo_id,
                "step": 0,
                "total_steps": 4,
                "message": "비평 생성이 사용자에 의해 중단되었습니다.",
                "progress": 0,
                "status": "cancelled",
            }

    def is_cancelled(self, photo_id: str) -> bool:
        with self._lock:
            return photo_id in self._cancelled_ids

    def check_cancelled(self, photo_id: str) -> None:
        if self.is_cancelled(photo_id):
            raise CritiqueCancelledException(f"Critique generation for photo '{photo_id}' was cancelled by user.")

    def reset(self, photo_id: str) -> None:
        with self._lock:
            self._cancelled_ids.discard(photo_id)
            self._statuses.pop(photo_id, None)

    def clear(self, photo_id: str) -> None:
        self.reset(photo_id)


critique_status_manager = CritiqueStatusManager()
