import os
import datetime
import shutil
import threading
from config import CHROMA_DIR

CHROMA_DB_PATH = CHROMA_DIR

_chroma_client = None
_collection = None
_init_lock = threading.RLock()

def get_chroma_client():
    """
    Initializes and returns the ChromaDB PersistentClient instance with self-healing.
    Uses lazy import of chromadb to prevent heavy eager import overhead during application startup.
    """
    global _chroma_client
    if _chroma_client is None:
        with _init_lock:
            if _chroma_client is None:
                import chromadb
                try:
                    _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                except Exception as e:
                    print(f"[ChromaDB] Initialization failed: {e}. Attempting self-healing...", flush=True)
                    # Backup corrupted folder
                    if os.path.exists(CHROMA_DB_PATH):
                        backup_path = f"{CHROMA_DB_PATH}_corrupted_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                        shutil.move(CHROMA_DB_PATH, backup_path)
                        print(f"[ChromaDB] Moved corrupted DB to {backup_path}", flush=True)
                    # Try again
                    try:
                        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                    except Exception as nested_e:
                        print(f"[ChromaDB] Fatal: Self-healing failed: {nested_e}", flush=True)
                        raise nested_e
    return _chroma_client

# Alias for backwards compatibility
_init_chroma_client = get_chroma_client

def get_chroma_collection():
    """
    Returns the initialized ChromaDB collection. Lazy loaded with self-healing.
    """
    global _collection
    if _collection is None:
        with _init_lock:
            if _collection is None:
                client = get_chroma_client()
                _collection = client.get_or_create_collection(
                    name="photo_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )
    return _collection
