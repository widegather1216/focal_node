"""
Indexing State Manager Module

Thread-safe encapsulation for background indexing status state, 
pause/resume events, and cancel requests.
"""

import asyncio
import logging
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("focal_node.indexing_state")

WaiterEntry = Tuple[asyncio.AbstractEventLoop, "asyncio.Future[bool]"]


def _get_running_loop_safe() -> Optional[asyncio.AbstractEventLoop]:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _get_bound_event_loop(event_obj: Any) -> Optional[asyncio.AbstractEventLoop]:
    bound_loop = getattr(event_obj, "_loop", None)
    if isinstance(bound_loop, asyncio.AbstractEventLoop):
        return bound_loop
    return None


def _resolve_waiter_future(waiter_future: "asyncio.Future[bool]") -> None:
    if not waiter_future.done():
        waiter_future.set_result(True)


def _dispatch_waiter_wakeup(
    waiter_loop: asyncio.AbstractEventLoop,
    waiter_future: "asyncio.Future[bool]",
    current_loop: Optional[asyncio.AbstractEventLoop],
) -> None:
    if waiter_loop.is_closed():
        return
    if current_loop is waiter_loop:
        _resolve_waiter_future(waiter_future)
        return
    try:
        waiter_loop.call_soon_threadsafe(_resolve_waiter_future, waiter_future)
    except RuntimeError as exc:
        logger.debug("[IndexerState] Failed to wake waiter on closed loop: %s", exc)


def _dispatch_custom_event_update(
    custom_event: Any,
    custom_loop: Optional[asyncio.AbstractEventLoop],
    current_loop: Optional[asyncio.AbstractEventLoop],
    set_flag: bool,
) -> None:
    action = custom_event.set if set_flag else custom_event.clear
    if custom_loop is None:
        try:
            action()
        except RuntimeError as exc:
            logger.debug("[IndexerState] Failed to update unbound custom event: %s", exc)
        return
    if custom_loop.is_closed():
        return
    if current_loop is custom_loop:
        action()
        return
    try:
        custom_loop.call_soon_threadsafe(action)
    except RuntimeError as exc:
        logger.debug("[IndexerState] Failed to signal custom event loop: %s", exc)


class _ThreadSafeAsyncEvent(asyncio.Event):
    """Thread-safe, multi-loop async event preserving asyncio.Event interface."""

    def __init__(self, lock: threading.RLock, initial_set: bool = True) -> None:
        super().__init__()
        self._lock = lock
        self._value = bool(initial_set)
        self._waiter_entries: list[WaiterEntry] = []

    def __repr__(self) -> str:
        with self._lock:
            status_label = "set" if self._value else "unset"
            waiter_count = len(self._waiter_entries)
        extra = f"{status_label}, waiters:{waiter_count}" if waiter_count else status_label
        return f"<{object.__repr__(self)[1:-1]} [{extra}]>"

    def is_set(self) -> bool:
        with self._lock:
            return self._value

    def apply_state_locked(self, set_flag: bool) -> list[WaiterEntry]:
        if not set_flag:
            self._value = False
            return []
        self._value = True
        pending_waiters = list(self._waiter_entries)
        self._waiter_entries.clear()
        return pending_waiters

    def set(self) -> None:
        with self._lock:
            pending_waiters = self.apply_state_locked(True)
        current_loop = _get_running_loop_safe()
        for waiter_loop, waiter_future in pending_waiters:
            _dispatch_waiter_wakeup(waiter_loop, waiter_future, current_loop)

    def clear(self) -> None:
        with self._lock:
            self.apply_state_locked(False)

    def register_waiter_locked(
        self, running_loop: asyncio.AbstractEventLoop
    ) -> Optional[WaiterEntry]:
        self._waiter_entries = [
            (loop, future) for loop, future in self._waiter_entries if not loop.is_closed()
        ]
        if self._value:
            return None
        waiter_future = running_loop.create_future()
        entry = (running_loop, waiter_future)
        self._waiter_entries.append(entry)
        return entry

    def remove_waiter(self, target_entry: WaiterEntry) -> None:
        _, target_future = target_entry
        with self._lock:
            self._waiter_entries = [
                (loop, future)
                for loop, future in self._waiter_entries
                if future is not target_future
            ]

    async def await_entry(self, entry: WaiterEntry) -> bool:
        _, waiter_future = entry
        try:
            await waiter_future
            return True
        finally:
            self.remove_waiter(entry)

    async def wait(self) -> bool:
        running_loop = asyncio.get_running_loop()
        with self._lock:
            entry = self.register_waiter_locked(running_loop)
        if entry is None:
            return True
        return await self.await_entry(entry)


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
        self._pause_gate = _ThreadSafeAsyncEvent(self._lock, initial_set=True)
        self._pause_event: asyncio.Event = self._pause_gate
        self._pause_loop: Optional[asyncio.AbstractEventLoop] = None

    def _is_custom_event_stale_locked(
        self, current_loop: Optional[asyncio.AbstractEventLoop]
    ) -> bool:
        if self._pause_event is self._pause_gate:
            return False
        bound_loop = _get_bound_event_loop(self._pause_event)
        if bound_loop is None:
            return False
        if bound_loop.is_closed():
            return True
        return current_loop is not None and bound_loop is not current_loop

    def _refresh_pause_loop_locked(
        self, current_loop: Optional[asyncio.AbstractEventLoop]
    ) -> None:
        if self._pause_loop is not None and self._pause_loop.is_closed():
            self._pause_loop = None

        if self._pause_event is self._pause_gate:
            if current_loop is not None:
                self._pause_loop = current_loop
            return

        if self._is_custom_event_stale_locked(current_loop):
            self._pause_event = self._pause_gate
            self._pause_loop = current_loop
            return

        bound_loop = _get_bound_event_loop(self._pause_event)
        if bound_loop is not None:
            self._pause_loop = bound_loop
        elif self._pause_loop is None and current_loop is not None:
            self._pause_loop = current_loop

    def _prepare_event_transition_locked(
        self, set_flag: bool, current_loop: Optional[asyncio.AbstractEventLoop]
    ) -> Tuple[list[WaiterEntry], Any, Optional[asyncio.AbstractEventLoop]]:
        self._refresh_pause_loop_locked(current_loop)
        pending_waiters = self._pause_gate.apply_state_locked(set_flag)
        custom_event = None if self._pause_event is self._pause_gate else self._pause_event
        return pending_waiters, custom_event, self._pause_loop

    def _dispatch_event_wakeups(
        self,
        pending_waiters: list[WaiterEntry],
        custom_event: Any,
        custom_loop: Optional[asyncio.AbstractEventLoop],
        current_loop: Optional[asyncio.AbstractEventLoop],
        set_flag: bool,
    ) -> None:
        for waiter_loop, waiter_future in pending_waiters:
            _dispatch_waiter_wakeup(waiter_loop, waiter_future, current_loop)
        if custom_event is not None:
            _dispatch_custom_event_update(custom_event, custom_loop, current_loop, set_flag)

    @property
    def pause_event(self) -> asyncio.Event:
        with self._lock:
            current_loop = _get_running_loop_safe()
            self._refresh_pause_loop_locked(current_loop)
            return self._pause_event

    @pause_event.setter
    def pause_event(self, new_event: asyncio.Event):
        current_loop = _get_running_loop_safe()
        pending_waiters: list[WaiterEntry] = []
        with self._lock:
            self._pause_event = new_event
            bound_loop = _get_bound_event_loop(new_event)
            target_loop = bound_loop if bound_loop is not None else current_loop
            if target_loop is not None and target_loop.is_closed():
                target_loop = None
            self._pause_loop = target_loop
            if new_event is not self._pause_gate:
                pending_waiters = self._pause_gate.apply_state_locked(bool(new_event.is_set()))
        for waiter_loop, waiter_future in pending_waiters:
            _dispatch_waiter_wakeup(waiter_loop, waiter_future, current_loop)

    def _set_event_safe(self, set_flag: bool):
        current_loop = _get_running_loop_safe()
        with self._lock:
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                set_flag, current_loop
            )
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, set_flag
        )

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

    def _acquire_wait_step_locked(
        self,
        effective_run_id: Optional[int],
        running_loop: asyncio.AbstractEventLoop,
    ) -> Tuple[str, Any]:
        self._refresh_pause_loop_locked(running_loop)
        if self.is_run_cancelled(effective_run_id):
            return ("cancelled", None)
        if self._pause_event is not self._pause_gate:
            return ("custom", self._pause_event)
        if self._pause_gate.is_set():
            return ("ready", None)
        entry = self._pause_gate.register_waiter_locked(running_loop)
        return ("wait", entry) if entry is not None else ("ready", None)

    async def wait_if_paused(self, run_id: Optional[int] = None) -> bool:
        """Waits atomically while paused unless the run is cancelled or superseded."""
        running_loop = asyncio.get_running_loop()
        with self._lock:
            effective_run_id = (
                run_id if run_id is not None else (self._run_generation if self._run_generation > 0 else None)
            )

        while True:
            with self._lock:
                step, payload = self._acquire_wait_step_locked(effective_run_id, running_loop)
            if step == "cancelled":
                return False
            if step == "ready":
                return True
            if step == "custom":
                await payload.wait()
                return not self.is_run_cancelled(effective_run_id)
            await self._pause_gate.await_entry(payload)

    def try_start_indexing(self) -> bool:
        """
        Atomically checks if indexing can start and preempts the status to 'processing'.
        Returns True if status successfully transitioned to 'processing'.
        Returns False if indexing is already in progress or paused.
        """
        current_loop = _get_running_loop_safe()
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
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                True, current_loop
            )
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, True
        )
        return True

    def _resolve_active_run_id_locked(self, run_id: Optional[int]) -> Optional[int]:
        if run_id is None:
            self._run_generation += 1
            return self._run_generation
        if run_id != self._run_generation or run_id in self._cancelled_run_ids:
            return None
        return run_id

    def initialize_background_run(self, run_id: Optional[int] = None) -> Optional[int]:
        """
        Ensures processing state and active event for background task startup
        without momentarily resetting status to 'idle'.
        Returns None if the scheduled run_id was already cancelled or superseded.
        """
        current_loop = _get_running_loop_safe()
        with self._lock:
            active_run_id = self._resolve_active_run_id_locked(run_id)
            if active_run_id is None:
                return None

            preserve_paused = run_id is not None and self._status_dict["status"] == "paused"
            if not preserve_paused:
                self._status_dict["status"] = "processing"
            self._status_dict["error_message"] = None
            self._status_dict["run_id"] = active_run_id
            self._cancel_requested = False
            desired_set = not preserve_paused
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                desired_set, current_loop
            )
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, desired_set
        )
        return active_run_id

    def _apply_final_status_locked(
        self, error_message: Optional[str], run_id: Optional[int]
    ) -> str:
        is_cancelled = self._cancel_requested or (
            run_id is not None and run_id in self._cancelled_run_ids
        )
        if is_cancelled:
            self._status_dict["status"] = "cancelled"
            self._status_dict["error_message"] = None
            return "cancelled"
        if error_message is not None:
            self._status_dict["status"] = "error"
            self._status_dict["error_message"] = error_message
            return "error"
        self._status_dict["status"] = "idle"
        self._status_dict["total_files"] = 0
        self._status_dict["processed_files"] = 0
        self._status_dict["current_file"] = ""
        self._status_dict["error_message"] = None
        return "idle"

    def finalize_run(
        self,
        error_message: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        Atomically finalizes a background indexing run into 'cancelled', 'error', or 'idle'.
        Returns None if run_id belongs to a superseded run so stale tasks cannot overwrite state.
        """
        current_loop = _get_running_loop_safe()
        with self._lock:
            if run_id is not None and run_id != self._run_generation:
                return None
            final_status = self._apply_final_status_locked(error_message, run_id)
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                True, current_loop
            )
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, True
        )
        return final_status

    def reset_status(self):
        current_loop = _get_running_loop_safe()
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
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                True, current_loop
            )
            self._pause_event = self._pause_gate
            self._pause_loop = current_loop
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, True
        )

    def pause(self) -> bool:
        current_loop = _get_running_loop_safe()
        with self._lock:
            if self._status_dict["status"] != "processing":
                return False
            self._status_dict["status"] = "paused"
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                False, current_loop
            )
            logger.info("[IndexerState] Background indexing paused.")
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, False
        )
        return True

    def resume(self) -> bool:
        current_loop = _get_running_loop_safe()
        with self._lock:
            if self._status_dict["status"] != "paused":
                return False
            self._status_dict["status"] = "processing"
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                True, current_loop
            )
            logger.info("[IndexerState] Background indexing resumed.")
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, True
        )
        return True

    def cancel(self) -> bool:
        current_loop = _get_running_loop_safe()
        with self._lock:
            if self._status_dict["status"] not in ["processing", "paused"]:
                return False
            self._cancel_requested = True
            if self._run_generation > 0:
                self._record_cancelled_run(self._run_generation)
            self._status_dict["status"] = "cancelled"
            pending_waiters, custom_event, custom_loop = self._prepare_event_transition_locked(
                True, current_loop
            )
            logger.info("[IndexerState] Background indexing cancelled.")
        self._dispatch_event_wakeups(
            pending_waiters, custom_event, custom_loop, current_loop, True
        )
        return True

# Global singleton manager instance
indexing_state_manager = IndexingStateManager()
