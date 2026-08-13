"""
Indexing State Manager Module

Thread-safe encapsulation for background indexing status state, 
pause/resume events, and cancel requests.
"""

import asyncio
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
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # set() = running, clear() = paused
        self.cancel_requested = False

    @property
    def status(self) -> str:
        return self._status_dict["status"]

    @status.setter
    def status(self, val: str):
        self._status_dict["status"] = val

    def get_status_dict(self) -> Dict[str, Any]:
        return dict(self._status_dict)

    def update_progress(self, processed_files: int, total_files: int, current_file: str):
        self._status_dict["processed_files"] = processed_files
        self._status_dict["total_files"] = total_files
        self._status_dict["current_file"] = current_file

    def reset_status(self):
        self._status_dict = {
            "status": "idle",
            "total_files": 0,
            "processed_files": 0,
            "current_file": ""
        }
        self.cancel_requested = False
        self.pause_event.set()

    def pause(self):
        if self._status_dict["status"] == "processing":
            self.pause_event.clear()
            self._status_dict["status"] = "paused"
            logger.info("[IndexerState] Background indexing paused.")

    def resume(self):
        if self._status_dict["status"] == "paused":
            self.pause_event.set()
            self._status_dict["status"] = "processing"
            logger.info("[IndexerState] Background indexing resumed.")

    def cancel(self):
        if self._status_dict["status"] in ["processing", "paused"]:
            self.cancel_requested = True
            self.pause_event.set()  # Unblock pause wait if currently paused
            self._status_dict["status"] = "cancelled"
            logger.info("[IndexerState] Background indexing cancelled.")

# Global singleton manager instance
indexing_state_manager = IndexingStateManager()
