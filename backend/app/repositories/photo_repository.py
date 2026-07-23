from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
import models

class PhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, photo_id: str) -> Optional[models.Image]:
        return self.db.query(models.Image).filter(models.Image.id == photo_id).first()

    def get_by_path(self, file_path: str) -> Optional[models.Image]:
        return self.db.query(models.Image).filter(models.Image.file_path == file_path).first()

    def list_photos(self, limit: int = 50, offset: int = 0, parent_dir: Optional[str] = None) -> List[models.Image]:
        query = self.db.query(models.Image).outerjoin(models.ImageMetadata)
        if parent_dir:
            query = query.filter(models.Image.parent_dir == parent_dir)
        query = query.order_by(models.ImageMetadata.capture_date.desc().nullslast(), models.Image.id)
        return query.offset(offset).limit(limit).all()

    def search_by_text(self, query_str: str) -> List[str]:
        """
        Performs full-text search against captions and tags in AIAnalysis table.
        Returns list of matching image IDs.
        """
        text_search_q = self.db.query(models.AIAnalysis.image_id).filter(
            or_(
                models.AIAnalysis.tags.ilike(f"%{query_str}%"),
                models.AIAnalysis.caption.ilike(f"%{query_str}%")
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
        q = self.db.query(models.Image).outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
        
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
