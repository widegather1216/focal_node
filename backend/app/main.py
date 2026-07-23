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
        
    import threading
    import time
    
    def download_with_retry(repo_id, label, max_retries=3):
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        # Ignore massive redundant weight files (PyTorch/TF/Flax) to prevent OOM and disk space exhaustion
        # This allows downloading all other configs, safetensors, and tokenizers.
        ignore_patterns = ["*.bin", "*.pth", "*.pt", "*.h5", "*.msgpack", "*.onnx", "*.ot"]
        
        # Check if already cached
        try:
            snapshot_download(
                repo_id=repo_id,
                local_files_only=True,
                ignore_patterns=ignore_patterns
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
                    max_workers=1
                )
                return True
            except Exception as e:
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
