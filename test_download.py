import sys
from huggingface_hub import snapshot_download
import time

def download_with_retry(repo_id, max_retries=1):
    ignore_patterns = ["*.bin", "*.pth", "*.pt", "*.h5", "*.msgpack", "*.onnx", "*.ot"]
    print(f"[Downloader] Downloading {repo_id} (검색 엔진)...", flush=True)
    try:
        snapshot_download(
            repo_id=repo_id,
            ignore_patterns=ignore_patterns,
            max_workers=1
        )
        return True
    except Exception as e:
        print(f"[Downloader] Error: {e}", flush=True)
        return False

download_with_retry("google/siglip2-base-patch16-224")
