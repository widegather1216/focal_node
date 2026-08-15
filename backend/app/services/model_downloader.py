import os
import time
import json
import threading
from typing import Dict, Any, Optional

KNOWN_MODEL_SIZES: Dict[str, int] = {
    "google/siglip2-base-patch16-224": 1539458338,
    "mlx-community/gemma-4-12B-it-8bit": 12748518855,
    "widegather/unipercept-mirror": 24952254453,
}

_size_cache: Dict[str, tuple[float, int]] = {}
_size_cache_lock = threading.Lock()

def get_repo_downloaded_bytes(repo_id: str, ttl: float = 1.5) -> int:
    now = time.time()
    with _size_cache_lock:
        if repo_id in _size_cache:
            ts, cached_val = _size_cache[repo_id]
            if now - ts < ttl:
                return cached_val

    folder_name = "models--" + repo_id.replace("/", "--")
    hub_path = os.path.expanduser(f"~/.cache/huggingface/hub/{folder_name}")
    if not os.path.isdir(hub_path):
        with _size_cache_lock:
            _size_cache[repo_id] = (now, 0)
        return 0
    blobs_path = os.path.join(hub_path, "blobs")
    target_dir = blobs_path if os.path.isdir(blobs_path) else hub_path
    total = 0
    for root, _, files in os.walk(target_dir):
        for f in files:
            f_path = os.path.join(root, f)
            if not os.path.islink(f_path):
                try:
                    total += os.path.getsize(f_path)
                except OSError:
                    pass
    with _size_cache_lock:
        _size_cache[repo_id] = (now, total)
    return total

class ModelDownloadStatusTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelDownloadStatusTracker, cls).__new__(cls)
                cls._instance._statuses: Dict[str, Dict[str, Any]] = {}
            return cls._instance

    def update_status(
        self,
        repo_id: str,
        label: str,
        status: str,
        downloaded_bytes: Optional[int] = None,
        total_bytes: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        with self._lock:
            cur_downloaded = downloaded_bytes if downloaded_bytes is not None else get_repo_downloaded_bytes(repo_id)
            cur_total = total_bytes if total_bytes is not None else KNOWN_MODEL_SIZES.get(repo_id, 10000000000)
            
            if progress is None:
                if status in ("cached", "completed"):
                    progress = 100
                    cur_downloaded = cur_total
                elif cur_total > 0:
                    progress = min(99, int((cur_downloaded / cur_total) * 100))
                else:
                    progress = 0

            self._statuses[repo_id] = {
                "repo_id": repo_id,
                "label": label,
                "status": status,  # "cached", "downloading", "completed", "error"
                "downloaded_bytes": cur_downloaded,
                "total_bytes": cur_total,
                "progress": progress,
                "error_message": error_message,
                "updated_at": time.time()
            }

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            # Refresh live downloaded_bytes and progress for downloading items
            for repo_id, item in self._statuses.items():
                if item.get("status") == "downloading":
                    d_bytes = get_repo_downloaded_bytes(repo_id)
                    t_bytes = item.get("total_bytes") or KNOWN_MODEL_SIZES.get(repo_id, 10000000000)
                    item["downloaded_bytes"] = d_bytes
                    item["total_bytes"] = t_bytes
                    item["progress"] = min(99, int((d_bytes / t_bytes) * 100)) if t_bytes > 0 else 0
            return dict(self._statuses)

def get_model_download_tracker() -> ModelDownloadStatusTracker:
    return ModelDownloadStatusTracker()

def get_missing_sharded_files(snapshot_dir: str) -> list[str]:
    """Returns a list of missing or incomplete sharded weight filenames from model index."""
    if not snapshot_dir or not os.path.isdir(snapshot_dir):
        return []
    index_filenames = ["model.safetensors.index.json", "pytorch_model.bin.index.json"]
    missing = []
    for root, _, files in os.walk(snapshot_dir):
        for idx_file in index_filenames:
            if idx_file in files:
                idx_path = os.path.join(root, idx_file)
                try:
                    with open(idx_path, "r", encoding="utf-8") as f:
                        idx_data = json.load(f)
                    weight_map = idx_data.get("weight_map", {})
                    sharded_files = set(weight_map.values())
                    for s_file in sharded_files:
                        s_path = os.path.join(root, s_file)
                        if not (os.path.exists(s_path) and os.path.getsize(s_path) > 1024 * 1024):
                            missing.append(s_file)
                except Exception as err:
                    print(f"[Downloader] Error parsing index file {idx_path}: {err}", flush=True)
    return missing

def is_snapshot_weights_valid(snapshot_dir: str) -> bool:
    """
    Validates if a snapshot directory contains complete model weight files.
    If an index file (e.g. model.safetensors.index.json or pytorch_model.bin.index.json) exists,
    checks that EVERY sharded weight file referenced in the index is present and >1MB.
    Otherwise, checks that at least one weight file (>1MB or .safetensors/.bin/.npz) exists.
    """
    if not snapshot_dir or not os.path.isdir(snapshot_dir):
        return False

    index_filenames = ["model.safetensors.index.json", "pytorch_model.bin.index.json"]
    for root, _, files in os.walk(snapshot_dir):
        for idx_file in index_filenames:
            if idx_file in files:
                return len(get_missing_sharded_files(snapshot_dir)) == 0

    # Fallback check for single-file models (like SigLIP 2)
    for root, _, files in os.walk(snapshot_dir):
        for f in files:
            f_path = os.path.join(root, f)
            try:
                ext = os.path.splitext(f)[1].lower()
                size = os.path.getsize(f_path)
                if ext in [".safetensors", ".bin", ".npz", ".pth", ".pt"] and size > 1024 * 1024:
                    return True
                if size > 5 * 1024 * 1024:  # Any file larger than 5MB
                    return True
            except OSError:
                pass
    return False

def ensure_nested_safetensors_linked(snapshot_dir: str):
    """Auto-link any subfolder safetensors (e.g. optiq/optiq_vision.safetensors) to top-level."""
    import glob, shutil
    if not snapshot_dir or not os.path.isdir(snapshot_dir):
        return
    sub_safetensors = glob.glob(os.path.join(snapshot_dir, "**", "*.safetensors"), recursive=True)
    for s_path in sub_safetensors:
        rel_dir = os.path.relpath(os.path.dirname(s_path), snapshot_dir)
        if rel_dir != ".":
            dst_name = f"{os.path.basename(os.path.dirname(s_path))}_{os.path.basename(s_path)}"
            top_dst = os.path.join(snapshot_dir, dst_name)
            direct_dst = os.path.join(snapshot_dir, os.path.basename(s_path))
            for dst in [top_dst, direct_dst]:
                if not os.path.exists(dst):
                    try:
                        os.symlink(s_path, dst)
                    except Exception:
                        shutil.copy2(s_path, dst)

def download_hf_smart(repo_id: str, filename: Optional[str] = None, **kwargs):
    """
    Attempts ultra-fast Rust hf_transfer first. If hf_transfer encounters any macOS C-extension
    session error (e.g. 'client has been closed' on partial resumes), seamlessly falls back to
    standard multi-worker Python HTTP streaming without failing.
    """
    from huggingface_hub import snapshot_download, hf_hub_download
    
    try:
        import hf_transfer
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
        use_hf_transfer = True
    except ImportError:
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
        use_hf_transfer = False

    file_kwargs = {k: v for k, v in kwargs.items() if k not in ["max_workers", "ignore_patterns"]}

    try:
        if filename:
            return hf_hub_download(repo_id=repo_id, filename=filename, **file_kwargs)
        else:
            return snapshot_download(repo_id=repo_id, **kwargs)
    except Exception as err:
        err_str = str(err)
        if use_hf_transfer and ("client has been closed" in err_str or "hf_transfer" in err_str or "RuntimeError" in err_str):
            print(f"[Downloader] hf_transfer session conflict detected ({err_str}). Smart fallback to standard Python HTTP download...", flush=True)
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
            if filename:
                return hf_hub_download(repo_id=repo_id, filename=filename, **file_kwargs)
            else:
                return snapshot_download(repo_id=repo_id, **kwargs)
        raise err

def clear_stale_hf_locks(repo_id: str):
    """Cleans up stale file locks in HuggingFace cache directory to prevent filelock deadlock loops."""
    folder_name = "models--" + repo_id.replace("/", "--")
    locks_dir = os.path.expanduser(f"~/.cache/huggingface/hub/.locks/{folder_name}")
    if os.path.isdir(locks_dir):
        for f in os.listdir(locks_dir):
            if f.endswith(".lock"):
                lock_file = os.path.join(locks_dir, f)
                try:
                    os.remove(lock_file)
                    print(f"[Downloader] Removed stale HF lock file: {f}", flush=True)
                except Exception:
                    pass

def download_with_retry(repo_id: str, label: str, max_retries: int = 3, **kwargs) -> bool:
    clear_stale_hf_locks(repo_id)
    tracker = get_model_download_tracker()
    ignore_patterns = ["*.pth", "*.pt", "*.h5", "*.msgpack", "*.onnx", "*.ot"]
    
    # Check if already cached with valid weight files
    try:
        local_path = download_hf_smart(
            repo_id=repo_id,
            local_files_only=True,
            ignore_patterns=ignore_patterns,
            **kwargs
        )
        ensure_nested_safetensors_linked(local_path)
        if is_snapshot_weights_valid(local_path):
            tracker.update_status(repo_id, label, status="cached")
            return True
    except Exception:
        pass
        
    tracker.update_status(repo_id, label, status="downloading")
    print(f"[Downloader] Downloading {label} ({repo_id})...", flush=True)

    try:
        for attempt in range(max_retries):
            try:
                local_path = download_hf_smart(
                    repo_id=repo_id,
                    ignore_patterns=ignore_patterns,
                    max_workers=8,
                    etag_timeout=30,
                    **kwargs
                )
                ensure_nested_safetensors_linked(local_path)

                # Check if HF snapshot_download skipped missing sharded files
                missing_shards = get_missing_sharded_files(local_path)
                if missing_shards:
                    for m_file in missing_shards:
                        print(f"[Downloader] Explicitly downloading missing shard: {m_file} for {repo_id}...", flush=True)
                        download_hf_smart(
                            repo_id=repo_id,
                            filename=m_file,
                            ignore_patterns=ignore_patterns,
                            **kwargs
                        )
                    ensure_nested_safetensors_linked(local_path)

                if is_snapshot_weights_valid(local_path):
                    tracker.update_status(repo_id, label, status="completed")
                    print(f"[Downloader] Successfully downloaded {label}.", flush=True)
                    return True
                else:
                    raise RuntimeError(f"Snapshot weights incomplete for {repo_id}")
            except Exception as e:
                err_str = str(e)
                if "401 Client Error" in err_str or "restricted" in err_str or "gated repo" in err_str:
                    print(f"[Downloader] Note: {repo_id}는 Hugging Face Gated 모델입니다. HF_TOKEN이 설정되거나 로컬 파일이 있을 때 활성화됩니다.", flush=True)
                    tracker.update_status(repo_id, label, status="error", error_message="Gated repository access required")
                    return False
                    
                print(f"[Downloader] Error on attempt {attempt+1} for {repo_id}: {e}", flush=True)
                

                if attempt < max_retries - 1:
                    backoff_delay = 5 * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    print(f"[Downloader] Retrying {repo_id} in {backoff_delay} seconds...", flush=True)
                    time.sleep(backoff_delay)
                else:
                    print(f"[Downloader] Failed to download {repo_id} after {max_retries} attempts.", flush=True)
                    tracker.update_status(repo_id, label, status="error", error_message=str(e))
                    return False
    finally:
        os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)

    return False

def download_models_background():
    download_with_retry("google/siglip2-base-patch16-224", "SigLIP 2 (검색 엔진)")
    download_with_retry("mlx-community/gemma-4-12B-it-8bit", "Gemma 4 (비전 분석 엔진)")
    
    # Check local checkpoint folder first for UniPercept
    local_unipercept = os.path.abspath("checkpoints/UniPercept")
    if not (os.path.exists(local_unipercept) and is_snapshot_weights_valid(local_unipercept)):
        # Download UniPercept public mirror seamlessly without tokens
        download_with_retry("widegather/unipercept-mirror", "UniPercept (전문가 비평 엔진)")
    else:
        tracker = get_model_download_tracker()
        tracker.update_status("widegather/unipercept-mirror", "UniPercept (전문가 비평 엔진)", status="cached")
        
    print("[Downloader] Completed all model downloads.", flush=True)

_downloader_thread: Optional[threading.Thread] = None
_downloader_lock = threading.Lock()

def start_background_model_downloader(force: bool = False) -> bool:
    global _downloader_thread
    with _downloader_lock:
        if force or _downloader_thread is None or not _downloader_thread.is_alive():
            print("[Downloader] Starting background model downloader thread...", flush=True)
            _downloader_thread = threading.Thread(target=download_models_background, daemon=True)
            _downloader_thread.start()
            return True
        return False
