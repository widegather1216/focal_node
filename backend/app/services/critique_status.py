import threading
from typing import Dict, Any

class CritiqueStatusManager:
    def __init__(self):
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def update(self, photo_id: str, step: int, total_steps: int, message: str, progress: int, status: str = "processing"):
        with self._lock:
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

    def clear(self, photo_id: str):
        with self._lock:
            if photo_id in self._statuses:
                del self._statuses[photo_id]

critique_status_manager = CritiqueStatusManager()
