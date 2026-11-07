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


