import threading
from types import SimpleNamespace
import numpy as np
import pytest
import torch

from services.siglip_adapter import SigLIP2Adapter
from services.taxonomy import SIGLIP_VISUAL_TAXONOMY


class _EnforcingMaxLengthProcessor:
    """Processor stub that simulates SiglipProcessor's default unbounded length unless truncated."""

    def __init__(self, max_position_embeddings: int = 64):
        self.max_position_embeddings = max_position_embeddings
        self.calls: list[dict] = []

    def __call__(self, text, padding=None, truncation=False, max_length=None, return_tensors=None):
        self.calls.append(
            {
                "text": text,
                "padding": padding,
                "truncation": truncation,
                "max_length": max_length,
                "return_tensors": return_tensors,
            }
        )
        longest_tokens = max((len(item.split()) for item in text), default=1)
        seq_len = max_length if (truncation and max_length is not None) else max(longest_tokens, self.max_position_embeddings)
        return {"input_ids": torch.ones((len(text), seq_len), dtype=torch.long)}


class _FakeEncodedBatch(dict):
    def to(self, _device):
        return self


class _EnforcingFakeProcessor(_EnforcingMaxLengthProcessor):
    def __call__(self, text, padding=None, truncation=False, max_length=None, return_tensors=None):
        batch = super().__call__(
            text=text,
            padding=padding,
            truncation=truncation,
            max_length=max_length,
            return_tensors=return_tensors,
        )
        return _FakeEncodedBatch(batch)


class _StrictSiglipTextModel:
    """Model stub that raises ValueError when sequence length exceeds max_position_embeddings (64)."""

    def __init__(self, max_position_embeddings: int = 64):
        self.config = SimpleNamespace(
            text_config=SimpleNamespace(max_position_embeddings=max_position_embeddings)
        )

    def get_text_features(self, input_ids, **_kwargs):
        if input_ids.shape[1] > self.config.text_config.max_position_embeddings:
            raise ValueError(
                f"Sequence length {input_ids.shape[1]} exceeds max_position_embeddings "
                f"{self.config.text_config.max_position_embeddings}"
            )
        embeddings = torch.ones((input_ids.shape[0], 768), dtype=torch.float32)
        return SimpleNamespace(pooler_output=embeddings)


def _build_stub_adapter(max_position_embeddings: int = 64) -> tuple[SigLIP2Adapter, _EnforcingFakeProcessor]:
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.device = "cpu"
    adapter.model_id = "google/siglip2-base-patch16-224"
    adapter.model = _StrictSiglipTextModel(max_position_embeddings=max_position_embeddings)
    processor = _EnforcingFakeProcessor(max_position_embeddings=max_position_embeddings)
    adapter.processor = processor
    adapter.cached_taxonomy_embeddings = None
    adapter.lock = threading.RLock()
    return adapter, processor


def test_siglip_taxonomy_taxonomy_defined():
    assert len(SIGLIP_VISUAL_TAXONOMY) > 50
    assert "바다" in SIGLIP_VISUAL_TAXONOMY
    assert "흑백" in SIGLIP_VISUAL_TAXONOMY


def test_siglip_adapter_get_zero_shot_hints_with_mocked_taxonomy():
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.cached_taxonomy_embeddings = np.zeros((len(SIGLIP_VISUAL_TAXONOMY), 768), dtype=np.float32)
    adapter.cached_taxonomy_embeddings[0, 0] = 1.0
    adapter.cached_taxonomy_embeddings[1, 0] = 0.9

    fake_img_emb = [0.0] * 768
    fake_img_emb[0] = 1.0

    hints = adapter.get_zero_shot_hints(fake_img_emb, top_k=2)
    assert hints == [SIGLIP_VISUAL_TAXONOMY[0], SIGLIP_VISUAL_TAXONOMY[1]]


def test_tc_src_08_siglip_get_text_embedding_truncates_over_64_tokens():
    adapter, processor = _build_stub_adapter(max_position_embeddings=64)
    long_query = " ".join(["비 내리는 밤거리 네온사인 시네마틱 골목길 portrait sunset bokeh"] * 12)

    embedding = adapter.get_text_embedding(long_query)

    assert len(embedding) == 768
    assert processor.calls[-1]["padding"] == "max_length"
    assert processor.calls[-1]["truncation"] is True
    assert processor.calls[-1]["max_length"] == 64


def test_tc_src_08_siglip_precompute_taxonomy_passes_truncation_and_max_length():
    adapter, processor = _build_stub_adapter(max_position_embeddings=64)

    adapter._precompute_taxonomy_embeddings()

    assert adapter.cached_taxonomy_embeddings is not None
    assert adapter.cached_taxonomy_embeddings.shape == (len(SIGLIP_VISUAL_TAXONOMY), 768)
    assert processor.calls[-1]["padding"] == "max_length"
    assert processor.calls[-1]["truncation"] is True
    assert processor.calls[-1]["max_length"] == 64


def test_tc_src_08_siglip_get_zero_shot_hints_accepts_ndarray_and_empty_inputs():
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.cached_taxonomy_embeddings = np.zeros((len(SIGLIP_VISUAL_TAXONOMY), 768), dtype=np.float32)
    adapter.cached_taxonomy_embeddings[0, 0] = 1.0
    adapter.cached_taxonomy_embeddings[1, 0] = 0.9

    ndarray_emb = np.zeros(768, dtype=np.float32)
    ndarray_emb[0] = 1.0

    hints = adapter.get_zero_shot_hints(ndarray_emb, top_k=2)
    assert hints == [SIGLIP_VISUAL_TAXONOMY[0], SIGLIP_VISUAL_TAXONOMY[1]]
    assert adapter.get_zero_shot_hints(None) == []
    assert adapter.get_zero_shot_hints([]) == []
    assert adapter.get_zero_shot_hints(np.array([], dtype=np.float32)) == []


class _TrackedRLock:
    """Test RLock wrapper that asserts GPU_LOCK -> adapter.lock ordering per thread."""

    def __init__(self, name: str, inner_lock: threading.RLock, thread_state: threading.local):
        self.name = name
        self._inner = inner_lock
        self._thread_state = thread_state

    def _held_names(self) -> list[str]:
        stack = getattr(self._thread_state, "held", None)
        if stack is None:
            stack = []
            self._thread_state.held = stack
        return stack

    def __enter__(self):
        held = self._held_names()
        if self.name == "GPU_LOCK" and "adapter.lock" in held:
            raise AssertionError(f"Lock order inversion detected: {held} -> GPU_LOCK")
        self._inner.acquire()
        held.append(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        held = self._held_names()
        assert held and held[-1] == self.name, f"Unexpected unlock order: {held} exiting {self.name}"
        held.pop()
        self._inner.release()
        return False


class _LockObservingBatch(dict):
    def __init__(self, batch: dict, on_to_device):
        super().__init__(batch)
        self._on_to_device = on_to_device

    def to(self, device):
        self._on_to_device(device)
        return self


class _LockObservingProcessor(_EnforcingMaxLengthProcessor):
    def __init__(self, max_position_embeddings: int, on_to_device):
        super().__init__(max_position_embeddings=max_position_embeddings)
        self._on_to_device = on_to_device

    def __call__(self, text, padding=None, truncation=False, max_length=None, return_tensors=None):
        batch = super().__call__(
            text=text,
            padding=padding,
            truncation=truncation,
            max_length=max_length,
            return_tensors=return_tensors,
        )
        return _LockObservingBatch(batch, self._on_to_device)


def test_tc_src_14_precompute_taxonomy_holds_gpu_lock_and_adapter_lock_without_inversion(monkeypatch):
    import services.siglip_adapter as siglip_module

    thread_state = threading.local()
    tracked_gpu_lock = _TrackedRLock("GPU_LOCK", threading.RLock(), thread_state)
    tracked_adapter_lock = _TrackedRLock("adapter.lock", threading.RLock(), thread_state)
    monkeypatch.setattr(siglip_module, "GPU_LOCK", tracked_gpu_lock)

    observed_to_locks: list[list[str]] = []
    observed_infer_locks: list[list[str]] = []

    def record_to_device(_device):
        observed_to_locks.append(list(getattr(thread_state, "held", [])))

    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.device = "mps"
    adapter.model_id = "google/siglip2-base-patch16-224"
    adapter.cached_taxonomy_embeddings = None
    adapter.lock = tracked_adapter_lock

    base_model = _StrictSiglipTextModel(max_position_embeddings=64)

    def wrapped_get_text_features(**kwargs):
        observed_infer_locks.append(list(getattr(thread_state, "held", [])))
        return base_model.get_text_features(**kwargs)

    adapter.model = SimpleNamespace(config=base_model.config, get_text_features=wrapped_get_text_features)
    processor = _LockObservingProcessor(64, record_to_device)
    adapter.processor = processor

    worker_count = 8
    barrier = threading.Barrier(worker_count)
    errors: list[BaseException] = []

    def run_precompute():
        try:
            barrier.wait(timeout=5)
            adapter._precompute_taxonomy_embeddings()
        except BaseException as err:
            errors.append(err)

    threads = [threading.Thread(target=run_precompute) for _ in range(worker_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert len(processor.calls) == 1
    assert observed_to_locks == [["GPU_LOCK", "adapter.lock"]]
    assert observed_infer_locks == [["GPU_LOCK", "adapter.lock"]]
    assert adapter.cached_taxonomy_embeddings is not None
    assert adapter.cached_taxonomy_embeddings.shape == (len(SIGLIP_VISUAL_TAXONOMY), 768)


def test_tc_src_14_load_model_completes_taxonomy_before_concurrent_callers_proceed(monkeypatch):
    import services.siglip_adapter as siglip_module

    thread_state = threading.local()
    tracked_gpu_lock = _TrackedRLock("GPU_LOCK", threading.RLock(), thread_state)
    tracked_adapter_lock = _TrackedRLock("adapter.lock", threading.RLock(), thread_state)
    monkeypatch.setattr(siglip_module, "GPU_LOCK", tracked_gpu_lock)

    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.device = "mps"
    adapter.model_id = "google/siglip2-base-patch16-224"
    adapter.model = None
    adapter.processor = None
    adapter.cached_taxonomy_embeddings = None
    adapter.lock = tracked_adapter_lock

    to_device_locks: list[list[str]] = []
    processor = _LockObservingProcessor(
        64, lambda _dev: to_device_locks.append(list(getattr(thread_state, "held", [])))
    )
    stub_model = _StrictSiglipTextModel(max_position_embeddings=64)
    load_count = 0

    def fake_load_pretrained():
        nonlocal load_count
        load_count += 1
        return stub_model, processor

    monkeypatch.setattr(adapter, "_load_pretrained_with_fallback", fake_load_pretrained)

    worker_count = 6
    barrier = threading.Barrier(worker_count)
    observed_cached: list[bool] = []
    errors: list[BaseException] = []

    def run_load():
        try:
            barrier.wait(timeout=5)
            adapter._load_model()
            observed_cached.append(adapter.cached_taxonomy_embeddings is not None)
        except BaseException as err:
            errors.append(err)

    threads = [threading.Thread(target=run_load) for _ in range(worker_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert load_count == 1
    assert len(processor.calls) == 1
    assert to_device_locks == [["GPU_LOCK", "adapter.lock"]]
    assert observed_cached == [True] * worker_count


def test_tc_src_14_get_zero_shot_hints_uses_lock_snapshot_against_concurrent_clear():
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.cached_taxonomy_embeddings = np.zeros((len(SIGLIP_VISUAL_TAXONOMY), 768), dtype=np.float32)
    adapter.cached_taxonomy_embeddings[0, 0] = 1.0
    adapter.lock = threading.RLock()

    def fake_get_image_embedding(_path: str):
        with adapter.lock:
            adapter.cached_taxonomy_embeddings = None
        vec = [0.0] * 768
        vec[0] = 1.0
        return vec

    adapter.get_image_embedding = fake_get_image_embedding

    hints = adapter.get_zero_shot_hints("/fake/photo.jpg", top_k=1)
    assert hints == [SIGLIP_VISUAL_TAXONOMY[0]]
    assert adapter.get_zero_shot_hints([0.0] * 768) == []


def test_tc_src_14_precompute_waits_for_external_gpu_lock_holder_before_mps_transfer(monkeypatch):
    import services.siglip_adapter as siglip_module

    gpu_lock = threading.RLock()
    monkeypatch.setattr(siglip_module, "GPU_LOCK", gpu_lock)

    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.device = "mps"
    adapter.model_id = "google/siglip2-base-patch16-224"
    adapter.cached_taxonomy_embeddings = None
    adapter.lock = threading.RLock()
    adapter.model = _StrictSiglipTextModel(max_position_embeddings=64)

    events: list[str] = []
    adapter.processor = _LockObservingProcessor(64, lambda _dev: events.append("to_device"))

    holder_acquired = threading.Event()
    release_holder = threading.Event()

    def external_gpu_worker():
        with gpu_lock:
            events.append("gpu_holder_entered")
            holder_acquired.set()
            release_holder.wait(timeout=5)
            events.append("gpu_holder_exiting")

    holder_thread = threading.Thread(target=external_gpu_worker)
    holder_thread.start()
    assert holder_acquired.wait(timeout=5)

    worker_thread = threading.Thread(target=adapter._precompute_taxonomy_embeddings)
    worker_thread.start()

    # Give worker a brief window to attempt GPU_LOCK acquisition; it must not call .to(device) yet.
    assert not release_holder.wait(timeout=0.05)
    assert events == ["gpu_holder_entered"]

    release_holder.set()
    holder_thread.join(timeout=5)
    worker_thread.join(timeout=5)

    assert events == ["gpu_holder_entered", "gpu_holder_exiting", "to_device"]
    assert adapter.cached_taxonomy_embeddings is not None
