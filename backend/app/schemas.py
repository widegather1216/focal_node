from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    capture_date: Optional[str] = None

class AIAnalysisSchema(BaseModel):
    caption: Optional[str] = None
    tags: List[str] = []
    aesthetic_tags: List[str] = []
    is_user_edited: bool = False

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

class ExportResponse(BaseModel):
    status: str
    exported_count: int
    errors: Optional[List[str]] = None

class SearchFilter(BaseModel):
    is_favorite: Optional[bool] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    iso_min: Optional[int] = None
    iso_max: Optional[int] = None
    f_number_min: Optional[float] = None
    f_number_max: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

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

class CritiqueResponse(BaseModel):
    critique: str
