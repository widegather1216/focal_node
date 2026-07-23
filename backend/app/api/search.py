from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
import asyncio
import schemas
import models
from database import get_db
from chroma import get_chroma_collection
from services.indexing_service import get_siglip_adapter

from repositories.photo_repository import PhotoRepository
from repositories.vector_repository import VectorRepository

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("", response_model=List[schemas.PhotoListResponse])
async def search_photos(
    request: schemas.SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search using text queries + EXIF metadata filtering.
    """
    try:
        photo_repo = PhotoRepository(db)
        vector_repo = VectorRepository()
        
        photo_ids_from_chroma = None
        
        if request.query and request.query.strip():
            query_str = request.query.strip()
            # 1. Text Search in SQLite (AIAnalysis)
            text_search_ids = photo_repo.search_by_text(query_str)

            # 2. Get query embedding (CPU bound)
            query_embedding = await asyncio.to_thread(get_siglip_adapter().get_text_embedding, query_str)
            
            # 3. Search ChromaDB (I/O bound)
            search_limit = request.offset + max(request.limit * 10, 500) if request.filters else request.limit + request.offset
            chroma_ids = await asyncio.to_thread(
                vector_repo.query_similar_by_embedding,
                query_embedding,
                search_limit
            )
            
            # 4. Combine IDs prioritizing text matches
            combined_ids = []
            seen = set()
            for pid in text_search_ids:
                if pid not in seen:
                    combined_ids.append(pid)
                    seen.add(pid)
            for pid in chroma_ids:
                if pid not in seen:
                    combined_ids.append(pid)
                    seen.add(pid)
                    
            if not combined_ids:
                return []
            photo_ids_from_chroma = combined_ids
            
        # Execute query using PhotoRepository
        final_images = photo_repo.filter_and_paginate(photo_ids_from_chroma, request.filters, request.offset, request.limit)
            
        result = [img.to_list_response_dict() for img in final_images]
        return result
        
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
    K-NN Reference Search using existing ChromaDB embedding.
    """
    try:
        photo_repo = PhotoRepository(db)
        vector_repo = VectorRepository()
        
        if vector_repo.count() == 0:
            return []
            
        # 1. Fetch embedding for the target photo
        target_embedding = await asyncio.to_thread(vector_repo.get_embedding_by_id, request.photo_id)
        if target_embedding is None:
            raise HTTPException(status_code=404, detail="Photo embedding not found")
        
        # 2. Query similar photos
        search_limit = request.offset + max(request.limit * 10, 500) if request.filters else request.limit + request.offset + 1
        chroma_ids = await asyncio.to_thread(
            vector_repo.query_similar_by_embedding,
            target_embedding,
            search_limit
        )
        
        if not chroma_ids:
            return []
            
        # Exclude the target photo itself
        photo_ids_from_chroma = [pid for pid in chroma_ids if pid != request.photo_id]
        
        # 3. Execute query using PhotoRepository
        final_images = photo_repo.filter_and_paginate(photo_ids_from_chroma, request.filters, request.offset, request.limit)
        
        return [img.to_list_response_dict() for img in final_images]
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")
