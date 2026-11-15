import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
from database import get_db
from services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=List[schemas.PhotoListResponse])
async def search_photos(
    request: schemas.SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search using text queries + EXIF metadata filtering via SearchService.
    """
    try:
        search_service = SearchService(db)
        final_images = await search_service.search_photos(request)
        return [img.to_list_response_dict() for img in final_images]
    except Exception as exc:
        logger.exception("Photo search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")


@router.post("/similar", response_model=List[schemas.PhotoListResponse])
async def search_similar_photos(
    request: schemas.SimilarSearchRequest,
    db: Session = Depends(get_db)
):
    """
    K-NN Reference Search using existing ChromaDB embedding via SearchService.
    """
    try:
        search_service = SearchService(db)
        final_images = await search_service.search_similar_photos(request)
        return [img.to_list_response_dict() for img in final_images]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Similar photo search failed")
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(exc)}")
