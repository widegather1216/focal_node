import os
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

import schemas
from database import get_db
from repositories.photo_repository import PhotoRepository
from services.indexing_state import indexing_state_manager
from services.indexing_service import (
    run_indexing_background, pause_indexing, resume_indexing, cancel_indexing
)

router = APIRouter(prefix="/api/index", tags=["indexing"])

@router.post("/start", status_code=202)
def start_indexing(payload: schemas.IndexStartRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not payload.folder_paths:
        raise HTTPException(status_code=400, detail="No folder paths provided.")

    if not indexing_state_manager.try_start_indexing():
        raise HTTPException(status_code=400, detail="Indexing is already in progress or paused.")

    try:
        run_id = indexing_state_manager.current_run_id
        normalized_paths = []
        seen = set()
        for folder_path in payload.folder_paths:
            try:
                real_p = os.path.realpath(folder_path)
            except Exception as norm_err:
                print(f"[IndexingAPI] realpath note: {norm_err}", flush=True)
                real_p = os.path.normpath(folder_path)
                
            if real_p not in seen:
                seen.add(real_p)
                normalized_paths.append(real_p)

        photo_repo = PhotoRepository(db)
        for folder_path in normalized_paths:
            existing = photo_repo.get_folder_by_path(folder_path)
            if not existing:
                photo_repo.add_folder(folder_path)
        db.commit()

        background_tasks.add_task(run_indexing_background, normalized_paths, run_id=run_id)
        return {"message": "Indexing started"}
    except Exception:
        indexing_state_manager.reset_status()
        raise

@router.post("/sync", status_code=202)
def sync_database(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not indexing_state_manager.try_start_indexing():
        raise HTTPException(status_code=400, detail="Indexing is already in progress or paused.")

    try:
        run_id = indexing_state_manager.current_run_id
        # Get all currently indexed folders
        photo_repo = PhotoRepository(db)
        folders = photo_repo.list_folders()
        folder_paths = []
        seen = set()
        for folder in folders:
            try:
                real_p = os.path.realpath(folder.path)
            except Exception as norm_err:
                print(f"[IndexingAPI] realpath note: {norm_err}", flush=True)
                real_p = os.path.normpath(folder.path)
            if real_p not in seen:
                seen.add(real_p)
                folder_paths.append(real_p)

        background_tasks.add_task(run_indexing_background, folder_paths, run_id=run_id)
        return {"message": "Sync started"}
    except Exception:
        indexing_state_manager.reset_status()
        raise

@router.post("/pause")
async def pause_indexing_endpoint():
    if not pause_indexing():
        raise HTTPException(status_code=400, detail=f"Cannot pause when status is '{indexing_state_manager.status}'.")
    return {"message": "Indexing paused"}

@router.post("/resume")
async def resume_indexing_endpoint():
    if not resume_indexing():
        raise HTTPException(status_code=400, detail=f"Cannot resume when status is '{indexing_state_manager.status}'.")
    return {"message": "Indexing resumed"}

@router.post("/cancel")
async def cancel_indexing_endpoint():
    if not cancel_indexing():
        raise HTTPException(status_code=400, detail=f"Cannot cancel when status is '{indexing_state_manager.status}'.")
    return {"message": "Indexing cancelled"}

@router.get("/status")
async def get_indexing_status():
    return indexing_state_manager.get_status_dict()
