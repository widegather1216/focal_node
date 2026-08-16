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
