from datetime import datetime, timezone, timedelta
import pytest
import models
from repositories.photo_repository import PhotoRepository


def _create_test_photo(db_session, photo_id: str, file_name: str):
    img = models.Image(
        id=photo_id,
        parent_dir="/test",
        file_name=file_name,
        file_path=f"/test/{file_name}",
        file_size=1024,
        file_mtime=1.0,
        mime_type="image/jpeg"
    )
    meta = models.ImageMetadata(
        image_id=photo_id,
        camera_model="Sony A7R V",
        lens_model="FE 35mm F1.4 GM",
        f_number=1.4,
        shutter_speed="1/500",
        iso=100,
        capture_date=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    db_session.add(img)
    db_session.add(meta)
    return img, meta


def test_list_critiques_default_sorting_recent(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "p1", "photo1.jpg")
    _create_test_photo(db_session, "p2", "photo2.jpg")
    _create_test_photo(db_session, "p3", "photo3.jpg")

    # p1: 2 hours ago, p2: now (most recent), p3: 1 hour ago
    ai1 = models.AIAnalysis(
        image_id="p1",
        critique="Critique 1",
        critique_updated_at=now - timedelta(hours=2),
        overall_score=70.0
    )
    ai2 = models.AIAnalysis(
        image_id="p2",
        critique="Critique 2",
        critique_updated_at=now,
        overall_score=90.0
    )
    ai3 = models.AIAnalysis(
        image_id="p3",
        critique="Critique 3",
        critique_updated_at=now - timedelta(hours=1),
        overall_score=80.0
    )
    db_session.add_all([ai1, ai2, ai3])
    db_session.commit()

    repo = PhotoRepository(db_session)
    results = repo.list_critiques(sort_by="recent")

    result_ids = [img.id for ai, img, meta in results]
    assert result_ids == ["p2", "p3", "p1"]


def test_list_critiques_sort_by_overall_score(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "score_a", "a.jpg")
    _create_test_photo(db_session, "score_b", "b.jpg")
    _create_test_photo(db_session, "score_c", "c.jpg")

    ai_a = models.AIAnalysis(
        image_id="score_a",
        critique="Critique A",
        critique_updated_at=now,
        overall_score=82.0
    )
    ai_b = models.AIAnalysis(
        image_id="score_b",
        critique="Critique B",
        critique_updated_at=now,
        overall_score=96.5
    )
    ai_c = models.AIAnalysis(
        image_id="score_c",
        critique="Critique C",
        critique_updated_at=now,
        overall_score=75.0
    )
    db_session.add_all([ai_a, ai_b, ai_c])
    db_session.commit()

    repo = PhotoRepository(db_session)
    results = repo.list_critiques(sort_by="overall_score")

    result_ids = [img.id for ai, img, meta in results]
    assert result_ids == ["score_b", "score_a", "score_c"]


def test_list_critiques_sort_by_iaa_score(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "iaa_a", "iaa_a.jpg")
    _create_test_photo(db_session, "iaa_b", "iaa_b.jpg")
    _create_test_photo(db_session, "iaa_c", "iaa_c.jpg")

    ai_a = models.AIAnalysis(
        image_id="iaa_a",
        critique="Critique A",
        critique_updated_at=now,
        iaa_score=91.0
    )
    ai_b = models.AIAnalysis(
        image_id="iaa_b",
        critique="Critique B",
        critique_updated_at=now,
        iaa_score=78.5
    )
    ai_c = models.AIAnalysis(
        image_id="iaa_c",
        critique="Critique C",
        critique_updated_at=now,
        iaa_score=95.0
    )
    db_session.add_all([ai_a, ai_b, ai_c])
    db_session.commit()

    repo = PhotoRepository(db_session)
    results = repo.list_critiques(sort_by="iaa_score")

    result_ids = [img.id for ai, img, meta in results]
    assert result_ids == ["iaa_c", "iaa_a", "iaa_b"]


def test_list_critiques_null_scores_nullslast(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "has_score", "has_score.jpg")
    _create_test_photo(db_session, "no_score", "no_score.jpg")

    ai_has = models.AIAnalysis(
        image_id="has_score",
        critique="Valid critique",
        critique_updated_at=now,
        overall_score=60.0
    )
    ai_no = models.AIAnalysis(
        image_id="no_score",
        critique="Valid critique but no score",
        critique_updated_at=now,
        overall_score=None
    )
    db_session.add_all([ai_has, ai_no])
    db_session.commit()

    repo = PhotoRepository(db_session)
    results = repo.list_critiques(sort_by="overall_score")

    result_ids = [img.id for ai, img, meta in results]
    assert result_ids == ["has_score", "no_score"]


def test_list_critiques_filters_empty_or_none(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "valid_p", "valid.jpg")
    _create_test_photo(db_session, "none_p", "none.jpg")
    _create_test_photo(db_session, "empty_p", "empty.jpg")

    ai_valid = models.AIAnalysis(
        image_id="valid_p",
        critique="Good photo",
        critique_updated_at=now
    )
    ai_none = models.AIAnalysis(
        image_id="none_p",
        critique=None,
        critique_updated_at=now
    )
    ai_empty = models.AIAnalysis(
        image_id="empty_p",
        critique="",
        critique_updated_at=now
    )
    db_session.add_all([ai_valid, ai_none, ai_empty])
    db_session.commit()

    repo = PhotoRepository(db_session)
    results = repo.list_critiques()

    assert len(results) == 1
    assert results[0][1].id == "valid_p"


def test_delete_critique_clears_all_normalized_fields(db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "del_p", "del.jpg")
    ai = models.AIAnalysis(
        image_id="del_p",
        critique="Original critique",
        critique_en="English critique",
        overall_score=85.0,
        iaa_score=88.0,
        iqa_score=82.0,
        ista_score=84.0,
        critique_updated_at=now
    )
    db_session.add(ai)
    db_session.commit()

    repo = PhotoRepository(db_session)
    deleted = repo.delete_critique("del_p")
    assert deleted is True

    updated_ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == "del_p").first()
    assert updated_ai.critique is None
    assert updated_ai.critique_en is None
    assert updated_ai.overall_score is None
    assert updated_ai.iaa_score is None
    assert updated_ai.iqa_score is None
    assert updated_ai.ista_score is None
    assert updated_ai.critique_updated_at is None

    # Deleting non-existent photo returns False
    assert repo.delete_critique("non_existent_id") is False


def test_api_get_all_critiques_and_response_fields(client, db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "api_p1", "api_p1.jpg")
    ai = models.AIAnalysis(
        image_id="api_p1",
        critique="한국어 비평",
        critique_en="English critique",
        overall_score=88.5,
        iaa_score=92.0,
        iqa_score=85.0,
        ista_score=87.5,
        critique_updated_at=now
    )
    db_session.add(ai)
    db_session.commit()

    response = client.get("/api/chat/critiques")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]

    assert item["photo_id"] == "api_p1"
    assert item["file_name"] == "api_p1.jpg"
    assert item["file_path"] == "/test/api_p1.jpg"
    assert item["critique"] == "한국어 비평"
    assert item["critique_en"] == "English critique"
    assert item["overall_score"] == 88.5
    assert item["iaa_score"] == 92.0
    assert item["iqa_score"] == 85.0
    assert item["ista_score"] == 87.5
    assert item["camera_model"] == "Sony A7R V"
    assert item["lens_model"] == "FE 35mm F1.4 GM"
    assert item["f_number"] == 1.4
    assert item["iso"] == 100


def test_api_get_all_critiques_sorting_parameters(client, db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "sort_p1", "sort1.jpg")
    _create_test_photo(db_session, "sort_p2", "sort2.jpg")

    ai1 = models.AIAnalysis(
        image_id="sort_p1",
        critique="Critique 1",
        critique_updated_at=now - timedelta(hours=1),
        overall_score=75.0,
        iaa_score=95.0
    )
    ai2 = models.AIAnalysis(
        image_id="sort_p2",
        critique="Critique 2",
        critique_updated_at=now,
        overall_score=92.0,
        iaa_score=80.0
    )
    db_session.add_all([ai1, ai2])
    db_session.commit()

    # 1. Default (recent)
    resp_recent = client.get("/api/chat/critiques")
    assert resp_recent.status_code == 200
    assert [x["photo_id"] for x in resp_recent.json()] == ["sort_p2", "sort_p1"]

    # 2. overall_score
    resp_overall = client.get("/api/chat/critiques?sort_by=overall_score")
    assert resp_overall.status_code == 200
    assert [x["photo_id"] for x in resp_overall.json()] == ["sort_p2", "sort_p1"]

    # 3. iaa_score
    resp_iaa = client.get("/api/chat/critiques?sort_by=iaa_score")
    assert resp_iaa.status_code == 200
    assert [x["photo_id"] for x in resp_iaa.json()] == ["sort_p1", "sort_p2"]

    # 4. Invalid sort parameter -> 422 Unprocessable Entity
    resp_invalid = client.get("/api/chat/critiques?sort_by=unknown_field")
    assert resp_invalid.status_code == 422


def test_api_delete_critique_endpoint(client, db_session):
    now = datetime.now(timezone.utc)
    _create_test_photo(db_session, "api_del", "api_del.jpg")
    ai = models.AIAnalysis(
        image_id="api_del",
        critique="To be deleted",
        critique_en="English",
        overall_score=80.0,
        critique_updated_at=now
    )
    db_session.add(ai)
    db_session.commit()

    del_resp = client.delete("/api/chat/critique/api_del")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"status": "ok", "photo_id": "api_del"}

    list_resp = client.get("/api/chat/critiques")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0
