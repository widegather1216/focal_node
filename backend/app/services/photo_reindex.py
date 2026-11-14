"""
Single Photo Reindex Service Module

Handles in-place EXIF, SigLIP embedding, and Gemma caption re-inference
with compensating ChromaDB/SQLite transaction guarantees.
"""

import asyncio
import json
from typing import Any, Callable, Optional, Tuple

from sqlalchemy.orm import Session

from database import SessionLocal
from models import AIAnalysis as DBAIAnalysis, Image as DBImage, ImageMetadata as DBImageMetadata
from repositories.vector_repository import VectorRepository
from services.photo import _prepare_chroma_metadata

_default_vector_repo = VectorRepository()

_METADATA_FIELDS = (
    "width", "height", "color_space", "camera_model", "lens_model",
    "f_number", "focal_length", "focal_length_35mm", "crop_factor",
    "sensor_format", "shutter_speed", "iso", "capture_date",
)


def validate_photo_for_reindex(
    photo_id: str,
    session_factory: Callable[[], Session] = SessionLocal,
) -> str:
    """Verifies photo exists in DB and on disk before re-indexing."""
    db_session = session_factory()
    try:
        db_img = db_session.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
            raise ValueError(f"Photo ID {photo_id} not found in database.")
        file_path = db_img.file_path
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} no longer exists.")
        return file_path
    finally:
        db_session.close()


def _update_image_metadata_orm(db_session: Session, photo_id: str, metadata: dict) -> None:
    """Updates or creates ImageMetadata ORM row for a photo."""
    db_meta = db_session.query(DBImageMetadata).filter(DBImageMetadata.image_id == photo_id).first()
    if not db_meta:
        db_meta = DBImageMetadata(image_id=photo_id)
        db_session.add(db_meta)
    for field_name in _METADATA_FIELDS:
        setattr(db_meta, field_name, metadata.get(field_name))


def _update_ai_analysis_orm(db_session: Session, photo_id: str, ai_result: dict) -> None:
    """Updates or creates AIAnalysis ORM row for a photo."""
    db_ai = db_session.query(DBAIAnalysis).filter(DBAIAnalysis.image_id == photo_id).first()
    if not db_ai:
        db_ai = DBAIAnalysis(image_id=photo_id)
        db_session.add(db_ai)
    db_ai.caption = ai_result.get("caption", "")
    db_ai.tags = json.dumps(ai_result.get("tags", []))
    db_ai.aesthetic_tags = json.dumps(ai_result.get("aesthetic_tags", []))
    db_ai.is_user_edited = False


def update_orm_photo_models(
    db_session: Session,
    photo_id: str,
    metadata: dict,
    ai_result: dict,
) -> None:
    """Updates ImageMetadata and AIAnalysis ORM entities with newly extracted values."""
    _update_image_metadata_orm(db_session, photo_id, metadata)
    _update_ai_analysis_orm(db_session, photo_id, ai_result)


def rollback_chroma_embedding(
    photo_id: str,
    old_embedding: Optional[list[float]],
    chroma_meta: dict,
    err: Exception,
    vector_repository: Optional[VectorRepository] = None,
) -> None:
    """Restores previous ChromaDB embedding or deletes it if previously absent."""
    active_vector_repo = vector_repository or _default_vector_repo
    try:
        if old_embedding:
            active_vector_repo.upsert(ids=[photo_id], embeddings=[old_embedding], metadatas=[chroma_meta])
        else:
            active_vector_repo.delete([photo_id])
        print(f"[CompensatingTx] Successfully reverted ChromaDB after SQLite failure: {err}", flush=True)
    except Exception as comp_err:
        print(f"[CompensatingTx] Failed to execute compensating ChromaDB rollback: {comp_err}", flush=True)


def commit_reindex_with_compensation(
    photo_id: str,
    metadata: dict,
    embedding: list[float],
    old_embedding: Optional[list[float]],
    db_session: Session,
    db_img: DBImage,
    vector_repository: Optional[VectorRepository] = None,
) -> dict:
    """Upserts ChromaDB embedding, commits SQLite, and rolls back ChromaDB if commit fails."""
    active_vector_repo = vector_repository or _default_vector_repo
    chroma_meta = _prepare_chroma_metadata(metadata)
    active_vector_repo.upsert(ids=[photo_id], embeddings=[embedding], metadatas=[chroma_meta])
    try:
        db_session.commit()
        db_session.refresh(db_img)
        return db_img.to_detail_dict()
    except Exception as commit_err:
        db_session.rollback()
        rollback_chroma_embedding(
            photo_id, old_embedding, chroma_meta, commit_err, vector_repository=active_vector_repo
        )
        raise commit_err


def _persist_reindex_sync(
    photo_id: str,
    metadata: dict,
    embedding: list[float],
    ai_result: dict,
    old_embedding: Optional[list[float]],
    session_factory: Callable[[], Session],
    vector_repository: VectorRepository,
) -> dict:
    """Persists re-indexed metadata and embedding in a worker-thread DB session."""
    db_session = session_factory()
    try:
        db_img = db_session.query(DBImage).filter(DBImage.id == photo_id).first()
        if not db_img:
            raise ValueError(f"Photo ID {photo_id} was deleted during re-indexing.")
        update_orm_photo_models(db_session, photo_id, metadata, ai_result)
        return commit_reindex_with_compensation(
            photo_id, metadata, embedding, old_embedding, db_session, db_img, vector_repository=vector_repository
        )
    finally:
        db_session.close()


async def reindex_single_photo_inplace(
    photo_id: str,
    ai_pipeline_fn: Callable[[str], Tuple[dict, list[float], dict]],
    session_factory: Callable[[], Session] = SessionLocal,
    vector_repository: Optional[VectorRepository] = None,
) -> dict:
    """Re-runs metadata, embedding, and caption inference for an existing photo in-place."""
    active_vector_repo = vector_repository or _default_vector_repo
    file_path = await asyncio.to_thread(validate_photo_for_reindex, photo_id, session_factory)
    metadata, embedding, ai_result = await asyncio.to_thread(ai_pipeline_fn, file_path)
    old_embedding = await asyncio.to_thread(active_vector_repo.get_embedding_by_id, photo_id)
    return await asyncio.to_thread(
        _persist_reindex_sync,
        photo_id,
        metadata,
        embedding,
        ai_result,
        old_embedding,
        session_factory,
        active_vector_repo,
    )
