from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
import schemas
from services.indexing_service import run_indexing_background, indexing_status, cleanup_zombie_records
from database import get_db
from sqlalchemy.orm import Session
from models import IndexedFolder

router = APIRouter(prefix="/api/index", tags=["indexing"])

@router.post("/start", status_code=202)
def start_indexing(payload: schemas.IndexStartRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if indexing_status["status"] == "processing":
        raise HTTPException(status_code=400, detail="Indexing is already in progress.")
        
    for folder_path in payload.folder_paths:
        existing = db.query(IndexedFolder).filter(IndexedFolder.path == folder_path).first()
        if not existing:
            new_folder = IndexedFolder(path=folder_path)
            db.add(new_folder)
    db.commit()

    # Set status synchronously to prevent race conditions
    indexing_status["status"] = "processing"
    background_tasks.add_task(run_indexing_background, payload.folder_paths)
    return {"message": "Indexing started"}

@router.post("/sync", status_code=202)
def sync_database(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if indexing_status["status"] == "processing":
        raise HTTPException(status_code=400, detail="Indexing is already in progress.")
        
    # Get all currently indexed folders
    folders = db.query(IndexedFolder).all()
    folder_paths = [folder.path for folder in folders]

    # Set status synchronously to prevent race conditions
    indexing_status["status"] = "processing"
    
    background_tasks.add_task(run_indexing_background, folder_paths)
    return {"message": "Sync started"}

@router.get("/status")
def get_indexing_status():
    return indexing_status
