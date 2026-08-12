from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
import models

class PhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, photo_id: str) -> Optional[models.Image]:
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.id == photo_id).first()

    def get_by_path(self, file_path: str) -> Optional[models.Image]:
        return self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).filter(models.Image.file_path == file_path).first()

    def list_photos(self, limit: int = 50, offset: int = 0, parent_dir: Optional[str] = None) -> List[models.Image]:
        query = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).outerjoin(models.ImageMetadata)
        if parent_dir:
            query = query.filter(models.Image.parent_dir == parent_dir)
        query = query.order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
        return query.offset(offset).limit(limit).all()

    def search_by_text(self, query_str: str) -> List[str]:
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
        return [r[0] for r in text_search_q.all()]

    def filter_and_paginate(
        self,
        photo_ids_from_chroma: Optional[List[str]],
        filters,
        offset: int,
        limit: int
    ) -> List[models.Image]:
        """
        Applies EXIF filters and orders/paginates results.
        """
        q = self.db.query(models.Image).options(joinedload(models.Image.metadata_rel)).outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
        
        if photo_ids_from_chroma is not None:
            if not photo_ids_from_chroma:
                return []
            
            chunk_size = 900
            if len(photo_ids_from_chroma) > chunk_size:
                conditions = [models.Image.id.in_(photo_ids_from_chroma[i:i + chunk_size]) 
                              for i in range(0, len(photo_ids_from_chroma), chunk_size)]
                q = q.filter(or_(*conditions))
            else:
                q = q.filter(models.Image.id.in_(photo_ids_from_chroma))
                
        # Apply EXIF filters
        if filters:
            f = filters
            if getattr(f, 'is_favorite', None) is not None:
                q = q.filter(models.Image.is_favorite == f.is_favorite)
            if getattr(f, 'camera_model', None):
                q = q.filter(models.ImageMetadata.camera_model.ilike(f"%{f.camera_model}%"))
            if getattr(f, 'lens_model', None):
                q = q.filter(models.ImageMetadata.lens_model.ilike(f"%{f.lens_model}%"))
                
            range_filters = [
                (getattr(f, 'iso_min', None), models.ImageMetadata.iso >= getattr(f, 'iso_min', None)),
                (getattr(f, 'iso_max', None), models.ImageMetadata.iso <= getattr(f, 'iso_max', None)),
                (getattr(f, 'f_number_min', None), models.ImageMetadata.f_number >= getattr(f, 'f_number_min', None)),
                (getattr(f, 'f_number_max', None), models.ImageMetadata.f_number <= getattr(f, 'f_number_max', None)),
                (getattr(f, 'focal_length_min', None), models.ImageMetadata.focal_length >= getattr(f, 'focal_length_min', None)),
                (getattr(f, 'focal_length_max', None), models.ImageMetadata.focal_length <= getattr(f, 'focal_length_max', None)),
                (getattr(f, 'date_from', None), models.ImageMetadata.capture_date >= getattr(f, 'date_from', None)),
                (getattr(f, 'date_to', None), models.ImageMetadata.capture_date <= getattr(f, 'date_to', None)),
            ]
            for val, cond in range_filters:
                if val is not None:
                    q = q.filter(cond)
                
        # Order and paginate
        if photo_ids_from_chroma is not None:
            images = q.all()
            image_map = {img.id: img for img in images}
            sorted_images = []
            for pid in photo_ids_from_chroma:
                if pid in image_map:
                    sorted_images.append(image_map[pid])
            return sorted_images[offset : offset + limit]
        else:
            return q.order_by(models.ImageMetadata.capture_date.desc()).offset(offset).limit(limit).all()

    def toggle_favorite(self, photo_id: str) -> Optional[models.Image]:
        db_image = self.get_by_id(photo_id)
        if not db_image:
            return None
        db_image.is_favorite = not db_image.is_favorite
        self.db.commit()
        self.db.refresh(db_image)
        return db_image

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

