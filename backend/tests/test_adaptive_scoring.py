import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import run_migrations, _backfill_adaptive_overall_scores
from services.scoring import (
    resolve_perceptual_weights,
    calculate_aesthetic_bonus,
    calculate_overall_vr_score,
)


def test_resolve_perceptual_weights_modes():
    """Verifies that weights match the 4-mode specification in spec.md."""
    # Mode A: Shallow depth of field (F <= 2.8)
    assert resolve_perceptual_weights(f_number=1.4, iso=100) == (0.65, 0.25, 0.10)
    assert resolve_perceptual_weights(f_number=2.8, iso=800) == (0.65, 0.25, 0.10)

    # Mode B: Pan-focus landscape/architecture (F >= 5.6)
    assert resolve_perceptual_weights(f_number=5.6, iso=100) == (0.45, 0.30, 0.25)
    assert resolve_perceptual_weights(f_number=8.0, iso=400) == (0.45, 0.30, 0.25)

    # Mode C: Night/Street snap (ISO >= 1600, F is between 2.8 and 5.6, or F is None)
    assert resolve_perceptual_weights(f_number=4.0, iso=1600) == (0.70, 0.20, 0.10)
    assert resolve_perceptual_weights(f_number=4.0, iso=3200) == (0.70, 0.20, 0.10)
    assert resolve_perceptual_weights(f_number=None, iso=6400) == (0.70, 0.20, 0.10)

    # Mode D: Standard / Fallback (otherwise or missing EXIF)
    assert resolve_perceptual_weights(f_number=4.0, iso=400) == (0.55, 0.30, 0.15)
    assert resolve_perceptual_weights(f_number=None, iso=None) == (0.55, 0.30, 0.15)
    assert resolve_perceptual_weights(f_number=0.0, iso=100) == (0.55, 0.30, 0.15)
    assert resolve_perceptual_weights(f_number=-1.0, iso=100) == (0.55, 0.30, 0.15)


def test_calculate_aesthetic_bonus():
    """Verifies bonus calculation when IAA >= 75 and IAA > IQA."""
    # Positive bonus: IAA=90, IQA=70 -> (90-70) * 0.25 * (90/100) = 4.5
    bonus = calculate_aesthetic_bonus(iaa=90.0, iqa=70.0)
    assert pytest.approx(bonus, 1e-4) == 4.5

    # Positive bonus: IAA=80, IQA=60 -> (80-60) * 0.25 * (80/100) = 4.0
    bonus = calculate_aesthetic_bonus(iaa=80.0, iqa=60.0)
    assert pytest.approx(bonus, 1e-4) == 4.0

    # Threshold condition: IAA=75, IQA=70 -> (75-70) * 0.25 * (75/100) = 0.9375
    bonus = calculate_aesthetic_bonus(iaa=75.0, iqa=70.0)
    assert pytest.approx(bonus, 1e-4) == 0.9375

    # Ineligible: IAA < 75
    assert calculate_aesthetic_bonus(iaa=74.9, iqa=50.0) == 0.0

    # Ineligible: IAA <= IQA
    assert calculate_aesthetic_bonus(iaa=90.0, iqa=90.0) == 0.0
    assert calculate_aesthetic_bonus(iaa=80.0, iqa=90.0) == 0.0


def test_calculate_overall_vr_score():
    """Verifies combined base score and aesthetic bonus with clamping."""
    # Mode A (F1.4): IAA=90, IQA=70, ISTA=60
    # base = (0.65*90) + (0.25*70) + (0.10*60) = 58.5 + 17.5 + 6.0 = 82.0
    # bonus = 4.5
    # total = 82.0 + 4.5 = 86.5 -> round(86.5) = 86 (Python banker's round to even)
    score = calculate_overall_vr_score(iaa=90.0, iqa=70.0, ista=60.0, f_number=1.4, iso=100)
    assert score == 86

    # Mode B (F8.0): IAA=70, IQA=80, ISTA=80
    # base = (0.45*70) + (0.30*80) + (0.25*80) = 31.5 + 24.0 + 20.0 = 75.5
    # bonus = 0.0 (IAA < 75 and IAA < IQA)
    # total = round(75.5) = 76
    score = calculate_overall_vr_score(iaa=70.0, iqa=80.0, ista=80.0, f_number=8.0, iso=400)
    assert score == 76

    # Mode C (ISO 3200): IAA=80, IQA=60, ISTA=50
    # base = (0.70*80) + (0.20*60) + (0.10*50) = 56.0 + 12.0 + 5.0 = 73.0
    # bonus = (80-60) * 0.25 * (80/100) = 4.0
    # total = round(73.0 + 4.0) = 77
    score = calculate_overall_vr_score(iaa=80.0, iqa=60.0, ista=50.0, f_number=4.0, iso=3200)
    assert score == 77

    # Clamping: upper bound 100
    assert calculate_overall_vr_score(iaa=100.0, iqa=100.0, ista=100.0) == 100
    # Clamping: lower bound 0
    assert calculate_overall_vr_score(iaa=0.0, iqa=0.0, ista=0.0) == 0


def test_tc_crt_08_backfill_adaptive_overall_scores():
    """
    TC-CRT-08: Verifies that database migration joins with image_metadata and backfills
    overall_score using the adaptive formula for all records where iaa_score IS NOT NULL.
    """
    fresh_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    # 1. Run migrations to initialize schema
    run_migrations(fresh_engine)

    Session = sessionmaker(bind=fresh_engine)
    with Session() as session:
        # Seed test images
        img1 = models.Image(
            id="photo_adaptive_1",
            parent_dir="/photos",
            file_name="portrait.jpg",
            file_path="/photos/portrait.jpg",
            file_size=5000,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img2 = models.Image(
            id="photo_adaptive_2",
            parent_dir="/photos",
            file_name="landscape.jpg",
            file_path="/photos/landscape.jpg",
            file_size=5000,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img3 = models.Image(
            id="photo_adaptive_3",
            parent_dir="/photos",
            file_name="night.jpg",
            file_path="/photos/night.jpg",
            file_size=5000,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img4 = models.Image(
            id="photo_adaptive_4",
            parent_dir="/photos",
            file_name="standard.jpg",
            file_path="/photos/standard.jpg",
            file_size=5000,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        img5 = models.Image(
            id="photo_adaptive_5",
            parent_dir="/photos",
            file_name="no_critique.jpg",
            file_path="/photos/no_critique.jpg",
            file_size=5000,
            file_mtime=1.0,
            mime_type="image/jpeg"
        )
        session.add_all([img1, img2, img3, img4, img5])

        # Metadata (EXIF)
        meta1 = models.ImageMetadata(image_id="photo_adaptive_1", f_number=1.4, iso=100)
        meta2 = models.ImageMetadata(image_id="photo_adaptive_2", f_number=8.0, iso=200)
        meta3 = models.ImageMetadata(image_id="photo_adaptive_3", f_number=4.0, iso=3200)
        # photo_adaptive_4 has no metadata entry
        meta5 = models.ImageMetadata(image_id="photo_adaptive_5", f_number=2.8, iso=100)
        session.add_all([meta1, meta2, meta3, meta5])

        # AI Analysis: initial rows with old linear overall_score
        # Photo 1 (Mode A): old score was 75.0 (0.4*90 + 0.3*70 + 0.3*60)
        ai1 = models.AIAnalysis(
            image_id="photo_adaptive_1",
            critique="비평 1",
            iaa_score=90.0,
            iqa_score=70.0,
            ista_score=60.0,
            overall_score=75.0
        )
        # Photo 2 (Mode B): old score 76.0
        ai2 = models.AIAnalysis(
            image_id="photo_adaptive_2",
            critique="비평 2",
            iaa_score=70.0,
            iqa_score=80.0,
            ista_score=80.0,
            overall_score=76.0
        )
        # Photo 3 (Mode C): old score 65.0
        ai3 = models.AIAnalysis(
            image_id="photo_adaptive_3",
            critique="비평 3",
            iaa_score=80.0,
            iqa_score=60.0,
            ista_score=50.0,
            overall_score=65.0
        )
        # Photo 4 (Mode D fallback): IAA=60, IQA=60, ISTA=60
        ai4 = models.AIAnalysis(
            image_id="photo_adaptive_4",
            critique="비평 4",
            iaa_score=60.0,
            iqa_score=60.0,
            ista_score=60.0,
            overall_score=60.0
        )
        # Photo 5: No critique (iaa_score is None)
        ai5 = models.AIAnalysis(
            image_id="photo_adaptive_5",
            critique=None,
            iaa_score=None,
            iqa_score=None,
            ista_score=None,
            overall_score=None
        )
        session.add_all([ai1, ai2, ai3, ai4, ai5])
        session.commit()

    # 2. Run adaptive backfill migration
    _backfill_adaptive_overall_scores(fresh_engine)

    # 3. Verify results
    with Session() as session:
        res1 = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_1").first()
        assert res1.overall_score == 86.0  # Updated from 75.0 to 86.0

        res2 = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_2").first()
        assert res2.overall_score == 76.0  # Mode B score: 76.0

        res3 = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_3").first()
        assert res3.overall_score == 77.0  # Updated from 65.0 to 77.0

        res4 = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_4").first()
        assert res4.overall_score == 60.0  # Standard mode fallback: 60.0

        res5 = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_5").first()
        assert res5.overall_score is None  # Remained None

    # 4. Idempotency check: running again should succeed without side effects
    _backfill_adaptive_overall_scores(fresh_engine)
    with Session() as session:
        res1_second = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_1").first()
        assert res1_second.overall_score == 86.0

    # 5. Full run_migrations() integration check: calling run_migrations directly
    # should invoke _backfill_adaptive_overall_scores safely without error
    run_migrations(fresh_engine)
    with Session() as session:
        res1_third = session.query(models.AIAnalysis).filter_by(image_id="photo_adaptive_1").first()
        assert res1_third.overall_score == 86.0


def test_tc_crt_06_unipercept_adaptive_weights_and_aesthetic_bonus(monkeypatch):
    """
    TC-CRT-06: Verifies UniPerceptAdapter's adaptive weights and aesthetic bonus integration:
    - Mode A (F1.4 portrait): w=(0.65, 0.25, 0.10) with aesthetic bonus when IAA >= 75 and IAA > IQA
    - Mode B (F8.0 pan-focus landscape): w=(0.45, 0.30, 0.25)
    - Mode C (ISO 3200 night/street): w=(0.70, 0.20, 0.10) with aesthetic bonus
    - Verifies delegation through _resolve_perceptual_weights, _calculate_aesthetic_bonus,
      _calculate_overall_vr_score, generate_vr_scores, and generate_full_ensemble_critique.
    """
    from services.unipercept_adapter import UniPerceptAdapter

    adapter = UniPerceptAdapter()

    # 1. Direct adapter delegation methods
    assert adapter._resolve_perceptual_weights(f_number=1.4, iso=100) == (0.65, 0.25, 0.10)
    assert adapter._resolve_perceptual_weights(f_number=8.0, iso=200) == (0.45, 0.30, 0.25)
    assert adapter._resolve_perceptual_weights(f_number=4.0, iso=3200) == (0.70, 0.20, 0.10)

    # Aesthetic bonus delegation
    bonus = adapter._calculate_aesthetic_bonus(iaa=90.0, iqa=70.0)
    assert pytest.approx(bonus, 1e-4) == 4.5

    # Overall VR score delegation
    # Mode A (F1.4): base = (0.65*90) + (0.25*70) + (0.10*60) = 82.0; bonus = 4.5; total = 86.5 -> 86
    score_a = adapter._calculate_overall_vr_score(iaa=90.0, iqa=70.0, ista=60.0, f_number=1.4, iso=100)
    assert score_a == 86

    # Mode B (F8.0): base = (0.45*70) + (0.30*80) + (0.25*80) = 75.5; bonus = 0.0; total = 76
    score_b = adapter._calculate_overall_vr_score(iaa=70.0, iqa=80.0, ista=80.0, f_number=8.0, iso=400)
    assert score_b == 76

    # Mode C (ISO 3200): base = (0.70*80) + (0.20*60) + (0.10*50) = 73.0; bonus = 4.0; total = 77
    score_c = adapter._calculate_overall_vr_score(iaa=80.0, iqa=60.0, ista=50.0, f_number=4.0, iso=3200)
    assert score_c == 77

    # 2. Pipeline integration via generate_vr_scores & generate_full_ensemble_critique
    def mock_vr(pixel_values, desc):
        if desc == "aesthetics":
            return 90.0
        elif desc == "quality":
            return 70.0
        elif desc == "structure and texture richness":
            return 60.0
        return 70.0

    monkeypatch.setattr(adapter, "compute_official_vr_score", mock_vr)
    monkeypatch.setattr(adapter, "_load_pil_image", lambda path: None)
    monkeypatch.setattr(adapter, "_prepare_pixel_values", lambda pil_img: None)
    adapter.model = type("MockModel", (), {"chat": lambda *args, **kwargs: "Mock critique"})()

    # Pass via metadata dict (Mode A)
    vr_res = adapter.generate_vr_scores("/fake/path.jpg", metadata={"f_number": 1.4, "iso": 100})
    assert vr_res["overall"] == 86
    assert vr_res["iaa"] == 90.0
    assert vr_res["iqa"] == 70.0
    assert vr_res["ista"] == 60.0

    # Pass via explicit kwargs (Mode B)
    vr_res_b = adapter.generate_vr_scores("/fake/path.jpg", f_number=8.0, iso=200)
    # Mode B: base = 0.45*90 + 0.30*70 + 0.25*60 = 40.5 + 21.0 + 15.0 = 76.5
    # bonus = (90-70)*0.25*0.9 = 4.5 -> total = 76.5 + 4.5 = 81.0 -> 81
    assert vr_res_b["overall"] == 81

    # Full ensemble critique pass
    ens_res = adapter.generate_full_ensemble_critique(
        "/fake/path.jpg",
        metadata={"camera_model": "Sony A7R V"},
        f_number=1.4,
        iso=100
    )
    assert ens_res["quality_score"] == 86
    assert ens_res["scores"]["overall"] == 86


def test_tc_crt_07_unipercept_fallback_and_clamping(monkeypatch):
    """
    TC-CRT-07: Verifies UniPerceptAdapter's fallback to Mode D on missing/invalid EXIF and score clamping:
    - Missing metadata/EXIF falls back to Mode D standard weights (0.55, 0.30, 0.15)
    - Invalid/negative/string aperture or ISO safely handled with fallback
    - Upper bound clamped to 100, lower bound clamped to 0
    - Extreme aesthetic bonus conditions clamped safely
    """
    from services.unipercept_adapter import UniPerceptAdapter

    adapter = UniPerceptAdapter()

    # 1. Missing or invalid optical values fallback to Mode D
    assert adapter._resolve_perceptual_weights(f_number=None, iso=None) == (0.55, 0.30, 0.15)
    assert adapter._resolve_perceptual_weights(f_number=0.0, iso=0.0) == (0.55, 0.30, 0.15)
    assert adapter._resolve_perceptual_weights(f_number=-2.8, iso=-100) == (0.55, 0.30, 0.15)

    # 2. Clamping edge cases
    assert adapter._calculate_overall_vr_score(iaa=100.0, iqa=100.0, ista=100.0) == 100
    assert adapter._calculate_overall_vr_score(iaa=0.0, iqa=0.0, ista=0.0) == 0

    # Extreme aesthetic bonus calculation & upper clamping
    # IAA=100, IQA=50, ISTA=50 in Mode A
    # base = 0.65*100 + 0.25*50 + 0.10*50 = 65.0 + 12.5 + 5.0 = 82.5
    # bonus = (100 - 50) * 0.25 * (100/100) = 12.5
    # total = 82.5 + 12.5 = 95.0 -> 95
    score_extreme = adapter._calculate_overall_vr_score(iaa=100.0, iqa=50.0, ista=50.0, f_number=1.4)
    assert score_extreme == 95

    # 3. Pipeline fallback with empty/invalid metadata in generate_vr_scores
    def mock_vr_flat(pixel_values, desc):
        return 60.0

    adapter.model = type("MockModel", (), {"chat": lambda *args, **kwargs: "Mock"})()
    monkeypatch.setattr(adapter, "compute_official_vr_score", mock_vr_flat)
    monkeypatch.setattr(adapter, "_load_pil_image", lambda path: None)
    monkeypatch.setattr(adapter, "_prepare_pixel_values", lambda pil_img: None)

    # Empty metadata -> Mode D: base = 0.55*60 + 0.30*60 + 0.15*60 = 60.0, bonus = 0.0 -> 60
    vr_res_none = adapter.generate_vr_scores("/fake/path.jpg", metadata=None)
    assert vr_res_none["overall"] == 60

    # Malformed string metadata -> safely falls back to Mode D
    vr_res_invalid = adapter.generate_vr_scores(
        "/fake/path.jpg",
        metadata={"f_number": "not_a_number", "iso": "unknown"}
    )
    assert vr_res_invalid["overall"] == 60

    # Valid string representation in metadata -> parses correctly
    # Mode A (F="1.4", ISO="100") with IAA=90, IQA=70, ISTA=60
    def mock_vr_varied(pixel_values, desc):
        if desc == "aesthetics":
            return 90.0
        elif desc == "quality":
            return 70.0
        return 60.0
    monkeypatch.setattr(adapter, "compute_official_vr_score", mock_vr_varied)

    vr_res_str = adapter.generate_vr_scores(
        "/fake/path.jpg",
        metadata={"f_number": "1.4", "iso": "100"}
    )
    assert vr_res_str["overall"] == 86
