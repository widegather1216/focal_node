from datetime import date, datetime
import json
import logging
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, run_migrations
from models import AIAnalysis, Image, ImageMetadata
from repositories.photo_repository import PhotoRepository
from schemas import SearchFilter
from services.photo import register_photos_batch_atomic
from services.photo_reindex import _update_ai_analysis_orm
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


def _build_batch_photo_item(photo_id: str, file_name: str, tags: list[str], aesthetic_tags: list[str]) -> dict:
    return {
        "image_data": {
            "id": photo_id,
            "parent_dir": "/test",
            "file_path": f"/test/{file_name}",
            "file_name": file_name,
            "file_size": 1024,
            "file_mtime": time.time(),
            "mime_type": "image/jpeg",
        },
        "metadata_data": {
            "iso": 200,
            "f_number": 2.8,
            "focal_length": 50.0,
        },
        "ai_data": {
            "caption": "Coastal twilight scene",
            "tags": tags,
            "aesthetic_tags": aesthetic_tags,
            "is_user_edited": False,
        },
        "embedding": None,
    }


def test_tc_src_09_korean_tags_sqlite_search_and_siglip_fallback(client, db_session, monkeypatch):
    register_photos_batch_atomic(
        db_session,
        [_build_batch_photo_item("idx_ko_1", "indexed_ko.jpg", ["바다", "노을"], ["골든아워", "역광"])],
    )

    _seed_photo(
        db_session,
        photo_id="edit_ko_2",
        file_name="edited_ko.jpg",
        caption="Shoreline horizon",
        tags_json='["ocean"]',
    )
    photo_repo = PhotoRepository(db_session)
    patch_resp = client.patch(
        "/api/photos/edit_ko_2/metadata",
        json={"caption": "Shoreline horizon", "tags": ["바다", "노을"]},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["ai_analysis"]["tags"] == ["바다", "노을"]

    _seed_photo(
        db_session,
        photo_id="reindex_ko_3",
        file_name="reindexed_ko.jpg",
        caption="Evening waves",
        tags_json='["ocean"]',
    )
    _update_ai_analysis_orm(
        db_session,
        "reindex_ko_3",
        {"caption": "Evening waves", "tags": ["바다", "노을"], "aesthetic_tags": ["미니멀리즘"]},
    )
    db_session.commit()

    for photo_id in ("idx_ko_1", "edit_ko_2", "reindex_ko_3"):
        image_row = photo_repo.get_by_id(photo_id)
        assert image_row is not None
        assert "\\u" not in (image_row.ai_analysis_rel.tags or "")
        detail = image_row.to_detail_dict()
        assert detail["ai_analysis"]["tags"] == ["바다", "노을"]

    indexed_row = photo_repo.get_by_id("idx_ko_1")
    reindexed_row = photo_repo.get_by_id("reindex_ko_3")
    assert "\\u" not in (indexed_row.ai_analysis_rel.aesthetic_tags or "")
    assert "\\u" not in (reindexed_row.ai_analysis_rel.aesthetic_tags or "")
    assert indexed_row.to_detail_dict()["ai_analysis"]["aesthetic_tags"] == ["골든아워", "역광"]
    assert reindexed_row.to_detail_dict()["ai_analysis"]["aesthetic_tags"] == ["미니멀리즘"]

    matched_ids = set(photo_repo.search_by_text("바다"))
    assert matched_ids == {"idx_ko_1", "edit_ko_2", "reindex_ko_3"}

    def raise_missing_model():
        raise RuntimeError("SigLIP 2 model weights are not installed")

    monkeypatch.setattr("services.search_service.get_siglip_adapter", raise_missing_model)
    response = client.post("/api/search", json={"query": "바다", "limit": 10, "offset": 0})
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {"idx_ko_1", "edit_ko_2", "reindex_ko_3"}


def test_tc_src_09_run_migrations_normalizes_escaped_ai_tags_and_skips_malformed(caplog):
    fresh_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=fresh_engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=fresh_engine)

    escaped_tags = json.dumps(["바다", "노을"], ensure_ascii=True)
    escaped_aesthetic = json.dumps(["골든아워", "역광"], ensure_ascii=True)
    malformed_tags = '["\\ubc14\\ub2e4"'

    with session_factory() as session:
        _seed_photo(session, "legacy_ko_1", "legacy1.jpg", "Evening coast", escaped_tags)
        analysis_1 = session.query(AIAnalysis).filter(AIAnalysis.image_id == "legacy_ko_1").first()
        analysis_1.aesthetic_tags = escaped_aesthetic

        _seed_photo(session, "legacy_bad_2", "legacy2.jpg", "Broken tags", malformed_tags)
        analysis_2 = session.query(AIAnalysis).filter(AIAnalysis.image_id == "legacy_bad_2").first()
        analysis_2.aesthetic_tags = json.dumps(["미니멀"], ensure_ascii=True)
        session.commit()
        assert PhotoRepository(session).search_by_text("바다") == []

    with caplog.at_level(logging.WARNING, logger="database"):
        run_migrations(fresh_engine)

    with session_factory() as session:
        migrated_1 = session.query(AIAnalysis).filter(AIAnalysis.image_id == "legacy_ko_1").first()
        migrated_2 = session.query(AIAnalysis).filter(AIAnalysis.image_id == "legacy_bad_2").first()
        assert migrated_1.tags == '["바다", "노을"]'
        assert migrated_1.aesthetic_tags == '["골든아워", "역광"]'
        assert migrated_2.tags == malformed_tags
        assert migrated_2.aesthetic_tags == '["미니멀"]'
        assert PhotoRepository(session).search_by_text("바다") == ["legacy_ko_1"]

    assert "legacy_bad_2" in caplog.text
    run_migrations(fresh_engine)


def _seed_dated_photo(db_session, photo_id: str, file_name: str, capture_date: datetime) -> None:
    image_row = Image(
        id=photo_id,
        parent_dir="/test",
        file_path=f"/test/{file_name}",
        file_name=file_name,
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg",
    )
    metadata_row = ImageMetadata(image_id=photo_id, capture_date=capture_date)
    db_session.add_all([image_row, metadata_row])
    db_session.commit()


def test_tc_src_10_date_filter_single_day_includes_full_day_and_preserves_explicit_timestamps(client, db_session):
    _seed_dated_photo(db_session, "same_day_midnight", "0000.jpg", datetime(2025, 11, 18, 0, 0, 0))
    _seed_dated_photo(db_session, "same_day_afternoon", "1430.jpg", datetime(2025, 11, 18, 14, 30, 0))
    _seed_dated_photo(db_session, "same_day_end", "235959.jpg", datetime(2025, 11, 18, 23, 59, 59, 999999))
    _seed_dated_photo(db_session, "next_day_midnight", "next.jpg", datetime(2025, 11, 19, 0, 0, 0))

    same_day_resp = client.post(
        "/api/search",
        json={"filters": {"date_from": "2025-11-18", "date_to": "2025-11-18"}, "limit": 20, "offset": 0},
    )
    assert same_day_resp.status_code == 200
    assert {item["id"] for item in same_day_resp.json()} == {
        "same_day_midnight",
        "same_day_afternoon",
        "same_day_end",
    }

    midnight_cutoff_resp = client.post(
        "/api/search",
        json={"filters": {"date_from": "2025-11-18T00:00:00", "date_to": "2025-11-18T00:00:00"}, "limit": 20, "offset": 0},
    )
    assert midnight_cutoff_resp.status_code == 200
    assert [item["id"] for item in midnight_cutoff_resp.json()] == ["same_day_midnight"]

    noon_cutoff_resp = client.post(
        "/api/search",
        json={"filters": {"date_from": "2025-11-18T00:00:00", "date_to": "2025-11-18T12:00:00"}, "limit": 20, "offset": 0},
    )
    assert noon_cutoff_resp.status_code == 200
    assert [item["id"] for item in noon_cutoff_resp.json()] == ["same_day_midnight"]


def test_tc_src_10_date_filter_supports_date_objects_and_utc_z_iso_strings(client, db_session):
    _seed_dated_photo(db_session, "year_end_2024", "ye2024.jpg", datetime(2024, 12, 31, 23, 59, 59))
    _seed_dated_photo(db_session, "new_year_2025", "ny2025.jpg", datetime(2025, 1, 1, 0, 0, 0))
    _seed_dated_photo(db_session, "nov_afternoon", "nov18.jpg", datetime(2025, 11, 18, 14, 30, 0))

    date_obj_filter = SearchFilter(date_from=date(2025, 11, 18), date_to=date(2025, 11, 18))
    assert date_obj_filter.date_from == datetime(2025, 11, 18, 0, 0, 0)
    assert date_obj_filter.date_to == datetime(2025, 11, 18, 23, 59, 59, 999999)

    explicit_dt_filter = SearchFilter(date_to=datetime(2025, 11, 18, 0, 0, 0))
    assert explicit_dt_filter.date_to == datetime(2025, 11, 18, 0, 0, 0)

    utc_filter = SearchFilter(date_from="2024-01-01T00:00:00Z", date_to="2024-12-31T23:59:59Z")
    assert utc_filter.date_from == datetime(2024, 1, 1, 0, 0, 0)
    assert utc_filter.date_to == datetime(2024, 12, 31, 23, 59, 59)
    assert utc_filter.date_from.tzinfo is None and utc_filter.date_to.tzinfo is None

    utc_resp = client.post(
        "/api/search",
        json={"filters": {"date_from": "2024-01-01T00:00:00Z", "date_to": "2024-12-31T23:59:59Z"}, "limit": 20, "offset": 0},
    )
    assert utc_resp.status_code == 200
    assert [item["id"] for item in utc_resp.json()] == ["year_end_2024"]

    repo_matches = PhotoRepository(db_session).filter_and_paginate(
        None, SimpleNamespace(date_from=date(2025, 11, 18), date_to=date(2025, 11, 18)), 0, 20
    )
    assert [img.id for img in repo_matches] == ["nov_afternoon"]

    invalid_resp = client.post("/api/search", json={"filters": {"date_to": "2025-02-30"}, "limit": 20, "offset": 0})
    assert invalid_resp.status_code == 422
