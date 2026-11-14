import json
import os
import shutil
import stat
import asyncio
import logging
import threading
import weakref
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

import database
import models
import services.photo as photo_service
from database import get_db
import schemas
from repositories.photo_repository import PhotoRepository
from utils.image import is_raw_image
from services.indexing_service import reindex_single_photo_inplace

logger = logging.getLogger("focal_node.photos_api")

MAX_CONCURRENT_DECODES = 3
_decode_semaphores: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()
_decode_semaphore_lock = threading.Lock()


def get_decode_semaphore() -> asyncio.Semaphore:
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.Semaphore(MAX_CONCURRENT_DECODES)

    with _decode_semaphore_lock:
        semaphore = _decode_semaphores.get(current_loop)
        if semaphore is None:
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_DECODES)
            _decode_semaphores[current_loop] = semaphore
        return semaphore


def _fetch_photo_media_record_sync(photo_id: str) -> Optional[tuple[str, str, str]]:
    """Fetches plain (id, file_path, mime_type) inside a short-lived worker-thread session."""
    with database.SessionLocal() as db:
        db_image = PhotoRepository(db).get_by_id(photo_id)
        if not db_image:
            return None
        return db_image.id, db_image.file_path, db_image.mime_type


def _read_cached_thumbnail_sync(cache_path: str, photo_id: str) -> Optional[bytes]:
    try:
        if not os.path.exists(cache_path) or os.path.getsize(cache_path) <= 0:
            return None
        with open(cache_path, "rb") as cache_file:
            thumb_bytes = cache_file.read()
            return thumb_bytes or None
    except (FileNotFoundError, OSError) as cache_err:
        logger.debug("Thumbnail cache read failed for %s: %s, falling back to generation", photo_id, cache_err)
        return None


def _stat_regular_file_sync(file_path: str) -> Optional[os.stat_result]:
    try:
        stat_result = os.stat(file_path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    if not stat.S_ISREG(stat_result.st_mode):
        return None
    return stat_result


async def _decode_raw_original(photo_id: str, file_path: str, mime_type: str) -> Response:
    # Construct transient sessionless model so worker threads never share a SQLAlchemy Session.
    transient_image = models.Image(id=photo_id, file_path=file_path, mime_type=mime_type)
    async with get_decode_semaphore():
        original_bytes, content_type = await asyncio.to_thread(
            photo_service.get_original_image_bytes,
            transient_image,
        )
    return Response(content=original_bytes, media_type=content_type)


def _prepare_export_items_sync(photo_ids: List[str], dest_folder: str) -> list[dict]:
    """Validates export destination directory and fetches plain file records in a worker thread."""
    if not os.path.exists(dest_folder) or not os.path.isdir(dest_folder):
        raise HTTPException(status_code=400, detail="Invalid destination folder")

    unique_ids = list(dict.fromkeys(photo_ids))
    with database.SessionLocal() as db:
        images = PhotoRepository(db).get_by_ids(unique_ids)
        if not images:
            raise HTTPException(status_code=404, detail="No photos found to export")
        images_by_id = {img.id: img for img in images}
        return [
            {
                "id": photo_id,
                "file_path": images_by_id[photo_id].file_path if photo_id in images_by_id else None,
                "file_name": images_by_id[photo_id].file_name if photo_id in images_by_id else photo_id,
                "missing_error": None if photo_id in images_by_id else f"Photo not found in database: {photo_id}",
            }
            for photo_id in unique_ids
        ]


def _parse_ai_tags(ai_model) -> tuple[list[str], list[str]]:
    tags_list = models._parse_json_list(ai_model.tags if ai_model and hasattr(ai_model, "tags") else None)
    aesthetic_tags_list = models._parse_json_list(ai_model.aesthetic_tags if ai_model and hasattr(ai_model, "aesthetic_tags") else None)
    return tags_list, aesthetic_tags_list

router = APIRouter(prefix="/api/photos", tags=["photos"])

@router.get("", response_model=List[schemas.PhotoListResponse])
def get_photos(
    limit: int = 50,
    offset: int = 0,
    parent_dir: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns list of photos, supporting pagination and directory filtering via PhotoRepository.
    """
    photo_repo = PhotoRepository(db)
    images = photo_repo.list_photos(limit=limit, offset=offset, parent_dir=parent_dir)
    return [img.to_list_response_dict() for img in images]

@router.get("/{id}/thumbnail")
async def get_photo_thumbnail(id: str):
    """
    Serves cached (or dynamically generated) thumbnail for a photo.
    """
    media_record = await asyncio.to_thread(_fetch_photo_media_record_sync, id)
    if not media_record:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo_id, file_path, _ = media_record

    try:
        cache_path = photo_service.get_thumbnail_path(photo_id)
        cached_bytes = await asyncio.to_thread(_read_cached_thumbnail_sync, cache_path, photo_id)
        if cached_bytes:
            return Response(content=cached_bytes, media_type="image/jpeg")

        async with get_decode_semaphore():
            thumb_bytes = await asyncio.to_thread(
                photo_service.generate_and_cache_thumbnail,
                file_path,
                photo_id,
            )
        return Response(content=thumb_bytes, media_type="image/jpeg")
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {str(exc)}")

@router.get("/{id}/original")
async def get_photo_original(id: str):
    """
    Serves the original image. For RAW formats, decodes dynamically to sRGB JPEG.
    """
    media_record = await asyncio.to_thread(_fetch_photo_media_record_sync, id)
    if not media_record:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo_id, file_path, mime_type = media_record

    try:
        if is_raw_image(file_path):
            return await _decode_raw_original(photo_id, file_path, mime_type)

        stat_result = await asyncio.to_thread(_stat_regular_file_sync, file_path)
        if stat_result is None:
            raise HTTPException(status_code=404, detail="Original file not found on disk")
        return FileResponse(file_path, media_type=mime_type, stat_result=stat_result)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to stream original image: {str(exc)}")

@router.get("/{id}", response_model=schemas.PhotoDetailResponse)
def get_photo_detail(id: str, db: Session = Depends(get_db)):
    """
    Fetches full metadata and AI analysis details for a single photo via PhotoRepository.
    """
    photo_repo = PhotoRepository(db)
    img = photo_repo.get_by_id(id)
    if not img:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    return img.to_detail_dict()

@router.patch("/{id}/metadata", response_model=schemas.UpdateMetadataResponse)
def patch_photo_metadata(
    id: str,
    payload: schemas.UpdateMetadataRequest,
    db: Session = Depends(get_db)
):
    """
    Updates custom tags and caption editing state for a photo.
    """
    photo_repo = PhotoRepository(db)
    db_image = photo_repo.get_by_id(id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    try:
        updated_ai = photo_service.update_photo_metadata(db, id, payload.caption, payload.tags)
        ai_payload = updated_ai.to_dict() if hasattr(updated_ai, "to_dict") else models.AIAnalysis.empty_dict()
        return {
            "status": "success",
            "id": id,
            "ai_analysis": ai_payload
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(err)}")

def _resolve_unique_dest_path(dest_folder: str, file_name: str) -> tuple[str, str]:
    base, ext = os.path.splitext(file_name)
    final_name = file_name
    counter = 1
    target_path = os.path.join(dest_folder, final_name)
    while os.path.exists(target_path):
        final_name = f"{base} ({counter}){ext}"
        target_path = os.path.join(dest_folder, final_name)
        counter += 1
    return target_path, final_name

def _copy_export_file_sync(item_dict: dict, dest_folder: str) -> tuple[bool, str, Optional[str]]:
    src_path = item_dict.get("file_path")
    src_name = item_dict.get("file_name", "unknown")
    if not src_path or not os.path.isfile(src_path):
        return False, src_name, f"File not found: {src_path or src_name}"

    target_path, final_name = _resolve_unique_dest_path(dest_folder, src_name)
    shutil.copy2(src_path, target_path)
    return True, final_name, None


def _format_sse_event(event_name: str, payload: dict) -> bytes:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")


def _build_export_done_payload(
    exported_count: int,
    failed_count: int,
    total_count: int,
    exported_ids: list[str],
    failed_ids: list[str],
    errors: list[str],
) -> dict:
    if exported_count == 0:
        export_status = "failed"
    elif failed_count > 0:
        export_status = "partial"
    else:
        export_status = "success"

    return {
        "status": export_status,
        "exported_count": exported_count,
        "failed_count": failed_count,
        "total_count": total_count,
        "exported_ids": exported_ids,
        "failed_ids": failed_ids,
        "errors": errors if errors else None,
    }


async def _process_single_export_item(item: dict, dest_folder: str) -> tuple[bool, str, Optional[str]]:
    file_name = item.get("file_name", "unknown")
    missing_error = item.get("missing_error")
    if missing_error:
        return False, file_name, missing_error

    try:
        return await asyncio.to_thread(_copy_export_file_sync, item, dest_folder)
    except Exception as exc:
        logger.warning("Export copy failed for %s: %s", file_name, exc)
        return False, file_name, f"Failed to copy {file_name}: {str(exc)}"


async def _record_export_step(
    item: dict,
    dest_folder: str,
    exported_ids: list[str],
    failed_ids: list[str],
    errors: list[str],
) -> tuple[bool, str]:
    success, final_name, err_msg = await _process_single_export_item(item, dest_folder)
    item_id = item.get("id")
    if success:
        if isinstance(item_id, str) and item_id:
            exported_ids.append(item_id)
        return True, final_name

    if isinstance(item_id, str) and item_id:
        failed_ids.append(item_id)
    errors.append(err_msg or f"Failed to export {final_name}")
    return False, final_name


async def _stream_export_events(export_items: list, dest_folder: str):
    errors: list[str] = []
    exported_ids: list[str] = []
    failed_ids: list[str] = []
    exported_count = 0
    failed_count = 0
    total_count = len(export_items)

    try:
        yield _format_sse_event("start", {"total": total_count})
        for idx, item in enumerate(export_items):
            success, final_name = await _record_export_step(
                item, dest_folder, exported_ids, failed_ids, errors
            )
            if success:
                exported_count += 1
                yield _format_sse_event("progress", {"processed": idx + 1, "total": total_count, "file": final_name})
            else:
                failed_count += 1

        yield _format_sse_event(
            "done",
            _build_export_done_payload(exported_count, failed_count, total_count, exported_ids, failed_ids, errors),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during export stream")
        yield _format_sse_event("error", {"detail": f"Export stream failed: {str(exc)}"})

@router.post("/export")
async def export_photos(payload: schemas.ExportRequest):
    """
    Exports selected photos to a destination folder via streaming.
    """
    dest_folder = payload.destination_folder
    export_items = await asyncio.to_thread(_prepare_export_items_sync, payload.photo_ids, dest_folder)
    return StreamingResponse(_stream_export_events(export_items, dest_folder), media_type="text/event-stream")

@router.post("/{id}/reindex", response_model=schemas.PhotoDetailResponse)
async def reindex_photo(id: str):
    """
    Forces a re-indexing of a single photo.
    """
    try:
        reindexed_photo = await reindex_single_photo_inplace(id)
        return reindexed_photo
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to reindex photo: {str(err)}")

@router.post("/{id}/favorite", response_model=schemas.FavoriteToggleResponse)
def toggle_favorite(id: str, db: Session = Depends(get_db)):
    """
    Toggles the favorite status of a photo via PhotoRepository.
    """
    photo_repo = PhotoRepository(db)
    updated_image = photo_repo.toggle_favorite(id)
    if not updated_image:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    return {"id": updated_image.id, "is_favorite": updated_image.is_favorite}
