import logging
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import torch

from models import AIAnalysis, Image, ImageMetadata
from services.siglip_adapter import SigLIP2Adapter


def _seed_photo(
    db_session,
    photo_id: str,
    file_name: str,
    caption: str,
    tags_json: str,
    iso: int = 200,
) -> None:
    image_row = Image(
        id=photo_id,
        parent_dir="/test",
        file_path=f"/test/{file_name}",
        file_name=file_name,
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg",
    )
    metadata_row = ImageMetadata(
        image_id=photo_id,
        iso=iso,
        f_number=2.8,
        focal_length=50.0,
    )
    analysis_row = AIAnalysis(
        image_id=photo_id,
        caption=caption,
        tags=tags_json,
    )
    db_session.add_all([image_row, metadata_row, analysis_row])
    db_session.commit()


def test_search_photos_text(client, db_session, monkeypatch):
    mock_siglip = MagicMock()
    mock_siglip.get_text_embedding.return_value = [0.1] * 768
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: mock_siglip)

    _seed_photo(
        db_session,
        photo_id="search_test_1",
        file_name="search.jpg",
        caption="A beautiful sunset over the mountains",
        tags_json='["sunset", "mountain"]',
    )

    response = client.post("/api/search", json={"query": "sunset", "limit": 10, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "search_test_1"


def test_search_photos_no_results(client, monkeypatch):
    mock_siglip = MagicMock()
    mock_siglip.get_text_embedding.return_value = [0.1] * 768
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: mock_siglip)

    response = client.post("/api/search", json={"query": "aliens", "limit": 10, "offset": 0})
    assert response.status_code == 200
    assert response.json() == []


def test_search_photos_falls_back_to_sqlite_when_siglip_missing(client, db_session, monkeypatch, caplog):
    _seed_photo(
        db_session,
        photo_id="fallback_match_1",
        file_name="sunset_low_iso.jpg",
        caption="Golden sunset over the ocean",
        tags_json='["sunset", "ocean"]',
        iso=200,
    )
    _seed_photo(
        db_session,
        photo_id="fallback_filtered_out",
        file_name="sunset_high_iso.jpg",
        caption="Night sunset street",
        tags_json='["sunset", "night"]',
        iso=3200,
    )

    def raise_missing_model():
        raise RuntimeError("SigLIP 2 model weights are not installed")

    monkeypatch.setattr("services.search_service.get_siglip_adapter", raise_missing_model)

    with caplog.at_level(logging.WARNING, logger="services.search_service"):
        response = client.post(
            "/api/search",
            json={
                "query": "sunset",
                "filters": {"iso_min": 100, "iso_max": 400},
                "limit": 10,
                "offset": 0,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == ["fallback_match_1"]
    assert "SigLIP 2 embedding unavailable" in caplog.text


def test_search_photos_falls_back_when_embedding_inference_fails(client, db_session, monkeypatch, caplog):
    _seed_photo(
        db_session,
        photo_id="fallback_infer_1",
        file_name="forest.jpg",
        caption="Misty morning forest trail",
        tags_json='["forest", "mist"]',
    )

    failing_siglip = MagicMock()
    failing_siglip.get_text_embedding.side_effect = OSError("MPS out of memory")
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: failing_siglip)

    with caplog.at_level(logging.WARNING, logger="services.search_service"):
        response = client.post("/api/search", json={"query": "forest", "limit": 10, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == ["fallback_infer_1"]
    assert "SigLIP 2 embedding unavailable" in caplog.text


def test_search_similar_photos_excludes_target_photo(client, db_session, monkeypatch):
    _seed_photo(
        db_session,
        photo_id="target_photo",
        file_name="target.jpg",
        caption="Warm portrait",
        tags_json='["portrait"]',
    )
    _seed_photo(
        db_session,
        photo_id="similar_photo_1",
        file_name="similar1.jpg",
        caption="Warm golden portrait",
        tags_json='["portrait", "warm"]',
    )

    mock_collection = MagicMock()
    mock_collection.count.return_value = 2
    mock_collection.get.return_value = {"embeddings": [[0.2] * 768]}
    mock_collection.query.return_value = {"ids": [["target_photo", "similar_photo_1"]]}
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: mock_collection)

    response = client.post("/api/search/similar", json={"photo_id": "target_photo", "limit": 10, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == ["similar_photo_1"]


class _EncodedBatch(dict):
    def to(self, _device):
        return self


class _LengthStrictProcessor:
    def __call__(self, text, padding=None, truncation=False, max_length=None, return_tensors=None):
        token_count = len(text[0].split())
        seq_len = max_length if (truncation and max_length is not None) else token_count
        return _EncodedBatch({"input_ids": torch.ones((1, seq_len), dtype=torch.long)})


class _LengthStrictTextModel:
    config = SimpleNamespace(text_config=SimpleNamespace(max_position_embeddings=64))

    def get_text_features(self, input_ids, **_kwargs):
        if input_ids.shape[1] > 64:
            raise ValueError("Sequence length exceeds max_position_embeddings")
        return SimpleNamespace(pooler_output=torch.ones((1, 768), dtype=torch.float32))


def _build_length_strict_siglip_adapter() -> SigLIP2Adapter:
    adapter = SigLIP2Adapter.__new__(SigLIP2Adapter)
    adapter.device = "cpu"
    adapter.model_id = "google/siglip2-base-patch16-224"
    adapter.model = _LengthStrictTextModel()
    adapter.processor = _LengthStrictProcessor()
    adapter.cached_taxonomy_embeddings = None
    adapter.lock = threading.RLock()
    return adapter


def test_tc_src_08_search_photos_long_query_uses_siglip_truncation(client, db_session, monkeypatch):
    _seed_photo(
        db_session,
        photo_id="long_query_match",
        file_name="neon_alley.jpg",
        caption="Rainy night street",
        tags_json='["night"]',
    )
    adapter = _build_length_strict_siglip_adapter()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 1
    mock_collection.query.return_value = {"ids": [["long_query_match"]]}
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: adapter)
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: mock_collection)

    long_korean_english_query = " ".join(
        ["비 내리는 밤거리 네온사인 시네마틱 골목길 젖은 아스팔트 반영 인물 스냅"] * 10
    )
    response = client.post("/api/search", json={"query": long_korean_english_query, "limit": 10, "offset": 0})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["long_query_match"]
    mock_collection.query.assert_called_once()
