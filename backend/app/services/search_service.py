import asyncio
from typing import List
from sqlalchemy.orm import Session
import schemas
import models
from repositories.photo_repository import PhotoRepository
from repositories.vector_repository import VectorRepository
from services.ai_factory import get_siglip_adapter

class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.photo_repo = PhotoRepository(db)
        self.vector_repo = VectorRepository()

    async def search_photos(self, request: schemas.SearchRequest) -> List[models.Image]:
        """
        Executes hybrid search (SQLite text search + SigLIP 2 vector search + EXIF metadata filters).
        """
        photo_ids_from_chroma = None
        
        if request.query and request.query.strip():
            query_str = request.query.strip()
            # 1. Text Search in SQLite (AIAnalysis)
            text_search_ids = self.photo_repo.search_by_text(query_str)

            # 2. Get query embedding (CPU bound)
            siglip = get_siglip_adapter()
            query_embedding = await asyncio.to_thread(siglip.get_text_embedding, query_str)
            
            # 3. Search ChromaDB (I/O bound)
            search_limit = request.offset + max(request.limit * 10, 500) if request.filters else max(1, request.limit + request.offset)
            chroma_ids = await asyncio.to_thread(
                self.vector_repo.query_similar_by_embedding,
                query_embedding,
                search_limit
            )
            
            # 4. Combine IDs prioritizing text matches
            combined_ids = []
            seen = set()
            for pid in text_search_ids + chroma_ids:
                if pid not in seen:
                    combined_ids.append(pid)
                    seen.add(pid)
                    
            if not combined_ids:
                return []
            photo_ids_from_chroma = combined_ids
            
        # Execute query using PhotoRepository
        return self.photo_repo.filter_and_paginate(
            photo_ids_from_chroma,
            request.filters,
            request.offset,
            request.limit
        )

    async def search_similar_photos(self, request: schemas.SimilarSearchRequest) -> List[models.Image]:
        """
        Executes K-NN reference search using existing ChromaDB embedding.
        """
        if self.vector_repo.count() == 0:
            return []
            
        target_embedding = await asyncio.to_thread(self.vector_repo.get_embedding_by_id, request.photo_id)
        if target_embedding is None:
            raise ValueError(f"Photo embedding for {request.photo_id} not found")
        
        search_limit = request.offset + max(request.limit * 10, 500) if request.filters else max(1, request.limit + request.offset + 1)
        chroma_ids = await asyncio.to_thread(
            self.vector_repo.query_similar_by_embedding,
            target_embedding,
            search_limit
        )
        
        if not chroma_ids:
            return []
            
        photo_ids_from_chroma = [pid for pid in chroma_ids if pid != request.photo_id]
        
        return self.photo_repo.filter_and_paginate(
            photo_ids_from_chroma,
            request.filters,
            request.offset,
            request.limit
        )
