import os
import time
import json
import threading
from typing import Dict, Any, Optional

class ModelDownloadStatusTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelDownloadStatusTracker, cls).__new__(cls)
                cls._instance._statuses: Dict[str, Dict[str, Any]] = {}
            return cls._instance

    def update_status(self, repo_id: str, label: str, status: str, error_message: Optional[str] = None):
        with self._lock:
            self._statuses[repo_id] = {
                "repo_id": repo_id,
                "label": label,
                "status": status,  # "cached", "downloading", "completed", "error"
                "error_message": error_message,
                "updated_at": time.time()
            }

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._statuses)

def get_model_download_tracker() -> ModelDownloadStatusTracker:
    return ModelDownloadStatusTracker()

def is_snapshot_weights_valid(snapshot_dir: str) -> bool:
    """
    Validates if a snapshot directory contains complete model weight files.
    If an index file (e.g. model.safetensors.index.json or pytorch_model.bin.index.json) exists,
    checks that EVERY sharded weight file referenced in the index is present and >1MB.
    Otherwise, checks that at least one weight file (>1MB or .safetensors/.bin/.npz) exists.
    """
    if not snapshot_dir or not os.path.isdir(snapshot_dir):
        return False

    # Check for index files first (for sharded models like Gemma 4, UniPercept)
    index_filenames = ["model.safetensors.index.json", "pytorch_model.bin.index.json"]
    for root, _, files in os.walk(snapshot_dir):
        for idx_file in index_filenames:
            if idx_file in files:
                idx_path = os.path.join(root, idx_file)
                try:
                    with open(idx_path, "r", encoding="utf-8") as f:
                        idx_data = json.load(f)
                    weight_map = idx_data.get("weight_map", {})
                    sharded_files = set(weight_map.values())
                    if sharded_files:
                        for s_file in sharded_files:
                            s_path = os.path.join(root, s_file)
                            if not (os.path.exists(s_path) and os.path.getsize(s_path) > 1024 * 1024):
                                print(f"[Downloader] Sharded weight file missing or incomplete: {s_file}", flush=True)
                                return False
                        return True
                except Exception as err:
                    print(f"[Downloader] Error parsing index file {idx_path}: {err}", flush=True)

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

def download_with_retry(repo_id: str, label: str, max_retries: int = 3, **kwargs) -> bool:
    from huggingface_hub import snapshot_download
    
    tracker = get_model_download_tracker()
    ignore_patterns = ["*.pth", "*.pt", "*.h5", "*.msgpack", "*.onnx", "*.ot"]
    
    # Check if already cached with valid weight files
    try:
        local_path = snapshot_download(
            repo_id=repo_id,
            local_files_only=True,
            ignore_patterns=ignore_patterns,
            **kwargs
        )
        if is_snapshot_weights_valid(local_path):
            tracker.update_status(repo_id, label, status="cached")
            return True
    except Exception:
        pass
        
    tracker.update_status(repo_id, label, status="downloading")
    print(f"[Downloader] Downloading {label} ({repo_id})...", flush=True)

    # Enable hf_transfer if installed for ultra-fast Rust/C++ downloads
    try:
        import hf_transfer
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
        use_hf_transfer = True
    except ImportError:
        use_hf_transfer = False

    for attempt in range(max_retries):
        try:
            snapshot_download(
                repo_id=repo_id,
                ignore_patterns=ignore_patterns,
                max_workers=8,
                etag_timeout=30,
                **kwargs
            )
            tracker.update_status(repo_id, label, status="completed")
            print(f"[Downloader] Successfully downloaded {label}.", flush=True)
            return True
        except Exception as e:
            err_str = str(e)
            if "401 Client Error" in err_str or "restricted" in err_str or "gated repo" in err_str:
                print(f"[Downloader] Note: {repo_id}는 Hugging Face Gated 모델입니다. HF_TOKEN이 설정되거나 로컬 파일이 있을 때 활성화됩니다.", flush=True)
                tracker.update_status(repo_id, label, status="error", error_message="Gated repository access required")
                return False
                
            print(f"[Downloader] Error on attempt {attempt+1} for {repo_id}: {e}", flush=True)
            
            # Fallback: Disable hf_transfer if first attempt failed with hf_transfer enabled
            if use_hf_transfer and "HF_HUB_ENABLE_HF_TRANSFER" in os.environ:
                print(f"[Downloader] Fallback to standard Python download for {repo_id}...", flush=True)
                os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
                use_hf_transfer = False

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
    download_with_retry("mlx-community/gemma-4-26B-A4B-it-qat-OptiQ-4bit", "Gemma 4 (비전 분석 엔진)")
    
    # Check local checkpoint folder first for UniPercept
    local_unipercept = os.path.abspath("checkpoints/UniPercept")
    if not (os.path.exists(local_unipercept) and is_snapshot_weights_valid(local_unipercept)):
        # Download UniPercept public mirror seamlessly without tokens
        download_with_retry("widegather/unipercept-mirror", "UniPercept (전문가 비평 엔진)")
        
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
