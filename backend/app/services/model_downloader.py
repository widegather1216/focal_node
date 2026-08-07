import os
import time
import threading

def download_with_retry(repo_id: str, label: str, max_retries: int = 3, **kwargs) -> bool:
    from huggingface_hub import snapshot_download
    
    # Ignore massive redundant weight files to prevent OOM and disk space exhaustion
    ignore_patterns = ["*.pth", "*.pt", "*.h5", "*.msgpack", "*.onnx", "*.ot"]
    
    # Check if already cached
    try:
        snapshot_download(
            repo_id=repo_id,
            local_files_only=True,
            ignore_patterns=ignore_patterns,
            **kwargs
        )
        return True
    except Exception:
        pass
        
    print(f"[Downloader] Downloading {label}...", flush=True)
    for attempt in range(max_retries):
        try:
            snapshot_download(
                repo_id=repo_id,
                ignore_patterns=ignore_patterns,
                max_workers=1,
                **kwargs
            )
            return True
        except Exception as e:
            err_str = str(e)
            if "401 Client Error" in err_str or "restricted" in err_str or "gated repo" in err_str:
                print(f"[Downloader] Note: {repo_id}는 Hugging Face Gated 모델입니다. HF_TOKEN이 설정되거나 checkpoints/UniPercept 폴더에 로컬 파일이 있을 때 활성화됩니다.", flush=True)
                return False
            print(f"[Downloader] Error on attempt {attempt+1} for {repo_id}: {e}", flush=True)
            if attempt < max_retries - 1:
                print(f"[Downloader] Retrying {repo_id} in 5 seconds...", flush=True)
                time.sleep(5)
            else:
                print(f"[Downloader] Failed to download {repo_id} after {max_retries} attempts.", flush=True)
                return False

def download_models_background():
    download_with_retry("google/siglip2-base-patch16-224", "SigLIP 2 (검색 엔진)")
    download_with_retry("mlx-community/gemma-4-26B-A4B-it-qat-OptiQ-4bit", "Gemma 4 (비전 분석 엔진)")
    
    # Check local checkpoint folder first for UniPercept
    local_unipercept = os.path.abspath("checkpoints/UniPercept")
    if not (os.path.exists(local_unipercept) and os.path.exists(os.path.join(local_unipercept, "config.json"))):
        # Download UniPercept public mirror seamlessly without tokens
        download_with_retry("widegather/unipercept-mirror", "UniPercept (전문가 비평 엔진)")
        
    print("[Downloader] Completed all model downloads.", flush=True)

def start_background_model_downloader():
    threading.Thread(target=download_models_background, daemon=True).start()
