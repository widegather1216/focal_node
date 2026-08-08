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

