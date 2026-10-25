from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch

import models
import schemas
from services.chat_service import ChatService, _save_critique_to_db
from services.critique_status import critique_status_manager


def _create_test_photo(db_session, photo_id: str = "photo_test_svc"):
    img = models.Image(
        id=photo_id,
        parent_dir="/test",
        file_name=f"{photo_id}.jpg",
        file_path=f"/test/{photo_id}.jpg",
        file_size=2048,
        file_mtime=1.0,
        mime_type="image/jpeg",
        is_favorite=False
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
    db_session.commit()
    return img, meta


def test_save_critique_to_db_full_scores_and_raw_en(db_session, monkeypatch):
    """
    Verifies that ChatService._save_critique_to_db persists all 4 float scores
    and critique_en into SQLite ai_analysis table.
    """
    photo_id = "photo_save_1"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    now = datetime(2026, 10, 24, 15, 30, 0, tzinfo=timezone.utc)
    scores = {"overall": 87.5, "iaa": 91.0, "iqa": 84.5, "ista": 87.0}
    raw_en = "  The lighting provides strong depth and clean separation.  "
    critique_ko = "조명이 공간적 깊이감과 명확한 분리감을 형성합니다."

    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text=critique_ko,
        updated_at=now,
        scores_dict=scores,
        raw_en=raw_en
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai is not None
    assert ai.critique == critique_ko
    assert ai.critique_en == "The lighting provides strong depth and clean separation."
    assert ai.overall_score == 87.5
    assert ai.iaa_score == 91.0
    assert ai.iqa_score == 84.5
    assert ai.ista_score == 87.0
    assert ai.critique_updated_at.year == now.year
    assert ai.critique_updated_at.month == now.month
    assert ai.critique_updated_at.day == now.day
    assert ai.critique_updated_at.hour == now.hour
    assert ai.critique_updated_at.minute == now.minute


def test_save_critique_to_db_updates_existing_record_preserves_caption(db_session, monkeypatch):
    """
    Verifies that updating an existing AIAnalysis row preserves caption and tags
    while overwriting critique, critique_en, and normalized scores.
    """
    photo_id = "photo_save_existing"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    existing_ai = models.AIAnalysis(
        image_id=photo_id,
        caption="아름다운 일몰 풍경",
        tags='["sunset", "golden_hour"]',
        aesthetic_tags='["골든 아워"]',
        is_user_edited=True,
        critique="구 버전 비평",
        overall_score=70.0
    )
    db_session.add(existing_ai)
    db_session.commit()

    now = datetime(2026, 10, 24, 16, 0, 0, tzinfo=timezone.utc)
    new_scores = {"overall": 95.0, "iaa": 98.0, "iqa": 93.0, "ista": 94.0}
    new_raw_en = "Exceptional golden hour composition."
    new_critique_ko = "독보적인 골든 아워 구도입니다."

    _save_critique_to_db(
        photo_id=photo_id,
        critique_text=new_critique_ko,
        updated_at=now,
        scores_dict=new_scores,
        raw_en=new_raw_en
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai is not None
    # Preserved existing fields
    assert ai.caption == "아름다운 일몰 풍경"
    assert ai.tags == '["sunset", "golden_hour"]'
    assert ai.is_user_edited is True
    # Updated critique fields
    assert ai.critique == new_critique_ko
    assert ai.critique_en == "Exceptional golden hour composition."
    assert ai.overall_score == 95.0
    assert ai.iaa_score == 98.0
    assert ai.iqa_score == 93.0
    assert ai.ista_score == 94.0


def test_save_critique_to_db_numeric_type_conversion(db_session, monkeypatch):
    """
    Verifies string and integer scores in scores_dict are cleanly converted to float.
    """
    photo_id = "photo_save_types"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    scores = {"overall": "88", "iaa": 92, "iqa": "83.5", "ista": 85.0}
    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text="점수 변환 테스트",
        updated_at=datetime.now(timezone.utc),
        scores_dict=scores,
        raw_en="Test raw"
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert isinstance(ai.overall_score, float)
    assert ai.overall_score == 88.0
    assert ai.iaa_score == 92.0
    assert ai.iqa_score == 83.5
    assert ai.ista_score == 85.0


def test_save_critique_to_db_fallback_parsing_from_text(db_session, monkeypatch):
    """
    Verifies that when scores_dict is None, scores are extracted from scoreboard header in critique_text.
    """
    photo_id = "photo_save_fallback"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    critique_with_header = (
        "[6-Way 앙상블 비평 스코어보드]\n"
        "- 최종 종합 평점: 86.5점 / 100점\n"
        "- 미학 및 구도 (IAA): 92.0점\n"
        "- 화질 및 선명도 (IQA): 81.0점\n"
        "- 구조 및 질감 (ISTA): 86.5점\n\n"
        "## 1. [시각적 미학 진단]\n본문 내용입니다."
    )

    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text=critique_with_header,
        updated_at=datetime.now(timezone.utc),
        scores_dict=None,
        raw_en=None
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai.overall_score == 86.5
    assert ai.iaa_score == 92.0
    assert ai.iqa_score == 81.0
    assert ai.ista_score == 86.5
    assert ai.critique_en is None


def test_save_critique_to_db_gemma_standalone_none_scores(db_session, monkeypatch):
    """
    Verifies that in Gemma 4 standalone mode without scores or raw_en,
    the normalized fields are stored as None safely without error.
    """
    photo_id = "photo_save_gemma"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    plain_critique = (
        "## 1. [시각적 미학 및 EXIF 광학 진단]\n"
        "점수가 없는 Gemma 단독 심층 비평 문서입니다."
    )

    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text=plain_critique,
        updated_at=datetime.now(timezone.utc),
        scores_dict=None,
        raw_en=None
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai.critique == plain_critique
    assert ai.critique_en is None
    assert ai.overall_score is None
    assert ai.iaa_score is None
    assert ai.iqa_score is None
    assert ai.ista_score is None


def test_save_critique_to_db_empty_raw_en_handling(db_session, monkeypatch):
    """
    Verifies whitespace and empty strings in raw_en are normalized to None.
    """
    photo_id = "photo_save_empty_en"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text="내용",
        updated_at=datetime.now(timezone.utc),
        scores_dict={"overall": 80},
        raw_en="   \n\t  "
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai.critique_en is None
    assert ai.overall_score == 80.0


def test_save_critique_to_db_iso_string_datetime(db_session, monkeypatch):
    """
    Verifies string ISO datetime is accepted and converted to datetime object.
    """
    photo_id = "photo_save_iso_date"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)

    iso_str = "2026-10-24T18:45:00+00:00"
    ChatService._save_critique_to_db(
        photo_id=photo_id,
        critique_text="내용",
        updated_at=iso_str
    )

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert isinstance(ai.critique_updated_at, datetime)
    assert ai.critique_updated_at.year == 2026


@pytest.mark.asyncio
async def test_generate_photo_critique_unipercept_pipeline_end_to_end(db_session, monkeypatch):
    """
    Verifies end-to-end generate_photo_critique flow for UniPercept engine:
    pipeline yields scores_dict and raw_en -> saved into DB and returned in response dict.
    """
    photo_id = "photo_e2e_unipercept"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)
    critique_status_manager.reset(photo_id)

    # Mock photo metadata lookup
    monkeypatch.setattr(
        "services.chat_service._get_photo_and_metadata",
        lambda pid: (f"/test/{pid}.jpg", {"camera_model": "Sony A7R V"})
    )

    # Mock UniPercept adapter
    mock_uni_inst = MagicMock()
    mock_uni_inst.generate_full_ensemble_critique.return_value = {
        "critique": "Raw English critique from UniPercept model.",
        "scores": {"overall": 88.5, "iaa": 92.0, "iqa": 85.0, "ista": 88.5},
        "quality_score": 88.5
    }
    monkeypatch.setattr("services.unipercept_adapter.get_unipercept_adapter", lambda: mock_uni_inst)

    # Mock Gemma adapter
    mock_gemma_inst = MagicMock()
    mock_gemma_inst.translate_and_format_critique.return_value = (
        "[6-Way 앙상블 비평 스코어보드]\n"
        "- 최종 종합 평점: 88.5점 / 100점\n"
        "- 미학 및 구도 (IAA): 92.0점\n"
        "- 화질 및 선명도 (IQA): 85.0점\n"
        "- 구조 및 질감 (ISTA): 88.5점\n\n"
        "한국어로 정제된 비평 본문입니다."
    )
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: mock_gemma_inst)

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    # Assert response payload contains normalized scores and raw_en
    assert result["status"] == "completed"
    assert result["engine_used"] == "unipercept"
    assert result["critique_en"] == "Raw English critique from UniPercept model."
    assert result["overall_score"] == 88.5
    assert result["iaa_score"] == 92.0
    assert result["iqa_score"] == 85.0
    assert result["ista_score"] == 88.5
    assert "한국어로 정제된 비평 본문입니다." in result["critique"]

    # Assert database contains normalized scores
    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai is not None
    assert ai.critique_en == "Raw English critique from UniPercept model."
    assert ai.overall_score == 88.5
    assert ai.iaa_score == 92.0
    assert ai.iqa_score == 85.0
    assert ai.ista_score == 88.5

    # Assert critique status manager has recorded completed status and scores
    status = critique_status_manager.get(photo_id)
    assert status["status"] == "completed"
    assert status["critique_en"] == "Raw English critique from UniPercept model."
    assert status["overall_score"] == 88.5
    assert status["iaa_score"] == 92.0


@pytest.mark.asyncio
async def test_generate_photo_critique_gemma_pipeline_end_to_end(db_session, monkeypatch):
    """
    Verifies end-to-end generate_photo_critique flow for Gemma engine:
    standalone mode has no raw_en or scores -> stores None safely and completes.
    """
    photo_id = "photo_e2e_gemma"
    _create_test_photo(db_session, photo_id)
    monkeypatch.setattr("services.chat_service.SessionLocal", lambda: db_session)
    critique_status_manager.reset(photo_id)

    monkeypatch.setattr(
        "services.chat_service._get_photo_and_metadata",
        lambda pid: (f"/test/{pid}.jpg", {"camera_model": "Sony A7R V"})
    )

    mock_gemma_inst = MagicMock()
    mock_gemma_inst.generate_deep_critique.return_value = "Gemma 1차 초안"
    mock_gemma_inst.format_and_structure_critique.return_value = "Gemma 최종 구조화 비평"
    monkeypatch.setattr("services.chat_service.get_gemma_adapter", lambda: mock_gemma_inst)

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="gemma4")
    result = await ChatService.generate_photo_critique(req)

    assert result["status"] == "completed"
    assert result["engine_used"] == "gemma4"
    assert result["critique"] == "Gemma 최종 구조화 비평"
    assert result["critique_en"] is None
    assert result["overall_score"] is None
    assert result["iaa_score"] is None

    ai = db_session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()
    assert ai is not None
    assert ai.critique == "Gemma 최종 구조화 비평"
    assert ai.critique_en is None
    assert ai.overall_score is None


@pytest.mark.asyncio
async def test_generate_photo_critique_cancellation_returns_normalized_nones(db_session, monkeypatch):
    """
    Verifies that when a critique task is cancelled, the returned dictionary
    has status='cancelled' and all normalized score/text fields set to None.
    """
    from services.critique_status import CritiqueCancelledException

    photo_id = "photo_e2e_cancelled"
    _create_test_photo(db_session, photo_id)
    critique_status_manager.reset(photo_id)

    monkeypatch.setattr(
        "services.chat_service._get_photo_and_metadata",
        lambda pid: (f"/test/{pid}.jpg", {"camera_model": "Sony A7R V"})
    )

    async def mock_cancelled_pipeline(*args, **kwargs):
        raise CritiqueCancelledException("User requested cancellation")

    monkeypatch.setattr("services.chat_service._execute_unipercept_critique_pipeline", mock_cancelled_pipeline)

    req = schemas.CritiqueRequest(photo_id=photo_id, engine="unipercept")
    result = await ChatService.generate_photo_critique(req)

    assert result["status"] == "cancelled"
    assert result["critique"] == ""
    assert result["critique_en"] is None
    assert result["overall_score"] is None
    assert result["iaa_score"] is None
    assert result["iqa_score"] is None
    assert result["ista_score"] is None
    assert result["critique_updated_at"] is None

