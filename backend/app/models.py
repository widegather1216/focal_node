import datetime
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(String(64), primary_key=True)  # SHA-256 hash
    parent_dir = Column(String(1024), index=True, nullable=False)
    file_path = Column(String(1024), unique=True, nullable=False)
    file_name = Column(String(256), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_mtime = Column(Float, nullable=False)
    mime_type = Column(String(50), nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    metadata_rel = relationship("ImageMetadata", back_populates="image", uselist=False, cascade="all, delete-orphan")
    ai_analysis_rel = relationship("AIAnalysis", back_populates="image", uselist=False, cascade="all, delete-orphan")

    def to_list_response_dict(self):
        cap_date = None
        cam_model = None
        w = None
        h = None
        if self.metadata_rel:
            cap_date = self.metadata_rel.capture_date.isoformat() if self.metadata_rel.capture_date else None
            cam_model = self.metadata_rel.camera_model
            w = self.metadata_rel.width
            h = self.metadata_rel.height
            
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "is_favorite": self.is_favorite,
            "capture_date": cap_date,
            "camera_model": cam_model,
            "width": w,
            "height": h
        }

    def to_detail_dict(self):
        meta = self.metadata_rel
        ai = self.ai_analysis_rel
        
        meta_data = {
            "width": meta.width if meta else None,
            "height": meta.height if meta else None,
            "color_space": meta.color_space if meta else "sRGB",
            "camera_model": meta.camera_model if meta else None,
            "lens_model": meta.lens_model if meta else None,
            "f_number": meta.f_number if meta else None,
            "focal_length": meta.focal_length if meta else None,
            "shutter_speed": meta.shutter_speed if meta else None,
            "iso": meta.iso if meta else None,
            "capture_date": meta.capture_date.isoformat() if meta and meta.capture_date else None,
        }
        
        tags_list = []
        if ai and ai.tags:
            try:
                tags_list = json.loads(ai.tags)
            except json.JSONDecodeError:
                pass
                
        aesthetic_tags_list = []
        if ai and ai.aesthetic_tags:
            try:
                aesthetic_tags_list = json.loads(ai.aesthetic_tags)
            except json.JSONDecodeError:
                pass
                
        ai_data = {
            "caption": ai.caption if ai else None,
            "tags": tags_list,
            "aesthetic_tags": aesthetic_tags_list,
            "is_user_edited": ai.is_user_edited if ai else False
        }
        
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_favorite": self.is_favorite,
            "metadata": meta_data,
            "ai_analysis": ai_data
        }


class ImageMetadata(Base):
    __tablename__ = "image_metadata"

    image_id = Column(String(64), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    color_space = Column(String(30), nullable=True)
    camera_model = Column(String(100), nullable=True)
    lens_model = Column(String(100), nullable=True)
    f_number = Column(Float, nullable=True)
    focal_length = Column(Float, nullable=True)
    shutter_speed = Column(String(30), nullable=True)
    iso = Column(Integer, nullable=True)
    capture_date = Column(DateTime, index=True, nullable=True)

    # Relationships
    image = relationship("Image", back_populates="metadata_rel")


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    image_id = Column(String(64), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)
    caption = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # Stored as JSON string (e.g. '["tag1", "tag2"]')
    aesthetic_tags = Column(String, nullable=True)  # Stored as JSON string for professional tags
    is_user_edited = Column(Boolean, default=False, nullable=False)

    # Relationships
    image = relationship("Image", back_populates="ai_analysis_rel")


class IndexedFolder(Base):
    __tablename__ = "indexed_folders"

    path = Column(String(1024), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
