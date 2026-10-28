"""
Perceptual scoring module for focal_node AI photo critique.
Implements the EXIF-adaptive perceptual scoring model (ADR-04):
- Resolves 4-mode optical weights based on aperture (F) and ISO.
- Computes aesthetic excellence bonus when artistic value (IAA) exceeds technical quality (IQA).
- Fuses and clamps the final overall score to [0, 100].
"""

from typing import Optional, Tuple


def resolve_perceptual_weights(
    f_number: Optional[float] = None,
    iso: Optional[float] = None
) -> Tuple[float, float, float]:
    """
    Resolves optical weights (w_iaa, w_iqa, w_ista) based on EXIF optics:
    - Mode A (Shallow depth of field / Portrait): F <= 2.8 -> (0.65, 0.25, 0.10)
    - Mode B (Pan-focus / Landscape): F >= 5.6 -> (0.45, 0.30, 0.25)
    - Mode C (Night / Street snap): ISO >= 1600 -> (0.70, 0.20, 0.10)
    - Mode D (Standard / Fallback): otherwise or missing EXIF -> (0.55, 0.30, 0.15)
    """
    # Guard against invalid optical values
    if f_number is not None and 0.0 < f_number <= 2.8:
        return 0.65, 0.25, 0.10

    if f_number is not None and f_number >= 5.6:
        return 0.45, 0.30, 0.25

    if iso is not None and iso >= 1600:
        return 0.70, 0.20, 0.10

    return 0.55, 0.30, 0.15


def calculate_aesthetic_bonus(iaa: float, iqa: float) -> float:
    """
    Calculates aesthetic excellence bonus when IAA >= 75 and IAA > IQA:
    Delta_aesthetic = (IAA - IQA) * 0.25 * (IAA / 100)
    """
    if iaa >= 75.0 and iaa > iqa:
        return (iaa - iqa) * 0.25 * (iaa / 100.0)
    return 0.0


def calculate_overall_vr_score(
    iaa: float,
    iqa: float,
    ista: float,
    f_number: Optional[float] = None,
    iso: Optional[float] = None
) -> int:
    """
    Calculates the final clamped overall perceptual score:
    S_base = (w_iaa * IAA) + (w_iqa * IQA) + (w_ista * ISTA)
    overall_score = min(100, max(0, round(S_base + Delta_aesthetic)))
    """
    w_iaa, w_iqa, w_ista = resolve_perceptual_weights(f_number, iso)
    base_score = (w_iaa * iaa) + (w_iqa * iqa) + (w_ista * ista)
    bonus = calculate_aesthetic_bonus(iaa, iqa)
    return min(100, max(0, round(base_score + bonus)))
