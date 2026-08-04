from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
import schemas
from database import get_db
from services.search_service import SearchService
from services.ai_factory import get_siglip_adapter
from chroma import get_chroma_collection



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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")
