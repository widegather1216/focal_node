import logging
import time
from unittest.mock import MagicMock

from models import AIAnalysis, Image, ImageMetadata


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
