import logging
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from repositories.photo_repository import PhotoRepository
from schemas import FolderResponse
from services.indexing_service import (
    FolderDeletionConflictError,
    FolderNotRegisteredError,
    remove_folder_data,
)

logger = logging.getLogger("focal_node.folders_api")
router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get("", response_model=List[FolderResponse])
def get_folders(db: Session = Depends(get_db)):
    photo_repo = PhotoRepository(db)
    folders = photo_repo.list_folders()
    return [
        {"path": folder_record.path, "created_at": folder_record.created_at.isoformat()}
        for folder_record in folders
    ]


@router.delete("")
def unindex_folder(path: str, db: Session = Depends(get_db)):
    if not path or not path.strip() or "\x00" in path:
        raise HTTPException(status_code=400, detail="Folder path must be a non-empty valid path.")
    if not os.path.isabs(path):
        raise HTTPException(status_code=400, detail="Folder path must be an absolute path.")

    try:
        remove_folder_data(path, db=db)
        return {"message": f"Folder {path} and associated images removed."}
    except FolderNotRegisteredError as not_found_err:
        raise HTTPException(status_code=404, detail=str(not_found_err))
    except FolderDeletionConflictError as conflict_err:
        raise HTTPException(status_code=409, detail=str(conflict_err))
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to unindex folder %s", path)
        raise HTTPException(status_code=500, detail=f"Failed to unindex folder: {str(exc)}")


