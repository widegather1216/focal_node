from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
import asyncio
import schemas
import models
from database import get_db
from chroma import get_chroma_collection
from services.indexing_service import siglip_adapter

router = APIRouter(prefix="/api/search", tags=["search"])

def _execute_search_query(db: Session, photo_ids_from_chroma: list[str] | None, filters, offset: int, limit: int):
    """
    Helper function to build SQLite query, apply filters, and order results.
    """
    q = db.query(models.Image).outerjoin(models.ImageMetadata, models.Image.id == models.ImageMetadata.image_id)
    
    if photo_ids_from_chroma is not None:
        if not photo_ids_from_chroma:
            return []
        
        chunk_size = 900
        if len(photo_ids_from_chroma) > chunk_size:
            from sqlalchemy import or_
            conditions = [models.Image.id.in_(photo_ids_from_chroma[i:i + chunk_size]) 
                          for i in range(0, len(photo_ids_from_chroma), chunk_size)]
            q = q.filter(or_(*conditions))
        else:
            q = q.filter(models.Image.id.in_(photo_ids_from_chroma))
            
    # Apply EXIF filters
    if filters:
        f = filters
        if f.is_favorite is not None:
            q = q.filter(models.Image.is_favorite == f.is_favorite)
        if getattr(f, 'camera_model', None):
            q = q.filter(models.ImageMetadata.camera_model.ilike(f"%{f.camera_model}%"))
        if getattr(f, 'lens_model', None):
            q = q.filter(models.ImageMetadata.lens_model.ilike(f"%{f.lens_model}%"))
        if getattr(f, 'iso_min', None) is not None:
            q = q.filter(models.ImageMetadata.iso >= f.iso_min)
        if getattr(f, 'iso_max', None) is not None:
            q = q.filter(models.ImageMetadata.iso <= f.iso_max)
        if getattr(f, 'f_number_min', None) is not None:
            q = q.filter(models.ImageMetadata.f_number >= f.f_number_min)
        if getattr(f, 'f_number_max', None) is not None:
            q = q.filter(models.ImageMetadata.f_number <= f.f_number_max)
        if getattr(f, 'focal_length_min', None) is not None:
            q = q.filter(models.ImageMetadata.focal_length >= f.focal_length_min)
        if getattr(f, 'focal_length_max', None) is not None:
            q = q.filter(models.ImageMetadata.focal_length <= f.focal_length_max)
        if getattr(f, 'date_from', None) is not None:
            q = q.filter(models.ImageMetadata.capture_date >= f.date_from)
        if getattr(f, 'date_to', None) is not None:
            q = q.filter(models.ImageMetadata.capture_date <= f.date_to)
            
    # Order and paginate
    if photo_ids_from_chroma is not None:
        # Preserve Chroma order
        images = q.all()
        image_map = {img.id: img for img in images}
        sorted_images = []
        for pid in photo_ids_from_chroma:
            if pid in image_map:
                sorted_images.append(image_map[pid])
        final_images = sorted_images[offset : offset + limit]
    else:
        # No semantic query, just filter and order by date
        final_images = q.order_by(models.ImageMetadata.capture_date.desc()).offset(offset).limit(limit).all()
        
    return final_images

@router.post("", response_model=List[schemas.PhotoListResponse])
async def search_photos(
    request: schemas.SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search using text queries + EXIF metadata filtering.
    """
    try:
        photo_ids_from_chroma = None
        
        if request.query and request.query.strip():
            query_str = request.query.strip()
            # 1. Text Search in SQLite (AIAnalysis)
            from sqlalchemy import or_
            text_search_q = db.query(models.AIAnalysis.image_id).filter(
                or_(
                    models.AIAnalysis.tags.ilike(f"%{query_str}%"),
                    models.AIAnalysis.caption.ilike(f"%{query_str}%")
                )
            )
            text_search_ids = [r[0] for r in text_search_q.all()]

            # 2. Get query embedding (CPU bound)
            query_embedding = await asyncio.to_thread(siglip_adapter.get_text_embedding, query_str)
            
            # 3. Search ChromaDB (I/O bound)
            # Fetch a larger pool because SQLite filtering might reduce the count
            search_limit = request.offset + max(request.limit * 10, 500) if request.filters else request.limit + request.offset
            collection = await asyncio.to_thread(get_chroma_collection)
            chroma_ids = []
            if collection.count() > 0:
                results = await asyncio.to_thread(
                    collection.query,
                    query_embeddings=[query_embedding],
                    n_results=search_limit
                )
                if results is not None and results.get('ids') is not None and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
                    chroma_ids = results['ids'][0]
            
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
            
        # Execute query using the unified helper
        final_images = _execute_search_query(db, photo_ids_from_chroma, request.filters, request.offset, request.limit)
            
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
        collection = await asyncio.to_thread(get_chroma_collection)
        if collection.count() == 0:
            return []
            
        # 1. Fetch embedding for the target photo
        target_data = await asyncio.to_thread(
            collection.get,
            ids=[request.photo_id],
            include=["embeddings"]
        )
        
        if target_data is None:
            raise HTTPException(status_code=404, detail="Photo embedding not found")
            
        embs = target_data.get('embeddings')
        if embs is None:
            raise HTTPException(status_code=404, detail="Photo embedding not found")
            
        try:
            if len(embs) == 0:
                raise HTTPException(status_code=404, detail="Photo embedding not found")
        except Exception:
            # If len() fails, just assume it's valid data (like a raw array)
            pass
            
        target_embedding = target_data['embeddings'][0]
        
        # 2. Query similar photos
        search_limit = request.offset + max(request.limit * 10, 500) if request.filters else request.limit + request.offset + 1
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[target_embedding],
            n_results=search_limit
        )
        
        if results is None or results.get('ids') is None or len(results['ids']) == 0 or len(results['ids'][0]) == 0:
            return []
            
        # Exclude the target photo itself
        photo_ids_from_chroma = [pid for pid in results['ids'][0] if pid != request.photo_id]
        
        # 3. Execute query using the unified helper
        final_images = _execute_search_query(db, photo_ids_from_chroma, request.filters, request.offset, request.limit)
        
        return [img.to_list_response_dict() for img in final_images]
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")
