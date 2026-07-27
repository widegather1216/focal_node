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
            if getattr(f, 'iso_min', None) is not None:
                q = q.filter(models.ImageMetadata.iso >= f.iso_min)
            if getattr(f, 'iso_max', None) is not None:
                q = q.filter(models.ImageMetadata.iso <= f.iso_max)
            if getattr(f, 'f_number_min', None) is not None:
                q = q.filter(models.ImageMetadata.f_number >= f.f_number_min)
            if getattr(f, 'f_number_max', None) is not None:
                q = q.filter(models.ImageMetadata.f_number <= f.f_number_max)
            if getattr(f, 'focal_length_min', None) is not None:
                q = q.filter(models.ImageMetadata.focal_length >= f.focal_length_min)
            if getattr(f, 'focal_length_max', None) is not None:
                q = q.filter(models.ImageMetadata.focal_length <= f.focal_length_max)
            if getattr(f, 'date_from', None) is not None:
                q = q.filter(models.ImageMetadata.capture_date >= f.date_from)
            if getattr(f, 'date_to', None) is not None:
                q = q.filter(models.ImageMetadata.capture_date <= f.date_to)
                
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

    def get_gear_analytics(self) -> dict:
        """
        Aggregates photo metadata into camera, lens, focal length, and aperture stats.
        """
        total_photos = self.db.query(func.count(models.Image.id)).scalar() or 0

        # Cameras
        camera_q = self.db.query(
            models.ImageMetadata.camera_model, func.count(models.ImageMetadata.image_id)
        ).filter(
            models.ImageMetadata.camera_model.isnot(None),
            models.ImageMetadata.camera_model != ""
        ).group_by(
            models.ImageMetadata.camera_model
        ).order_by(func.count(models.ImageMetadata.image_id).desc()).limit(10).all()

        cameras = [{"name": row[0], "count": row[1]} for row in camera_q]

        # Lenses
        lens_q = self.db.query(
            models.ImageMetadata.lens_model, func.count(models.ImageMetadata.image_id)
        ).filter(
            models.ImageMetadata.lens_model.isnot(None),
            models.ImageMetadata.lens_model != ""
        ).group_by(
            models.ImageMetadata.lens_model
        ).order_by(func.count(models.ImageMetadata.image_id).desc()).limit(10).all()

        lenses = [{"name": row[0], "count": row[1]} for row in lens_q]

        # Focal lengths
        focal_q = self.db.query(
            models.ImageMetadata.focal_length, func.count(models.ImageMetadata.image_id)
        ).filter(
            models.ImageMetadata.focal_length.isnot(None)
        ).group_by(
            models.ImageMetadata.focal_length
        ).order_by(models.ImageMetadata.focal_length.asc()).limit(15).all()

        focal_lengths = [{"name": f"{int(row[0]) if row[0].is_integer() else row[0]}mm", "count": row[1]} for row in focal_q]

        # 35mm Equivalent Focal lengths
        focal35_q = self.db.query(
            models.ImageMetadata.focal_length_35mm, func.count(models.ImageMetadata.image_id)
        ).filter(
            models.ImageMetadata.focal_length_35mm.isnot(None)
        ).group_by(
            models.ImageMetadata.focal_length_35mm
        ).order_by(models.ImageMetadata.focal_length_35mm.asc()).limit(15).all()

        focal_lengths_35mm = [{"name": f"{int(row[0]) if row[0].is_integer() else row[0]}mm", "count": row[1]} for row in focal35_q]

        # Apertures
        aperture_q = self.db.query(
            models.ImageMetadata.f_number, func.count(models.ImageMetadata.image_id)
        ).filter(
            models.ImageMetadata.f_number.isnot(None)
        ).group_by(
            models.ImageMetadata.f_number
        ).order_by(models.ImageMetadata.f_number.asc()).limit(15).all()

        apertures = [{"name": f"f/{round(row[0], 2) if isinstance(row[0], (int, float)) else row[0]}", "count": row[1]} for row in aperture_q]

        return {
            "total_photos": total_photos,
            "cameras": cameras,
            "lenses": lenses,
            "focal_lengths": focal_lengths,
            "focal_lengths_35mm": focal_lengths_35mm,
            "apertures": apertures,
        }

