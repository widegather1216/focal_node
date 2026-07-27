from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
import schemas
from services.indexing_service import (
    run_indexing_background, indexing_status, cleanup_zombie_records,
    pause_indexing, resume_indexing, cancel_indexing
)
from database import get_db
from sqlalchemy.orm import Session
from models import IndexedFolder

router = APIRouter(prefix="/api/index", tags=["indexing"])

import os

@router.post("/start", status_code=202)
def start_indexing(payload: schemas.IndexStartRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if indexing_status["status"] in ["processing", "paused"]:
        raise HTTPException(status_code=400, detail="Indexing is already in progress or paused.")
        
    normalized_paths = []
    seen = set()
    for folder_path in payload.folder_paths:
        try:
            real_p = os.path.realpath(folder_path)
        except Exception:
            real_p = os.path.normpath(folder_path)
            
        if real_p not in seen:
            seen.add(real_p)
            normalized_paths.append(real_p)

    for folder_path in normalized_paths:
        existing = db.query(IndexedFolder).filter(IndexedFolder.path == folder_path).first()
        if not existing:
            new_folder = IndexedFolder(path=folder_path)
            db.add(new_folder)
    db.commit()

    # Set status synchronously to prevent race conditions
    indexing_status["status"] = "processing"
    background_tasks.add_task(run_indexing_background, normalized_paths)
    return {"message": "Indexing started"}

@router.post("/sync", status_code=202)
def sync_database(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if indexing_status["status"] in ["processing", "paused"]:
        raise HTTPException(status_code=400, detail="Indexing is already in progress or paused.")
        
    # Get all currently indexed folders
    folders = db.query(IndexedFolder).all()
    folder_paths = []
    seen = set()
    for folder in folders:
        try:
            real_p = os.path.realpath(folder.path)
        except Exception:
            real_p = os.path.normpath(folder.path)
        if real_p not in seen:
            seen.add(real_p)
            folder_paths.append(real_p)

    # Set status synchronously to prevent race conditions
    indexing_status["status"] = "processing"
    
    background_tasks.add_task(run_indexing_background, folder_paths)
    return {"message": "Sync started"}

@router.post("/pause")
def pause_indexing_endpoint():
    if indexing_status["status"] != "processing":
        raise HTTPException(status_code=400, detail=f"Cannot pause when status is '{indexing_status['status']}'.")
    pause_indexing()
    return {"message": "Indexing paused"}

@router.post("/resume")
def resume_indexing_endpoint():
    if indexing_status["status"] != "paused":
        raise HTTPException(status_code=400, detail=f"Cannot resume when status is '{indexing_status['status']}'.")
    resume_indexing()
    return {"message": "Indexing resumed"}

@router.post("/cancel")
def cancel_indexing_endpoint():
    if indexing_status["status"] not in ["processing", "paused"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel when status is '{indexing_status['status']}'.")
    cancel_indexing()
    return {"message": "Indexing cancelled"}

@router.get("/status")
def get_indexing_status():
    return indexing_status
