"""
Unit tests for the perceptual ensemble scoring mathematics (services.scoring).
Verifies:
- 4-mode optical weight resolution based on EXIF optics (aperture, ISO).
- Aesthetic excellence bonus calculation (IAA >= 75 and IAA > IQA).
- Overall perceptual score fusion, rounding, and [0, 100] clamping.
"""

import pytest
from services.scoring import (
    resolve_perceptual_weights,
    calculate_aesthetic_bonus,
    calculate_overall_vr_score,
)


class TestEnsembleMath:
    """Production mathematical verification for services.scoring."""

    def test_resolve_perceptual_weights_modes(self):
        # Mode A: Shallow depth of field / Portrait (F <= 2.8)
        assert resolve_perceptual_weights(f_number=1.4, iso=100) == (0.65, 0.25, 0.10)
        assert resolve_perceptual_weights(f_number=2.8, iso=800) == (0.65, 0.25, 0.10)

        # Mode B: Pan-focus / Landscape (F >= 5.6)
        assert resolve_perceptual_weights(f_number=5.6, iso=100) == (0.45, 0.30, 0.25)
        assert resolve_perceptual_weights(f_number=11.0, iso=400) == (0.45, 0.30, 0.25)

        # Mode C: Night / Street snap (ISO >= 1600, F between 2.8 and 5.6 or missing)
        assert resolve_perceptual_weights(f_number=4.0, iso=1600) == (0.70, 0.20, 0.10)
        assert resolve_perceptual_weights(f_number=None, iso=3200) == (0.70, 0.20, 0.10)

        # Mode D: Standard / Fallback (mid-aperture, normal ISO, or missing/invalid EXIF)
        assert resolve_perceptual_weights(f_number=4.0, iso=400) == (0.55, 0.30, 0.15)
        assert resolve_perceptual_weights(f_number=None, iso=None) == (0.55, 0.30, 0.15)
        assert resolve_perceptual_weights(f_number=0.0, iso=100) == (0.55, 0.30, 0.15)
        assert resolve_perceptual_weights(f_number=-1.5, iso=100) == (0.55, 0.30, 0.15)

    def test_calculate_aesthetic_bonus(self):
        # Trigger condition: IAA >= 75.0 and IAA > IQA
        # Delta = (IAA - IQA) * 0.25 * (IAA / 100)

        # Case 1: IAA=90, IQA=70 -> (20) * 0.25 * 0.9 = 4.5
        bonus_1 = calculate_aesthetic_bonus(90.0, 70.0)
        assert pytest.approx(bonus_1, 0.001) == 4.5

        # Case 2: IAA=80, IQA=60 -> (20) * 0.25 * 0.8 = 4.0
        bonus_2 = calculate_aesthetic_bonus(80.0, 60.0)
        assert pytest.approx(bonus_2, 0.001) == 4.0

        # Case 3: Exact threshold IAA=75, IQA=50 -> (25) * 0.25 * 0.75 = 4.6875
        bonus_3 = calculate_aesthetic_bonus(75.0, 50.0)
        assert pytest.approx(bonus_3, 0.001) == 4.6875

        # Suppressed: IAA below 75 even if IAA > IQA
        assert calculate_aesthetic_bonus(74.9, 50.0) == 0.0

        # Suppressed: IAA <= IQA even if IAA >= 75
        assert calculate_aesthetic_bonus(90.0, 95.0) == 0.0
        assert calculate_aesthetic_bonus(80.0, 80.0) == 0.0

    def test_calculate_overall_vr_score_perfect_and_zero(self):
        # Perfect scores
        perfect = calculate_overall_vr_score(100.0, 100.0, 100.0, f_number=1.4, iso=100)
        assert perfect == 100

        # Zero scores
        zero = calculate_overall_vr_score(0.0, 0.0, 0.0, f_number=1.4, iso=100)
        assert zero == 0

    def test_calculate_overall_vr_score_mode_a_portrait(self):
        # Mode A: w = (0.65, 0.25, 0.10)
        # IAA=90, IQA=70, ISTA=80
        # base = (0.65 * 90) + (0.25 * 70) + (0.10 * 80) = 58.5 + 17.5 + 8.0 = 84.0
        # bonus = (90 - 70) * 0.25 * 0.9 = 4.5
        # total = 84.0 + 4.5 = 88.5 -> round(88.5) = 88 (banker's rounding in Python)
        score = calculate_overall_vr_score(90.0, 70.0, 80.0, f_number=1.4, iso=100)
        assert score == 88

    def test_calculate_overall_vr_score_mode_b_landscape(self):
        # Mode B: w = (0.45, 0.30, 0.25)
        # IAA=80, IQA=90, ISTA=85
        # base = (0.45 * 80) + (0.30 * 90) + (0.25 * 85) = 36.0 + 27.0 + 21.25 = 84.25
        # bonus = 0.0 (IAA < IQA)
        # total = round(84.25) = 84
        score = calculate_overall_vr_score(80.0, 90.0, 85.0, f_number=8.0, iso=100)
        assert score == 84

    def test_calculate_overall_vr_score_mode_c_night(self):
        # Mode C: w = (0.70, 0.20, 0.10)
        # IAA=85, IQA=60, ISTA=70
        # base = (0.70 * 85) + (0.20 * 60) + (0.10 * 70) = 59.5 + 12.0 + 7.0 = 78.5
        # bonus = (85 - 60) * 0.25 * 0.85 = 25 * 0.2125 = 5.3125
        # total = 78.5 + 5.3125 = 83.8125 -> round = 84
        score = calculate_overall_vr_score(85.0, 60.0, 70.0, f_number=4.0, iso=3200)
        assert score == 84

    def test_calculate_overall_vr_score_mode_d_fallback(self):
        # Mode D: w = (0.55, 0.30, 0.15)
        # IAA=80, IQA=70, ISTA=60
        # base = (0.55 * 80) + (0.30 * 70) + (0.15 * 60) = 44.0 + 21.0 + 9.0 = 74.0
        # bonus = (80 - 70) * 0.25 * 0.8 = 2.0
        # total = 74.0 + 2.0 = 76.0 -> 76
        score = calculate_overall_vr_score(80.0, 70.0, 60.0, f_number=None, iso=None)
        assert score == 76

    def test_clamping_bounds(self):
        # Extreme upper bound clamping
        score_upper = calculate_overall_vr_score(120.0, 100.0, 100.0, f_number=1.4, iso=100)
        assert score_upper == 100

        # Extreme lower bound clamping
        score_lower = calculate_overall_vr_score(-20.0, -10.0, 0.0, f_number=1.4, iso=100)
        assert score_lower == 0
