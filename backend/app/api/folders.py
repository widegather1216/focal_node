import os
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
def unindex_folder(path: str, db: Session = Depends(get_db)):
    try:
        try:
            norm_path = os.path.realpath(path)
        except Exception as norm_err:
            print(f"[FoldersAPI] realpath note for {path}: {norm_err}", flush=True)
            norm_path = os.path.normpath(path)
        remove_folder_data(norm_path, db=db)
        return {"message": f"Folder {path} and associated images removed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unindex folder: {str(e)}")

