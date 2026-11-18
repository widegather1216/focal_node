import asyncio
from datetime import date, datetime
import json
import logging
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
import torch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import database
from database import Base, get_db, run_migrations
from main import app
from models import AIAnalysis, Image, ImageMetadata
from repositories.photo_repository import PhotoRepository
from schemas import SearchFilter, SearchRequest, SimilarSearchRequest
from services.photo import register_photos_batch_atomic
from services.photo_reindex import _update_ai_analysis_orm
from services.search_service import SearchService
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


def _seed_scoped_photo(
    db_session,
    photo_id: str,
    parent_dir: str,
    file_name: str,
    caption: str,
    tags_json: str,
    iso: int = 200,
    capture_date: datetime | None = None,
) -> None:
    image_row = Image(
        id=photo_id,
        parent_dir=parent_dir,
        file_path=f"{parent_dir}/{file_name}",
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
        capture_date=capture_date,
    )
    analysis_row = AIAnalysis(
        image_id=photo_id,
        caption=caption,
        tags=tags_json,
    )
    db_session.add_all([image_row, metadata_row, analysis_row])
    db_session.commit()


def _seed_folder_scope_library(db_session) -> None:
    _seed_scoped_photo(
        db_session,
        "a_root",
        "/folder_a",
        "a_root.jpg",
        "Sunset on coast",
        '["sunset"]',
        iso=200,
        capture_date=datetime(2026, 5, 1, 10, 0, 0),
    )
    _seed_scoped_photo(
        db_session,
        "a_sub",
        "/folder_a/sub",
        "a_sub.jpg",
        "Sunset in sub",
        '["sunset"]',
        iso=200,
        capture_date=datetime(2026, 5, 2, 10, 0, 0),
    )
    _seed_scoped_photo(
        db_session,
        "a_other",
        "/folder_a_other",
        "a_other.jpg",
        "Sunset in sibling",
        '["sunset"]',
        iso=200,
        capture_date=datetime(2026, 5, 3, 10, 0, 0),
    )
    _seed_scoped_photo(
        db_session,
        "b_root",
        "/folder_b",
        "b_root.jpg",
        "Sunset in b",
        '["sunset"]',
        iso=200,
        capture_date=datetime(2026, 5, 4, 10, 0, 0),
    )


def test_tc_src_11_search_and_similar_respect_parent_dir_scope(client, db_session, monkeypatch):
    _seed_folder_scope_library(db_session)

    mock_siglip = MagicMock()
    mock_siglip.get_text_embedding.return_value = [0.1] * 768
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: mock_siglip)

    mock_collection = MagicMock()
    mock_collection.count.return_value = 1000
    mock_collection.get.return_value = {"embeddings": [[0.2] * 768]}
    mock_collection.query.return_value = {"ids": [["b_root", "a_other", "a_sub", "a_root"]]}
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: mock_collection)

    nl_resp = client.post(
        "/api/search",
        json={"query": "sunset", "parent_dir": "/folder_a", "limit": 2, "offset": 0},
    )
    assert nl_resp.status_code == 200
    assert {item["id"] for item in nl_resp.json()} == {"a_root", "a_sub"}
    assert mock_collection.query.call_args.kwargs["n_results"] >= 500

    nl_exif_resp = client.post(
        "/api/search",
        json={
            "query": "sunset",
            "filters": {"iso_min": 100, "iso_max": 400},
            "parent_dir": "/folder_a",
            "limit": 10,
            "offset": 0,
        },
    )
    assert nl_exif_resp.status_code == 200
    assert {item["id"] for item in nl_exif_resp.json()} == {"a_root", "a_sub"}

    filter_only_resp = client.post(
        "/api/search",
        json={
            "filters": {"iso_min": 100, "iso_max": 400},
            "parent_dir": "/folder_a",
            "limit": 10,
            "offset": 0,
        },
    )
    assert filter_only_resp.status_code == 200
    assert [item["id"] for item in filter_only_resp.json()] == ["a_sub", "a_root"]

    similar_resp = client.post(
        "/api/search/similar",
        json={"photo_id": "a_root", "parent_dir": "/folder_a", "limit": 10, "offset": 0},
    )
    assert similar_resp.status_code == 200
    assert [item["id"] for item in similar_resp.json()] == ["a_sub"]
    assert mock_collection.query.call_args.kwargs["n_results"] >= 500


def test_tc_src_11_parent_dir_nfd_symlink_whitespace_and_text_pool_boundaries(client, db_session, tmp_path, monkeypatch):
    import os
    import unicodedata

    root_nfc = unicodedata.normalize("NFC", str(tmp_path / "여행폴더"))
    root_nfd = unicodedata.normalize("NFD", str(tmp_path / "여행폴더"))
    sub_nfd = os.path.join(root_nfd, unicodedata.normalize("NFD", "부산"))
    sibling_dir = unicodedata.normalize("NFC", str(tmp_path / "여행폴더_백업"))
    symlink_folder = tmp_path / "LinkFolder"
    os.makedirs(sub_nfd, exist_ok=True)
    os.makedirs(sibling_dir, exist_ok=True)
    os.symlink(str(tmp_path), str(symlink_folder))

    _seed_scoped_photo(db_session, "ko_root", root_nfc, "a.jpg", "Golden harbor", '["harbor"]')
    _seed_scoped_photo(db_session, "ko_sub", sub_nfd, "b.jpg", "Golden harbor", '["harbor"]')
    _seed_scoped_photo(db_session, "ko_sib", sibling_dir, "c.jpg", "Golden harbor", '["harbor"]')
    _seed_scoped_photo(db_session, "ko_link", str(symlink_folder), "d.jpg", "Golden harbor", '["harbor"]')

    for idx in range(505):
        _seed_scoped_photo(db_session, f"bulk_b_{idx}", sibling_dir, f"b_{idx}.jpg", "Bulk sunset", '["sunset"]')
    _seed_scoped_photo(db_session, "target_a_late", root_nfc, "late.jpg", "Bulk sunset", '["sunset"]')

    monkeypatch.setattr(
        "services.search_service.get_siglip_adapter",
        lambda: (_ for _ in ()).throw(RuntimeError("SigLIP disabled")),
    )

    for folder_variant in (root_nfc, root_nfc + os.sep, root_nfd, root_nfc.upper()):
        folder_response = client.post("/api/search", json={"query": "harbor", "parent_dir": folder_variant, "limit": 10, "offset": 0})
        assert folder_response.status_code == 200
        assert {item["id"] for item in folder_response.json()} == {"ko_root", "ko_sub"}

    link_response = client.post("/api/search", json={"query": "harbor", "parent_dir": str(symlink_folder), "limit": 10, "offset": 0})
    assert [item["id"] for item in link_response.json()] == ["ko_link"]

    late_response = client.post("/api/search", json={"query": "sunset", "parent_dir": root_nfc, "limit": 10, "offset": 0})
    assert [item["id"] for item in late_response.json()] == ["target_a_late"]

    assert client.post("/api/search", json={"query": "harbor", "parent_dir": "   ", "limit": 10, "offset": 0}).json() == []
    assert len(client.post("/api/search", json={"query": "harbor", "parent_dir": "", "limit": 10, "offset": 0}).json()) == 4
    assert client.post("/api/search", json={"query": "harbor", "parent_dir": root_nfc, "limit": -1, "offset": 0}).status_code == 422
    assert client.post("/api/search", json={"query": "harbor", "parent_dir": root_nfc, "limit": 10, "offset": -5}).status_code == 422

    repo = PhotoRepository(db_session)
    assert repo.filter_and_paginate(["ko_root", "ko_sub"], None, 0, -1, parent_dir=root_nfc) == []
    assert len(repo.filter_and_paginate(["ko_root", "ko_sub"], None, -5, 10, parent_dir=root_nfc)) == 2


def test_tc_src_15_chunked_35k_candidate_ids_preserve_rank_pagination_and_folder_scope(db_session):
    _seed_scoped_photo(db_session, "rank_first", "/album_a", "1.jpg", "Sunset", '["sunset"]', iso=200)
    _seed_scoped_photo(db_session, "rank_second_wrong_iso", "/album_a", "2.jpg", "Sunset", '["sunset"]', iso=1600)
    _seed_scoped_photo(db_session, "rank_third_wrong_folder", "/album_b", "3.jpg", "Sunset", '["sunset"]', iso=200)
    _seed_scoped_photo(db_session, "rank_fourth", "/album_a/sub", "4.jpg", "Sunset", '["sunset"]', iso=200)

    candidate_ids = (
        [f"ghost_head_{idx}" for idx in range(18000)]
        + ["rank_first", "rank_first", "rank_second_wrong_iso", "rank_third_wrong_folder"]
        + [f"ghost_mid_{idx}" for idx in range(17000)]
        + ["rank_fourth"]
    )
    assert len(candidate_ids) > 35000

    repo = PhotoRepository(db_session)
    exif_filter = SimpleNamespace(iso_min=100, iso_max=400)

    all_matches = repo.filter_and_paginate(candidate_ids, exif_filter, offset=0, limit=10, parent_dir="/album_a")
    assert [img.id for img in all_matches] == ["rank_first", "rank_fourth"]

    second_page = repo.filter_and_paginate(candidate_ids, exif_filter, offset=1, limit=1, parent_dir="/album_a")
    assert [img.id for img in second_page] == ["rank_fourth"]

    unscoped_matches = repo.filter_and_paginate(candidate_ids, exif_filter, offset=0, limit=10)
    assert [img.id for img in unscoped_matches] == ["rank_first", "rank_third_wrong_folder", "rank_fourth"]


def test_tc_src_15_list_critiques_over_35k_ids_avoids_sqlite_limit_and_preserves_order(db_session):
    _seed_photo(db_session, "crt_low", "low.jpg", "Low", '["a"]')
    _seed_photo(db_session, "crt_high_old", "high_old.jpg", "High old", '["a"]')
    _seed_photo(db_session, "crt_high_new", "high_new.jpg", "High new", '["a"]')
    _seed_photo(db_session, "crt_null_score", "null.jpg", "Null", '["a"]')

    repo = PhotoRepository(db_session)
    repo.upsert_critique("crt_low", "Critique low", datetime(2026, 1, 3, 12, 0, 0), overall_score=0.0)
    repo.upsert_critique("crt_high_old", "Critique high old", datetime(2026, 1, 1, 12, 0, 0), overall_score=90.0)
    repo.upsert_critique("crt_high_new", "Critique high new", datetime(2026, 1, 2, 12, 0, 0), overall_score=90.0)
    repo.upsert_critique("crt_null_score", "Critique null", datetime(2026, 1, 4, 12, 0, 0), overall_score=None)

    bulk_ids = [f"missing_{idx}" for idx in range(35000)] + [
        "crt_low",
        "crt_high_old",
        "crt_high_old",
        "crt_high_new",
        "crt_null_score",
    ]
    rows = repo.list_critiques(sort_by="overall_score", photo_ids=bulk_ids)
    assert [img.id for _, img, _ in rows] == ["crt_high_new", "crt_high_old", "crt_low", "crt_null_score"]


def test_tc_src_15_negative_and_out_of_range_pagination_validation(client, db_session):
    _seed_photo(db_session, "page_guard_1", "guard1.jpg", "Sunset", '["sunset"]')
    _seed_photo(db_session, "page_guard_2", "guard2.jpg", "Sunset", '["sunset"]')

    invalid_payloads = [
        {"query": "sunset", "limit": -1, "offset": 0},
        {"query": "sunset", "limit": 0, "offset": 0},
        {"query": "sunset", "limit": 501, "offset": 0},
        {"query": "sunset", "limit": 10, "offset": -1},
    ]
    for payload in invalid_payloads:
        resp = client.post("/api/search", json=payload)
        assert resp.status_code == 422
        assert isinstance(resp.json()["detail"], list)

        similar_resp = client.post(
            "/api/search/similar",
            json={"photo_id": "page_guard_1", "limit": payload["limit"], "offset": payload["offset"]},
        )
        assert similar_resp.status_code == 422
        assert isinstance(similar_resp.json()["detail"], list)

    repo = PhotoRepository(db_session)
    assert repo.filter_and_paginate(None, None, offset=0, limit=0) == []
    assert repo.filter_and_paginate(None, None, offset=0, limit=-10) == []
    direct_results = repo.filter_and_paginate(None, None, offset=-5, limit=10)
    assert {img.id for img in direct_results} == {"page_guard_1", "page_guard_2"}


def test_tc_src_15_exif_ilike_wildcard_escape_whitespace_and_deterministic_tie_breaker(client, db_session):
    same_timestamp = datetime(2026, 5, 10, 12, 0, 0)
    samples = [
        ("burst_c", "c.jpg", "NIKON Z6_2", "NIKKOR 24_70mm 100%", same_timestamp),
        ("burst_a", "a.jpg", "Z6_2", "RF 50% Macro", same_timestamp),
        ("burst_b", "b.jpg", "Z6X2", "RF 500 Macro", same_timestamp),
        ("null_z", "z.jpg", "Z6_2", "Prime", None),
        ("null_d", "d.jpg", "Z6_2", "Prime", None),
    ]
    for photo_id, file_name, camera_model, lens_model, capture_dt in samples:
        db_session.add(
            Image(
                id=photo_id,
                parent_dir="/burst",
                file_path=f"/burst/{file_name}",
                file_name=file_name,
                file_size=100,
                file_mtime=time.time(),
                mime_type="image/jpeg",
            )
        )
        db_session.add(
            ImageMetadata(
                image_id=photo_id,
                camera_model=camera_model,
                lens_model=lens_model,
                capture_date=capture_dt,
            )
        )
    db_session.commit()

    underscore_resp = client.post(
        "/api/search",
        json={"filters": {"camera_model": "Z6_2"}, "limit": 10, "offset": 0},
    )
    assert underscore_resp.status_code == 200
    assert [item["id"] for item in underscore_resp.json()] == [
        "burst_a",
        "burst_c",
        "null_d",
        "null_z",
    ]

    page_1 = client.post(
        "/api/search",
        json={"filters": {"camera_model": "Z6_2"}, "limit": 2, "offset": 0},
    )
    page_2 = client.post(
        "/api/search",
        json={"filters": {"camera_model": "Z6_2"}, "limit": 2, "offset": 2},
    )
    assert [item["id"] for item in page_1.json()] == ["burst_a", "burst_c"]
    assert [item["id"] for item in page_2.json()] == ["null_d", "null_z"]

    lens_percent_resp = client.post(
        "/api/search",
        json={"filters": {"lens_model": "50%"}, "limit": 10, "offset": 0},
    )
    assert [item["id"] for item in lens_percent_resp.json()] == ["burst_a"]

    blank_filter_resp = client.post(
        "/api/search",
        json={"filters": {"camera_model": "   ", "lens_model": ""}, "limit": 10, "offset": 0},
    )
    assert blank_filter_resp.status_code == 200
    assert len(blank_filter_resp.json()) == 5
    assert [item["id"] for item in blank_filter_resp.json()] == [
        "burst_a",
        "burst_b",
        "burst_c",
        "null_d",
        "null_z",
    ]


def _build_mock_chroma_collection(count_val: int, embeddings=None, query_ids=None) -> MagicMock:
    collection = MagicMock()
    collection.count.return_value = count_val
    if embeddings is not None:
        collection.get.return_value = {"embeddings": embeddings}
    if query_ids is not None:
        collection.query.return_value = {"ids": [query_ids]}
    return collection


def test_tc_src_16_similar_search_returns_404_when_vector_index_empty_or_missing(
    client, db_session, monkeypatch
):
    _seed_photo(db_session, "unindexed_photo", "unindexed.jpg", "Harbor dusk", '["harbor"]')
    payload = {"photo_id": "unindexed_photo", "limit": 10, "offset": 0}

    empty_collection = _build_mock_chroma_collection(count_val=0)
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: empty_collection)
    empty_index_resp = client.post("/api/search/similar", json=payload)
    assert empty_index_resp.status_code == 404
    assert "unindexed_photo" in empty_index_resp.json()["detail"]

    partial_collection = _build_mock_chroma_collection(count_val=3, embeddings=[])
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: partial_collection)
    missing_emb_resp = client.post("/api/search/similar", json=payload)
    assert missing_emb_resp.status_code == 404
    assert "unindexed_photo" in missing_emb_resp.json()["detail"]

    singleton_collection = _build_mock_chroma_collection(
        count_val=1, embeddings=[[0.2] * 768], query_ids=["unindexed_photo"]
    )
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: singleton_collection)
    no_peers_resp = client.post("/api/search/similar", json=payload)
    assert no_peers_resp.status_code == 200
    assert no_peers_resp.json() == []


def _create_wal_test_session_factory(tmp_path):
    db_file = tmp_path / "search_isolation.db"
    wal_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )

    @event.listens_for(wal_engine, "connect")
    def _configure_wal(dbapi_conn, _conn_rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    Base.metadata.create_all(bind=wal_engine)
    return wal_engine, sessionmaker(autocommit=False, autoflush=False, bind=wal_engine)


def _seed_wal_search_photos(session_factory) -> None:
    with session_factory() as seed_db:
        for photo_id, file_name, caption in (
            ("wal_a", "harbor_a.jpg", "Harbor sunset"),
            ("wal_b", "harbor_b.jpg", "Harbor twilight"),
        ):
            seed_db.add_all([
                Image(
                    id=photo_id,
                    parent_dir="/wal_photos",
                    file_path=f"/wal_photos/{file_name}",
                    file_name=file_name,
                    file_size=2048,
                    file_mtime=time.time(),
                    mime_type="image/jpeg",
                ),
                ImageMetadata(
                    image_id=photo_id,
                    camera_model="ILCE-7M4",
                    width=4000,
                    height=3000,
                    capture_date=datetime(2025, 11, 18, 12, 0, 0),
                ),
                AIAnalysis(image_id=photo_id, caption=caption, tags='["harbor"]'),
            ])
        seed_db.commit()


def _build_tracked_session_factory(base_factory, session_records: list[dict]):
    def _open_tracked_session():
        session = base_factory()
        record = {"open_tid": threading.get_ident(), "close_tid": None}
        session_records.append(record)
        orig_close = session.close

        def _tracked_close():
            record["close_tid"] = threading.get_ident()
            return orig_close()

        session.close = _tracked_close
        return session

    return _open_tracked_session


@pytest.mark.asyncio
async def test_tc_src_17_search_isolates_worker_sessions_on_cancellation_and_avoids_detached_errors(
    tmp_path, monkeypatch
):
    wal_engine, wal_factory = _create_wal_test_session_factory(tmp_path)
    _seed_wal_search_photos(wal_factory)
    session_records: list[dict] = []
    get_db_events: list[tuple[str, int]] = []

    monkeypatch.setattr(database, "SessionLocal", _build_tracked_session_factory(wal_factory, session_records))
    mock_siglip = MagicMock()
    mock_siglip.get_text_embedding.return_value = [0.1] * 768
    monkeypatch.setattr("services.search_service.get_siglip_adapter", lambda: mock_siglip)
    collection = _build_mock_chroma_collection(count_val=2, embeddings=[[0.1] * 768], query_ids=["wal_a", "wal_b"])
    monkeypatch.setattr("repositories.vector_repository.get_chroma_collection", lambda: collection)

    def _forbidden_get_db():
        get_db_events.append(("enter", threading.get_ident()))
        db = wal_factory()
        try:
            yield db
        finally:
            get_db_events.append(("close", threading.get_ident()))
            db.close()

    app.dependency_overrides[get_db] = _forbidden_get_db
    loop_tid = threading.get_ident()
    worker_entered = threading.Event()
    release_worker = threading.Event()
    worker_done = threading.Event()
    worker_errors: list[Exception] = []
    orig_filter = PhotoRepository.filter_and_paginate

    def _blocking_filter(self, *args, **kwargs):
        worker_entered.set()
        release_worker.wait(timeout=3.0)
        try:
            return orig_filter(self, *args, **kwargs)
        except Exception as exc:
            worker_errors.append(exc)
            raise
        finally:
            worker_done.set()

    try:
        with monkeypatch.context() as scoped_patch:
            scoped_patch.setattr(PhotoRepository, "filter_and_paginate", _blocking_filter)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as async_client:
                task = asyncio.create_task(
                    async_client.post("/api/search", json={"query": "harbor", "limit": 10, "offset": 0})
                )
                assert await asyncio.to_thread(worker_entered.wait, 3.0)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

                assert get_db_events == []
                release_worker.set()
                assert await asyncio.to_thread(worker_done.wait, 3.0)
                assert worker_errors == []

        assert len(session_records) >= 2
        for record in session_records:
            assert record["open_tid"] != loop_tid
            assert record["close_tid"] == record["open_tid"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as async_client:
            search_response = await async_client.post(
                "/api/search", json={"query": "harbor", "limit": 10, "offset": 0}
            )
            similar_response = await async_client.post(
                "/api/search/similar", json={"photo_id": "wal_a", "limit": 10, "offset": 0}
            )
        assert search_response.status_code == 200
        assert similar_response.status_code == 200
        assert search_response.json()[0]["camera_model"] == "ILCE-7M4"
        assert similar_response.json()[0]["id"] == "wal_b"

        direct_search = await SearchService().search_photos(SearchRequest(query="harbor", limit=10, offset=0))
        direct_similar = await SearchService().search_similar_photos(
            SimilarSearchRequest(photo_id="wal_a", limit=10, offset=0)
        )
        assert isinstance(direct_search[0], dict)
        assert direct_search[0]["width"] == 4000
        assert isinstance(direct_similar[0], dict)
        assert direct_similar[0]["capture_date"] == "2025-11-18T12:00:00"
    finally:
        release_worker.set()
        app.dependency_overrides.clear()
        wal_engine.dispose()



