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
