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
