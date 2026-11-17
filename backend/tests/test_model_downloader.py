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


def test_start_background_model_downloader_prevents_duplicate_threads_when_alive(monkeypatch):
    """TC-CF-05 / DEFECT-04: start_background_model_downloader(force=True) must not spawn a new thread when already alive."""
    import threading
    import services.model_downloader as md

    # Reset downloader thread state
    with md._downloader_lock:
        md._downloader_thread = None

    stop_event = threading.Event()
    started_event = threading.Event()

    def mock_download():
        started_event.set()
        stop_event.wait(timeout=5)
        return True

    monkeypatch.setattr(md, "download_models_background", mock_download)

    try:
        # 1. First start should succeed
        first_started = md.start_background_model_downloader(force=False)
        assert first_started is True
        assert started_event.wait(timeout=2) is True
        initial_thread = md._downloader_thread
        assert initial_thread is not None
        assert initial_thread.is_alive() is True

        # 2. While initial thread is alive, calling with force=True MUST NOT start a new thread
        second_started = md.start_background_model_downloader(force=True)
        assert second_started is False
        assert md._downloader_thread is initial_thread

        # 3. API endpoint POST /api/system/models/download should also return started=False
        response = client.post("/api/system/models/download")
        assert response.status_code == 200
        assert response.json()["started"] is False
        assert md._downloader_thread is initial_thread

        # 4. Wait for initial thread to terminate
        stop_event.set()
        initial_thread.join(timeout=3)
        assert initial_thread.is_alive() is False

        # 5. When thread is stopped, force=False returns False
        retry_passive = md.start_background_model_downloader(force=False)
        assert retry_passive is False

        # 6. When thread is stopped, force=True successfully restarts a new thread
        stop_event.clear()
        started_event.clear()
        retry_forced = md.start_background_model_downloader(force=True)
        assert retry_forced is True
        assert started_event.wait(timeout=2) is True
        new_thread = md._downloader_thread
        assert new_thread is not initial_thread
        assert new_thread.is_alive() is True
    finally:
        stop_event.set()
        if md._downloader_thread is not None:
            md._downloader_thread.join(timeout=3)
        with md._downloader_lock:
            md._downloader_thread = None


def test_tc_cf_07_is_snapshot_weights_valid_rejects_partial_non_weight_and_unindexed_shards(tmp_path, monkeypatch):
    """TC-CF-07 / DEFECT-06: Reject >5MB non-weight files (tokenizer.json) and unindexed shards while accepting valid single/nested/sharded weights."""
    from services.model_downloader import (
        is_snapshot_weights_valid,
        _is_model_cached,
        get_model_download_tracker,
    )

    payload_6mb = b"x" * (6 * 1024 * 1024)
    payload_2mb = b"w" * (2 * 1024 * 1024)

    # 1. Partial snapshot with config.json + 6MB tokenizer.json + ignored format >5MB (no weight file)
    partial_tok_dir = tmp_path / "partial_tokenizer_only"
    partial_tok_dir.mkdir()
    (partial_tok_dir / "config.json").write_text('{"model_type": "siglip"}')
    (partial_tok_dir / "tokenizer.json").write_bytes(payload_6mb)
    (partial_tok_dir / "model.onnx").write_bytes(payload_6mb)
    assert is_snapshot_weights_valid(str(partial_tok_dir)) is False

    # _is_model_cached must also return False and leave status as pending (not "cached")
    tracker = get_model_download_tracker()
    tracker.reset_statuses()
    monkeypatch.setattr("services.model_downloader.download_hf_smart", lambda *args, **kwargs: str(partial_tok_dir))
    assert _is_model_cached("google/siglip2-base-patch16-224", "SigLIP 2", [], tracker) is False
    assert tracker.get_all_statuses()["google/siglip2-base-patch16-224"]["status"] == "pending"

    # 2. Partial sharded snapshot without index.json
    unindexed_safetensors_dir = tmp_path / "unindexed_safetensors"
    unindexed_safetensors_dir.mkdir()
    (unindexed_safetensors_dir / "config.json").write_text("{}")
    (unindexed_safetensors_dir / "model-00001-of-00003.safetensors").write_bytes(payload_2mb)
    assert is_snapshot_weights_valid(str(unindexed_safetensors_dir)) is False

    unindexed_bin_dir = tmp_path / "unindexed_bin"
    unindexed_bin_dir.mkdir()
    (unindexed_bin_dir / "pytorch_model-00001-of-00002.bin").write_bytes(payload_2mb)
    assert is_snapshot_weights_valid(str(unindexed_bin_dir)) is False

    # 3. Valid single-file weight formats (.safetensors, .bin, .npz) with large tokenizer.json
    for idx, filename in enumerate(["model.safetensors", "pytorch_model.bin", "weights.npz"]):
        valid_single = tmp_path / f"valid_single_{idx}"
        valid_single.mkdir()
        (valid_single / "tokenizer.json").write_bytes(payload_6mb)
        (valid_single / filename).write_bytes(payload_2mb)
        assert is_snapshot_weights_valid(str(valid_single)) is True

    # 4. Valid nested safetensors model
    nested_dir = tmp_path / "valid_nested"
    (nested_dir / "optiq").mkdir(parents=True)
    (nested_dir / "optiq" / "optiq_vision.safetensors").write_bytes(payload_2mb)
    assert is_snapshot_weights_valid(str(nested_dir)) is True

    # 5. Valid sharded model with index.json
    sharded_dir = tmp_path / "valid_sharded"
    sharded_dir.mkdir()
    (sharded_dir / "model.safetensors.index.json").write_text(
        '{"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}}'
    )
    (sharded_dir / "model-00001-of-00002.safetensors").write_bytes(payload_2mb)
    (sharded_dir / "model-00002-of-00002.safetensors").write_bytes(payload_2mb)
    assert is_snapshot_weights_valid(str(sharded_dir)) is True


def test_tc_cf_09_corrupted_index_and_shard_recovery_passes_force_download(tmp_path, monkeypatch):
    """TC-CF-09 / DEFECT-08 (1 & 2): Corrupted index.json and <1MB shard must recover via force_download=True without re-downloading valid shards."""
    import services.model_downloader as md

    payload_2mb = b"w" * (2 * 1024 * 1024)

    # Case 1: Corrupted index.json + valid shard1 -> only index.json is force-downloaded
    snap_corrupted_idx = tmp_path / "snap_corrupted_idx"
    snap_corrupted_idx.mkdir()
    (snap_corrupted_idx / "model.safetensors.index.json").write_text("{corrupted_json")
    (snap_corrupted_idx / "model-00001-of-00001.safetensors").write_bytes(payload_2mb)

    calls_idx = []

    def mock_smart_idx(repo_id, filename=None, **kwargs):
        calls_idx.append((filename, dict(kwargs)))
        if filename == "model.safetensors.index.json" and kwargs.get("force_download") is True:
            (snap_corrupted_idx / "model.safetensors.index.json").write_text(
                '{"weight_map": {"layer": "model-00001-of-00001.safetensors"}}'
            )
        return str(snap_corrupted_idx / filename) if filename else str(snap_corrupted_idx)

    monkeypatch.setattr(md, "download_hf_smart", mock_smart_idx)
    tracker = md.get_model_download_tracker()
    tracker.reset_statuses()

    assert md._download_snapshot_and_shards("test/corrupted-idx", "TestIdx", [], tracker) is True
    file_calls_idx = [(fn, kw.get("force_download")) for fn, kw in calls_idx if fn is not None]
    assert file_calls_idx == [("model.safetensors.index.json", True)]

    # Case 2: Valid index.json, valid shard1, <1MB corrupted shard2 -> only shard2 is force-downloaded
    snap_corrupted_shard = tmp_path / "snap_corrupted_shard"
    snap_corrupted_shard.mkdir()
    (snap_corrupted_shard / "model.safetensors.index.json").write_text(
        '{"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "model-00002-of-00002.safetensors"}}'
    )
    (snap_corrupted_shard / "model-00001-of-00002.safetensors").write_bytes(payload_2mb)
    (snap_corrupted_shard / "model-00002-of-00002.safetensors").write_bytes(b"tiny_corrupt")

    calls_shard = []

    def mock_smart_shard(repo_id, filename=None, **kwargs):
        calls_shard.append((filename, dict(kwargs)))
        if filename == "model-00002-of-00002.safetensors" and kwargs.get("force_download") is True:
            (snap_corrupted_shard / "model-00002-of-00002.safetensors").write_bytes(payload_2mb)
        return str(snap_corrupted_shard / filename) if filename else str(snap_corrupted_shard)

    monkeypatch.setattr(md, "download_hf_smart", mock_smart_shard)
    assert md._download_snapshot_and_shards("test/corrupted-shard", "TestShard", [], tracker) is True
    file_calls_shard = [(fn, kw.get("force_download")) for fn, kw in calls_shard if fn is not None]
    assert file_calls_shard == [("model-00002-of-00002.safetensors", True)]


def test_tc_cf_09_single_weight_recovery_and_kwargs_preservation(tmp_path, monkeypatch):
    """TC-CF-09 / DEFECT-08 (3): <1MB single-file weight recovery, _is_model_cached force_download isolation, and hf_transfer fallback kwargs preservation."""
    import sys
    import types
    import services.model_downloader as md

    payload_2mb = b"w" * (2 * 1024 * 1024)

    # 1. Single-file weight model (<1MB corrupted model.safetensors, no index.json)
    snap_single = tmp_path / "snap_single"
    snap_single.mkdir()
    (snap_single / "config.json").write_text("{}")
    (snap_single / "model.safetensors").write_bytes(b"corrupted_small_weight")

    calls_single = []

    def mock_smart_single(repo_id, filename=None, **kwargs):
        calls_single.append((filename, dict(kwargs)))
        if filename == "model.safetensors" and kwargs.get("force_download") is True:
            (snap_single / "model.safetensors").write_bytes(payload_2mb)
        return str(snap_single / filename) if filename else str(snap_single)

    monkeypatch.setattr(md, "download_hf_smart", mock_smart_single)
    tracker = md.get_model_download_tracker()
    tracker.reset_statuses()

    assert md._download_snapshot_and_shards("test/single-weight", "TestSingle", [], tracker) is True
    file_calls_single = [(fn, kw.get("force_download")) for fn, kw in calls_single if fn is not None]
    assert file_calls_single == [("model.safetensors", True)]

    # 2. _is_model_cached must not pass force_download=True alongside local_files_only=True
    cached_calls = []

    def mock_smart_cached(repo_id, filename=None, **kwargs):
        cached_calls.append(dict(kwargs))
        return str(snap_single)

    monkeypatch.setattr(md, "download_hf_smart", mock_smart_cached)
    assert md._is_model_cached("test/single-weight", "TestSingle", [], tracker, force_download=True) is False
    assert all(not (kw.get("local_files_only") and kw.get("force_download")) for kw in cached_calls)

    # 3. download_hf_smart preserves force_download=True during hf_transfer fallback
    monkeypatch.undo()
    hf_calls = []

    def fake_hf_hub_download(repo_id, filename, **kwargs):
        hf_calls.append(dict(kwargs))
        if len(hf_calls) == 1:
            raise RuntimeError("client has been closed")
        return "/tmp/fake"

    monkeypatch.setitem(sys.modules, "hf_transfer", types.ModuleType("hf_transfer"))
    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_hf_hub_download)
    try:
        result = md.download_hf_smart(
            "test/single-weight",
            filename="model.safetensors",
            ignore_patterns=["*.pt"],
            max_workers=8,
            force_download=True,
        )
        assert result == "/tmp/fake"
        assert len(hf_calls) == 2
        assert hf_calls[0]["force_download"] is True
        assert hf_calls[1]["force_download"] is True
        assert "max_workers" not in hf_calls[1]
        assert "ignore_patterns" not in hf_calls[1]
    finally:
        md.os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)


def test_tc_cf_09_real_huggingface_hub_cache_shortcut_bypass(tmp_path, monkeypatch):
    """TC-CF-09 / DEFECT-08 (4): End-to-end verification with real huggingface_hub==1.21.0 snapshot_download & hf_hub_download."""
    import os
    from huggingface_hub import constants
    import services.model_downloader as md

    repo_id = "test/hf-real-probe"
    commit_hash = "a" * 40
    storage = tmp_path / "models--test--hf-real-probe"
    snap_dir = storage / "snapshots" / commit_hash
    blobs_dir = storage / "blobs"
    refs_dir = storage / "refs"
    snap_dir.mkdir(parents=True)
    blobs_dir.mkdir(parents=True)
    refs_dir.mkdir(parents=True)
    (refs_dir / "main").write_text(commit_hash)

    # Seed corrupted index.json symlink and <1MB corrupted shard symlink in HF cache
    idx_blob = blobs_dir / "etag_idx"
    idx_blob.write_bytes(b"{corrupted_json")
    os.symlink(os.path.relpath(idx_blob, snap_dir), snap_dir / "model.safetensors.index.json")

    shard_blob = blobs_dir / "etag_shard1"
    shard_blob.write_bytes(b"tiny")
    os.symlink(os.path.relpath(shard_blob, snap_dir), snap_dir / "model-00001-of-00001.safetensors")

    valid_idx = b'{"weight_map": {"w": "model-00001-of-00001.safetensors"}}'
    valid_shard = b"W" * (2 * 1024 * 1024)

    def fake_meta(**kwargs):
        fn = kwargs["filename"]
        if fn.endswith(".index.json"):
            return ("http://example.com/idx", "etag_idx", commit_hash, len(valid_idx), None, None)
        return ("http://example.com/s1", "etag_shard1", commit_hash, len(valid_shard), None, None)

    def fake_dl_to_tmp(incomplete_path, destination_path, filename, **kwargs):
        payload = valid_idx if filename.endswith(".index.json") else valid_shard
        with open(destination_path, "wb") as fp:
            fp.write(payload)

    class FakeRepoInfo:
        sha = commit_hash
        siblings = [
            type("Sibling", (), {"rfilename": "model.safetensors.index.json"})(),
            type("Sibling", (), {"rfilename": "model-00001-of-00001.safetensors"})(),
        ]

    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr("huggingface_hub._snapshot_download.constants.HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr("huggingface_hub.file_download.constants.HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr("huggingface_hub._snapshot_download.HfApi.repo_info", lambda *a, **kw: FakeRepoInfo())
    monkeypatch.setattr("huggingface_hub.file_download._get_metadata_or_catch_error", fake_meta)
    monkeypatch.setattr("huggingface_hub.file_download._download_to_tmp_and_move", fake_dl_to_tmp)

    tracker = md.get_model_download_tracker()
    tracker.reset_statuses()

    assert md._download_snapshot_and_shards(repo_id, "RealHFProbe", [], tracker) is True
    assert md.is_snapshot_weights_valid(str(snap_dir)) is True
    assert tracker.get_all_statuses()[repo_id]["status"] == "completed"

    # Also verify single-file model (<1MB regular file pointer in snapshots/<sha>/) recovers via real hf_hub_download
    single_repo = "test/hf-single-probe"
    single_storage = tmp_path / "models--test--hf-single-probe"
    single_snap = single_storage / "snapshots" / commit_hash
    single_blobs = single_storage / "blobs"
    single_refs = single_storage / "refs"
    single_snap.mkdir(parents=True)
    single_blobs.mkdir(parents=True)
    single_refs.mkdir(parents=True)
    (single_refs / "main").write_text(commit_hash)
    (single_snap / "model.safetensors").write_bytes(b"corrupted_regular_file")

    class FakeSingleRepoInfo:
        sha = commit_hash
        siblings = [type("Sibling", (), {"rfilename": "model.safetensors"})()]

    monkeypatch.setattr("huggingface_hub._snapshot_download.HfApi.repo_info", lambda *a, **kw: FakeSingleRepoInfo())
    monkeypatch.setattr(
        "huggingface_hub.file_download._get_metadata_or_catch_error",
        lambda **kw: ("http://example.com/model", "etag_single", commit_hash, len(valid_shard), None, None),
    )

    assert md._download_snapshot_and_shards(single_repo, "RealHFSingleProbe", [], tracker) is True
    assert md.is_snapshot_weights_valid(str(single_snap)) is True






