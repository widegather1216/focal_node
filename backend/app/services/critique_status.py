import threading
from typing import Dict, Any, Set

class CritiqueCancelledException(Exception):
    """Raised when photo critique generation is cancelled by user request."""
    pass

class CritiqueStatusManager:
    def __init__(self):
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._cancelled_ids: Set[str] = set()
        self._lock = threading.Lock()

    def update(self, photo_id: str, step: int, total_steps: int, message: str, progress: int, status: str = "processing"):
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
            }

    def get(self, photo_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._statuses.get(photo_id, {
                "photo_id": photo_id,
                "step": 0,
                "total_steps": 4,
                "message": "준비 중...",
                "progress": 0,
                "status": "idle"
            })

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
