import asyncio
import logging
from typing import Callable, List, Optional, Union
from sqlalchemy.orm import Session
import database
import schemas
from repositories.photo_repository import PhotoRepository
from repositories.vector_repository import VectorRepository
from services.ai_factory import get_siglip_adapter

logger = logging.getLogger(__name__)


class SearchService:
    """Coordinates hybrid SQLite text/EXIF search and SigLIP 2/ChromaDB vector search."""

    def __init__(
        self,
        db: Optional[Session] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ):
        self.db = db
        self._session_factory = session_factory
        self.photo_repo = PhotoRepository(db) if db is not None else None
        self.vector_repo = VectorRepository()

    def _open_thread_session(self) -> Session:
        factory = self._session_factory or database.SessionLocal
        return factory()

    @staticmethod
    def _serialize_photo_rows(images: list) -> List[dict]:
        return [
            img.to_list_response_dict() if hasattr(img, "to_list_response_dict") else img
            for img in images
        ]

    def _search_by_text_sync(self, query_text: str, text_limit: Optional[int]) -> List[str]:
        """Executes SQLite text search in an isolated worker-thread session when db is omitted."""
        if self.photo_repo is not None:
            return self.photo_repo.search_by_text(query_text, text_limit)
        with self._open_thread_session() as thread_db:
            return PhotoRepository(thread_db).search_by_text(query_text, text_limit)

    def _filter_and_paginate_sync(
        self,
        candidate_ids: Optional[List[str]],
        request: Union[schemas.SearchRequest, schemas.SimilarSearchRequest],
    ) -> List[dict]:
        """Filters, paginates, and serializes photos inside the worker session before close."""
        if self.photo_repo is not None:
            matched_images = self.photo_repo.filter_and_paginate(
                candidate_ids,
                request.filters,
                request.offset,
                request.limit,
                parent_dir=request.parent_dir,
            )
            return self._serialize_photo_rows(matched_images)

        with self._open_thread_session() as thread_db:
            matched_images = PhotoRepository(thread_db).filter_and_paginate(
                candidate_ids,
                request.filters,
                request.offset,
                request.limit,
                parent_dir=request.parent_dir,
            )
            return self._serialize_photo_rows(matched_images)

    def _extract_query_embedding_sync(self, query_text: str) -> Optional[List[float]]:
        """Extracts a SigLIP 2 text embedding, returning None on model or inference failure."""
        try:
            siglip_adapter = get_siglip_adapter()
            return siglip_adapter.get_text_embedding(query_text)
        except Exception as exc:
            logger.warning(
                "[SearchService] SigLIP 2 embedding unavailable; falling back to SQLite text/EXIF search: %s",
                exc,
            )
            return None

    @staticmethod
    def _compute_search_limit(limit: int, offset: int, has_filters: bool, extra_buffer: int = 0) -> int:
        safe_offset = max(0, offset)
        safe_limit = max(1, limit)
        if has_filters:
            return safe_offset + max(safe_limit * 10, 500)
        return max(1, safe_limit + safe_offset + extra_buffer)

    async def _query_vector_ids(
        self, query_text: str, request: schemas.SearchRequest
    ) -> List[str]:
        """Queries ChromaDB for text-similar photo IDs, returning empty list on failure."""
        query_embedding = await asyncio.to_thread(self._extract_query_embedding_sync, query_text)
        if not query_embedding:
            return []

        has_scoping = bool(request.filters or request.parent_dir)
        search_limit = self._compute_search_limit(request.limit, request.offset, has_scoping)
        try:
            return await asyncio.to_thread(
                self.vector_repo.query_similar_by_embedding,
                query_embedding,
                search_limit,
            )
        except Exception as exc:
            logger.warning(
                "[SearchService] Vector similarity query failed; falling back to SQLite text/EXIF search: %s",
                exc,
            )
            return []

    async def _resolve_query_candidate_ids(
        self, query_text: str, request: schemas.SearchRequest
    ) -> List[str]:
        """Combines SQLite text matches and vector matches, prioritizing text hits."""
        text_limit = None if request.parent_dir else 500
        text_search_ids = await asyncio.to_thread(
            self._search_by_text_sync, query_text, text_limit
        )
        chroma_ids = await self._query_vector_ids(query_text, request)
        return list(dict.fromkeys(text_search_ids + chroma_ids))

    async def search_photos(self, request: schemas.SearchRequest) -> List[dict]:
        """Executes hybrid search (SQLite text + SigLIP 2 vector + EXIF metadata filters)."""
        candidate_ids = None
        query_text = request.query.strip() if request.query else ""

        if query_text:
            candidate_ids = await self._resolve_query_candidate_ids(query_text, request)
            if not candidate_ids:
                return []

        return await asyncio.to_thread(
            self._filter_and_paginate_sync,
            candidate_ids,
            request,
        )

    async def search_similar_photos(self, request: schemas.SimilarSearchRequest) -> List[dict]:
        """Executes K-NN reference search using existing ChromaDB embedding."""
        target_embedding = await asyncio.to_thread(self.vector_repo.get_embedding_by_id, request.photo_id)
        if target_embedding is None:
            logger.warning("[SearchService] Photo embedding for %s not found.", request.photo_id)
            raise ValueError(f"Photo embedding for {request.photo_id} not found")

        has_scoping = bool(request.filters or request.parent_dir)
        search_limit = self._compute_search_limit(
            request.limit, request.offset, has_scoping, extra_buffer=1
        )
        chroma_ids = await asyncio.to_thread(
            self.vector_repo.query_similar_by_embedding, target_embedding, search_limit
        )
        similar_photo_ids = [photo_id for photo_id in chroma_ids if photo_id != request.photo_id]
        if not similar_photo_ids:
            return []

        return await asyncio.to_thread(
            self._filter_and_paginate_sync,
            similar_photo_ids,
            request,
        )
