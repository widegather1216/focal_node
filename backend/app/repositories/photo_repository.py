from datetime import datetime
import math
from typing import Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
import models
from schemas import normalize_date_filter_bound
from utils.path import (
    is_path_within_folder,
    normalize_path_preserving_leaf_symlink,
    to_slash_bounded_prefix,
)

CHROMA_ID_CHUNK_SIZE = 900


def _escape_like_pattern(raw_pattern: str) -> str:
    """Escapes SQL LIKE/ILIKE wildcards (\\, %, _) for literal substring matching."""
    return raw_pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _normalize_text_filter(raw_value: Any) -> Optional[str]:
    """Strips whitespace from optional text filters, returning None for blank strings."""
    if not isinstance(raw_value, str):
        return None
    stripped = raw_value.strip()
    return stripped or None


def _normalize_naive_datetime(raw_dt: Any) -> Optional[datetime]:
    """Normalizes datetime values to naive UTC-less instances for safe sorting."""
    if not isinstance(raw_dt, datetime):
        return None
    return raw_dt.replace(tzinfo=None) if raw_dt.tzinfo is not None else raw_dt


def _sort_desc_nulls_last(rows: list[tuple], key_fn) -> list[tuple]:
    """Sorts rows descending by key_fn while keeping None keys at the end."""
    present_rows = [row for row in rows if key_fn(row) is not None]
    missing_rows = [row for row in rows if key_fn(row) is None]
    present_rows.sort(key=key_fn, reverse=True)
    return present_rows + missing_rows


def _sort_critique_rows(rows: list[tuple], sort_by: str) -> list[tuple]:
    """Applies SQLite-equivalent DESC NULLS LAST ordering across chunked critique rows."""
    sorted_rows = _sort_desc_nulls_last(
        rows,
        lambda row: _normalize_naive_datetime(row[0].critique_updated_at),
    )
    if sort_by not in ("overall_score", "iaa_score"):
        return sorted_rows

    score_attr = "overall_score" if sort_by == "overall_score" else "iaa_score"

    def extract_finite_score(row: tuple) -> Optional[float]:
        score_value = getattr(row[0], score_attr, None)
        if score_value is None or not math.isfinite(score_value):
            return None
        return float(score_value)

    return _sort_desc_nulls_last(sorted_rows, extract_finite_score)


def _resolve_date_filter_bound(raw_value: Any, *, end_of_day: bool) -> Any:
    """Normalizes date bounds for direct repository callers bypassing SearchFilter."""
    normalized = normalize_date_filter_bound(raw_value, end_of_day=end_of_day)
    if not isinstance(normalized, str):
        return normalized
    stripped = normalized.strip()
    iso_text = f"{stripped[:-1]}+00:00" if stripped.endswith(("Z", "z")) else stripped
    parsed_dt = datetime.fromisoformat(iso_text)
    return parsed_dt.replace(tzinfo=None) if parsed_dt.tzinfo is not None else parsed_dt

class PhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, photo_id: str) -> Optional[models.Image]:
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id == photo_id).first()

    def get_by_ids(self, photo_ids: List[str]) -> List[models.Image]:
        if not photo_ids:
            return []
        unique_ids = list(dict.fromkeys(photo_ids))
        if len(unique_ids) > CHROMA_ID_CHUNK_SIZE:
            results = []
            for start_idx in range(0, len(unique_ids), CHROMA_ID_CHUNK_SIZE):
                chunk = unique_ids[start_idx : start_idx + CHROMA_ID_CHUNK_SIZE]
                rows = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id.in_(chunk)).all()
                results.extend(rows)
            return results
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id.in_(unique_ids)).all()

    @staticmethod
    def _filter_matching_photo_ids(
        ordered_rows: list[tuple[str, str]],
        target_root: str,
        bounded_prefix: str,
        dir_match_cache: Optional[dict[str, bool]] = None,
    ) -> List[str]:
        """Filters ordered (id, parent_dir) rows using a per-directory normalization cache."""
        match_cache = dir_match_cache if dir_match_cache is not None else {}
        matching_ids: List[str] = []
        for photo_id, row_parent_dir in ordered_rows:
            cache_key = row_parent_dir or ""
            is_match = match_cache.get(cache_key)
            if is_match is None:
                is_match = is_path_within_folder(cache_key, target_root, bounded_prefix)
                match_cache[cache_key] = is_match
            if is_match:
                matching_ids.append(photo_id)
        return matching_ids

    def _fetch_ordered_images_by_ids(self, page_ids: List[str]) -> List[models.Image]:
        """Loads Image + metadata rows for page_ids while preserving page_ids order."""
        page_images = self.get_by_ids(page_ids)
        images_by_id = {img.id: img for img in page_images}
        return [images_by_id[photo_id] for photo_id in page_ids if photo_id in images_by_id]

    @staticmethod
    def _resolve_folder_bounds(parent_dir: Optional[str]) -> Optional[tuple[str, str]]:
        """Returns (normalized_root, slash_bounded_prefix) for valid folder scopes."""
        if not parent_dir:
            return None
        target_root = normalize_path_preserving_leaf_symlink(parent_dir)
        if not target_root:
            return None
        return target_root, to_slash_bounded_prefix(target_root)

    def _paginate_ordered_folder_query(
        self,
        ordered_query,
        folder_bounds: tuple[str, str],
        offset: int,
        limit: int,
    ) -> List[models.Image]:
        """Filters an ordered query by folder bounds and loads only the requested slice."""
        target_root, bounded_prefix = folder_bounds
        ordered_rows = ordered_query.with_entities(models.Image.id, models.Image.parent_dir).all()
        matching_ids = self._filter_matching_photo_ids(ordered_rows, target_root, bounded_prefix)
        page_ids = matching_ids[offset : offset + limit]
        if not page_ids:
            return []
        return self._fetch_ordered_images_by_ids(page_ids)

    def _list_photos_in_folder(self, parent_dir: str, limit: int, offset: int) -> List[models.Image]:
        """Lists photos inside parent_dir or its subdirectories with NFC/case/symlink parity."""
        folder_bounds = self._resolve_folder_bounds(parent_dir)
        if folder_bounds is None:
            return []

        ordered_query = (
            self.db.query(models.Image)
            .outerjoin(models.ImageMetadata)
            .order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
        )
        return self._paginate_ordered_folder_query(ordered_query, folder_bounds, offset, limit)

    def list_photos(self, limit: int = 50, offset: int = 0, parent_dir: Optional[str] = None) -> List[models.Image]:
        """Lists photos ordered by capture_date DESC NULLS LAST, id ASC with optional folder scoping."""
        if limit <= 0:
            return []
        safe_offset = max(0, offset)
        if parent_dir:
            return self._list_photos_in_folder(parent_dir, limit=limit, offset=safe_offset)

        query = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).outerjoin(models.ImageMetadata)
        query = query.order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
        return query.offset(safe_offset).limit(limit).all()

    def search_by_text(self, query_str: str, limit: Optional[int] = 500) -> List[str]:
        """
        Performs full-text search against captions and tags in AIAnalysis table.
        Returns list of matching image IDs safely handling SQL LIKE wildcards.
        """
        escaped = _escape_like_pattern(query_str)
        text_search_q = self.db.query(models.AIAnalysis.image_id).filter(
            or_(
                models.AIAnalysis.tags.ilike(f"%{escaped}%", escape="\\"),
                models.AIAnalysis.caption.ilike(f"%{escaped}%", escape="\\")
            )
        )
        if limit and limit > 0:
            text_search_q = text_search_q.limit(limit)
        return [row[0] for row in text_search_q.all()]

    @staticmethod
    def _has_active_filters(filters: Any) -> bool:
        if not filters:
            return False
        text_fields = ("camera_model", "lens_model")
        if any(_normalize_text_filter(getattr(filters, field_name, None)) is not None for field_name in text_fields):
            return True
        scalar_fields = (
            "is_favorite", "iso_min", "iso_max",
            "f_number_min", "f_number_max", "focal_length_min", "focal_length_max",
            "date_from", "date_to",
        )
        return any(getattr(filters, field_name, None) is not None for field_name in scalar_fields)

    @staticmethod
    def _apply_exif_filters(query, filters: Any):
        if getattr(filters, "is_favorite", None) is not None:
            query = query.filter(models.Image.is_favorite == filters.is_favorite)
        camera_model = _normalize_text_filter(getattr(filters, "camera_model", None))
        if camera_model is not None:
            escaped_camera = _escape_like_pattern(camera_model)
            query = query.filter(models.ImageMetadata.camera_model.ilike(f"%{escaped_camera}%", escape="\\"))
        lens_model = _normalize_text_filter(getattr(filters, "lens_model", None))
        if lens_model is not None:
            escaped_lens = _escape_like_pattern(lens_model)
            query = query.filter(models.ImageMetadata.lens_model.ilike(f"%{escaped_lens}%", escape="\\"))

        range_mappings = [
            ("iso_min", models.ImageMetadata.iso, lambda col, val: col >= val),
            ("iso_max", models.ImageMetadata.iso, lambda col, val: col <= val),
            ("f_number_min", models.ImageMetadata.f_number, lambda col, val: col >= val),
            ("f_number_max", models.ImageMetadata.f_number, lambda col, val: col <= val),
            ("focal_length_min", models.ImageMetadata.focal_length, lambda col, val: col >= val),
            ("focal_length_max", models.ImageMetadata.focal_length, lambda col, val: col <= val),
            ("date_from", models.ImageMetadata.capture_date, lambda col, val: col >= _resolve_date_filter_bound(val, end_of_day=False)),
            ("date_to", models.ImageMetadata.capture_date, lambda col, val: col <= _resolve_date_filter_bound(val, end_of_day=True)),
        ]
        for field_name, col, op in range_mappings:
            val = getattr(filters, field_name, None)
            if val is not None:
                query = query.filter(op(col, val))
        return query

    def _build_filtered_image_query(self, filters: Any, has_active_filters: bool):
        """Creates an Image query joined with ImageMetadata and optional EXIF filters."""
        query = self.db.query(models.Image).outerjoin(
            models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id
        )
        if has_active_filters:
            return self._apply_exif_filters(query, filters)
        return query

    def _query_chunk_matching_ids(
        self,
        base_query,
        id_chunk: List[str],
        folder_bounds: Optional[tuple[str, str]],
        dir_match_cache: dict[str, bool],
    ) -> List[str]:
        """Evaluates EXIF and optional folder bounds for a single <=900 ID chunk."""
        chunk_query = base_query.filter(models.Image.id.in_(id_chunk))
        if folder_bounds is None:
            return [row[0] for row in chunk_query.with_entities(models.Image.id).all()]
        target_root, bounded_prefix = folder_bounds
        candidate_rows = chunk_query.with_entities(models.Image.id, models.Image.parent_dir).all()
        return self._filter_matching_photo_ids(
            candidate_rows, target_root, bounded_prefix, dir_match_cache
        )

    def _collect_matching_candidate_ids(
        self,
        base_query,
        unique_photo_ids: List[str],
        folder_bounds: Optional[tuple[str, str]],
    ) -> set[str]:
        """Collects matching photo IDs across 900-item SQLite IN chunks to avoid variable limits."""
        matching_ids: set[str] = set()
        dir_match_cache: dict[str, bool] = {}
        for start_idx in range(0, len(unique_photo_ids), CHROMA_ID_CHUNK_SIZE):
            id_chunk = unique_photo_ids[start_idx : start_idx + CHROMA_ID_CHUNK_SIZE]
            chunk_matches = self._query_chunk_matching_ids(
                base_query, id_chunk, folder_bounds, dir_match_cache
            )
            matching_ids.update(chunk_matches)
        return matching_ids

    def _filter_candidate_ids(
        self,
        photo_ids: List[str],
        filters: Any,
        has_active_filters: bool,
        folder_bounds: Optional[tuple[str, str]],
        offset: int,
        limit: int,
    ) -> List[models.Image]:
        """Applies optional EXIF/folder scoping over candidate IDs, fast-pathing when unscoped."""
        if not photo_ids or limit <= 0:
            return []
        safe_offset = max(0, offset)
        unique_photo_ids = list(dict.fromkeys(photo_ids))
        if not has_active_filters and folder_bounds is None:
            page_pids = unique_photo_ids[safe_offset : safe_offset + limit]
            return self._fetch_ordered_images_by_ids(page_pids) if page_pids else []

        base_query = self._build_filtered_image_query(filters, has_active_filters)
        matching_ids = self._collect_matching_candidate_ids(
            base_query, unique_photo_ids, folder_bounds
        )
        ordered_pids = [pid for pid in unique_photo_ids if pid in matching_ids]
        page_pids = ordered_pids[safe_offset : safe_offset + limit]
        return self._fetch_ordered_images_by_ids(page_pids) if page_pids else []

    def filter_and_paginate(
        self,
        photo_ids_from_chroma: Optional[List[str]],
        filters,
        offset: int,
        limit: int,
        parent_dir: Optional[str] = None,
    ) -> List[models.Image]:
        """Applies EXIF/folder filters and orders/paginates results."""
        if limit <= 0:
            return []
        safe_offset = max(0, offset)
        folder_bounds = self._resolve_folder_bounds(parent_dir)
        if parent_dir and folder_bounds is None:
            return []

        has_active_filters = self._has_active_filters(filters)
        if photo_ids_from_chroma is not None:
            return self._filter_candidate_ids(
                photo_ids_from_chroma, filters, has_active_filters, folder_bounds, safe_offset, limit
            )

        base_query = self._build_filtered_image_query(filters, has_active_filters)
        if folder_bounds is not None:
            ordered_query = base_query.order_by(
                models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id
            )
            return self._paginate_ordered_folder_query(ordered_query, folder_bounds, safe_offset, limit)

        return (
            base_query.options(joinedload(models.Image.metadata_rel))
            .order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
            .offset(safe_offset)
            .limit(limit)
            .all()
        )

    def toggle_favorite(self, photo_id: str) -> Optional[models.Image]:
        db_image = self.get_by_id(photo_id)
        if not db_image:
            return None
        db_image.is_favorite = not db_image.is_favorite
        self.db.commit()
        self.db.refresh(db_image)
        return db_image

    def get_ai_analysis(self, photo_id: str) -> Optional[models.AIAnalysis]:
        """
        Fetches the AIAnalysis record for a given photo_id.
        """
        return self.db.query(models.AIAnalysis).filter(models.AIAnalysis.image_id == photo_id).first()

    def update_caption_and_tags(self, photo_id: str, caption: str, tags: List[str]) -> models.AIAnalysis:
        """
        Updates the user-edited caption and tags for a photo, creating AIAnalysis if missing.
        """
        import json
        ai_record = self.get_ai_analysis(photo_id)
        if not ai_record:
            ai_record = models.AIAnalysis(image_id=photo_id)
            self.db.add(ai_record)

        ai_record.caption = caption
        ai_record.tags = json.dumps(tags, ensure_ascii=False)
        ai_record.is_user_edited = True
        self.db.commit()
        self.db.refresh(ai_record)
        return ai_record

    def upsert_critique(
        self,
        photo_id: str,
        critique_text: str,
        updated_at: Any,
        critique_en: Optional[str] = None,
        overall_score: Optional[float] = None,
        iaa_score: Optional[float] = None,
        iqa_score: Optional[float] = None,
        ista_score: Optional[float] = None,
    ) -> models.AIAnalysis:
        """
        Inserts or updates critique text, raw English anchor, and normalized 4-dimension scores.
        """
        ai_record = self.get_ai_analysis(photo_id)
        if not ai_record:
            ai_record = models.AIAnalysis(
                image_id=photo_id,
                critique=critique_text,
                critique_en=critique_en,
                overall_score=overall_score,
                iaa_score=iaa_score,
                iqa_score=iqa_score,
                ista_score=ista_score,
                critique_updated_at=updated_at,
            )
            self.db.add(ai_record)
        else:
            ai_record.critique = critique_text
            ai_record.critique_en = critique_en
            ai_record.overall_score = overall_score
            ai_record.iaa_score = iaa_score
            ai_record.iqa_score = iqa_score
            ai_record.ista_score = ista_score
            ai_record.critique_updated_at = updated_at
        self.db.commit()
        return ai_record

    @staticmethod
    def _apply_critique_sql_order(query, sort_by: str):
        if sort_by == "overall_score":
            return query.order_by(
                models.AIAnalysis.overall_score.desc().nullslast(),
                models.AIAnalysis.critique_updated_at.desc().nullslast(),
            )
        if sort_by == "iaa_score":
            return query.order_by(
                models.AIAnalysis.iaa_score.desc().nullslast(),
                models.AIAnalysis.critique_updated_at.desc().nullslast(),
            )
        return query.order_by(models.AIAnalysis.critique_updated_at.desc().nullslast())

    def _fetch_critique_rows_chunked(self, base_query, unique_photo_ids: List[str], sort_by: str) -> List[tuple]:
        aggregated_rows: list[tuple] = []
        for start_idx in range(0, len(unique_photo_ids), CHROMA_ID_CHUNK_SIZE):
            id_chunk = unique_photo_ids[start_idx : start_idx + CHROMA_ID_CHUNK_SIZE]
            aggregated_rows.extend(base_query.filter(models.Image.id.in_(id_chunk)).all())
        return _sort_critique_rows(aggregated_rows, sort_by)

    def list_critiques(
        self,
        sort_by: str = "recent",
        photo_ids: Optional[List[str]] = None
    ) -> List[tuple]:
        """
        Returns list of (AIAnalysis, Image, ImageMetadata) tuples with non-empty critiques.
        Supports optional photo_ids filtering (with 900-chunking) and sorting by:
        - 'recent': ordered by critique_updated_at DESC
        - 'overall_score': ordered by overall_score DESC, then critique_updated_at DESC
        - 'iaa_score': ordered by iaa_score DESC, then critique_updated_at DESC
        """
        base_query = (
            self.db.query(models.AIAnalysis, models.Image, models.ImageMetadata)
            .join(models.Image, models.AIAnalysis.image_id == models.Image.id)
            .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
            .filter(models.AIAnalysis.critique.isnot(None))
            .filter(models.AIAnalysis.critique != "")
        )
        if photo_ids:
            unique_photo_ids = list(dict.fromkeys(photo_ids))
            if len(unique_photo_ids) > CHROMA_ID_CHUNK_SIZE:
                return self._fetch_critique_rows_chunked(base_query, unique_photo_ids, sort_by)
            base_query = base_query.filter(models.Image.id.in_(unique_photo_ids))

        return self._apply_critique_sql_order(base_query, sort_by).all()

    def delete_critique(self, photo_id: str) -> bool:
        """
        Clears stored critique and normalized score data for a photo.
        """
        ai = self.get_ai_analysis(photo_id)
        if not ai:
            return False
        ai.critique = None
        ai.critique_en = None
        ai.overall_score = None
        ai.iaa_score = None
        ai.iqa_score = None
        ai.ista_score = None
        ai.critique_updated_at = None
        self.db.commit()
        return True

    def _aggregate_field_stats(self, column, limit: int = 10, asc: bool = False, format_fn=None, filter_empty_str: bool = False) -> list[dict]:
        q = self.db.query(column, func.count(models.ImageMetadata.image_id)).filter(column.isnot(None))
        if filter_empty_str:
            q = q.filter(column != "")
        order_col = column.asc() if asc else func.count(models.ImageMetadata.image_id).desc()
        rows = q.group_by(column).order_by(order_col).limit(limit).all()
        
        result = []
        for val, count in rows:
            name = format_fn(val) if format_fn else str(val)
            result.append({"name": name, "count": count})
        return result

    def get_gear_analytics(self) -> dict:
        """
        Aggregates photo metadata into camera, lens, focal length, and aperture stats.
        """
        total_photos = self.db.query(func.count(models.Image.id)).scalar() or 0
        fmt_mm = lambda v: f"{int(v) if isinstance(v, (int, float)) and float(v).is_integer() else v}mm"
        fmt_f = lambda v: f"f/{round(v, 2) if isinstance(v, (int, float)) else v}"

        return {
            "total_photos": total_photos,
            "cameras": self._aggregate_field_stats(models.ImageMetadata.camera_model, limit=10, filter_empty_str=True),
            "lenses": self._aggregate_field_stats(models.ImageMetadata.lens_model, limit=10, filter_empty_str=True),
            "focal_lengths": self._aggregate_field_stats(models.ImageMetadata.focal_length, limit=15, asc=True, format_fn=fmt_mm),
            "focal_lengths_35mm": self._aggregate_field_stats(models.ImageMetadata.focal_length_35mm, limit=15, asc=True, format_fn=fmt_mm),
            "apertures": self._aggregate_field_stats(models.ImageMetadata.f_number, limit=15, asc=True, format_fn=fmt_f),
        }

    def list_folders(self) -> List[models.IndexedFolder]:
        """
        Returns all registered indexed folders.
        """
        return self.db.query(models.IndexedFolder).all()

    def get_folder_by_path(self, path: str) -> Optional[models.IndexedFolder]:
        """
        Finds an indexed folder by its exact normalized path.
        """
        return self.db.query(models.IndexedFolder).filter(models.IndexedFolder.path == path).first()

    def add_folder(self, path: str) -> models.IndexedFolder:
        """
        Adds a new indexed folder to the session (caller responsible for commit).
        """
        new_folder = models.IndexedFolder(path=path)
        self.db.add(new_folder)
        return new_folder


