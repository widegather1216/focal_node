from typing import Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
import models

class PhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, photo_id: str) -> Optional[models.Image]:
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id == photo_id).first()

    def get_by_ids(self, photo_ids: List[str]) -> List[models.Image]:
        if not photo_ids:
            return []
        if len(photo_ids) > 900:
            results = []
            for i in range(0, len(photo_ids), 900):
                chunk = photo_ids[i:i+900]
                rows = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id.in_(chunk)).all()
                results.extend(rows)
            return results
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id.in_(photo_ids)).all()

    def list_photos(self, limit: int = 50, offset: int = 0, parent_dir: Optional[str] = None) -> List[models.Image]:
        query = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).outerjoin(models.ImageMetadata)
        if parent_dir:
            query = query.filter(models.Image.parent_dir == parent_dir)
        query = query.order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
        return query.offset(offset).limit(limit).all()

    def search_by_text(self, query_str: str, limit: Optional[int] = 500) -> List[str]:
        """
        Performs full-text search against captions and tags in AIAnalysis table.
        Returns list of matching image IDs safely handling SQL LIKE wildcards.
        """
        escaped = query_str.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        text_search_q = self.db.query(models.AIAnalysis.image_id).filter(
            or_(
                models.AIAnalysis.tags.ilike(f"%{escaped}%", escape="\\"),
                models.AIAnalysis.caption.ilike(f"%{escaped}%", escape="\\")
            )
        )
        if limit and limit > 0:
            text_search_q = text_search_q.limit(limit)
        return [r[0] for r in text_search_q.all()]

    @staticmethod
    def _has_active_filters(filters: Any) -> bool:
        if not filters:
            return False
        filter_fields = (
            "is_favorite", "camera_model", "lens_model", "iso_min", "iso_max",
            "f_number_min", "f_number_max", "focal_length_min", "focal_length_max",
            "date_from", "date_to"
        )
        return any(getattr(filters, f, None) is not None for f in filter_fields)

    @staticmethod
    def _build_chroma_id_filter(query, photo_ids: List[str]):
        chunk_size = 900
        if len(photo_ids) > chunk_size:
            conditions = [
                models.Image.id.in_(photo_ids[i : i + chunk_size])
                for i in range(0, len(photo_ids), chunk_size)
            ]
            return query.filter(or_(*conditions))
        return query.filter(models.Image.id.in_(photo_ids))

    @staticmethod
    def _apply_exif_filters(query, filters: Any):
        if getattr(filters, "is_favorite", None) is not None:
            query = query.filter(models.Image.is_favorite == filters.is_favorite)
        if getattr(filters, "camera_model", None):
            query = query.filter(models.ImageMetadata.camera_model.ilike(f"%{filters.camera_model}%"))
        if getattr(filters, "lens_model", None):
            query = query.filter(models.ImageMetadata.lens_model.ilike(f"%{filters.lens_model}%"))

        range_mappings = [
            ("iso_min", models.ImageMetadata.iso, lambda col, val: col >= val),
            ("iso_max", models.ImageMetadata.iso, lambda col, val: col <= val),
            ("f_number_min", models.ImageMetadata.f_number, lambda col, val: col >= val),
            ("f_number_max", models.ImageMetadata.f_number, lambda col, val: col <= val),
            ("focal_length_min", models.ImageMetadata.focal_length, lambda col, val: col >= val),
            ("focal_length_max", models.ImageMetadata.focal_length, lambda col, val: col <= val),
            ("date_from", models.ImageMetadata.capture_date, lambda col, val: col >= val),
            ("date_to", models.ImageMetadata.capture_date, lambda col, val: col <= val),
        ]
        for field_name, col, op in range_mappings:
            val = getattr(filters, field_name, None)
            if val is not None:
                query = query.filter(op(col, val))
        return query

    def _paginate_by_chroma_order(
        self,
        query,
        photo_ids: List[str],
        offset: int,
        limit: int
    ) -> List[models.Image]:
        matching_id_rows = query.with_entities(models.Image.id).all()
        matching_ids = set(r[0] for r in matching_id_rows)
        sorted_pids = [pid for pid in photo_ids if pid in matching_ids]
        page_pids = sorted_pids[offset : offset + limit]
        if not page_pids:
            return []
        page_images = self.get_by_ids(page_pids)
        image_map = {img.id: img for img in page_images}
        return [image_map[pid] for pid in page_pids if pid in image_map]

    def filter_and_paginate(
        self,
        photo_ids_from_chroma: Optional[List[str]],
        filters,
        offset: int,
        limit: int
    ) -> List[models.Image]:
        """
        Applies EXIF filters and orders/paginates results.
        Optimized with fast-path pagination when no EXIF filters are present.
        """
        query = (
            self.db.query(models.Image)
            .options(joinedload(models.Image.metadata_rel))
            .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
        )
        has_active_filters = self._has_active_filters(filters)

        if photo_ids_from_chroma is not None:
            if not photo_ids_from_chroma:
                return []
            if not has_active_filters:
                page_pids = photo_ids_from_chroma[offset : offset + limit]
                if not page_pids:
                    return []
                images = query.filter(models.Image.id.in_(page_pids)).all()
                image_map = {img.id: img for img in images}
                return [image_map[pid] for pid in page_pids if pid in image_map]

            query = self._build_chroma_id_filter(query, photo_ids_from_chroma)

        if has_active_filters:
            query = self._apply_exif_filters(query, filters)

        if photo_ids_from_chroma is not None:
            return self._paginate_by_chroma_order(query, photo_ids_from_chroma, offset, limit)

        return query.order_by(models.ImageMetadata.capture_date.desc()).offset(offset).limit(limit).all()

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
        ai_record.tags = json.dumps(tags)
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
        query = (
            self.db.query(models.AIAnalysis, models.Image, models.ImageMetadata)
            .join(models.Image, models.AIAnalysis.image_id == models.Image.id)
            .outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
            .filter(models.AIAnalysis.critique.isnot(None))
            .filter(models.AIAnalysis.critique != "")
        )
        if photo_ids:
            query = self._build_chroma_id_filter(query, photo_ids)
        if sort_by == "overall_score":
            return query.order_by(
                models.AIAnalysis.overall_score.desc().nullslast(),
                models.AIAnalysis.critique_updated_at.desc().nullslast(),
            ).all()
        if sort_by == "iaa_score":
            return query.order_by(
                models.AIAnalysis.iaa_score.desc().nullslast(),
                models.AIAnalysis.critique_updated_at.desc().nullslast(),
            ).all()
        return query.order_by(models.AIAnalysis.critique_updated_at.desc().nullslast()).all()

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


