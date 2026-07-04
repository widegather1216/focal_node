from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import IndexedFolder
from schemas import FolderResponse
from services.indexing_service import remove_folder_data

router = APIRouter(prefix="/api/folders", tags=["folders"])

@router.get("", response_model=List[FolderResponse])
def get_folders(db: Session = Depends(get_db)):
    folders = db.query(IndexedFolder).all()
    return [{"path": f.path, "created_at": f.created_at.isoformat()} for f in folders]

@router.delete("")
def unindex_folder(path: str):
    try:
        remove_folder_data(path)
        return {"message": f"Folder {path} and associated images removed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
