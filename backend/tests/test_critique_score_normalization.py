import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import schemas
from database import Base, run_migrations, _backfill_critique_scores
from services.ai_parser import parse_scoreboard_scores
from services.critique_status import CritiqueStatusManager


def test_parse_scoreboard_scores_standard():
    sample_text = (
        "[6-Way 앙상블 비평 스코어보드]\n"
        "- 최종 종합 평점: 85점 / 100점\n"
        "- 미학 및 구도 (IAA): 88점\n"
        "- 화질 및 선명도 (IQA): 82점\n"
        "- 구조 및 질감 (ISTA): 84점\n\n"
        "> **한 줄 총평**: 탁월한 구도와 빛의 조화가 돋보이는 수작입니다.\n\n"
        "## 1. [미학 및 구도 평가 (IAA)]\n"
        "- 황금분할에 정렬된 주 피사체\n"
    )
    scores = parse_scoreboard_scores(sample_text)
    assert scores["overall"] == 85.0
    assert scores["iaa"] == 88.0
    assert scores["iqa"] == 82.0
    assert scores["ista"] == 84.0


def test_parse_scoreboard_scores_with_decimals_and_icon():
    sample_text = (
        "[📊 6-Way 앙상블 비평 스코어보드]\n"
        "- 최종 종합 평점: 84.5점 / 100점\n"
        "- 미학 및 구도 (IAA): 88.2점\n"
        "- 화질 및 광학 기술 (IQA): 81.0점\n"
        "- 구조 및 질감 (ISTA): 84.3점\n\n"
    )
    scores = parse_scoreboard_scores(sample_text)
    assert scores["overall"] == 84.5
    assert scores["iaa"] == 88.2
    assert scores["iqa"] == 81.0
    assert scores["ista"] == 84.3


def test_parse_scoreboard_scores_fallback_standalone():
    sample_text = (
        "[품질/미학 점수: 78점 / 100점]\n\n"
        "> **한 줄 총평**: 피사체의 감성적인 톤이 인상적입니다.\n"
    )
    scores = parse_scoreboard_scores(sample_text)
    assert scores["overall"] == 78.0
    assert scores["iaa"] is None
    assert scores["iqa"] is None
    assert scores["ista"] is None


def test_parse_scoreboard_scores_empty_or_invalid():
    assert parse_scoreboard_scores(None) == {"overall": None, "iaa": None, "iqa": None, "ista": None}
    assert parse_scoreboard_scores("") == {"overall": None, "iaa": None, "iqa": None, "ista": None}
    assert parse_scoreboard_scores("일반 캡션 텍스트입니다.") == {"overall": None, "iaa": None, "iqa": None, "ista": None}


def test_database_migration_columns_and_indices():
    fresh_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    run_migrations(fresh_engine)

    inspector = inspect(fresh_engine)
    columns = [col["name"] for col in inspector.get_columns("ai_analysis")]
    assert "overall_score" in columns
    assert "iaa_score" in columns
    assert "iqa_score" in columns
    assert "ista_score" in columns
    assert "critique_en" in columns

    indexes = [idx["name"] for idx in inspector.get_indexes("ai_analysis")]
    assert "idx_ai_analysis_overall_score" in indexes
    assert "idx_ai_analysis_iaa_score" in indexes


def test_database_backfill_legacy_critiques():
    fresh_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    run_migrations(fresh_engine)

    Session = sessionmaker(bind=fresh_engine)
    with Session() as session:
        # 1. Base images
        img1 = models.Image(
            id="photo_backfill_1",
            parent_dir="/test",
            file_name="p1.jpg",
            file_path="/test/p1.jpg",
            file_size=100,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img2 = models.Image(
            id="photo_backfill_2",
            parent_dir="/test",
            file_name="p2.jpg",
            file_path="/test/p2.jpg",
            file_size=100,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img3 = models.Image(
            id="photo_backfill_3",
            parent_dir="/test",
            file_name="p3.jpg",
            file_path="/test/p3.jpg",
            file_size=100,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        session.add_all([img1, img2, img3])
        session.commit()

        # Row 1: Legacy critique with 6-Way scoreboard, overall_score is NULL
        ai1 = models.AIAnalysis(
            image_id="photo_backfill_1",
            critique=(
                "[6-Way 앙상블 비평 스코어보드]\n"
                "- 최종 종합 평점: 86.5점 / 100점\n"
                "- 미학 및 구도 (IAA): 90.0점\n"
                "- 화질 및 선명도 (IQA): 83.0점\n"
                "- 구조 및 질감 (ISTA): 85.5점\n\n"
                "본문 비평..."
            ),
            overall_score=None
        )
        # Row 2: Standalone format, overall_score is NULL
        ai2 = models.AIAnalysis(
            image_id="photo_backfill_2",
            critique="[품질/미학 점수: 75점 / 100점]\n비평 본문...",
            overall_score=None
        )
        # Row 3: Already has overall_score set to 92.0
        ai3 = models.AIAnalysis(
            image_id="photo_backfill_3",
            critique="[6-Way 앙상블 비평 스코어보드]\n- 최종 종합 평점: 50점 / 100점\n...",
            overall_score=92.0
        )
        session.add_all([ai1, ai2, ai3])
        session.commit()

    # Trigger backfill
    _backfill_critique_scores(fresh_engine)

    with Session() as session:
        updated_ai1 = session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == "photo_backfill_1").first()
        assert updated_ai1.overall_score == 86.5
        assert updated_ai1.iaa_score == 90.0
        assert updated_ai1.iqa_score == 83.0
        assert updated_ai1.ista_score == 85.5

        updated_ai2 = session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == "photo_backfill_2").first()
        assert updated_ai2.overall_score == 75.0
        assert updated_ai2.iaa_score is None

        updated_ai3 = session.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == "photo_backfill_3").first()
        # Should not be overwritten since overall_score was already populated
        assert updated_ai3.overall_score == 92.0


def test_models_and_schemas_serialization(db_session):
    img = models.Image(
        id="photo_serial_test",
        parent_dir="/test",
        file_name="serial.jpg",
        file_path="/test/serial.jpg",
        file_size=2048,
        file_mtime=1.0,
        mime_type="image/jpeg"
    )
    ai = models.AIAnalysis(
        image_id="photo_serial_test",
        caption="아름다운 바다",
        tags='["바다", "일몰"]',
        aesthetic_tags='["골든 아워"]',
        critique="[6-Way 앙상블 비평 스코어보드]...",
        critique_en="Detailed English critique...",
        overall_score=87.5,
        iaa_score=91.0,
        iqa_score=84.0,
        ista_score=86.5
    )
    db_session.add(img)
    db_session.add(ai)
    db_session.commit()

    detail_dict = img.to_detail_dict()
    ai_dict = detail_dict["ai_analysis"]
    assert ai_dict["critique_en"] == "Detailed English critique..."
    assert ai_dict["overall_score"] == 87.5
    assert ai_dict["iaa_score"] == 91.0
    assert ai_dict["iqa_score"] == 84.0
    assert ai_dict["ista_score"] == 86.5

    # Validate with Pydantic schemas
    schema_obj = schemas.AIAnalysisSchema(**ai_dict)
    assert schema_obj.overall_score == 87.5
    assert schema_obj.critique_en == "Detailed English critique..."

    critique_resp = schemas.CritiqueResponse(
        critique="한국어 비평",
        critique_en="English critique",
        overall_score=87.5,
        iaa_score=91.0,
        iqa_score=84.0,
        ista_score=86.5
    )
    assert critique_resp.overall_score == 87.5
    assert critique_resp.critique_en == "English critique"


def test_critique_status_manager_normalized_fields():
    mgr = CritiqueStatusManager()
    photo_id = "test_status_norm_photo"

    mgr.update(
        photo_id=photo_id,
        step=4,
        total_steps=4,
        message="비평 완료",
        progress=100,
        status="completed",
        critique="한국어 비평",
        critique_en="English critique",
        overall_score=89.5,
        iaa_score=92.0,
        iqa_score=86.0,
        ista_score=88.5
    )

    status = mgr.get(photo_id)
    assert status["status"] == "completed"
    assert status["overall_score"] == 89.5
    assert status["iaa_score"] == 92.0
    assert status["iqa_score"] == 86.0
    assert status["ista_score"] == 88.5
    assert status["critique_en"] == "English critique"
