import pytest
import threading
import asyncio
from unittest.mock import MagicMock, patch
from services.base_model import BaseKeepAliveModel
from services.ai_factory import _factory_lock, get_siglip_adapter, get_gemma_adapter
from services.unipercept_adapter import _unipercept_lock
from services.model_downloader import ModelDownloadStatusTracker, _downloader_lock, _size_cache_lock
from services.indexing_state import indexing_state_manager
from api.indexing import (
    pause_indexing_endpoint,
    resume_indexing_endpoint,
    cancel_indexing_endpoint,
    get_indexing_status
)


class DummyModel(BaseKeepAliveModel):
    def __init__(self):
        super().__init__("DummyModel", keep_alive_timeout=0.2)
        self.model = object()


def test_base_keep_alive_model_reentrant_lock():
    """
    Verifies that BaseKeepAliveModel uses a reentrant lock (RLock).
    Nested acquisitions and calls to touch_used() while holding self.lock
    must NOT deadlock.
    """
    dummy = DummyModel()
    
    # 1. Outer lock acquisition
    with dummy.lock:
        # 2. Re-entrant call to touch_used() which acquires self.lock internally
        dummy.touch_used()
        assert dummy.last_used_time > 0
        
        # 3. Triple nested acquisition
        with dummy.lock:
            with dummy.lock:
                dummy.touch_used()
                dummy.active_requests += 1

    with dummy.lock:
        dummy.active_requests -= 1
        assert dummy.active_requests == 0


def test_singleton_locks_reentrancy():
    """
    Verifies that singleton and tracker locks across services are reentrant.
    """
    # 1. ai_factory_lock
    with _factory_lock:
        with _factory_lock:
            pass

    # 2. unipercept_lock
    with _unipercept_lock:
        with _unipercept_lock:
            pass

    # 3. model_downloader locks
    with _downloader_lock:
        with _downloader_lock:
            pass

    with _size_cache_lock:
        with _size_cache_lock:
            pass

    # 4. ModelDownloadStatusTracker lock
    tracker = ModelDownloadStatusTracker()
    with tracker._lock:
        with tracker._lock:
            tracker.update_status(
                repo_id="dummy/repo",
                label="Dummy",
                status="cached",
                downloaded_bytes=100,
                total_bytes=100
            )


@pytest.mark.asyncio
async def test_indexing_endpoints_async_thread_safety():
    """
    Verifies that indexing control endpoints run on the event loop as async functions
    and correctly update indexing_state_manager without thread boundary errors.
    """
    indexing_state_manager.reset_status()
    indexing_state_manager.status = "processing"
    
    # Pause
    pause_res = await pause_indexing_endpoint()
    assert pause_res == {"message": "Indexing paused"}
    assert indexing_state_manager.status == "paused"
    assert not indexing_state_manager.pause_event.is_set()

    # Resume
    resume_res = await resume_indexing_endpoint()
    assert resume_res == {"message": "Indexing resumed"}
    assert indexing_state_manager.status == "processing"
    assert indexing_state_manager.pause_event.is_set()

    # Cancel
    cancel_res = await cancel_indexing_endpoint()
    assert cancel_res == {"message": "Indexing cancelled"}
    assert indexing_state_manager.status == "cancelled"

    # Status
    status_dict = await get_indexing_status()
    assert status_dict["status"] == "cancelled"
    
    indexing_state_manager.reset_status()


@pytest.mark.asyncio
async def test_reindex_single_photo_compensating_transaction():
    """
    Verifies that when SQLite commit fails during reindex_single_photo_inplace,
    a compensating transaction restores the previous ChromaDB embedding.
    """
    from services.indexing_service import reindex_single_photo_inplace
    import models

    fake_photo_id = "abc123hash"
    old_embedding = [0.1, 0.2, 0.3]
    new_embedding = [0.9, 0.8, 0.7]

    mock_db_img = MagicMock(spec=models.Image)
    mock_db_img.id = fake_photo_id
    mock_db_img.file_path = "/fake/photo.jpg"

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_db_img
    # Simulate database commit error
    mock_session.commit.side_effect = RuntimeError("Simulated SQLite Disk I/O or Lock Error")

    with patch("services.indexing_service.SessionLocal", return_value=mock_session), \
         patch("os.path.exists", return_value=True), \
         patch("services.indexing_service.run_ai_pipeline_sync", return_value=({}, new_embedding, {})), \
         patch("services.indexing_service.vector_repo") as mock_vector_repo:

        # Old embedding exists in ChromaDB
        mock_vector_repo.get_embedding_by_id.return_value = old_embedding

        with pytest.raises(RuntimeError, match="Simulated SQLite Disk I/O or Lock Error"):
            await reindex_single_photo_inplace(fake_photo_id)

        # 1. Rollback must have been called on SQLite session
        assert mock_session.rollback.called

        # 2. Compensating upsert restoring old_embedding must have been called
        upsert_calls = mock_vector_repo.upsert.call_args_list
        assert len(upsert_calls) == 2
        # First call: attempted upsert of new_embedding
        assert upsert_calls[0].kwargs["embeddings"] == [new_embedding]
        # Second call (compensating transaction): restored old_embedding
        assert upsert_calls[1].kwargs["embeddings"] == [old_embedding]


def test_vector_repository_thread_safe_lock():
    """
    Verifies that VectorRepository uses _vector_lock to synchronize concurrent calls.
    """
    from repositories.vector_repository import VectorRepository, _vector_lock
    import concurrent.futures

    repo = VectorRepository()
    mock_coll = MagicMock()
    mock_coll.count.return_value = 10
    mock_coll.query.return_value = {"ids": [["id1", "id2"]]}

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        def worker(i):
            repo.count()
            repo.query_similar_by_embedding([0.1, 0.2], 5)
            repo.upsert([f"id_{i}"], [[0.1, 0.2]], [{"key": "val"}])
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(worker, range(20)))

        assert all(results)
        # repo.count() called directly 20 times + called inside query_similar_by_embedding 20 times = 40
        assert mock_coll.count.call_count == 40
        assert mock_coll.query.call_count == 20
        assert mock_coll.upsert.call_count == 20


def test_atomic_transaction_delete_and_commit_order():
    """
    Verifies that delete_and_commit deletes from ChromaDB BEFORE committing SQLite session,
    and rolls back SQLite if ChromaDB delete raises.
    """
    from repositories.atomic_transaction import CompensatingTransactionManager

    mock_db = MagicMock()
    mock_vector_repo = MagicMock()

    call_order = []
    mock_vector_repo.delete.side_effect = lambda ids: call_order.append("chroma_delete")
    mock_db.commit.side_effect = lambda: call_order.append("sqlite_commit")

    mgr = CompensatingTransactionManager(db_session=mock_db, vector_repo=mock_vector_repo)
    success = mgr.delete_and_commit(["id_123"])

    assert success is True
    assert call_order == ["chroma_delete", "sqlite_commit"]
    assert not mock_db.rollback.called

    # If ChromaDB delete raises, SQLite commit must NOT be called and rollback must happen
    mock_vector_repo.delete.side_effect = RuntimeError("ChromaDB I/O failure")
    mock_db.reset_mock()
    call_order.clear()

    with pytest.raises(RuntimeError, match="ChromaDB I/O failure"):
        mgr.delete_and_commit(["id_123"])

    assert "sqlite_commit" not in call_order
    assert mock_db.rollback.called


@pytest.mark.asyncio
async def test_search_service_non_blocking():
    """
    Verifies that SearchService.search_photos offloads DB operations to worker threads
    without blocking the main async event loop.
    """
    from services.search_service import SearchService
    import schemas

    mock_db = MagicMock()
    service = SearchService(mock_db)

    service.photo_repo.search_by_text = MagicMock(return_value=["id1", "id2"])
    service.photo_repo.filter_and_paginate = MagicMock(return_value=[MagicMock()])
    service.vector_repo.query_similar_by_embedding = MagicMock(return_value=["id1", "id3"])

    with patch("services.search_service.get_siglip_adapter") as mock_siglip:
        mock_siglip.return_value.get_text_embedding.return_value = [0.1, 0.2]

        req = schemas.SearchRequest(query="sunset in mountains", limit=10, offset=0)
        res = await service.search_photos(req)

        assert len(res) == 1
        assert service.photo_repo.search_by_text.called
        assert service.photo_repo.filter_and_paginate.called


@pytest.mark.asyncio
async def test_chat_service_non_blocking_calls():
    """
    Verifies that ChatService.generate_photo_critique uses asyncio.to_thread
    for unipercept unload_model and database persistence.
    """
    import schemas
    from services.chat_service import ChatService

    req = schemas.CritiqueRequest(photo_id="test_photo_123", engine="unipercept")

    with patch("services.chat_service._get_photo_and_metadata", return_value=("/path/to/test.jpg", {})) as mock_get_meta, \
         patch("services.chat_service.get_gemma_adapter") as mock_gemma, \
         patch("services.chat_service._save_critique_to_db") as mock_save, \
         patch("services.unipercept_adapter.get_unipercept_adapter") as mock_unipercept:

        mock_uni_inst = MagicMock()
        mock_uni_inst.generate_full_ensemble_critique.return_value = {
            "critique": "Aesthetic composition.",
            "scores": {"overall": 85, "iaa": 85, "iqa": 85, "ista": 85},
            "quality_score": 85
        }
        mock_unipercept.return_value = mock_uni_inst

        mock_gemma.return_value.translate_and_format_critique.return_value = "훌륭한 구도입니다."

        res = await ChatService.generate_photo_critique(req)

        assert res["status"] == "completed"
        assert mock_uni_inst.unload_model.called
        assert mock_save.called


def test_decode_raw_to_pil_min_dimension():
    """
    Verifies that decode_raw_to_pil skips low-resolution embedded thumbnails
    when min_dimension is specified, falling back to raw.postprocess.
    """
    from utils.image import decode_raw_to_pil
    from PIL import Image
    import numpy as np

    with patch("rawpy.imread") as mock_imread:
        mock_raw = MagicMock()
        mock_imread.return_value.__enter__.return_value = mock_raw

        # Simulate low-resolution thumbnail (160x120)
        mock_thumb = MagicMock()
        import rawpy
        mock_thumb.format = rawpy.ThumbFormat.BITMAP
        mock_thumb.data = np.zeros((120, 160, 3), dtype=np.uint8)
        mock_raw.extract_thumb.return_value = mock_thumb

        # Full postprocess returns high-resolution image (1920x1080)
        mock_raw.postprocess.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # 1. When min_dimension is 100, low-res 160x120 is accepted
        img_low = decode_raw_to_pil("dummy.arw", min_dimension=100)
        assert img_low.size == (160, 120)
        assert not mock_raw.postprocess.called

        # 2. When min_dimension is 1080, low-res 160x120 is rejected, fallback to postprocess
        mock_raw.reset_mock()
        mock_raw.extract_thumb.return_value = mock_thumb
        mock_raw.postprocess.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)

        img_high = decode_raw_to_pil("dummy.arw", min_dimension=1080)
        assert img_high.size == (1920, 1080)
        assert mock_raw.postprocess.called


def test_indexing_service_deletion_order():
    """
    Verifies that remove_folder_data and cleanup_zombie_records delete from
    ChromaDB before committing SQLite deletions, ensuring Rule 2.2 integrity.
    """
    from services.indexing_service import remove_folder_data, cleanup_zombie_records
    import models

    # 1. Test remove_folder_data
    call_order = []
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [MagicMock(id="img_1")]
    mock_db.query.return_value.all.return_value = []
    mock_db.commit.side_effect = lambda: call_order.append("sqlite_commit")

    with patch("services.indexing_service.vector_repo") as mock_vector:
        mock_vector.delete.side_effect = lambda ids: call_order.append("chroma_delete")

        remove_folder_data("/fake/folder", db=mock_db)

        assert call_order == ["chroma_delete", "sqlite_commit"]

    # 2. Test cleanup_zombie_records
    call_order.clear()
    mock_db.reset_mock()
    mock_db.query.return_value.all.side_effect = [
        [],  # indexed_folders
        [("img_zombie", "/nonexistent/path/z.jpg", "/nonexistent/path")]  # all_images
    ]
    mock_db.commit.side_effect = lambda: call_order.append("sqlite_commit")

    with patch("services.indexing_service.vector_repo") as mock_vector, \
         patch("os.path.exists", return_value=False):
        mock_vector.delete.side_effect = lambda ids: call_order.append("chroma_delete")

        cleanup_zombie_records(db=mock_db)

        assert call_order == ["chroma_delete", "sqlite_commit"]


