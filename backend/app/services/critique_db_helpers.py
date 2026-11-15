"""Database lookup, score normalization, and persistence helpers for critique service."""

import datetime
from typing import Any, Callable, Dict, List, Optional

from repositories.photo_repository import PhotoRepository


def _coerce_score_float(score_val: Any) -> Optional[float]:
    if score_val is None or score_val == "":
        return None
    try:
        return float(score_val)
    except (ValueError, TypeError):
        return None


def extract_score_floats(
    scores_dict: Optional[Dict[str, Any]],
    critique_text: Optional[str],
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Resolves overall, iaa, iqa, and ista scores from dict or critique scoreboard."""
    from services.ai_parser import parse_scoreboard_scores

    overall = _coerce_score_float(scores_dict.get("overall")) if scores_dict else None
    iaa = _coerce_score_float(scores_dict.get("iaa")) if scores_dict else None
    iqa = _coerce_score_float(scores_dict.get("iqa")) if scores_dict else None
    ista = _coerce_score_float(scores_dict.get("ista")) if scores_dict else None

    needs_fallback = overall is None or iaa is None or iqa is None or ista is None
    if needs_fallback and critique_text:
        parsed_scores = parse_scoreboard_scores(critique_text)
        overall = overall if overall is not None else parsed_scores.get("overall")
        iaa = iaa if iaa is not None else parsed_scores.get("iaa")
        iqa = iqa if iqa is not None else parsed_scores.get("iqa")
        ista = ista if ista is not None else parsed_scores.get("ista")

    return overall, iaa, iqa, ista


def build_metadata_dict(meta: Any) -> dict[str, Any]:
    """Serializes ImageMetadata ORM row into critique pipeline metadata dict."""
    if not meta:
        return {
            "camera_model": None,
            "lens_model": None,
            "f_number": None,
            "focal_length": None,
            "focal_length_35mm": None,
            "sensor_format": None,
            "crop_factor": None,
            "shutter_speed": None,
            "iso": None,
        }
    return {
        "camera_model": meta.camera_model,
        "lens_model": meta.lens_model,
        "f_number": meta.f_number,
        "focal_length": meta.focal_length,
        "focal_length_35mm": meta.focal_length_35mm,
        "sensor_format": meta.sensor_format,
        "crop_factor": meta.crop_factor,
        "shutter_speed": meta.shutter_speed,
        "iso": meta.iso,
    }


def normalize_updated_at(updated_at: Any) -> Any:
    """Converts ISO datetime string to datetime object if needed."""
    if not isinstance(updated_at, str):
        return updated_at
    try:
        return datetime.datetime.fromisoformat(updated_at)
    except Exception as date_err:
        print(f"[ChatService] Failed to parse updated_at string '{updated_at}': {date_err}", flush=True)
        return updated_at


def get_photo_and_metadata_with_session(session_factory: Callable[[], Any], photo_id: str) -> tuple[str, dict]:
    """Loads file path and optical metadata dict using caller-provided session factory."""
    with session_factory() as db:
        img = PhotoRepository(db).get_by_id(photo_id)
        if not img:
            raise ValueError("Photo not found")
        return img.file_path, build_metadata_dict(img.metadata_rel)


def save_critique_with_session(
    session_factory: Callable[[], Any],
    photo_id: str,
    critique_text: str,
    updated_at: Any,
    scores_dict: Optional[Dict[str, Any]] = None,
    raw_en: Optional[str] = None,
) -> None:
    """Persists critique text, raw english anchor, and normalized 4-dim scores."""
    overall_score, iaa_score, iqa_score, ista_score = extract_score_floats(scores_dict, critique_text)
    critique_en = raw_en.strip() if (raw_en and isinstance(raw_en, str) and raw_en.strip()) else None
    normalized_updated_at = normalize_updated_at(updated_at)

    with session_factory() as db:
        PhotoRepository(db).upsert_critique(
            photo_id=photo_id,
            critique_text=critique_text,
            updated_at=normalized_updated_at,
            critique_en=critique_en,
            overall_score=overall_score,
            iaa_score=iaa_score,
            iqa_score=iqa_score,
            ista_score=ista_score,
        )


def fetch_critiques_with_session(session_factory: Callable[[], Any], photo_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Fetches stored critiques joined with image and camera metadata for portfolio summary."""
    with session_factory() as db:
        rows = PhotoRepository(db).list_critiques(sort_by="recent", photo_ids=photo_ids)
        if not rows:
            raise ValueError("요약할 AI 비평 데이터가 존재하지 않습니다.")
        return [
            {
                "photo_id": img.id,
                "file_name": img.file_name,
                "camera_model": meta.camera_model if meta else None,
                "lens_model": meta.lens_model if meta else None,
                "critique": ai.critique,
            }
            for ai, img, meta in rows
        ]
