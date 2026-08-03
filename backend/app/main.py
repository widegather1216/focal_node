import sys
import os
import multiprocessing

# 1. Must be the absolute first thing in a PyInstaller app to prevent fork bombs 
#    from module-level imports in child processes (e.g. loading MLX models multiple times).
multiprocessing.freeze_support()

# 2. Prevent Rust tokenizers from implicit forking which causes deadlocks/fork bombs on macOS
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from config import METAL_CACHE_DIR
# 3. Ensure Metal shader cache persists across PyInstaller executions to prevent 10s recompilation delay
os.environ["MTL_SHADER_CACHE_DIR"] = METAL_CACHE_DIR

# 4. Ensure MLX C++ engine finds mlx.metallib in PyInstaller frozen package
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(exe_dir, "_internal", "mlx", "lib", "mlx.metallib"),
        os.path.join(exe_dir, "_internal", "mlx.metallib"),
        os.path.join(exe_dir, "mlx.metallib"),
        os.path.join(exe_dir, "..", "Resources", "_internal", "mlx", "lib", "mlx.metallib"),
        os.path.join(exe_dir, "..", "Resources", "binaries", "_internal", "mlx", "lib", "mlx.metallib"),
    ]
    for c in candidates:
        if os.path.exists(c):
            os.environ["MLX_METAL_PATH"] = c
            print(f"[Sidecar] MLX_METAL_PATH set to {c}", flush=True)
            break

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import DB configurations and SQLAlchemy ORM models
from database import engine, Base
import api.photos
import api.indexing
import api.search
import api.folders
import api.chat
import api.analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically generate SQLite schemas if they do not exist
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE images ADD COLUMN is_favorite BOOLEAN DEFAULT 0 NOT NULL"))
    except Exception:
        pass
        
    for col_sql in [
        "ALTER TABLE image_metadata ADD COLUMN focal_length_35mm FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN crop_factor FLOAT",
        "ALTER TABLE image_metadata ADD COLUMN sensor_format VARCHAR(50)",
        "ALTER TABLE ai_analysis ADD COLUMN critique TEXT",
        "ALTER TABLE ai_analysis ADD COLUMN critique_updated_at DATETIME"
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(col_sql))
        except Exception:
            pass
        
    import threading
    import time
    
    def download_with_retry(repo_id, label, max_retries=3, **kwargs):
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        # Ignore massive redundant weight files to prevent OOM and disk space exhaustion
        # This allows downloading all other configs, safetensors, and tokenizers.
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
        download_with_retry("google/gemma-4-E4B-it", "Gemma 4 (비전 분석 엔진)")
        
        # Check local checkpoint folder first for UniPercept
        local_unipercept = os.path.abspath("checkpoints/UniPercept")
        if not (os.path.exists(local_unipercept) and os.path.exists(os.path.join(local_unipercept, "config.json"))):
            # Download UniPercept public mirror seamlessly without tokens
            download_with_retry("widegather/unipercept-mirror", "UniPercept (전문가 비평 엔진)")
            
        print("[Downloader] Completed all model downloads.", flush=True)
        
    # Start the robust download process in a background thread to prevent blocking the API
    threading.Thread(target=download_models_background, daemon=True).start()
        
    yield

app = FastAPI(title="Focal Node Backend API", lifespan=lifespan)

# CORS configurations
origins = [
    "http://localhost",
    "http://localhost:1420",     # Vite dev server
    "tauri://localhost",         # Tauri Mac/Linux custom protocol
    "https://tauri.localhost",   # Tauri Windows custom protocol
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(api.photos.router)
app.include_router(api.indexing.router)
app.include_router(api.search.router)
app.include_router(api.folders.router)
app.include_router(api.chat.router)
app.include_router(api.analytics.router)

# --- Base API Endpoint ---
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# --- Uvicorn Port Dynamic Mapping ---

class CustomServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        port = None
        for server in self.servers:
            if hasattr(server, 'sockets'):
                for socket in server.sockets:
                    port = socket.getsockname()[1]
                    break
            if port:
                break
        if port:
            print(f"[Sidecar] PORT: {port}", flush=True)
        else:
            print("Failed to get port", file=sys.stderr, flush=True)

import time
import threading

def watch_parent():
    while True:
        if os.getppid() == 1:
            print("[Backend] Parent process died. Exiting to prevent zombie process.", flush=True)
            os._exit(0)
        time.sleep(2)

def start_server():
    print("[Sidecar] Starting backend server...", flush=True)
    
    # Start zombie prevention watcher
    threading.Thread(target=watch_parent, daemon=True).start()
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=0,
        log_level="info",
        loop="asyncio"
    )
    server = CustomServer(config)
    server.run()

if __name__ == "__main__":
    start_server()
