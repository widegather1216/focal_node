from fastapi.testclient import TestClient
from main import app
from services.model_downloader import get_model_download_tracker

client = TestClient(app)

def test_model_download_status_tracker():
    tracker = get_model_download_tracker()
    tracker.update_status("test/repo", "Test Model", "downloading")
    
    statuses = tracker.get_all_statuses()
    assert "test/repo" in statuses
    assert statuses["test/repo"]["label"] == "Test Model"
    assert statuses["test/repo"]["status"] == "downloading"

def test_model_download_status_endpoint():
    response = client.get("/api/system/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "statuses" in data

def test_is_snapshot_weights_valid(tmp_path):
    from services.model_downloader import is_snapshot_weights_valid
    
    # Metadata-only directory (small json/md files)
    meta_dir = tmp_path / "meta_only"
    meta_dir.mkdir()
    (meta_dir / "config.json").write_text('{"model_type": "gemma"}')
    (meta_dir / "README.md").write_text("Hello")
    assert is_snapshot_weights_valid(str(meta_dir)) is False

    # Directory with safetensors weight file > 1MB
    weights_dir = tmp_path / "valid_weights"
    weights_dir.mkdir()
    (weights_dir / "config.json").write_text('{"model_type": "gemma"}')
    weight_file = weights_dir / "model.safetensors"
    with open(weight_file, "wb") as f:
        f.write(b"0" * (1024 * 1024 + 100))  # Slightly > 1MB
    assert is_snapshot_weights_valid(str(weights_dir)) is True

    # Sharded model directory with index where one shard is missing
    sharded_dir = tmp_path / "sharded_incomplete"
    sharded_dir.mkdir()
    idx_content = '{"weight_map": {"a": "part1.safetensors", "b": "part2.safetensors"}}'
    (sharded_dir / "model.safetensors.index.json").write_text(idx_content)
    with open(sharded_dir / "part1.safetensors", "wb") as f:
        f.write(b"0" * (1024 * 1024 + 100))
    assert is_snapshot_weights_valid(str(sharded_dir)) is False

    # Sharded model directory with all shards present
    with open(sharded_dir / "part2.safetensors", "wb") as f:
        f.write(b"0" * (1024 * 1024 + 100))
    assert is_snapshot_weights_valid(str(sharded_dir)) is True

def test_is_snapshot_weights_valid_corrupted_index(tmp_path):
    """TC-CF-04: Ensure corrupted or invalid index JSON is treated as invalid and not cached."""
    from services.model_downloader import is_snapshot_weights_valid, get_missing_sharded_files

    # 1. Truncated / malformed JSON index
    corrupted_dir = tmp_path / "corrupted_json"
    corrupted_dir.mkdir()
    (corrupted_dir / "model.safetensors.index.json").write_text('{"weight_map": {"layer1": ')
    missing = get_missing_sharded_files(str(corrupted_dir))
    assert "model.safetensors.index.json" in missing
    assert is_snapshot_weights_valid(str(corrupted_dir)) is False

    # 2. Empty weight_map in index
    empty_map_dir = tmp_path / "empty_weight_map"
    empty_map_dir.mkdir()
    (empty_map_dir / "pytorch_model.bin.index.json").write_text('{"weight_map": {}}')
    missing_empty = get_missing_sharded_files(str(empty_map_dir))
    assert "pytorch_model.bin.index.json" in missing_empty
    assert is_snapshot_weights_valid(str(empty_map_dir)) is False

    # 3. Non-dict index file (e.g. malformed json array)
    array_idx_dir = tmp_path / "array_index"
    array_idx_dir.mkdir()
    (array_idx_dir / "model.safetensors.index.json").write_text('["not", "a", "dict"]')
    missing_array = get_missing_sharded_files(str(array_idx_dir))
    assert "model.safetensors.index.json" in missing_array
    assert is_snapshot_weights_valid(str(array_idx_dir)) is False


def test_download_models_background_failure_suppresses_completed(monkeypatch, capsys):
    """TC-CF-03 / DEFECT-02: Ensure model failure does not emit completed message and returns False."""
    from services.model_downloader import download_models_background

    def mock_download_with_retry(repo_id, label, **kwargs):
        if "siglip" in repo_id:
            return False
        return True

    monkeypatch.setattr("services.model_downloader.download_with_retry", mock_download_with_retry)
    monkeypatch.setattr("os.path.exists", lambda p: False)

    result = download_models_background()
    captured = capsys.readouterr()

    assert result is False
    assert "[Downloader] Completed" not in captured.out
    assert "[Downloader] Download process finished with errors." in captured.out


def test_download_models_background_all_success(monkeypatch, capsys):
    """TC-CF-03 / DEFECT-02: Ensure all success outputs completed message and returns True."""
    from services.model_downloader import download_models_background

    monkeypatch.setattr("services.model_downloader.download_with_retry", lambda repo_id, label, **kwargs: True)
    monkeypatch.setattr("os.path.exists", lambda p: False)

    result = download_models_background()
    captured = capsys.readouterr()

    assert result is True
    assert "[Downloader] Completed all model downloads." in captured.out
    assert "[Downloader] Download process finished with errors." not in captured.out


def test_model_download_status_tracker_initial_pending_state():
    """TC-CF-03 / DEFECT-03: Tracker must pre-register KNOWN_MODEL_SIZES with pending/0%."""
    from services.model_downloader import get_model_download_tracker, KNOWN_MODEL_SIZES

    tracker = get_model_download_tracker()
    tracker.reset_statuses()
    statuses = tracker.get_all_statuses()

    assert len(statuses) >= len(KNOWN_MODEL_SIZES)
    for repo_id, total_bytes in KNOWN_MODEL_SIZES.items():
        assert repo_id in statuses
        assert statuses[repo_id]["status"] == "pending"
        assert statuses[repo_id]["progress"] == 0
        assert statuses[repo_id]["downloaded_bytes"] == 0
        assert statuses[repo_id]["total_bytes"] == total_bytes


def test_calculate_overall_progress_requires_all_known_models():
    """TC-CF-03 / DEFECT-03: _calculate_overall_progress must not return is_all_done=True when only 1 model is cached."""
    from main import _calculate_overall_progress

    # 1. Only 1 model cached out of 3 known models
    partial_statuses = {
        "google/siglip2-base-patch16-224": {
            "status": "cached",
            "downloaded_bytes": 1539458338,
            "total_bytes": 1539458338,
            "progress": 100,
        }
    }
    result_partial = _calculate_overall_progress(partial_statuses)
    assert result_partial["is_all_done"] is False

    # 2. All 3 models present, but 2 are still pending
    mixed_statuses = {
        "google/siglip2-base-patch16-224": {
            "status": "cached",
            "downloaded_bytes": 1539458338,
            "total_bytes": 1539458338,
            "progress": 100,
        },
        "mlx-community/gemma-4-12B-it-8bit": {
            "status": "pending",
            "downloaded_bytes": 0,
            "total_bytes": 12748518855,
            "progress": 0,
        },
        "widegather/unipercept-mirror": {
            "status": "pending",
            "downloaded_bytes": 0,
            "total_bytes": 24952254453,
            "progress": 0,
        },
    }
    result_mixed = _calculate_overall_progress(mixed_statuses)
    assert result_mixed["is_all_done"] is False

    # 3. All 3 models completed or cached
    all_done_statuses = {
        "google/siglip2-base-patch16-224": {
            "status": "cached",
            "downloaded_bytes": 1539458338,
            "total_bytes": 1539458338,
            "progress": 100,
        },
        "mlx-community/gemma-4-12B-it-8bit": {
            "status": "completed",
            "downloaded_bytes": 12748518855,
            "total_bytes": 12748518855,
            "progress": 100,
        },
        "widegather/unipercept-mirror": {
            "status": "cached",
            "downloaded_bytes": 24952254453,
            "total_bytes": 24952254453,
            "progress": 100,
        },
    }
    result_done = _calculate_overall_progress(all_done_statuses)
    assert result_done["is_all_done"] is True



