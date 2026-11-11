import json
import os
import time
import pytest
from PIL import Image
from fastapi import HTTPException

import models
from repositories.photo_repository import PhotoRepository
from services.base_model import BaseKeepAliveModel
from services.pipeline import PipelineContext, HashStep
import services.photo as photo_service
from services.photo import generate_and_cache_thumbnail, register_photos_batch_atomic
from services.model_downloader import get_repo_downloaded_bytes


def test_favorite_toggle_persistence_and_api(client, db_session, tmp_path):
    """
    Verifies that toggle_favorite correctly persists favorite state in SQLite
    and returns 200 OK with accurate JSON response via API endpoint.
    """
    test_img = tmp_path / "test_fav.jpg"
    img = Image.new("RGB", (50, 50), color="red")
    img.save(str(test_img), format="JPEG")

    photo_id = "test_fav_photo_123"
    db_img = models.Image(
        id=photo_id,
        parent_dir=str(tmp_path),
        file_path=str(test_img),
        file_name="test_fav.jpg",
        file_size=1024,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add(db_img)
    db_session.commit()

    # 1. Test Repository method directly
    repo = PhotoRepository(db_session)
    updated = repo.toggle_favorite(photo_id)
    assert updated is not None
    assert updated.is_favorite is True

    # Check persistence in fresh query
    persisted = db_session.query(models.Image).filter(models.Image.id == photo_id).first()
    assert persisted is not None
    assert persisted.is_favorite is True

    # 2. Test API endpoint toggle back to False
    resp = client.post(f"/api/photos/{photo_id}/favorite")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == photo_id
    assert data["is_favorite"] is False

    # 3. Test non-existent photo returns 404
    resp_404 = client.post("/api/photos/non_existent_id/favorite")
    assert resp_404.status_code == 404


def test_base_keep_alive_model_lifecycle():
    """
    Verifies BaseKeepAliveModel timer lifecycle, keep-alive timeout unloading,
    and thread survival when active requests prevent unload.
    """
    class MockModel(BaseKeepAliveModel):
        def __init__(self):
            super().__init__("MockModel", keep_alive_timeout=0.2)
            self.model = "loaded_weights"

    mock_instance = MockModel()
    mock_instance.touch_used()
    assert mock_instance.timer_active is True
    assert mock_instance.model is not None

    # Simulate active requests during timeout
    mock_instance.active_requests = 1
    time.sleep(0.3)
    # Model should NOT unload because active_requests > 0
    assert mock_instance.model is not None

    # Complete active requests
    mock_instance.active_requests = 0
    mock_instance.touch_used()

    # Explicit unload test
    mock_instance.unload_model()
    assert mock_instance.model is None
    assert mock_instance.timer_active is False


def test_thumbnail_zero_dimension_guard(tmp_path, monkeypatch):
    """
    Verifies generate_and_cache_thumbnail guards against invalid 0-width or 0-height images
    and generates valid JPEG thumbnails.
    """
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(photo_service, "THUMBNAIL_CACHE_DIR", str(thumb_dir))
    monkeypatch.setattr("services.photo.THUMBNAIL_CACHE_DIR", str(thumb_dir))

    img_file = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(str(img_file), format="JPEG")

    # Valid thumbnail generation
    thumb_bytes = generate_and_cache_thumbnail(str(img_file), "test_valid_thumb")
    assert len(thumb_bytes) > 0
    assert thumb_bytes[:2] == b"\xff\xd8"  # JPEG Magic Bytes

    # Check cached file exists on disk
    cached_thumb = thumb_dir / "test_valid_thumb.jpg"
    assert cached_thumb.exists()


def test_pipeline_single_pass_hashing(tmp_path):
    """
    Verifies HashStep skips re-calculating SHA256 if image_id is already populated in PipelineContext.
    """
    sample_file = tmp_path / "sample_hash.jpg"
    sample_file.write_bytes(b"test image content")

    precomputed_id = "precomputed_hash_abcdef"
    ctx = PipelineContext(str(sample_file), image_id=precomputed_id)
    assert ctx.image_id == precomputed_id

    step = HashStep()
    result = step.execute(ctx)
    assert result is True
    # Ensure it preserved the precomputed hash without re-reading
    assert ctx.image_id == precomputed_id


def test_batch_atomic_registration_efficiency(db_session):
    """
    Verifies register_photos_batch_atomic executes without raising errors
    and correctly persists batch items into SQLite.
    """
    batch_items = []
    for i in range(5):
        pid = f"batch_test_photo_{i}"
        batch_items.append({
            "image_data": {
                "id": pid,
                "parent_dir": "/tmp/test",
                "file_path": f"/tmp/test/photo_{i}.jpg",
                "file_name": f"photo_{i}.jpg",
                "file_size": 2048,
                "file_mtime": time.time(),
                "mime_type": "image/jpeg",
                "is_favorite": False
            },
            "metadata_data": {
                "width": 1920,
                "height": 1080,
                "camera_model": "Sony A7IV",
                "lens_model": "FE 35mm F1.4 GM",
                "iso": 100,
                "f_number": 1.4,
                "focal_length": 35.0,
                "shutter_speed": "1/500"
            },
            "ai_data": {
                "caption": f"Sample batch photo {i}",
                "tags": ["landscape", "nature"],
                "aesthetic_tags": ["cinematic"]
            },
            "embedding": [0.1] * 128
        })

    register_photos_batch_atomic(db_session, batch_data=batch_items)

    count = db_session.query(models.Image).filter(models.Image.id.like("batch_test_photo_%")).count()
    assert count == 5


def test_model_downloader_throttled_cache():
    """
    Verifies that get_repo_downloaded_bytes leverages TTL cache for rapid polling calls.
    """
    repo = "google/siglip2-base-patch16-224"
    size1 = get_repo_downloaded_bytes(repo, ttl=5.0)
    size2 = get_repo_downloaded_bytes(repo, ttl=5.0)
    assert size1 == size2


def test_photo_repository_batch_get_by_ids(db_session):
    """
    Verifies PhotoRepository.get_by_ids fetches multiple photos in a single query.
    """
    repo = PhotoRepository(db_session)
    for i in range(10):
        img = models.Image(
            id=f"get_by_ids_{i}",
            parent_dir="/test",
            file_path=f"/test/img_{i}.jpg",
            file_name=f"img_{i}.jpg",
            file_size=1000,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False
        )
        db_session.add(img)
    db_session.commit()

    ids_to_fetch = [f"get_by_ids_{i}" for i in range(5)]
    results = repo.get_by_ids(ids_to_fetch)
    assert len(results) == 5
    assert {r.id for r in results} == set(ids_to_fetch)


def test_ensure_string_list_and_parse_gemma_json():
    """
    Verifies parse_gemma_json_output handles comma-separated strings and markdown code fences.
    """
    from services.ai_parser import parse_gemma_json_output, _ensure_string_list

    # 1. Direct helper tests
    assert _ensure_string_list(["tag1", "tag2"]) == ["tag1", "tag2"]
    assert _ensure_string_list("sunset, ocean, beach") == ["sunset", "ocean", "beach"]
    assert _ensure_string_list("single_tag") == ["single_tag"]
    assert _ensure_string_list(None) == []

    # 2. JSON candidate with comma-separated string instead of list
    raw_output = '```json\n{"caption": "A sunset view.", "tags": "golden hour, ocean", "aesthetic_tags": "bokeh"}\n```'
    parsed = parse_gemma_json_output(raw_output)
    assert parsed["caption"] == "A sunset view."
    assert parsed["tags"] == ["golden hour", "ocean"]
    assert parsed["aesthetic_tags"] == ["bokeh"]


def test_models_parse_json_list_edge_cases():
    """
    Verifies models._parse_json_list handles null, scalar string, and malformed json safely.
    """
    from models import _parse_json_list
    assert _parse_json_list(None) == []
    assert _parse_json_list("") == []
    assert _parse_json_list('["landscape", "city"]') == ["landscape", "city"]
    assert _parse_json_list('"single_string"') == ["single_string"]
    assert _parse_json_list("{invalid json") == []


def test_vector_repository_zero_n_results():
    """
    Verifies VectorRepository.query_similar_by_embedding safely returns empty list for n_results <= 0.
    """
    from repositories.vector_repository import VectorRepository
    repo = VectorRepository()
    assert repo.query_similar_by_embedding([0.1] * 128, n_results=0) == []
    assert repo.query_similar_by_embedding([0.1] * 128, n_results=-5) == []


def test_tc_idx_07_get_embedding_by_id_ndarray_and_boundary():
    """
    [TC-IDX-07 / DEFECT-01]
    Verifies VectorRepository.get_embedding_by_id safely handles:
    1. NumPy ndarray (prevents ValueError: The truth value of an array with more than one element is ambiguous)
    2. Conversion from ndarray to standard Python list
    3. Boundary conditions: empty ndarray, empty list, None embeddings, count == 0
    4. Missing photo ID
    """
    from unittest.mock import MagicMock, patch
    import numpy as np
    from repositories.vector_repository import VectorRepository

    repo = VectorRepository()
    mock_coll = MagicMock()

    # 1. Normal NumPy ndarray (shape 1, 3)
    mock_coll.count.return_value = 5
    mock_coll.get.return_value = {"embeddings": np.array([[0.1, 0.2, 0.3]])}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        res = repo.get_embedding_by_id("photo_valid_ndarray")
        assert isinstance(res, list)
        assert res == [0.1, 0.2, 0.3]

    # 2. Python list of floats
    mock_coll.get.return_value = {"embeddings": [[0.4, 0.5, 0.6]]}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        res = repo.get_embedding_by_id("photo_valid_list")
        assert isinstance(res, list)
        assert res == [0.4, 0.5, 0.6]

    # 3. Empty ndarray 1D and 2D
    mock_coll.get.return_value = {"embeddings": np.array([])}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_empty_ndarray_1d") is None

    mock_coll.get.return_value = {"embeddings": np.empty((0, 768))}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_empty_ndarray_2d") is None

    # 4. Empty list / None embeddings / Missing ID
    mock_coll.get.return_value = {"embeddings": []}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_empty_list") is None

    mock_coll.get.return_value = {"embeddings": None}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_none_embeddings") is None

    mock_coll.get.return_value = {}
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_missing_id") is None

    # 5. count == 0
    mock_coll.count.return_value = 0
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        assert repo.get_embedding_by_id("photo_zero_count") is None


def test_tc_idx_08_vector_repository_delete_raises_and_compensating_tx_rollbacks():
    """
    [TC-IDX-08 / DEFECT-02]
    Verifies that:
    1. VectorRepository.delete re-raises exceptions when ChromaDB collection.delete fails,
       rather than silently catching/swallowing them.
    2. CompensatingTransactionManager.delete_and_commit catches this re-raised exception,
       prevents SQLite commit, and invokes SQLite rollback cleanly to prevent zombie vectors.
    3. Normal successful deletion invokes ChromaDB delete and commits SQLite transaction.
    """
    from unittest.mock import MagicMock, patch
    from repositories.vector_repository import VectorRepository
    from repositories.atomic_transaction import CompensatingTransactionManager

    repo = VectorRepository()
    mock_coll = MagicMock()
    mock_db = MagicMock()

    # 1. Direct VectorRepository.delete re-raises on ChromaDB error
    mock_coll.delete.side_effect = RuntimeError("ChromaDB connection lost")
    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        with pytest.raises(RuntimeError, match="ChromaDB connection lost"):
            repo.delete(["photo_err_1", "photo_err_2"])

    # 2. End-to-end integration with CompensatingTransactionManager.delete_and_commit
    # When ChromaDB fails, SQLite commit must NOT be called and rollback MUST be called.
    mock_coll.delete.side_effect = RuntimeError("ChromaDB I/O disk failure")
    mock_db.reset_mock()

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        mgr = CompensatingTransactionManager(db_session=mock_db, vector_repo=repo)
        with pytest.raises(RuntimeError, match="ChromaDB I/O disk failure"):
            mgr.delete_and_commit(["orphan_photo_hash"])

        assert not mock_db.commit.called, "SQLite commit must NOT be called when ChromaDB delete fails!"
        assert mock_db.rollback.called, "SQLite rollback MUST be invoked to prevent zombie vectors!"

    # 3. Successful deletion path
    mock_coll.reset_mock()
    mock_coll.delete.side_effect = None
    mock_db.reset_mock()

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
        mgr = CompensatingTransactionManager(db_session=mock_db, vector_repo=repo)
        success = mgr.delete_and_commit(["clean_photo_1", "clean_photo_2"])

        assert success is True
        mock_coll.delete.assert_called_once_with(ids=["clean_photo_1", "clean_photo_2"])
        assert mock_db.commit.called
        assert not mock_db.rollback.called


def test_tc_idx_09_start_sync_concurrency_toctou_prevention(client, tmp_path, monkeypatch):
    """
    [TC-IDX-09 / DEFECT-03]
    Verifies that:
    1. IndexingStateManager.try_start_indexing() provides atomic check-and-set preemption,
       so concurrent callers across threads cannot both succeed.
    2. Concurrent /api/index/start and /api/index/sync requests cannot execute simultaneously:
       When one request preempts indexing, concurrent or overlapping requests during folder
       preparation and DB commit are immediately rejected with 400 Bad Request.
    3. If folder normalization or DB commit fails during start_indexing,
       the state is safely rolled back to idle via reset_status().
    """
    import concurrent.futures
    from services.indexing_state import indexing_state_manager
    from repositories.photo_repository import PhotoRepository

    indexing_state_manager.reset_status()
    assert indexing_state_manager.status == "idle"

    # --- Part 1: Atomic preemption multi-thread race test ---
    # Attempting to start from 10 parallel threads simultaneously
    def attempt_preemption():
        return indexing_state_manager.try_start_indexing()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: attempt_preemption(), range(10)))

    # Exactly 1 thread must succeed, and 9 must be rejected
    assert results.count(True) == 1, f"Expected exactly 1 success, got {results.count(True)}"
    assert results.count(False) == 9
    assert indexing_state_manager.status == "processing"

    indexing_state_manager.reset_status()

    # --- Part 2: TOCTOU race window prevention in /api/index/start vs /api/index/sync ---
    # Simulate a slow folder preparation or DB commit during start_indexing.
    # While start_indexing is in progress, sync_database is called.
    # With atomic preemption, sync_database MUST receive 400 immediately.
    folder_dir = tmp_path / "race_folder"
    folder_dir.mkdir()

    orig_add_folder = PhotoRepository.add_folder
    sync_called = []
    sync_status_code = []

    def slow_add_folder(self, path):
        # Trigger concurrent sync request while inside start_indexing's folder loop
        if not sync_called:
            sync_called.append(True)
            res = client.post("/api/index/sync")
            sync_status_code.append(res.status_code)
        return orig_add_folder(self, path)

    monkeypatch.setattr(PhotoRepository, "add_folder", slow_add_folder)

    # Prevent actual background task from running heavy jobs
    monkeypatch.setattr("app.api.indexing.run_indexing_background", lambda paths: None)

    start_res = client.post("/api/index/start", json={"folder_paths": [str(folder_dir)]})
    assert start_res.status_code == 202
    assert sync_called == [True]
    # The concurrent sync MUST be rejected with 400 Bad Request!
    assert sync_status_code == [400], f"Expected sync to be rejected with 400, got {sync_status_code}"

    # --- Part 3: Exception during folder prep safely rolls back state to idle ---
    indexing_state_manager.reset_status()

    err_folder = tmp_path / "err_folder"
    err_folder.mkdir()

    def failing_add_folder(self, path):
        raise RuntimeError("Simulated SQLite disk write failure")

    monkeypatch.setattr(PhotoRepository, "add_folder", failing_add_folder)

    with pytest.raises(RuntimeError, match="Simulated SQLite disk write failure"):
        client.post("/api/index/start", json={"folder_paths": [str(err_folder)]})

    # Status must NOT remain stuck in 'processing'
    assert indexing_state_manager.status == "idle"

    # --- Part 4: Exception during sync_database safely rolls back state to idle ---
    indexing_state_manager.reset_status()

    def failing_list_folders(self):
        raise RuntimeError("Simulated DB list_folders failure")

    monkeypatch.setattr(PhotoRepository, "list_folders", failing_list_folders)

    with pytest.raises(RuntimeError, match="Simulated DB list_folders failure"):
        client.post("/api/index/sync")

    assert indexing_state_manager.status == "idle"

    # --- Part 5: initialize_background_run maintains processing state without idle gap ---
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    assert indexing_state_manager.status == "processing"
    # Background initialization must NOT flip status to idle
    indexing_state_manager.initialize_background_run()
    assert indexing_state_manager.status == "processing"
    assert indexing_state_manager.cancel_requested is False
    assert indexing_state_manager.pause_event.is_set() is True

    # Clean up state
    indexing_state_manager.reset_status()


@pytest.mark.asyncio
async def test_tc_idx_10_batch_commit_failure_propagates_and_sets_error_status(client, monkeypatch, capsys):
    """
    [TC-IDX-10 / DEFECT-04]
    Verifies that:
    1. _commit_batch_with_retry rolls back and re-raises the exception after 3 failed attempts
       rather than swallowing it and returning None.
    2. run_indexing_background aborts subsequent chunks on batch commit failure, transitions
       indexing_state_manager to status="error" with single-line error_message, exposes it
       via GET /api/index/status, and does NOT emit false completion logs.
    3. State recovers cleanly via try_start_indexing(), and stale/pre-cancelled runs cannot
       resurrect or overwrite newer runs.
    """
    from unittest.mock import MagicMock, patch
    import services.indexing_service as idx_svc
    from services.indexing_state import indexing_state_manager

    indexing_state_manager.reset_status()

    # --- Part 1: _commit_batch_with_retry boundary & propagation ---
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        idx_svc._commit_batch_with_retry([{"image_data": {"id": "x"}}], max_attempts=0)

    # Empty batch returns immediately without DB access
    idx_svc._commit_batch_with_retry([], max_attempts=3)

    mock_session = MagicMock()
    batch_payload = [{"image_data": {"id": "p1", "file_path": "/p1.jpg"}}]
    with patch.object(idx_svc, "SessionLocal", return_value=mock_session), \
         patch("services.photo.register_photos_batch_atomic", side_effect=RuntimeError("DB disk full\n[SQL: INSERT]")) as mock_reg, \
         patch("time.sleep"):
        with pytest.raises(RuntimeError, match="DB disk full"):
            idx_svc._commit_batch_with_retry(batch_payload, max_attempts=3)

    assert mock_reg.call_count == 3
    assert mock_session.rollback.call_count == 3
    assert mock_session.close.call_count == 3

    # --- Part 2: End-to-end run_indexing_background stops on chunk failure & prevents false completion ---
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    first_run_id = indexing_state_manager.current_run_id

    # 105 files across 2 chunks (100 + 5): chunk 1 commit fails, so chunk 2 must never execute
    files_list = [f"/fake/img_{i}.jpg" for i in range(105)]
    processed_paths = []

    def fake_index_single(path):
        processed_paths.append(path)
        return {
            "image_data": {"id": f"id_{path}", "file_path": path},
            "metadata_data": {},
            "ai_data": {},
            "embedding": [0.1] * 4,
        }

    capsys.readouterr()
    with patch.object(idx_svc, "scan_directory", return_value=files_list), \
         patch.object(idx_svc, "cleanup_zombie_records"), \
         patch.object(idx_svc, "index_single_file_sync", side_effect=fake_index_single), \
         patch("services.photo.register_photos_batch_atomic", side_effect=RuntimeError("SQLite I/O\nline2")), \
         patch("time.sleep"):
        await idx_svc.run_indexing_background(["/fake"], run_id=first_run_id)

    captured_stdout = capsys.readouterr().out
    assert "[Indexer] Background indexing completed." not in captured_stdout
    assert "[Indexer] Sync completed." not in captured_stdout
    assert f"[Indexer] Background indexing failed [run={first_run_id}]: SQLite I/O line2" in captured_stdout

    # Only chunk 1 (100 files) should have been processed before aborting
    assert len(processed_paths) == 100

    status_resp = client.get("/api/index/status")
    assert status_resp.status_code == 200
    status_json = status_resp.json()
    assert status_json["status"] == "error"
    assert status_json["error_message"] == "SQLite I/O line2"
    assert status_json["processed_files"] == 100
    assert status_json["total_files"] == 105
    assert status_json["run_id"] == first_run_id

    # --- Part 3: Recovery from error state & pre-cancel/stale-run protection ---
    assert indexing_state_manager.try_start_indexing() is True
    cancelled_run_id = indexing_state_manager.current_run_id
    assert indexing_state_manager.status == "processing"
    assert indexing_state_manager.get_status_dict()["error_message"] is None

    # Pre-cancel before background task starts: initialize_background_run must return None
    indexing_state_manager.cancel()
    assert indexing_state_manager.initialize_background_run(run_id=cancelled_run_id) is None
    assert indexing_state_manager.status == "cancelled"

    # Start a new run and ensure stale run_id cannot overwrite its active status
    assert indexing_state_manager.try_start_indexing() is True
    active_run_id = indexing_state_manager.current_run_id
    assert active_run_id > cancelled_run_id
    assert indexing_state_manager.finalize_run(error_message="stale err", run_id=first_run_id) is None
    assert indexing_state_manager.status == "processing"

    # Cancellation takes precedence over error_message on active run finalization
    indexing_state_manager.cancel()
    assert indexing_state_manager.finalize_run(error_message="err during cancel", run_id=active_run_id) == "cancelled"
    assert indexing_state_manager.status == "cancelled"
    assert indexing_state_manager.get_status_dict()["error_message"] is None

    # BaseException (CancelledError) must transition to error (not idle/completed) when not user-cancelled
    import asyncio
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    interrupted_run_id = indexing_state_manager.current_run_id
    capsys.readouterr()
    with patch.object(idx_svc, "scan_directory", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await idx_svc.run_indexing_background(["/fake"], run_id=interrupted_run_id)
    interrupted_stdout = capsys.readouterr().out
    assert "[Indexer] Background indexing completed." not in interrupted_stdout
    assert indexing_state_manager.status == "error"
    assert indexing_state_manager.get_status_dict()["error_message"] == "CancelledError"

    indexing_state_manager.reset_status()


@pytest.mark.asyncio
async def test_tc_idx_11_modified_file_reindex_preserves_old_record_on_interrupt(tmp_path, monkeypatch):
    """
    [TC-IDX-11 / DEFECT-05]
    Verifies that re-indexing a modified file defers old-record deletion until
    new-record batch commit succeeds:
    1. Cancellation before batch commit preserves old SQLite rows, Chroma vector, and thumbnail.
    2. Batch commit failure across retries rolls back SQLite + compensates new vector, preserving old state.
    3. Successful replacement avoids UNIQUE(file_path) conflicts, cleans child/parent rows without orphans,
       and isolates post-commit old-vector deletion errors from re-entering commit retries.
    4. mtime-only touch and pipeline error paths keep existing records intact.
    """
    from unittest.mock import MagicMock, patch
    from sqlalchemy.orm import sessionmaker
    import services.indexing_service as idx_svc
    import services.pipeline as pipeline_mod
    from services.indexing_state import indexing_state_manager
    from repositories.vector_repository import VectorRepository
    from tests.conftest import engine as test_engine

    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()

    monkeypatch.setattr(photo_service, "THUMBNAIL_CACHE_DIR", str(thumb_dir))
    monkeypatch.setattr("services.photo.THUMBNAIL_CACHE_DIR", str(thumb_dir))
    monkeypatch.setattr(
        pipeline_mod,
        "generate_and_cache_thumbnail",
        lambda src_path, img_id: (thumb_dir / f"{img_id}.jpg").write_bytes(b"thumb:" + img_id.encode()),
    )

    mock_siglip = MagicMock()
    mock_siglip.get_image_embedding.return_value = [0.2] * 768
    mock_siglip.get_zero_shot_hints.return_value = ["landscape", "sky"]
    mock_gemma = MagicMock()
    mock_gemma.generate_caption_and_tags.return_value = {
        "caption": "Updated test image",
        "tags": ["updated"],
        "aesthetic_tags": ["clean"],
    }
    monkeypatch.setattr(pipeline_mod, "get_siglip_adapter", lambda: mock_siglip)
    monkeypatch.setattr(pipeline_mod, "get_gemma_adapter", lambda: mock_gemma)

    photo_file = photo_dir / "edited.jpg"
    Image.new("RGB", (32, 32), color="red").save(str(photo_file), format="JPEG")
    os.utime(photo_file, (100.0, 100.0))
    old_id = idx_svc.calculate_sha256(str(photo_file))
    old_thumb = thumb_dir / f"{old_id}.jpg"
    old_thumb.write_bytes(b"old-thumb")

    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    setup_db = SessionFactory()
    try:
        setup_db.add(models.IndexedFolder(path=str(photo_dir)))
        setup_db.add(
            models.Image(
                id=old_id,
                parent_dir=str(photo_dir),
                file_path=str(photo_file),
                file_name="edited.jpg",
                file_size=photo_file.stat().st_size,
                file_mtime=100.0,
                mime_type="image/jpeg",
                is_favorite=True,
            )
        )
        setup_db.add(models.ImageMetadata(image_id=old_id, width=32, height=32, camera_model="Sony A7M4"))
        setup_db.add(models.AIAnalysis(image_id=old_id, caption="old caption", critique="keep critique"))
        setup_db.commit()
    finally:
        setup_db.close()

    chroma_vectors = {old_id: [0.1] * 768}

    def fake_upsert(ids, embeddings, metadatas):
        for pid, emb in zip(ids, embeddings):
            chroma_vectors[pid] = emb

    def fake_delete(ids):
        for pid in ids:
            chroma_vectors.pop(pid, None)

    mock_coll = MagicMock()
    mock_coll.upsert.side_effect = fake_upsert
    mock_coll.delete.side_effect = fake_delete

    # Modify file bytes so SHA-256 changes
    Image.new("RGB", (32, 32), color="blue").save(str(photo_file), format="JPEG")
    os.utime(photo_file, (200.0, 200.0))
    new_id = idx_svc.calculate_sha256(str(photo_file))
    assert new_id != old_id

    # --- Part 1: Cancellation after index_single_file_sync (before batch commit) ---
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    cancel_run_id = indexing_state_manager.current_run_id

    orig_index_single = idx_svc.index_single_file_sync

    def cancel_after_single(path):
        single_result = orig_index_single(path)
        assert isinstance(single_result, dict)
        assert single_result.get("replaces_image_id") == old_id
        indexing_state_manager.cancel()
        return single_result

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll), \
         patch.object(idx_svc, "cleanup_zombie_records"), \
         patch.object(idx_svc, "index_single_file_sync", side_effect=cancel_after_single):
        await idx_svc.run_indexing_background([str(photo_dir)], run_id=cancel_run_id)

    check_db = SessionFactory()
    try:
        assert check_db.query(models.Image).filter_by(id=old_id).first().is_favorite is True
        assert check_db.query(models.AIAnalysis).filter_by(image_id=old_id).first().critique == "keep critique"
        assert check_db.query(models.Image).filter_by(id=new_id).first() is None
    finally:
        check_db.close()
    assert old_id in chroma_vectors and new_id not in chroma_vectors
    assert old_thumb.exists()

    # --- Part 2: Batch commit failure across 3 retries restores SQLite & compensates new vector ---
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    fail_run_id = indexing_state_manager.current_run_id

    orig_upsert_and_commit = photo_service.CompensatingTransactionManager.upsert_and_commit

    def fail_sqlite_commit_in_tx(self, image_ids, embeddings, metadatas):
        self.db.commit = MagicMock(side_effect=RuntimeError("SQLite commit disk full"))
        return orig_upsert_and_commit(self, image_ids, embeddings, metadatas)

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll), \
         patch.object(idx_svc, "cleanup_zombie_records"), \
         patch.object(photo_service.CompensatingTransactionManager, "upsert_and_commit", fail_sqlite_commit_in_tx), \
         patch("time.sleep"):
        await idx_svc.run_indexing_background([str(photo_dir)], run_id=fail_run_id)

    assert indexing_state_manager.status == "error"
    assert "SQLite commit disk full" in indexing_state_manager.get_status_dict()["error_message"]

    check_db = SessionFactory()
    try:
        assert check_db.query(models.Image).filter_by(id=old_id).first().is_favorite is True
        assert check_db.query(models.ImageMetadata).filter_by(image_id=old_id).first().camera_model == "Sony A7M4"
        assert check_db.query(models.AIAnalysis).filter_by(image_id=old_id).first().critique == "keep critique"
        assert check_db.query(models.Image).filter_by(id=new_id).first() is None
    finally:
        check_db.close()
    assert old_id in chroma_vectors and new_id not in chroma_vectors
    assert old_thumb.exists()

    # --- Part 3: Post-commit Chroma delete error does NOT trigger retry or lose new_id ---
    mock_coll.delete.side_effect = RuntimeError("Post-commit Chroma delete error")
    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    post_err_run_id = indexing_state_manager.current_run_id

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll), \
         patch.object(idx_svc, "cleanup_zombie_records"):
        await idx_svc.run_indexing_background([str(photo_dir)], run_id=post_err_run_id)

    assert indexing_state_manager.status == "idle"
    check_db = SessionFactory()
    try:
        assert check_db.query(models.Image).filter_by(id=old_id).first() is None
        assert check_db.query(models.ImageMetadata).filter_by(image_id=old_id).first() is None
        assert check_db.query(models.AIAnalysis).filter_by(image_id=old_id).first() is None
        assert check_db.query(models.Image).filter_by(id=new_id).first() is not None
    finally:
        check_db.close()
    assert new_id in chroma_vectors
    assert not old_thumb.exists()
    assert (thumb_dir / f"{new_id}.jpg").exists()

    # --- Part 4: Clean replacement + mtime-only touch + pipeline error preservation ---
    mock_coll.delete.side_effect = fake_delete
    Image.new("RGB", (32, 32), color="green").save(str(photo_file), format="JPEG")
    os.utime(photo_file, (300.0, 300.0))
    v3_id = idx_svc.calculate_sha256(str(photo_file))
    assert v3_id != new_id

    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    clean_run_id = indexing_state_manager.current_run_id

    with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll), \
         patch.object(idx_svc, "cleanup_zombie_records"):
        await idx_svc.run_indexing_background([str(photo_dir)], run_id=clean_run_id)

    assert indexing_state_manager.status == "idle"
    check_db = SessionFactory()
    try:
        assert check_db.query(models.Image).filter_by(id=new_id).first() is None
        assert check_db.query(models.Image).filter_by(id=v3_id).first() is not None
    finally:
        check_db.close()
    assert v3_id in chroma_vectors and new_id not in chroma_vectors
    assert not (thumb_dir / f"{new_id}.jpg").exists()
    assert (thumb_dir / f"{v3_id}.jpg").exists()

    # mtime-only touch returns "skipped" and preserves record
    os.utime(photo_file, (400.0, 400.0))
    assert idx_svc.index_single_file_sync(str(photo_file)) == "skipped"
    check_db = SessionFactory()
    try:
        v3_row = check_db.query(models.Image).filter_by(id=v3_id).first()
        assert v3_row is not None and abs(v3_row.file_mtime - 400.0) < 0.01
    finally:
        check_db.close()

    # Missing file / pipeline error preserves v3_id
    assert idx_svc.index_single_file_sync(str(photo_dir / "missing.jpg")) == "error"
    Image.new("RGB", (32, 32), color="yellow").save(str(photo_file), format="JPEG")
    os.utime(photo_file, (500.0, 500.0))
    with patch.object(pipeline_mod.IndexingPipeline, "run", return_value="error"):
        assert idx_svc.index_single_file_sync(str(photo_file)) == "error"
    check_db = SessionFactory()
    try:
        assert check_db.query(models.Image).filter_by(id=v3_id).first() is not None
    finally:
        check_db.close()

    # --- Part 5: Idempotent replacement when old_id absent & self/cross-batch protection ---
    swap_thumb = thumb_dir / "swap_a.jpg"
    swap_thumb.write_bytes(b"thumb:swap_a")
    swap_batch = [
        {
            "image_data": {
                "id": "swap_b",
                "parent_dir": str(photo_dir),
                "file_path": str(photo_dir / "swap_b.jpg"),
                "file_name": "swap_b.jpg",
                "file_size": 100,
                "file_mtime": 600.0,
                "mime_type": "image/jpeg",
                "is_favorite": False,
            },
            "metadata_data": {"width": 10, "height": 10},
            "ai_data": {"caption": "swap b", "tags": [], "aesthetic_tags": []},
            "embedding": [0.3] * 768,
            "replaces_image_id": "swap_a",
        },
        {
            "image_data": {
                "id": "swap_a",
                "parent_dir": str(photo_dir),
                "file_path": str(photo_dir / "swap_a_new.jpg"),
                "file_name": "swap_a_new.jpg",
                "file_size": 100,
                "file_mtime": 600.0,
                "mime_type": "image/jpeg",
                "is_favorite": False,
            },
            "metadata_data": {"width": 10, "height": 10},
            "ai_data": {"caption": "swap a", "tags": [], "aesthetic_tags": []},
            "embedding": [0.4] * 768,
            "replaces_image_id": "non_existent_old_id",
        },
    ]
    swap_db = SessionFactory()
    try:
        with patch.object(VectorRepository, "collection", new_callable=lambda: mock_coll):
            register_photos_batch_atomic(swap_db, swap_batch)
        assert swap_db.query(models.Image).filter_by(id="swap_a").first() is not None
        assert swap_db.query(models.Image).filter_by(id="swap_b").first() is not None
    finally:
        swap_db.close()
    assert "swap_a" in chroma_vectors and "swap_b" in chroma_vectors
    assert swap_thumb.exists()

    indexing_state_manager.reset_status()


def test_tc_idx_12_korean_folder_nfd_nfc_zombie_prevention(db_session, tmp_path, monkeypatch):
    """
    TC-IDX-12 (DEFECT-06): Verifies that NFD vs NFC Unicode normalization differences
    between IndexedFolder (e.g. Tauri NFC) and Image paths (e.g. macOS APFS NFD)
    do not cause false-positive zombie purge during cleanup_zombie_records,
    while preserving genuine zombie cleanup for deleted files and sibling folders.
    """
    import unicodedata
    from unittest.mock import patch
    from services.indexing_service import cleanup_zombie_records, _identify_zombie_photo_ids
    import services.indexing_service as idx_svc

    thumb_dir = tmp_path / "thumbs_tc_idx_12"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    # 1. NFC IndexedFolder vs NFD Image paths (macOS APFS simulation)
    korean_root_nfc = unicodedata.normalize("NFC", str(tmp_path / "한글사진폴더"))
    korean_root_nfd = unicodedata.normalize("NFD", str(tmp_path / "한글사진폴더"))
    os.mkdir(korean_root_nfc)

    sub_nfd = os.path.join(korean_root_nfd, unicodedata.normalize("NFD", "제주여행"))
    os.mkdir(sub_nfd)
    sub_nfc = unicodedata.normalize("NFC", sub_nfd)

    root_photo_nfd = os.path.join(korean_root_nfd, unicodedata.normalize("NFD", "바다풍경.jpg"))
    with open(root_photo_nfd, "wb") as f_handle:
        f_handle.write(b"jpg-root")

    sub_photo_nfd = os.path.join(sub_nfd, unicodedata.normalize("NFD", "한라산.jpg"))
    with open(sub_photo_nfd, "wb") as f_handle:
        f_handle.write(b"jpg-sub")

    # 2. Reverse direction: NFD IndexedFolder vs NFC Image paths
    reverse_dir_nfd = unicodedata.normalize("NFD", str(tmp_path / "역방향폴더"))
    reverse_dir_nfc = unicodedata.normalize("NFC", reverse_dir_nfd)
    os.mkdir(reverse_dir_nfd)
    reverse_photo_nfc = os.path.join(reverse_dir_nfc, unicodedata.normalize("NFC", "노을.jpg"))
    with open(reverse_photo_nfc, "wb") as f_handle:
        f_handle.write(b"jpg-rev")

    # 3. Genuine zombies: physically deleted file inside Korean folder + sibling unindexed folder
    deleted_korean_file = os.path.join(korean_root_nfd, unicodedata.normalize("NFD", "삭제됨.jpg"))
    sibling_unindexed_dir = unicodedata.normalize("NFC", str(tmp_path / "한글사진폴더_미등록"))
    os.mkdir(sibling_unindexed_dir)
    sibling_photo = os.path.join(sibling_unindexed_dir, unicodedata.normalize("NFD", "외부.jpg"))
    with open(sibling_photo, "wb") as f_handle:
        f_handle.write(b"jpg-sibling")

    db_session.add_all([
        models.IndexedFolder(path=korean_root_nfc),
        models.IndexedFolder(path=reverse_dir_nfd),
        models.Image(
            id="tc12_nfd_in_nfc_root",
            parent_dir=korean_root_nfd,
            file_path=root_photo_nfd,
            file_name=unicodedata.normalize("NFD", "바다풍경.jpg"),
            file_size=8,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False,
        ),
        models.Image(
            id="tc12_nfd_in_nfc_sub",
            parent_dir=sub_nfd,
            file_path=sub_photo_nfd,
            file_name=unicodedata.normalize("NFD", "한라산.jpg"),
            file_size=7,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=True,
        ),
        models.Image(
            id="tc12_nfc_in_nfd_root",
            parent_dir=reverse_dir_nfc,
            file_path=reverse_photo_nfc,
            file_name=unicodedata.normalize("NFC", "노을.jpg"),
            file_size=7,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False,
        ),
        models.Image(
            id="tc12_genuine_deleted",
            parent_dir=korean_root_nfd,
            file_path=deleted_korean_file,
            file_name=unicodedata.normalize("NFD", "삭제됨.jpg"),
            file_size=7,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False,
        ),
        models.Image(
            id="tc12_sibling_unindexed",
            parent_dir=sibling_unindexed_dir,
            file_path=sibling_photo,
            file_name=unicodedata.normalize("NFD", "외부.jpg"),
            file_size=11,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False,
        ),
    ])
    db_session.commit()

    (thumb_dir / "tc12_nfd_in_nfc_root.jpg").write_bytes(b"keep-thumb-1")
    (thumb_dir / "tc12_nfd_in_nfc_sub.jpg").write_bytes(b"keep-thumb-2")
    (thumb_dir / "tc12_nfc_in_nfd_root.jpg").write_bytes(b"keep-thumb-3")
    (thumb_dir / "tc12_genuine_deleted.jpg").write_bytes(b"del-thumb")
    (thumb_dir / "tc12_sibling_unindexed.jpg").write_bytes(b"sib-thumb")

    # Direct call to _identify_zombie_photo_ids with NFC prefix for subfolder vs NFD DB row
    direct_zombies = _identify_zombie_photo_ids(
        db_session,
        [(sub_nfc, sub_nfc + os.sep), (reverse_dir_nfd, reverse_dir_nfd + os.sep)],
    )
    assert "tc12_nfd_in_nfc_sub" not in direct_zombies
    assert "tc12_nfc_in_nfd_root" not in direct_zombies
    assert "tc12_genuine_deleted" in direct_zombies
    assert "tc12_sibling_unindexed" in direct_zombies

    deleted_vector_ids = []
    with patch.object(idx_svc, "vector_repo") as mock_vector:
        mock_vector.delete.side_effect = lambda ids: deleted_vector_ids.extend(ids)
        cleanup_zombie_records(db=db_session)

    # Existing Korean-path images (both NFC and NFD variants) MUST survive
    assert db_session.query(models.Image).filter_by(id="tc12_nfd_in_nfc_root").first() is not None
    assert db_session.query(models.Image).filter_by(id="tc12_nfd_in_nfc_sub").first() is not None
    assert db_session.query(models.Image).filter_by(id="tc12_nfc_in_nfd_root").first() is not None
    assert (thumb_dir / "tc12_nfd_in_nfc_root.jpg").exists()
    assert (thumb_dir / "tc12_nfd_in_nfc_sub.jpg").exists()
    assert (thumb_dir / "tc12_nfc_in_nfd_root.jpg").exists()

    # Physically deleted and unindexed sibling-prefix images MUST be purged
    assert db_session.query(models.Image).filter_by(id="tc12_genuine_deleted").first() is None
    assert db_session.query(models.Image).filter_by(id="tc12_sibling_unindexed").first() is None
    assert not (thumb_dir / "tc12_genuine_deleted.jpg").exists()
    assert not (thumb_dir / "tc12_sibling_unindexed.jpg").exists()
    assert set(deleted_vector_ids) == {"tc12_genuine_deleted", "tc12_sibling_unindexed"}


def test_tc_idx_13_exif_empty_tag_values_preserves_remaining_metadata(tmp_path):
    """
    TC-IDX-13 (DEFECT-07): Verifies that ExifRead tags with empty values (values=[])
    or empty/oversized IFD entries do not raise IndexError in _get_tag_val and do not
    abort parsing of remaining EXIF metadata or fallback keys.
    """
    import io
    import struct
    import datetime
    from types import SimpleNamespace
    from utils.image import _get_tag_val, extract_metadata

    # 1. Direct _get_tag_val boundary checks
    tags = {
        "EmptyList": SimpleNamespace(values=[]),
        "EmptyTuple": SimpleNamespace(values=()),
        "EmptyStr": SimpleNamespace(values="   "),
        "ZeroList": SimpleNamespace(values=[0]),
        "PrimaryEmpty": SimpleNamespace(values=[]),
        "SecondaryValid": SimpleNamespace(values=[400]),
        "PrimaryEmptyStr": SimpleNamespace(values=""),
        "SecondaryLens": SimpleNamespace(values="FE 35mm F1.4 GM"),
    }
    assert _get_tag_val(tags, "EmptyList") is None
    assert _get_tag_val(tags, "EmptyTuple") is None
    assert _get_tag_val(tags, "EmptyStr") is None
    assert _get_tag_val(tags, "ZeroList") == 0
    assert _get_tag_val(tags, ["PrimaryEmpty", "SecondaryValid"]) == 400
    assert _get_tag_val(tags, ["PrimaryEmptyStr", "SecondaryLens"]) == "FE 35mm F1.4 GM"

    # 2. End-to-end real JPEG with malformed EXIF IFD entries:
    #    - EXIF FNumber (0x829D): count=0 -> ExifRead produces values=[]
    #    - EXIF FocalLengthIn35mmFilm (0xA405): count=1500 (>=1000) -> ExifRead produces values=[]
    #    - EXIF ISOSpeedRatings (0x8827): count=0 -> values=[], falls back to EXIF ISOSpeed (0x8833)=400
    #    - Valid FocalLength (50/1), ExposureTime (1/250), DateTimeOriginal, Image Model ("ILCE-7M4")
    model_bytes = b"ILCE-7M4\x00"       # 9 bytes
    date_bytes = b"2026:07:15 10:20:30\x00"  # 20 bytes

    # Little-endian TIFF layout:
    # Header (8): offset 0..8
    # IFD0 (2 entries = 2 + 24 + 4 = 30): offset 8..38
    # Model string (9): offset 38..47 (pad 1 byte -> 48)
    # ExifIFD (7 entries = 2 + 84 + 4 = 90): offset 48..138
    # DateTimeOriginal (20): offset 138..158
    # FocalLength rational 50/1 (8): offset 158..166
    # ExposureTime rational 1/250 (8): offset 166..174
    tiff = bytearray()
    tiff += b"II" + struct.pack("<HI", 42, 8)
    tiff += struct.pack("<H", 2)
    tiff += struct.pack("<HHII", 0x0110, 2, len(model_bytes), 38)  # Image Model
    tiff += struct.pack("<HHII", 0x8769, 4, 1, 48)                 # ExifOffset
    tiff += struct.pack("<I", 0)
    assert len(tiff) == 38
    tiff += model_bytes + b"\x00"
    assert len(tiff) == 48

    tiff += struct.pack("<H", 7)
    tiff += struct.pack("<HHII", 0x829D, 5, 0, 0)       # FNumber count=0 -> values=[]
    tiff += struct.pack("<HHII", 0x8827, 3, 0, 0)       # ISOSpeedRatings count=0 -> values=[]
    tiff += struct.pack("<HHII", 0x8833, 4, 1, 400)     # ISOSpeed=400 (fallback key)
    tiff += struct.pack("<HHII", 0x9003, 2, len(date_bytes), 138)  # DateTimeOriginal
    tiff += struct.pack("<HHII", 0x920A, 5, 1, 158)     # FocalLength=50/1
    tiff += struct.pack("<HHII", 0x829A, 5, 1, 166)     # ExposureTime=1/250
    tiff += struct.pack("<HHII", 0xA405, 3, 1500, 174)  # FocalLengthIn35mmFilm count=1500 -> values=[]
    tiff += struct.pack("<I", 0)
    assert len(tiff) == 138
    tiff += date_bytes
    assert len(tiff) == 158
    tiff += struct.pack("<II", 50, 1)
    tiff += struct.pack("<II", 1, 250)

    jpeg_buf = io.BytesIO()
    Image.new("RGB", (32, 24), color="blue").save(jpeg_buf, format="JPEG")
    raw_jpeg = jpeg_buf.getvalue()
    app1_payload = b"Exif\x00\x00" + bytes(tiff)
    app1_segment = b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload
    crafted_path = tmp_path / "malformed_exif_empty_values.jpg"
    crafted_path.write_bytes(raw_jpeg[:2] + app1_segment + raw_jpeg[2:])

    meta = extract_metadata(str(crafted_path))
    assert meta["width"] == 32
    assert meta["height"] == 24
    assert meta["camera_model"] == "ILCE-7M4"
    assert meta["f_number"] is None
    assert meta["focal_length"] == 50.0
    assert meta["focal_length_35mm"] == 50.0
    assert meta["crop_factor"] == 1.0
    assert meta["sensor_format"] == "Full Frame"
    assert meta["shutter_speed"] == "1/250"
    assert meta["iso"] == 400
    assert meta["capture_date"] == datetime.datetime(2026, 7, 15, 10, 20, 30)

    # 3. Early tag (Image Model) empty list & corrupted Ratio(n, 0) / tuple values must not abort parsing
    from exifread.utils import Ratio
    from utils.image import _extract_tags_dict

    corrupted_tags = {
        "Image Model": SimpleNamespace(values=[]),
        "EXIF LensModel": SimpleNamespace(values=[]),
        "EXIF FNumber": SimpleNamespace(values=[Ratio(28, 10)]),
        "EXIF FocalLength": SimpleNamespace(values=[Ratio(35, 1)]),
        "EXIF FocalLengthIn35mmFilm": SimpleNamespace(values=[Ratio(35, 0)]),
        "EXIF ExposureTime": SimpleNamespace(values=[Ratio(1, 125)]),
        "EXIF ISOSpeedRatings": SimpleNamespace(values=[(800,)]),
        "EXIF DateTimeOriginal": SimpleNamespace(values="2026:08:01 09:15:00"),
    }
    parsed = _extract_tags_dict(corrupted_tags)
    assert "camera_model" not in parsed
    assert "lens_model" not in parsed
    assert parsed["f_number"] == 2.8
    assert parsed["focal_length"] == 35.0
    assert "focal_length_35mm" not in parsed
    assert parsed["shutter_speed"] == "1/125"
    assert "iso" not in parsed
    assert parsed["capture_date"] == datetime.datetime(2026, 8, 1, 9, 15, 0)


@pytest.mark.asyncio
async def test_tc_idx_14_async_media_routes_offload_db_and_fs_io(tmp_path, monkeypatch):
    """
    TC-IDX-14 (DEFECT-08): Verifies async media/export endpoints in api.photos
    offload DB queries and filesystem checks to worker threads via asyncio.to_thread,
    preventing FastAPI event-loop freezes, sharing no SQLAlchemy Sessions across threads,
    and preserving 404/422 error contracts.
    """
    import asyncio
    import threading
    import httpx
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    import database
    from main import app
    from repositories.photo_repository import PhotoRepository

    db_file = tmp_path / "wal_media.db"
    wal_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )

    @event.listens_for(wal_engine, "connect")
    def _set_wal(dbapi_conn, _conn_rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.close()

    models.Base.metadata.create_all(bind=wal_engine)
    WalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=wal_engine)

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    subdir_as_file = tmp_path / "not_a_file_dir"
    subdir_as_file.mkdir()

    jpg_cached = photo_dir / "cached.jpg"
    Image.new("RGB", (40, 30), color="green").save(str(jpg_cached), format="JPEG")
    cached_thumb = thumb_dir / "tc14_cached.jpg"
    Image.new("RGB", (20, 15), color="green").save(str(cached_thumb), format="JPEG")

    jpg_uncached = photo_dir / "uncached.jpg"
    Image.new("RGB", (60, 45), color="red").save(str(jpg_uncached), format="JPEG")

    raw_file = photo_dir / "sample.arw"
    raw_file.write_bytes(b"RAW_PLACEHOLDER")

    corrupt_file = photo_dir / "corrupt.jpg"
    corrupt_file.write_bytes(b"not-a-valid-jpeg")

    with WalSessionLocal() as seed_db:
        seed_db.add_all([
            models.Image(
                id="tc14_cached",
                parent_dir=str(photo_dir),
                file_path=str(jpg_cached),
                file_name="cached.jpg",
                file_size=jpg_cached.stat().st_size,
                file_mtime=time.time(),
                mime_type="image/jpeg",
                is_favorite=False,
            ),
            models.Image(
                id="tc14_uncached",
                parent_dir=str(photo_dir),
                file_path=str(jpg_uncached),
                file_name="uncached.jpg",
                file_size=jpg_uncached.stat().st_size,
                file_mtime=time.time(),
                mime_type="image/jpeg",
                is_favorite=False,
            ),
            models.Image(
                id="tc14_raw",
                parent_dir=str(photo_dir),
                file_path=str(raw_file),
                file_name="sample.arw",
                file_size=raw_file.stat().st_size,
                file_mtime=time.time(),
                mime_type="image/x-sony-arw",
                is_favorite=False,
            ),
            models.Image(
                id="tc14_corrupt",
                parent_dir=str(photo_dir),
                file_path=str(corrupt_file),
                file_name="corrupt.jpg",
                file_size=corrupt_file.stat().st_size,
                file_mtime=time.time(),
                mime_type="image/jpeg",
                is_favorite=False,
            ),
            models.Image(
                id="tc14_dir_path",
                parent_dir=str(tmp_path),
                file_path=str(subdir_as_file),
                file_name="not_a_file_dir",
                file_size=0,
                file_mtime=time.time(),
                mime_type="image/jpeg",
                is_favorite=False,
            ),
            models.Image(
                id="tc14_missing_disk",
                parent_dir=str(photo_dir),
                file_path=str(photo_dir / "missing.jpg"),
                file_name="missing.jpg",
                file_size=10,
                file_mtime=time.time(),
                mime_type="image/jpeg",
                is_favorite=False,
            ),
        ])
        seed_db.commit()

    loop_thread_id = threading.get_ident()
    session_thread_ids = []

    def tracked_session_factory():
        session_thread_ids.append(threading.get_ident())
        return WalSessionLocal()

    monkeypatch.setattr(database, "SessionLocal", tracked_session_factory)
    monkeypatch.setattr(photo_service, "THUMBNAIL_CACHE_DIR", str(thumb_dir))
    monkeypatch.setattr(photo_service, "generate_and_cache_thumbnail", generate_and_cache_thumbnail)
    monkeypatch.setattr(
        photo_service,
        "decode_raw_to_pil",
        lambda path, min_dimension=None: Image.new("RGB", (64, 48), color="blue"),
    )

    import api.photos as api_photos

    orig_get_by_id = PhotoRepository.get_by_id
    orig_get_by_ids = PhotoRepository.get_by_ids
    orig_stat_regular = api_photos._stat_regular_file_sync
    orig_prepare_export = api_photos._prepare_export_items_sync
    fs_thread_ids = []

    def slow_get_by_id(self, photo_id):
        assert threading.get_ident() != loop_thread_id, "DB get_by_id ran on event loop thread!"
        time.sleep(0.18)
        return orig_get_by_id(self, photo_id)

    def slow_get_by_ids(self, photo_ids):
        assert threading.get_ident() != loop_thread_id, "DB get_by_ids ran on event loop thread!"
        time.sleep(0.18)
        return orig_get_by_ids(self, photo_ids)

    def slow_stat_regular(path):
        tid = threading.get_ident()
        fs_thread_ids.append(tid)
        assert tid != loop_thread_id, "_stat_regular_file_sync ran on event loop thread!"
        time.sleep(0.15)
        return orig_stat_regular(path)

    def wrapped_prepare_export(photo_ids, dest_folder):
        tid = threading.get_ident()
        fs_thread_ids.append(tid)
        assert tid != loop_thread_id, "_prepare_export_items_sync ran on event loop thread!"
        return orig_prepare_export(photo_ids, dest_folder)

    monkeypatch.setattr(PhotoRepository, "get_by_id", slow_get_by_id)
    monkeypatch.setattr(PhotoRepository, "get_by_ids", slow_get_by_ids)
    monkeypatch.setattr(api_photos, "_stat_regular_file_sync", slow_stat_regular)
    monkeypatch.setattr(api_photos, "_prepare_export_items_sync", wrapped_prepare_export)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            max_loop_lag = 0.0
            stop_monitor = False

            async def monitor_event_loop():
                nonlocal max_loop_lag
                while not stop_monitor:
                    tick_start = time.perf_counter()
                    await asyncio.sleep(0.01)
                    lag = (time.perf_counter() - tick_start) - 0.01
                    if lag > max_loop_lag:
                        max_loop_lag = lag

            monitor_task = asyncio.create_task(monitor_event_loop())
            await asyncio.sleep(0.02)

            # Concurrent requests across thumbnail (cached/uncached), original (RAW/non-RAW), export, and health
            (
                thumb_cached_resp,
                thumb_gen_resp,
                orig_jpg_resp,
                orig_raw_resp,
                export_resp,
                health_resp,
            ) = await asyncio.gather(
                async_client.get("/api/photos/tc14_cached/thumbnail"),
                async_client.get("/api/photos/tc14_uncached/thumbnail"),
                async_client.get("/api/photos/tc14_cached/original"),
                async_client.get("/api/photos/tc14_raw/original"),
                async_client.post(
                    "/api/photos/export",
                    json={"photo_ids": ["tc14_cached"], "destination_folder": str(export_dir)},
                ),
                async_client.get("/api/health"),
            )

            stop_monitor = True
            await monitor_task

            assert max_loop_lag < 0.08, f"Event loop froze for {max_loop_lag:.3f}s"
            assert health_resp.status_code == 200
            assert thumb_cached_resp.status_code == 200
            assert thumb_gen_resp.status_code == 200 and thumb_gen_resp.content[:2] == b"\xff\xd8"
            assert (thumb_dir / "tc14_uncached.jpg").exists()
            assert orig_jpg_resp.status_code == 200 and len(orig_jpg_resp.content) == jpg_cached.stat().st_size
            assert orig_raw_resp.status_code == 200 and orig_raw_resp.content[:2] == b"\xff\xd8"
            assert export_resp.status_code == 200
            assert '"exported_count": 1' in export_resp.text
            assert (export_dir / "cached.jpg").exists()
            assert len(session_thread_ids) >= 5
            assert all(tid != loop_thread_id for tid in session_thread_ids)
            assert len(fs_thread_ids) >= 2
            assert all(tid != loop_thread_id for tid in fs_thread_ids)

            # Error contract preservation (404 / 422 / 400 must not degrade into 500)
            corrupt_thumb_resp = await async_client.get("/api/photos/tc14_corrupt/thumbnail")
            assert corrupt_thumb_resp.status_code == 422

            dir_orig_resp = await async_client.get("/api/photos/tc14_dir_path/original")
            assert dir_orig_resp.status_code == 404

            missing_orig_resp = await async_client.get("/api/photos/tc14_missing_disk/original")
            assert missing_orig_resp.status_code == 404

            bad_export_dir_resp = await async_client.post(
                "/api/photos/export",
                json={"photo_ids": ["tc14_cached"], "destination_folder": str(tmp_path / "nonexistent")},
            )
            assert bad_export_dir_resp.status_code == 400

            missing_export_ids_resp = await async_client.post(
                "/api/photos/export",
                json={"photo_ids": ["does_not_exist"], "destination_folder": str(export_dir)},
            )
            assert missing_export_ids_resp.status_code == 404
    finally:
        wal_engine.dispose()


def test_tc_idx_14_decode_semaphore_loop_isolation():
    """
    TC-IDX-14 (DEFECT-08): Verifies get_decode_semaphore() binds per running event loop
    so contended async decodes across sequential event loops do not raise RuntimeError.
    """
    import asyncio
    from api.photos import get_decode_semaphore

    async def run_contended_batch():
        sem = get_decode_semaphore()

        async def worker():
            async with sem:
                await asyncio.sleep(0.01)

        await asyncio.gather(*[worker() for _ in range(5)])
        return sem

    sem_loop_1 = asyncio.run(run_contended_batch())
    sem_loop_2 = asyncio.run(run_contended_batch())
    assert sem_loop_1 is not sem_loop_2


def test_tc_idx_14_conftest_sessionlocal_compatibility(client, db_session, tmp_path, monkeypatch):
    """
    TC-IDX-14 (DEFECT-08): Verifies thumbnail, original, and export endpoints work
    with conftest's default database.SessionLocal monkeypatch (TestingSessionLocal).
    """
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    photo_file = photo_dir / "sample.jpg"
    Image.new("RGB", (30, 30), color="navy").save(str(photo_file), format="JPEG")
    monkeypatch.setattr(photo_service, "THUMBNAIL_CACHE_DIR", str(thumb_dir))
    monkeypatch.setattr(photo_service, "generate_and_cache_thumbnail", generate_and_cache_thumbnail)

    db_session.add(
        models.Image(
            id="tc14_conftest_1",
            parent_dir=str(photo_dir),
            file_path=str(photo_file),
            file_name="sample.jpg",
            file_size=photo_file.stat().st_size,
            file_mtime=time.time(),
            mime_type="image/jpeg",
            is_favorite=False,
        )
    )
    db_session.commit()

    thumb_resp = client.get("/api/photos/tc14_conftest_1/thumbnail")
    assert thumb_resp.status_code == 200
    assert thumb_resp.content[:2] == b"\xff\xd8"

    orig_resp = client.get("/api/photos/tc14_conftest_1/original")
    assert orig_resp.status_code == 200
    assert len(orig_resp.content) == photo_file.stat().st_size

    export_resp = client.post(
        "/api/photos/export",
        json={"photo_ids": ["tc14_conftest_1"], "destination_folder": str(export_dir)},
    )
    assert export_resp.status_code == 200
    assert '"exported_count": 1' in export_resp.text
    assert (export_dir / "sample.jpg").exists()


def test_tc_idx_15_cross_thread_loop_binding_and_wake_after_sync_start():
    """
    TC-IDX-15 (DEFECT-09): Verifies that starting indexing from a sync worker thread
    (no running event loop) does not permanently pin _pause_loop to None, binds cleanly
    to the async loop, and wakes paused waiters promptly via call_soon_threadsafe.
    """
    import asyncio
    import threading
    from services.indexing_state import IndexingStateManager

    manager = IndexingStateManager()

    # 1. Simulate FastAPI sync route calling try_start_indexing() in an AnyIO worker thread
    start_results = []
    start_thread = threading.Thread(target=lambda: start_results.append(manager.try_start_indexing()))
    start_thread.start()
    start_thread.join(timeout=2.0)
    assert start_results == [True]
    run_id = manager.current_run_id

    async def run_async_waiter():
        loop = asyncio.get_running_loop()
        orig_call_soon_threadsafe = loop.call_soon_threadsafe
        threadsafe_calls = []

        def spy_call_soon_threadsafe(callback, *args, **kwargs):
            threadsafe_calls.append(callback)
            return orig_call_soon_threadsafe(callback, *args, **kwargs)

        loop.call_soon_threadsafe = spy_call_soon_threadsafe

        active_id = manager.initialize_background_run(run_id=run_id)
        assert active_id == run_id
        assert manager._pause_loop is loop

        assert manager.pause() is True
        assert manager.pause_event.is_set() is False

        resume_done = threading.Event()

        def bg_resume():
            threading.Event().wait(0.05)
            manager.resume()
            resume_done.set()

        t_resume = threading.Thread(target=bg_resume)
        t_resume.start()
        await asyncio.wait_for(manager.pause_event.wait(), timeout=0.5)
        t_resume.join(timeout=2.0)
        assert resume_done.is_set()
        assert len(threadsafe_calls) >= 1

        # Also verify cross-thread cancel() wakes wait_if_paused() via call_soon_threadsafe
        assert manager.pause() is True
        cst_before_cancel = len(threadsafe_calls)

        def bg_cancel():
            threading.Event().wait(0.05)
            manager.cancel()

        t_cancel = threading.Thread(target=bg_cancel)
        t_cancel.start()
        should_continue = await asyncio.wait_for(manager.wait_if_paused(run_id), timeout=0.5)
        t_cancel.join(timeout=2.0)
        assert should_continue is False
        assert manager.status == "cancelled"
        assert len(threadsafe_calls) > cst_before_cancel

    asyncio.run(run_async_waiter())


def test_tc_idx_15_cross_loop_and_rapid_sequence_isolation():
    """
    TC-IDX-15 (DEFECT-09): Verifies multi-loop safety:
    1. Another event loop calling resume() / cancel() wakes waiters on loop_1 without orphaning.
    2. Rapid cancel() -> try_start_indexing() -> pause() never swallows Run 1 wakeup pulse.
    3. Sequential closed loops and custom asyncio.Event setter transitions never raise RuntimeError.
    """
    import asyncio
    import threading
    from services.indexing_state import IndexingStateManager

    manager = IndexingStateManager()

    # Part 1: loop_1 paused while loop_2 calls resume()
    async def run_cross_loop_resume():
        assert manager.try_start_indexing() is True
        assert manager.pause() is True

        def second_loop_resume():
            threading.Event().wait(0.05)
            async def invoke_resume():
                assert manager.resume() is True
            asyncio.run(invoke_resume())

        t = threading.Thread(target=second_loop_resume)
        t.start()
        await asyncio.wait_for(manager.pause_event.wait(), timeout=0.5)
        t.join(timeout=2.0)
        assert manager.status == "processing"

    asyncio.run(run_cross_loop_resume())

    # Part 2: Rapid cancel() -> try_start_indexing() -> pause() while Run 1 is waiting
    manager.reset_status()

    async def run_rapid_cancel_restart_pause():
        assert manager.try_start_indexing() is True
        run1 = manager.current_run_id
        assert manager.pause() is True

        def rapid_sequence():
            threading.Event().wait(0.05)
            assert manager.cancel() is True
            assert manager.try_start_indexing() is True
            assert manager.pause() is True

        t = threading.Thread(target=rapid_sequence)
        t.start()
        run1_ok = await asyncio.wait_for(manager.wait_if_paused(run1), timeout=0.5)
        t.join(timeout=2.0)
        assert run1_ok is False
        assert manager.status == "paused"
        assert manager.pause_event.is_set() is False

    asyncio.run(run_rapid_cancel_restart_pause())

    # Part 3: Closed loop custom event recovery & sequential loops
    async def bind_custom_event_on_closed_loop():
        custom = asyncio.Event()
        custom.clear()
        manager.pause_event = custom
        task = asyncio.create_task(manager.pause_event.wait())
        await asyncio.sleep(0.01)
        assert manager.resume() is True
        await asyncio.wait_for(task, timeout=0.5)
        assert manager.cancel() is True

    manager.reset_status()
    manager.status = "paused"
    asyncio.run(bind_custom_event_on_closed_loop())

    # Next loop must auto-recover from closed-loop custom event without reset_status()
    async def next_loop_after_close():
        assert manager.try_start_indexing() is True
        assert manager.pause() is True
        assert manager.pause_event.is_set() is False

        def bg_resume():
            threading.Event().wait(0.03)
            assert manager.resume() is True

        t = threading.Thread(target=bg_resume)
        t.start()
        await asyncio.wait_for(manager.pause_event.wait(), timeout=0.5)
        t.join(timeout=2.0)
        manager.reset_status()
        assert manager.pause_event.is_set() is True

    asyncio.run(next_loop_after_close())


@pytest.mark.asyncio
async def test_tc_idx_15_pre_pause_before_scan_and_finalize_idle_resets_event(monkeypatch):
    """
    TC-IDX-15 (DEFECT-09): Verifies pre-start pause() halts run_indexing_background
    before directory scanning/zombie cleanup, and finalize_run('idle') restores pause_event.
    """
    import asyncio
    from unittest.mock import MagicMock
    import services.indexing_service as idx_svc
    from services.indexing_state import indexing_state_manager

    indexing_state_manager.reset_status()
    assert indexing_state_manager.try_start_indexing() is True
    run_id = indexing_state_manager.current_run_id

    # Pause BEFORE background task starts
    assert indexing_state_manager.pause() is True
    assert indexing_state_manager.status == "paused"

    scan_mock = MagicMock(return_value=[])
    cleanup_mock = MagicMock()
    monkeypatch.setattr(idx_svc, "scan_directory", scan_mock)
    monkeypatch.setattr(idx_svc, "cleanup_zombie_records", cleanup_mock)

    bg_task = asyncio.create_task(idx_svc.run_indexing_background(["/fake"], run_id=run_id))
    await asyncio.sleep(0.05)

    # Must still be paused BEFORE scan_directory and cleanup_zombie_records
    assert indexing_state_manager.status == "paused"
    assert scan_mock.call_count == 0
    assert cleanup_mock.call_count == 0

    # Resuming lets scan/cleanup complete and finalize cleanly to idle
    assert indexing_state_manager.resume() is True
    await asyncio.wait_for(bg_task, timeout=1.0)
    assert scan_mock.call_count == 1
    assert cleanup_mock.call_count == 1
    assert indexing_state_manager.status == "idle"
    assert indexing_state_manager.pause_event.is_set() is True

    # Even if pause() happens right before finalize_run("idle"), event must reset to set
    assert indexing_state_manager.try_start_indexing() is True
    r2 = indexing_state_manager.current_run_id
    assert indexing_state_manager.pause() is True
    assert indexing_state_manager.finalize_run(run_id=r2) == "idle"
    assert indexing_state_manager.pause_event.is_set() is True

    indexing_state_manager.reset_status()


def test_tc_idx_15_fastapi_sync_start_and_testclient_portal_resume(client, tmp_path, monkeypatch):
    """
    TC-IDX-15 (DEFECT-09): End-to-end FastAPI TestClient verification where
    POST /api/index/start runs in AnyIO worker thread, background loop awaits pause,
    and POST /api/index/resume / cancel from TestClient portal loop wakes it safely.
    """
    import asyncio
    import threading
    import api.indexing as indexing_api
    from services.indexing_state import indexing_state_manager

    indexing_state_manager.reset_status()
    target_dir = tmp_path / "tc15_photos"
    target_dir.mkdir()

    captured_runs = []
    monkeypatch.setattr(
        indexing_api,
        "run_indexing_background",
        lambda paths, run_id=None: captured_runs.append((paths, run_id)),
    )

    start_res = client.post("/api/index/start", json={"folder_paths": [str(target_dir)]})
    assert start_res.status_code == 202
    assert len(captured_runs) == 1
    run_id = captured_runs[0][1]

    pause_res = client.post("/api/index/pause")
    assert pause_res.status_code == 200
    assert indexing_state_manager.status == "paused"

    wait_result = []
    wait_ready = threading.Event()

    def run_bg_loop():
        async def wait_paused():
            wait_ready.set()
            res = await asyncio.wait_for(indexing_state_manager.wait_if_paused(run_id), timeout=1.0)
            wait_result.append(res)

        asyncio.run(wait_paused())

    bg_thread = threading.Thread(target=run_bg_loop)
    bg_thread.start()
    assert wait_ready.wait(timeout=1.0)
    threading.Event().wait(0.05)

    resume_res = client.post("/api/index/resume")
    assert resume_res.status_code == 200
    bg_thread.join(timeout=1.0)
    assert not bg_thread.is_alive()
    assert wait_result == [True]
    assert indexing_state_manager.status == "processing"

    cancel_res = client.post("/api/index/cancel")
    assert cancel_res.status_code == 200
    assert indexing_state_manager.status == "cancelled"
    indexing_state_manager.reset_status()


def _parse_export_sse_events(raw_stream_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for frame in raw_stream_text.strip().split("\n\n"):
        if not frame.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in frame.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_tc_idx_16_export_sse_failure_and_partial_contracts(client, db_session, tmp_path, monkeypatch):
    """
    TC-IDX-16 (DEFECT-10): Verifies POST /api/photos/export SSE contracts across
    total failure, partial disk failure, partial missing DB IDs, deduplication,
    PermissionError copy failure, and full success.
    """
    import shutil

    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    ok_file_1 = photo_dir / "valid_1.jpg"
    ok_file_2 = photo_dir / "valid_2.jpg"
    Image.new("RGB", (24, 24), color="teal").save(str(ok_file_1), format="JPEG")
    Image.new("RGB", (24, 24), color="gold").save(str(ok_file_2), format="JPEG")

    db_session.add_all([
        models.Image(
            id="tc16_ok_1",
            parent_dir=str(photo_dir),
            file_path=str(ok_file_1),
            file_name="valid_1.jpg",
            file_size=ok_file_1.stat().st_size,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc16_ok_2",
            parent_dir=str(photo_dir),
            file_path=str(ok_file_2),
            file_name="valid_2.jpg",
            file_size=ok_file_2.stat().st_size,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc16_missing_1",
            parent_dir=str(photo_dir),
            file_path=str(photo_dir / "missing_1.jpg"),
            file_name="missing_1.jpg",
            file_size=100,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc16_missing_2",
            parent_dir=str(photo_dir),
            file_path=str(photo_dir / "missing_2.jpg"),
            file_name="missing_2.jpg",
            file_size=100,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
    ])
    db_session.commit()

    # 1. All files missing on disk -> status="failed", exported_count=0, failed_count=2
    all_fail_resp = client.post(
        "/api/photos/export",
        json={"photo_ids": ["tc16_missing_1", "tc16_missing_2"], "destination_folder": str(export_dir)},
    )
    assert all_fail_resp.status_code == 200
    all_fail_events = _parse_export_sse_events(all_fail_resp.text)
    all_fail_done = dict(all_fail_events)["done"]
    assert all_fail_done["status"] == "failed"
    assert all_fail_done["exported_count"] == 0
    assert all_fail_done["failed_count"] == 2
    assert all_fail_done["total_count"] == 2
    assert all_fail_done["exported_ids"] == []
    assert all_fail_done["failed_ids"] == ["tc16_missing_1", "tc16_missing_2"]
    assert len(all_fail_done["errors"]) == 2

    # 2. Partial disk failure + duplicate photo_ids -> deduplicated & status="partial"
    partial_disk_resp = client.post(
        "/api/photos/export",
        json={"photo_ids": ["tc16_ok_1", "tc16_ok_1", "tc16_missing_1"], "destination_folder": str(export_dir)},
    )
    assert partial_disk_resp.status_code == 200
    partial_disk_done = dict(_parse_export_sse_events(partial_disk_resp.text))["done"]
    assert partial_disk_done["status"] == "partial"
    assert partial_disk_done["exported_count"] == 1
    assert partial_disk_done["failed_count"] == 1
    assert partial_disk_done["total_count"] == 2
    assert partial_disk_done["exported_ids"] == ["tc16_ok_1"]
    assert partial_disk_done["failed_ids"] == ["tc16_missing_1"]
    assert len(partial_disk_done["errors"]) == 1

    # 3. Partial DB missing ID -> reported as partial failure instead of silent drop
    partial_db_resp = client.post(
        "/api/photos/export",
        json={"photo_ids": ["tc16_ok_2", "tc16_not_in_db"], "destination_folder": str(export_dir)},
    )
    assert partial_db_resp.status_code == 200
    partial_db_done = dict(_parse_export_sse_events(partial_db_resp.text))["done"]
    assert partial_db_done["status"] == "partial"
    assert partial_db_done["exported_count"] == 1
    assert partial_db_done["failed_count"] == 1
    assert partial_db_done["total_count"] == 2
    assert partial_db_done["exported_ids"] == ["tc16_ok_2"]
    assert partial_db_done["failed_ids"] == ["tc16_not_in_db"]
    assert "Photo not found in database: tc16_not_in_db" in partial_db_done["errors"]

    # 4. Copy exception (PermissionError) -> status="failed" with error reason preserved
    def fail_copy(_src, _dst):
        raise PermissionError("read-only destination")

    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(shutil, "copy2", fail_copy)
        perm_fail_resp = client.post(
            "/api/photos/export",
            json={"photo_ids": ["tc16_ok_1"], "destination_folder": str(export_dir)},
        )
        assert perm_fail_resp.status_code == 200
        perm_fail_done = dict(_parse_export_sse_events(perm_fail_resp.text))["done"]
        assert perm_fail_done["status"] == "failed"
        assert perm_fail_done["exported_count"] == 0
        assert perm_fail_done["failed_count"] == 1
        assert perm_fail_done["failed_ids"] == ["tc16_ok_1"]
        assert "read-only destination" in perm_fail_done["errors"][0]

    # 5. Clean full success contract preserved
    success_resp = client.post(
        "/api/photos/export",
        json={"photo_ids": ["tc16_ok_1"], "destination_folder": str(export_dir)},
    )
    assert success_resp.status_code == 200
    success_done = dict(_parse_export_sse_events(success_resp.text))["done"]
    assert success_done["status"] == "success"
    assert success_done["exported_count"] == 1
    assert success_done["failed_count"] == 0
    assert success_done["total_count"] == 1
    assert success_done["exported_ids"] == ["tc16_ok_1"]
    assert success_done["failed_ids"] == []
    assert success_done["errors"] is None


@pytest.mark.asyncio
async def test_tc_idx_16_export_stream_unexpected_error_emits_error_event(monkeypatch):
    """
    TC-IDX-16 (DEFECT-10): Verifies unexpected stream exceptions inside _stream_export_events
    emit a structured `event: error` SSE frame instead of silently dropping the stream.
    """
    import api.photos as api_photos

    async def broken_process_item(_item, _dest_folder):
        raise RuntimeError("unexpected disk controller failure")

    monkeypatch.setattr(api_photos, "_process_single_export_item", broken_process_item)

    chunks: list[str] = []
    async for chunk in api_photos._stream_export_events(
        [{"id": "p1", "file_path": "/tmp/a.jpg", "file_name": "a.jpg"}],
        "/tmp",
    ):
        chunks.append(chunk.decode("utf-8"))

    events = _parse_export_sse_events("".join(chunks))
    event_names = [name for name, _payload in events]
    assert "error" in event_names
    error_payload = dict(events)["error"]
    assert "unexpected disk controller failure" in error_payload["detail"]


def test_start_indexing_empty_payload(client):
    """
    Verifies /api/index/start returns 400 Bad Request if folder_paths is empty.
    """
    resp = client.post("/api/index/start", json={"folder_paths": []})
    assert resp.status_code == 400
    assert "No folder paths" in resp.json()["detail"]


def test_scan_directory_deduplication(tmp_path):
    """
    Verifies scan_directory does not produce duplicate files when given duplicate paths.
    """
    from services.indexing_service import scan_directory

    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    sample_img = sub_dir / "photo.jpg"
    sample_img.write_bytes(b"content")

    # Pass root and subfolder simultaneously
    scanned = scan_directory([str(tmp_path), str(sub_dir)])
    assert len(scanned) == 1
    assert str(sample_img) in scanned


def test_delete_photo_atomic_sync(db_session, tmp_path, monkeypatch):
    """
    Verifies delete_photo_atomic_sync cleans SQLite, ChromaDB, and disk thumbnail.
    """
    from services.indexing_service import delete_photo_atomic_sync
    import services.indexing_service as idx_svc

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    pid = "delete_test_photo_1"
    # Create fake thumbnail
    fake_thumb = thumb_dir / f"{pid}.jpg"
    fake_thumb.write_bytes(b"thumbnail_bytes")

    img = models.Image(
        id=pid,
        parent_dir="/test",
        file_path="/test/photo1.jpg",
        file_name="photo1.jpg",
        file_size=1000,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add(img)
    db_session.commit()

    delete_photo_atomic_sync(db_session, pid)

    # SQLite record must be gone
    assert db_session.query(models.Image).filter(models.Image.id == pid).first() is None
    # Thumbnail file must be deleted from disk
    assert not fake_thumb.exists()


def test_remove_folder_data(db_session, tmp_path, monkeypatch):
    """
    Verifies remove_folder_data deletes all contained images, thumbnails, and IndexedFolder records.
    """
    from services.indexing_service import remove_folder_data
    import services.indexing_service as idx_svc

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    folder_a = str(tmp_path / "FolderA")
    folder_a_sub = str(tmp_path / "FolderA" / "Sub")

    f1 = models.IndexedFolder(path=folder_a)
    f2 = models.IndexedFolder(path=folder_a_sub)
    img1 = models.Image(
        id="folder_test_1",
        parent_dir=folder_a,
        file_path=os.path.join(folder_a, "p1.jpg"),
        file_name="p1.jpg",
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )
    img2 = models.Image(
        id="folder_test_2",
        parent_dir=folder_a_sub,
        file_path=os.path.join(folder_a_sub, "p2.jpg"),
        file_name="p2.jpg",
        file_size=100,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )
    db_session.add_all([f1, f2, img1, img2])
    db_session.commit()

    # Fake thumbnails
    (thumb_dir / "folder_test_1.jpg").write_bytes(b"t1")
    (thumb_dir / "folder_test_2.jpg").write_bytes(b"t2")

    remove_folder_data(folder_a, db=db_session)

    # Both images should be deleted
    assert db_session.query(models.Image).filter(models.Image.id.in_(["folder_test_1", "folder_test_2"])).count() == 0
    # Both IndexedFolder records should be deleted
    assert db_session.query(models.IndexedFolder).count() == 0
    # Thumbnails should be removed
    assert not (thumb_dir / "folder_test_1.jpg").exists()
    assert not (thumb_dir / "folder_test_2.jpg").exists()


def test_cleanup_zombie_records_when_file_deleted(db_session, tmp_path, monkeypatch):
    """
    Verifies cleanup_zombie_records detects physically deleted files and cleans SQLite & thumbnails.
    """
    from services.indexing_service import cleanup_zombie_records
    import services.indexing_service as idx_svc

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    folder = tmp_path / "photos"
    folder.mkdir()
    f_rec = models.IndexedFolder(path=str(folder))

    # Real file that exists
    real_file = folder / "exists.jpg"
    real_file.write_bytes(b"real")
    img_real = models.Image(
        id="zombie_test_real",
        parent_dir=str(folder),
        file_path=str(real_file),
        file_name="exists.jpg",
        file_size=4,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )

    # Missing file (deleted by user on disk)
    missing_file = folder / "deleted.jpg"
    img_deleted = models.Image(
        id="zombie_test_deleted",
        parent_dir=str(folder),
        file_path=str(missing_file),
        file_name="deleted.jpg",
        file_size=4,
        file_mtime=time.time(),
        mime_type="image/jpeg",
        is_favorite=False
    )

    db_session.add_all([f_rec, img_real, img_deleted])
    db_session.commit()

    (thumb_dir / "zombie_test_deleted.jpg").write_bytes(b"thumb_deleted")

    cleanup_zombie_records(db=db_session)

    # Real image survives
    assert db_session.query(models.Image).filter(models.Image.id == "zombie_test_real").first() is not None
    # Deleted image is purged from SQLite
    assert db_session.query(models.Image).filter(models.Image.id == "zombie_test_deleted").first() is None
    # Thumbnail for deleted image is purged from disk
    assert not (thumb_dir / "zombie_test_deleted.jpg").exists()


@pytest.mark.asyncio
async def test_sync_and_zero_file_indexing_lifecycle(client):
    """
    Verifies that running background indexing with 0 files cleanly sets status to idle and emits completion.
    """
    from services.indexing_service import run_indexing_background
    from services.indexing_state import indexing_state_manager

    # 1. Direct background run with empty list
    await run_indexing_background([])
    assert indexing_state_manager.status == "idle"
    status_dict = indexing_state_manager.get_status_dict()
    assert status_dict["status"] == "idle"
    assert status_dict["total_files"] == 0
    assert status_dict["processed_files"] == 0

    # 2. Test /api/index/sync endpoint returns 202 and status returns idle
    resp = client.post("/api/index/sync")
    assert resp.status_code == 202

    status_resp = client.get("/api/index/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ["idle", "processing"]


def test_document_structuring_prompt_and_fallback():
    """
    Verifies that the 2nd-pass document structuring prompt builds correctly,
    includes required editorial instructions, and safely handles fallbacks.
    """
    from services.ai_parser import (
        GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT,
        format_critique_document_structuring_user_prompt
    )
    from services.critique_status import critique_status_manager

    # 1. System prompt contains editorial guidelines
    assert "한 줄 총평" in GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT
    assert "시각적 미학 및 EXIF 광학 진단" in GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT
    assert "구도 및 화질 결함과 왜곡 위치 지적" in GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT
    assert "현장 재촬영 및 보정 실전 기술 조언" in GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT
    assert "이모티콘" in GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT

    # 2. User prompt builder formats draft and EXIF metadata
    test_draft = "1차 비평 초안: 구도가 훌륭하며 빛의 활용이 뛰어남."
    test_meta = {
        "camera_model": "Sony A7M4",
        "lens_model": "FE 35mm F1.4 GM",
        "f_number": 1.4,
        "shutter_speed": "1/500",
        "iso": 100
    }
    user_prompt = format_critique_document_structuring_user_prompt(test_draft, test_meta)
    assert test_draft in user_prompt
    assert "Sony A7M4" in user_prompt
    assert "F1.4" in user_prompt

    # 3. Status manager supports Step 3 progress
    critique_status_manager.update("test_photo_doc", 3, 4, "[Gemma] 리포트 문서 양식 다듬는 중...", 75)
    st = critique_status_manager.get("test_photo_doc")
    assert st["step"] == 3
    assert st["progress"] == 75
    assert "리포트 문서 양식" in st["message"]


def test_tc_idx_17_rejects_unregistered_parent_and_root_paths(client, db_session, tmp_path, monkeypatch):
    """
    TC-IDX-17 (DEFECT-11): Verifies DELETE /api/folders and remove_folder_data reject
    unregistered root, ancestor, subpath, traversal, sibling, empty, and relative paths
    while preserving all registered IndexedFolder records, images, thumbnails, and vectors.
    """
    import unicodedata
    from unittest.mock import patch
    import services.indexing_service as idx_svc
    from services.indexing_state import indexing_state_manager

    indexing_state_manager.reset_status()
    thumb_dir = tmp_path / "thumbs_tc17_reject"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    photos_root = tmp_path / "photos"
    trip_dir = photos_root / "2026" / "trip"
    family_dir = photos_root / "2026" / "family"
    korean_dir_nfc = unicodedata.normalize("NFC", str(tmp_path / "한글보관함" / "여행"))
    trip_dir.mkdir(parents=True)
    family_dir.mkdir(parents=True)
    os.makedirs(korean_dir_nfc, exist_ok=True)

    db_session.add_all([
        models.IndexedFolder(path=str(trip_dir)),
        models.IndexedFolder(path=str(family_dir)),
        models.IndexedFolder(path=korean_dir_nfc),
        models.Image(
            id="tc17_trip_1",
            parent_dir=str(trip_dir),
            file_path=str(trip_dir / "a.jpg"),
            file_name="a.jpg",
            file_size=10,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_family_1",
            parent_dir=str(family_dir),
            file_path=str(family_dir / "b.jpg"),
            file_name="b.jpg",
            file_size=10,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_kor_1",
            parent_dir=korean_dir_nfc,
            file_path=os.path.join(korean_dir_nfc, "kor.jpg"),
            file_name="kor.jpg",
            file_size=10,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
    ])
    db_session.commit()

    for pid in ("tc17_trip_1", "tc17_family_1", "tc17_kor_1"):
        (thumb_dir / f"{pid}.jpg").write_bytes(b"thumb")

    deleted_vectors: list[str] = []
    with patch.object(idx_svc, "vector_repo") as mock_vector:
        mock_vector.delete.side_effect = lambda ids: deleted_vectors.extend(ids)

        for unregistered_path in [
            "/",
            "//",
            str(tmp_path),
            str(photos_root),
            str(photos_root / "2026"),
            str(trip_dir / "sub"),
            str(trip_dir / ".."),
            str(photos_root / "2026" / "trip_other"),
        ]:
            resp = client.delete("/api/folders", params={"path": unregistered_path})
            assert resp.status_code == 404, f"Expected 404 for {unregistered_path}, got {resp.status_code}"

        for invalid_path in ["", "   ", ".", "..", "photos/2026/trip", f"{trip_dir}\x00evil"]:
            resp = client.delete("/api/folders", params={"path": invalid_path})
            assert resp.status_code == 400, f"Expected 400 for {invalid_path!r}, got {resp.status_code}"

        # Defense-in-depth: direct service invocation must also refuse unregistered parents
        with pytest.raises(idx_svc.FolderNotRegisteredError):
            idx_svc.remove_folder_data("/", db=db_session)
        with pytest.raises(idx_svc.FolderNotRegisteredError):
            idx_svc.remove_folder_data(str(photos_root), db=db_session)
        with pytest.raises(ValueError):
            idx_svc.remove_folder_data("   ", db=db_session)

    assert deleted_vectors == []
    assert db_session.query(models.IndexedFolder).count() == 3
    assert db_session.query(models.Image).count() == 3
    for pid in ("tc17_trip_1", "tc17_family_1", "tc17_kor_1"):
        assert (thumb_dir / f"{pid}.jpg").exists()


def test_tc_idx_17_canonical_match_symlink_guards_and_indexing_conflict(client, db_session, tmp_path, monkeypatch):
    """
    TC-IDX-17 (DEFECT-11): Verifies NFC/NFD + trailing-slash exact matching, nested vs
    sibling folder scoping, leaf/file symlink containment, active indexing 409 conflict,
    and ChromaDB failure rollback propagation.
    """
    import unicodedata
    from unittest.mock import patch
    import services.indexing_service as idx_svc
    from services.indexing_state import indexing_state_manager

    indexing_state_manager.reset_status()
    thumb_dir = tmp_path / "thumbs_tc17_ok"
    thumb_dir.mkdir()
    monkeypatch.setattr(idx_svc, "get_thumbnail_path", lambda pid: str(thumb_dir / f"{pid}.jpg"))

    # 1. NFC IndexedFolder vs NFD image + NFD delete query with trailing slash
    kor_nfc = unicodedata.normalize("NFC", str(tmp_path / "여행사진"))
    kor_nfd = unicodedata.normalize("NFD", str(tmp_path / "여행사진"))
    os.makedirs(kor_nfc, exist_ok=True)

    # 2. Nested folders + sibling prefix folder
    parent_dir = tmp_path / "Album"
    child_dir = parent_dir / "Best"
    sibling_dir = tmp_path / "Album_Backup"
    parent_dir.mkdir()
    child_dir.mkdir()
    sibling_dir.mkdir()

    # 3. Symlink escalation guard: Temp replaced by symlink to tmp_path + Protected sibling
    protected_dir = tmp_path / "Protected"
    protected_dir.mkdir()
    temp_link = tmp_path / "TempLink"
    os.symlink(str(tmp_path), str(temp_link))

    # 4. Cross-folder file symlink guard: FolderB/shortcut.jpg -> FolderA/sunset.jpg
    folder_a = tmp_path / "FolderA"
    folder_b = tmp_path / "FolderB"
    folder_a.mkdir()
    folder_b.mkdir()
    sunset_a = folder_a / "sunset.jpg"
    sunset_a.write_bytes(b"a")
    shortcut_b = folder_b / "shortcut.jpg"
    os.symlink(str(sunset_a), str(shortcut_b))

    db_session.add_all([
        models.IndexedFolder(path=kor_nfc),
        models.IndexedFolder(path=str(parent_dir)),
        models.IndexedFolder(path=str(child_dir)),
        models.IndexedFolder(path=str(sibling_dir)),
        models.IndexedFolder(path=str(temp_link)),
        models.IndexedFolder(path=str(protected_dir)),
        models.IndexedFolder(path=str(folder_a)),
        models.IndexedFolder(path=str(folder_b)),
        models.Image(
            id="tc17_kor_nfd",
            parent_dir=kor_nfd,
            file_path=os.path.join(kor_nfd, unicodedata.normalize("NFD", "바다.jpg")),
            file_name="바다.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_parent_img",
            parent_dir=str(parent_dir),
            file_path=str(parent_dir / "p.jpg"),
            file_name="p.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_child_img",
            parent_dir=str(child_dir),
            file_path=str(child_dir / "c.jpg"),
            file_name="c.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_sibling_img",
            parent_dir=str(sibling_dir),
            file_path=str(sibling_dir / "s.jpg"),
            file_name="s.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_protected_img",
            parent_dir=str(protected_dir),
            file_path=str(protected_dir / "keep.jpg"),
            file_name="keep.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_folder_a_img",
            parent_dir=str(folder_a),
            file_path=str(sunset_a),
            file_name="sunset.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
        models.Image(
            id="tc17_folder_b_shortcut",
            parent_dir=str(folder_b),
            file_path=str(shortcut_b),
            file_name="shortcut.jpg",
            file_size=5,
            file_mtime=time.time(),
            mime_type="image/jpeg",
        ),
    ])
    db_session.commit()
    (thumb_dir / "tc17_kor_nfd.jpg").write_bytes(b"tk")

    with patch.object(idx_svc, "vector_repo") as mock_vector:
        # A. NFD query with trailing slash deletes NFC IndexedFolder and NFD image
        resp_kor = client.delete("/api/folders", params={"path": kor_nfd + os.sep})
        assert resp_kor.status_code == 200
        assert db_session.query(models.Image).filter_by(id="tc17_kor_nfd").first() is None
        assert not (thumb_dir / "tc17_kor_nfd.jpg").exists()
        mock_vector.delete.assert_called_with(["tc17_kor_nfd"])

        # B. Deleting registered TempLink (symlink to tmp_path) must NOT delete Protected or others
        resp_sym = client.delete("/api/folders", params={"path": str(temp_link)})
        assert resp_sym.status_code == 200
        assert db_session.query(models.IndexedFolder).filter_by(path=str(protected_dir)).first() is not None
        assert db_session.query(models.Image).filter_by(id="tc17_protected_img").first() is not None

        # C. Deleting registered parent Album deletes Album + Album/Best, preserves Album_Backup
        resp_parent = client.delete("/api/folders", params={"path": str(parent_dir)})
        assert resp_parent.status_code == 200
        assert db_session.query(models.IndexedFolder).filter_by(path=str(child_dir)).first() is None
        assert db_session.query(models.Image).filter_by(id="tc17_parent_img").first() is None
        assert db_session.query(models.Image).filter_by(id="tc17_child_img").first() is None
        assert db_session.query(models.IndexedFolder).filter_by(path=str(sibling_dir)).first() is not None
        assert db_session.query(models.Image).filter_by(id="tc17_sibling_img").first() is not None

        # D. Deleting FolderA must NOT delete FolderB/shortcut.jpg pointing to FolderA/sunset.jpg
        resp_a = client.delete("/api/folders", params={"path": str(folder_a)})
        assert resp_a.status_code == 200
        assert db_session.query(models.Image).filter_by(id="tc17_folder_a_img").first() is None
        assert db_session.query(models.Image).filter_by(id="tc17_folder_b_shortcut").first() is not None

        # E. Active indexing returns 409 for registered folder and 404 for unregistered path
        assert indexing_state_manager.try_start_indexing() is True
        try:
            assert client.delete("/api/folders", params={"path": "/"}).status_code == 404
            conflict_resp = client.delete("/api/folders", params={"path": str(folder_b)})
            assert conflict_resp.status_code == 409
            assert db_session.query(models.IndexedFolder).filter_by(path=str(folder_b)).first() is not None
        finally:
            indexing_state_manager.reset_status()

        # F. ChromaDB failure rolls back SQLite and returns 500 instead of false 200
        mock_vector.delete.side_effect = RuntimeError("Chroma delete failure")
        err_resp = client.delete("/api/folders", params={"path": str(folder_b)})
        assert err_resp.status_code == 500
        assert db_session.query(models.IndexedFolder).filter_by(path=str(folder_b)).first() is not None
        assert db_session.query(models.Image).filter_by(id="tc17_folder_b_shortcut").first() is not None


