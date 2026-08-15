import gc
import time
import threading
from typing import Optional, Any

# Global lock to prevent MLX and PyTorch MPS from crashing due to concurrent GPU access
GPU_LOCK = threading.RLock()


class BaseKeepAliveModel:
    """
    Base class for AI model adapters requiring lazy loading, 
    active request tracking, and automatic keep-alive unloading (default 60s timeout).
    """

    def __init__(self, model_name: str, keep_alive_timeout: float = 60.0):
        self.model_name = model_name
        self.keep_alive_timeout = keep_alive_timeout

        self.model: Optional[Any] = None
        self.processor: Optional[Any] = None
        self.tokenizer: Optional[Any] = None

        self.last_used_time: float = 0.0
        self.active_requests: int = 0
        self.lock = threading.Lock()
        self.timer_thread: Optional[threading.Thread] = None
        self.timer_active: bool = False

    def touch_used(self):
        """Updates last used timestamp and ensures keep-alive timer is running."""
        self.last_used_time = time.time()
        self._start_keep_alive_timer_locked()

    def _start_keep_alive_timer_locked(self):
        if not self.timer_active:
            self.timer_active = True
            self.timer_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self.timer_thread.start()

    def _keep_alive_loop(self):
        while True:
            time.sleep(5)
            with self.lock:
                if self.active_requests > 0:
                    continue
                if self.model is None:
                    self.timer_active = False
                    break
                elapsed = time.time() - self.last_used_time
                if elapsed < self.keep_alive_timeout:
                    continue

            with GPU_LOCK:
                with self.lock:
                    if self.active_requests == 0 and self.model is not None:
                        elapsed = time.time() - self.last_used_time
                        if elapsed >= self.keep_alive_timeout:
                            print(f"[{self.model_name}] Keep-alive timeout reached ({self.keep_alive_timeout}s). Unloading model...", flush=True)
                            self._unload_model_locked()
                            break
                    elif self.model is None:
                        self.timer_active = False
                        break

    def _unload_model_locked(self):
        """Internal locked method to clear references and trigger memory garbage collection."""
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.timer_active = False

        self._on_unload()

        gc.collect()
        try:
            import torch
            if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                torch.mps.empty_cache()
        except Exception:
            pass

        try:
            import mlx.core as mx
            mx.clear_cache()
        except Exception:
            pass

    def _on_unload(self):
        """Override in subclass for custom unload steps if necessary."""
        pass

    def unload_model(self):
        """Explicitly unload model from memory and clear GPU cache immediately."""
        with GPU_LOCK:
            with self.lock:
                if self.model is not None:
                    print(f"[{self.model_name}] Explicitly unloading model to free memory...", flush=True)
                    self._unload_model_locked()
                    print(f"[{self.model_name}] Model explicitly unloaded.", flush=True)
