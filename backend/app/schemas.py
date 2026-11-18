from datetime import date, datetime, time
import re
from typing import Any, List, Optional
from pydantic import BaseModel, field_validator

_DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_date_filter_bound(raw_value: Any, *, end_of_day: bool) -> Any:
    """Expands date-only values to full-day boundaries and strips tzinfo for naive SQLite comparison."""
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value.replace(tzinfo=None) if raw_value.tzinfo is not None else raw_value
    boundary_time = time.max if end_of_day else time.min
    if isinstance(raw_value, date):
        return datetime.combine(raw_value, boundary_time)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if _DATE_ONLY_PATTERN.fullmatch(stripped):
            return datetime.combine(date.fromisoformat(stripped), boundary_time)
    return raw_value

class PhotoListResponse(BaseModel):
    id: str
    file_name: str
    file_path: str
    is_favorite: bool
    capture_date: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class PhotoMetadataSchema(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    color_space: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    f_number: Optional[float] = None
    focal_length: Optional[float] = None
    focal_length_35mm: Optional[float] = None
    crop_factor: Optional[float] = None
    sensor_format: Optional[str] = None
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    capture_date: Optional[str] = None

class AIAnalysisSchema(BaseModel):
    caption: Optional[str] = None
    tags: List[str] = []
    aesthetic_tags: List[str] = []
    is_user_edited: bool = False
    critique: Optional[str] = None
    critique_en: Optional[str] = None
    overall_score: Optional[float] = None
    iaa_score: Optional[float] = None
    iqa_score: Optional[float] = None
    ista_score: Optional[float] = None
    critique_updated_at: Optional[str] = None

class PhotoDetailResponse(BaseModel):
    id: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    is_favorite: bool
    metadata: PhotoMetadataSchema
    ai_analysis: AIAnalysisSchema

class UpdateMetadataRequest(BaseModel):
    caption: str
    tags: List[str]

class UpdateMetadataResponse(BaseModel):
    status: str
    id: str
    ai_analysis: AIAnalysisSchema

class FavoriteToggleResponse(BaseModel):
    id: str
    is_favorite: bool

class IndexStartRequest(BaseModel):
    folder_paths: List[str]

class FolderResponse(BaseModel):
    path: str
    created_at: str

class ExportRequest(BaseModel):
    photo_ids: List[str]
    destination_folder: str

class SearchFilter(BaseModel):
    is_favorite: Optional[bool] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    iso_min: Optional[int] = None
    iso_max: Optional[int] = None
    f_number_min: Optional[float] = None
    f_number_max: Optional[float] = None
    focal_length_min: Optional[float] = None
    focal_length_max: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    @field_validator("date_from", mode="before")
    @classmethod
    def _normalize_date_from(cls, raw_value: Any) -> Any:
        return normalize_date_filter_bound(raw_value, end_of_day=False)

    @field_validator("date_to", mode="before")
    @classmethod
    def _normalize_date_to(cls, raw_value: Any) -> Any:
        return normalize_date_filter_bound(raw_value, end_of_day=True)

    @field_validator("date_from", "date_to", mode="after")
    @classmethod
    def _ensure_naive_datetime(cls, parsed_dt: Optional[datetime]) -> Optional[datetime]:
        if parsed_dt is not None and parsed_dt.tzinfo is not None:
            return parsed_dt.replace(tzinfo=None)
        return parsed_dt

class SearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[SearchFilter] = None
    limit: int = 50
    offset: int = 0

class SimilarSearchRequest(BaseModel):
    photo_id: str
    filters: Optional[SearchFilter] = None
    limit: int = 50
    offset: int = 0

class CritiqueRequest(BaseModel):
    photo_id: str
    engine: Optional[str] = "unipercept"

class CritiqueResponse(BaseModel):
    critique: str
    critique_en: Optional[str] = None
    overall_score: Optional[float] = None
    iaa_score: Optional[float] = None
    iqa_score: Optional[float] = None
    ista_score: Optional[float] = None
    critique_updated_at: Optional[str] = None
    engine_used: Optional[str] = "unipercept"
    status: Optional[str] = "completed"

class CritiqueCancelResponse(BaseModel):
    photo_id: str
    status: str = "cancelled"
    message: str

class CritiqueItemResponse(BaseModel):
    photo_id: str
    file_name: str
    file_path: str
    capture_date: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    f_number: Optional[float] = None
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    critique: str
    critique_en: Optional[str] = None
    overall_score: Optional[float] = None
    iaa_score: Optional[float] = None
    iqa_score: Optional[float] = None
    ista_score: Optional[float] = None
    critique_updated_at: Optional[str] = None

class CritiqueSummaryRequest(BaseModel):
    photo_ids: Optional[List[str]] = None

class CritiqueSummaryResponse(BaseModel):
    summary: str
    total_critiques_analyzed: int
    created_at: str

class CritiqueStatusResponse(BaseModel):
    photo_id: str
    step: int
    total_steps: int
    message: str
    progress: int
    status: str
    critique: Optional[str] = None
    critique_en: Optional[str] = None
    overall_score: Optional[float] = None
    iaa_score: Optional[float] = None
    iqa_score: Optional[float] = None
    ista_score: Optional[float] = None
    critique_updated_at: Optional[str] = None




