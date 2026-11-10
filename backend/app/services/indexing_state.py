"""
Indexing State Manager Module

Thread-safe encapsulation for background indexing status state, 
pause/resume events, and cancel requests.
"""

import asyncio
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("focal_node.indexing_state")

class IndexingStateManager:
    def __init__(self):
        self._run_generation: int = 0
        self._cancelled_run_ids: set[int] = set()
        self._cancel_requested: bool = False
        self._status_dict: Dict[str, Any] = {
            "status": "idle",
            "total_files": 0,
            "processed_files": 0,
            "current_file": "",
            "error_message": None,
            "run_id": 0,
        }
        self._lock = threading.RLock()
        self._pause_event: asyncio.Event | None = None
        self._pause_loop: Any = None

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
    def cancel_requested(self) -> bool:
        with self._lock:
            return self._cancel_requested

    @cancel_requested.setter
    def cancel_requested(self, val: bool) -> None:
        with self._lock:
            self._cancel_requested = bool(val)

    @property
    def current_run_id(self) -> int:
        with self._lock:
            return self._run_generation

    def _record_cancelled_run(self, run_id: int) -> None:
        if len(self._cancelled_run_ids) >= 64:
            oldest_run = min(self._cancelled_run_ids)
            self._cancelled_run_ids.discard(oldest_run)
        self._cancelled_run_ids.add(run_id)

    def is_run_cancelled(self, run_id: Optional[int] = None) -> bool:
        with self._lock:
            if run_id is None:
                return self._cancel_requested
            return run_id in self._cancelled_run_ids or run_id != self._run_generation

    def is_run_active(self, run_id: Optional[int] = None) -> bool:
        return not self.is_run_cancelled(run_id)

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

    def update_progress(
        self,
        processed_files: int,
        total_files: int,
        current_file: str,
        run_id: Optional[int] = None,
    ):
        with self._lock:
            if run_id is not None and run_id != self._run_generation:
                return
            self._status_dict["processed_files"] = processed_files
            self._status_dict["total_files"] = total_files
            self._status_dict["current_file"] = current_file

    def try_start_indexing(self) -> bool:
        """
        Atomically checks if indexing can start and preempts the status to 'processing'.
        Returns True if status successfully transitioned to 'processing'.
        Returns False if indexing is already in progress or paused.
        """
        with self._lock:
            if self._status_dict["status"] in ["processing", "paused"]:
                return False
            self._run_generation += 1
            self._status_dict["status"] = "processing"
            self._status_dict["total_files"] = 0
            self._status_dict["processed_files"] = 0
            self._status_dict["current_file"] = ""
            self._status_dict["error_message"] = None
            self._status_dict["run_id"] = self._run_generation
            self._cancel_requested = False
            self._set_event_safe(True)
            return True

    def initialize_background_run(self, run_id: Optional[int] = None) -> Optional[int]:
        """
        Ensures processing state and active event for background task startup
        without momentarily resetting status to 'idle'.
        Returns None if the scheduled run_id was already cancelled or superseded.
        """
        with self._lock:
            if run_id is not None:
                if run_id != self._run_generation or run_id in self._cancelled_run_ids:
                    return None
                active_run_id = run_id
            else:
                self._run_generation += 1
                active_run_id = self._run_generation

            self._status_dict["status"] = "processing"
            self._status_dict["error_message"] = None
            self._status_dict["run_id"] = active_run_id
            self._cancel_requested = False
            self._set_event_safe(True)
            return active_run_id

    def finalize_run(
        self,
        error_message: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        Atomically finalizes a background indexing run into 'cancelled', 'error', or 'idle'.
        Returns None if run_id belongs to a superseded run so stale tasks cannot overwrite state.
        """
        with self._lock:
            if run_id is not None and run_id != self._run_generation:
                return None

            is_cancelled = self._cancel_requested or (
                run_id is not None and run_id in self._cancelled_run_ids
            )
            if is_cancelled:
                self._status_dict["status"] = "cancelled"
                self._status_dict["error_message"] = None
                self._set_event_safe(True)
                return "cancelled"

            if error_message is not None:
                self._status_dict["status"] = "error"
                self._status_dict["error_message"] = error_message
                self._set_event_safe(True)
                return "error"

            self._status_dict["status"] = "idle"
            self._status_dict["total_files"] = 0
            self._status_dict["processed_files"] = 0
            self._status_dict["current_file"] = ""
            self._status_dict["error_message"] = None
            return "idle"

    def reset_status(self):
        with self._lock:
            self._run_generation += 1
            self._status_dict = {
                "status": "idle",
                "total_files": 0,
                "processed_files": 0,
                "current_file": "",
                "error_message": None,
                "run_id": self._run_generation,
            }
            self._cancel_requested = False
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
                self._cancel_requested = True
                if self._run_generation > 0:
                    self._record_cancelled_run(self._run_generation)
                self._set_event_safe(True)  # Unblock pause wait if currently paused
                self._status_dict["status"] = "cancelled"
                logger.info("[IndexerState] Background indexing cancelled.")

# Global singleton manager instance
indexing_state_manager = IndexingStateManager()
