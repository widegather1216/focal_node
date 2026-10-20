import threading
from typing import Dict, Any, Set, Optional

class CritiqueCancelledException(Exception):
    """Raised when photo critique generation is cancelled by user request."""
    pass

class CritiqueStatusManager:
    def __init__(self):
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._cancelled_ids: Set[str] = set()
        self._lock = threading.Lock()

    def update(
        self,
        photo_id: str,
        step: int,
        total_steps: int,
        message: str,
        progress: int,
        status: str = "processing",
        critique: Optional[str] = None,
        critique_updated_at: Optional[str] = None,
        critique_en: Optional[str] = None,
        overall_score: Optional[float] = None,
        iaa_score: Optional[float] = None,
        iqa_score: Optional[float] = None,
        ista_score: Optional[float] = None,
    ):
        with self._lock:
            # If already cancelled, do not overwrite status unless explicitly resetting
            if photo_id in self._cancelled_ids and status != "cancelled":
                return
            self._statuses[photo_id] = {
                "photo_id": photo_id,
                "step": step,
                "total_steps": total_steps,
                "message": message,
                "progress": progress,
                "status": status,
                "critique": critique,
                "critique_en": critique_en,
                "overall_score": overall_score,
                "iaa_score": iaa_score,
                "iqa_score": iqa_score,
                "ista_score": ista_score,
                "critique_updated_at": critique_updated_at,
            }

    def get(self, photo_id: str) -> Dict[str, Any]:
        with self._lock:
            if photo_id in self._statuses:
                return dict(self._statuses[photo_id])

        # Self-healing fallback: check database if critique already exists
        # Useful when sleep/resume occurs or memory status was cleared
        try:
            from database import SessionLocal
            import models
            with SessionLocal() as db:
                ai = db.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
                if ai and ai.critique:
                    updated_at_str = ai.critique_updated_at.isoformat() if ai.critique_updated_at else None
                    return {
                        "photo_id": photo_id,
                        "step": 4,
                        "total_steps": 4,
                        "message": "비평 완료",
                        "progress": 100,
                        "status": "completed",
                        "critique": ai.critique,
                        "critique_en": ai.critique_en,
                        "overall_score": ai.overall_score,
                        "iaa_score": ai.iaa_score,
                        "iqa_score": ai.iqa_score,
                        "ista_score": ai.ista_score,
                        "critique_updated_at": updated_at_str,
                    }
        except Exception as e:
            print(f"[CritiqueStatus] DB fallback query notice: {e}", flush=True)

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


    def request_cancel(self, photo_id: str):
        with self._lock:
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

    def check_cancelled(self, photo_id: str):
        if self.is_cancelled(photo_id):
            raise CritiqueCancelledException(f"Critique generation for photo '{photo_id}' was cancelled by user.")

    def reset(self, photo_id: str):
        with self._lock:
            self._cancelled_ids.discard(photo_id)
            if photo_id in self._statuses:
                del self._statuses[photo_id]

    def clear(self, photo_id: str):
        with self._lock:
            self._cancelled_ids.discard(photo_id)
            if photo_id in self._statuses:
                del self._statuses[photo_id]

critique_status_manager = CritiqueStatusManager()
