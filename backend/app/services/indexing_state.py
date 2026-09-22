"""
Indexing State Manager Module

Thread-safe encapsulation for background indexing status state, 
pause/resume events, and cancel requests.
"""

import asyncio
import threading
import logging
from typing import Dict, Any

logger = logging.getLogger("focal_node.indexing_state")

class IndexingStateManager:
    def __init__(self):
        self._status_dict: Dict[str, Any] = {
            "status": "idle",
            "total_files": 0,
            "processed_files": 0,
            "current_file": ""
        }
        self._lock = threading.RLock()
        self._pause_event: asyncio.Event | None = None
        self._pause_loop: Any = None
        self.cancel_requested = False

    @property
    def pause_event(self) -> asyncio.Event:
        with self._lock:
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if self._pause_event is None:
                self._pause_event = asyncio.Event()
                self._pause_event.set()
                self._pause_loop = current_loop
            elif current_loop is not None and self._pause_loop is not None and self._pause_loop != current_loop:
                # Re-bind event if running loop has changed (e.g. between tests or new async runner)
                was_set = self._pause_event.is_set()
                self._pause_event = asyncio.Event()
                if was_set:
                    self._pause_event.set()
                self._pause_loop = current_loop
            return self._pause_event

    @pause_event.setter
    def pause_event(self, val: asyncio.Event):
        with self._lock:
            self._pause_event = val
            try:
                self._pause_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._pause_loop = None

    def _set_event_safe(self, set_flag: bool):
        with self._lock:
            evt = self.pause_event
            target_loop = self._pause_loop
            if target_loop and target_loop.is_running():
                try:
                    current_loop = asyncio.get_running_loop()
                except RuntimeError:
                    current_loop = None

                if current_loop == target_loop:
                    if set_flag:
                        evt.set()
                    else:
                        evt.clear()
                else:
                    fn = evt.set if set_flag else evt.clear
                    target_loop.call_soon_threadsafe(fn)
            else:
                if set_flag:
                    evt.set()
                else:
                    evt.clear()

    @property
    def status(self) -> str:
        with self._lock:
            return self._status_dict["status"]

    @status.setter
    def status(self, val: str):
        with self._lock:
            self._status_dict["status"] = val

    def get_status_dict(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status_dict)

    def update_progress(self, processed_files: int, total_files: int, current_file: str):
        with self._lock:
            self._status_dict["processed_files"] = processed_files
            self._status_dict["total_files"] = total_files
            self._status_dict["current_file"] = current_file

    def reset_status(self):
        with self._lock:
            self._status_dict = {
                "status": "idle",
                "total_files": 0,
                "processed_files": 0,
                "current_file": ""
            }
            self.cancel_requested = False
            self._set_event_safe(True)

    def pause(self):
        with self._lock:
            if self._status_dict["status"] == "processing":
                self._set_event_safe(False)
                self._status_dict["status"] = "paused"
                logger.info("[IndexerState] Background indexing paused.")

    def resume(self):
        with self._lock:
            if self._status_dict["status"] == "paused":
                self._set_event_safe(True)
                self._status_dict["status"] = "processing"
                logger.info("[IndexerState] Background indexing resumed.")

    def cancel(self):
        with self._lock:
            if self._status_dict["status"] in ["processing", "paused"]:
                self.cancel_requested = True
                self._set_event_safe(True)  # Unblock pause wait if currently paused
                self._status_dict["status"] = "cancelled"
                logger.info("[IndexerState] Background indexing cancelled.")

# Global singleton manager instance
indexing_state_manager = IndexingStateManager()
