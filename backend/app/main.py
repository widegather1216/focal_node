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
from database import run_migrations
from services.model_downloader import start_background_model_downloader
from utils.process import start_parent_watcher

import api.photos
import api.indexing
import api.search
import api.folders
import api.chat
import api.analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Automatically generate SQLite schemas & apply migrations
    run_migrations()
    
    # 2. Start robust model downloader process in a background thread
    start_background_model_downloader()
        
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

# --- Model Download Status & Trigger Endpoints ---
@app.get("/api/system/models/status")
def get_model_download_status():
    from services.model_downloader import get_model_download_tracker, start_background_model_downloader
    tracker = get_model_download_tracker()
    statuses = tracker.get_all_statuses()
    if not statuses:
        start_background_model_downloader()
        statuses = tracker.get_all_statuses()
        
    total_dl = sum(item.get("downloaded_bytes", 0) for item in statuses.values())
    total_sz = sum(item.get("total_bytes", 0) for item in statuses.values())
    overall_progress = min(100, int((total_dl / total_sz) * 100)) if total_sz > 0 else 0
    is_all_done = len(statuses) > 0 and all(item.get("status") in ("completed", "cached") for item in statuses.values())
    
    downloading_item = next((item for item in statuses.values() if item.get("status") == "downloading"), None)
    current_label = downloading_item.get("label", "") if downloading_item else ""

    return {
        "statuses": statuses,
        "overall": {
            "progress": overall_progress,
            "downloaded_bytes": total_dl,
            "total_bytes": total_sz,
            "current_label": current_label,
            "is_all_done": is_all_done
        }
    }

@app.post("/api/system/models/download")
def trigger_model_download():
    from services.model_downloader import start_background_model_downloader, get_model_download_tracker
    started = start_background_model_downloader(force=True)
    tracker = get_model_download_tracker()
    statuses = tracker.get_all_statuses()
    total_dl = sum(item.get("downloaded_bytes", 0) for item in statuses.values())
    total_sz = sum(item.get("total_bytes", 0) for item in statuses.values())
    overall_progress = min(100, int((total_dl / total_sz) * 100)) if total_sz > 0 else 0
    return {
        "started": started,
        "statuses": statuses,
        "overall": {
            "progress": overall_progress,
            "downloaded_bytes": total_dl,
            "total_bytes": total_sz,
            "is_all_done": False
        }
    }

# --- Uvicorn Port Dynamic Mapping ---

class CustomServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        port = None
        servers = getattr(self, 'servers', [])
        for server in servers:
            if hasattr(server, 'sockets'):
                for socket in server.sockets:
                    port = socket.getsockname()[1]
                    break
            if port:
                break
        if not port and sockets:
            for s in sockets:
                port = s.getsockname()[1]
                break
        if port:
            print(f"[Sidecar] PORT: {port}", flush=True)
        else:
            print("Failed to get port", file=sys.stderr, flush=True)


def start_server():
    print("[Sidecar] Starting backend server...", flush=True)
    
    # Start zombie prevention watcher
    start_parent_watcher()
    
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

