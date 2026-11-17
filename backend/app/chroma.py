import datetime
import logging
import os
import shutil
import threading
from typing import Any, Optional

from config import CHROMA_DIR

logger = logging.getLogger("focal_node.chroma")

CHROMA_DB_PATH = CHROMA_DIR

_chroma_client = None
_collection = None
_init_lock = threading.RLock()


def _resolve_system_identifiers(chroma_path: str, client: Any = None) -> list[str]:
    """Computes SharedSystemClient cache keys matching the given Chroma persistence path."""
    identifiers: list[str] = []
    try:
        from chromadb.api.shared_system_client import SharedSystemClient
        from chromadb.config import Settings

        settings = Settings(persist_directory=str(chroma_path), is_persistent=True)
        computed_id = SharedSystemClient._get_identifier_from_settings(settings)
        if computed_id:
            identifiers.append(computed_id)
    except Exception as exc:
        logger.debug("[ChromaDB] Fallback identifier resolution for %s: %s", chroma_path, exc)
        identifiers.append(str(chroma_path))

    client_identifier = getattr(client, "_identifier", None)
    if isinstance(client_identifier, str) and client_identifier and client_identifier not in identifiers:
        identifiers.append(client_identifier)
    return identifiers


def _evict_shared_system_cache(chroma_path: str, client: Any = None) -> None:
    """Removes only the targeted path's System from SharedSystemClient cache before moving DB files."""
    try:
        from chromadb.api.shared_system_client import SharedSystemClient
    except Exception as exc:
        logger.debug("[ChromaDB] Unable to import SharedSystemClient for cache eviction: %s", exc)
        return

    identifiers = _resolve_system_identifiers(chroma_path, client=client)
    stale_systems: list[Any] = []
    with SharedSystemClient._refcount_lock:
        for identifier in identifiers:
            stale_system = SharedSystemClient._identifier_to_system.pop(identifier, None)
            SharedSystemClient._identifier_to_refcount.pop(identifier, None)
            if stale_system is not None:
                stale_systems.append(stale_system)

    # Stop evicted Systems outside _refcount_lock and ignore partial-init AttributeError: bindings.
    for stale_system in stale_systems:
        try:
            stale_system.stop()
        except Exception as stop_err:
            logger.debug("[ChromaDB] Ignored error stopping evicted System: %s", stop_err)


def _backup_corrupted_chroma_dir(chroma_path: str) -> None:
    """Moves a corrupted ChromaDB directory aside with microsecond timestamp uniqueness."""
    if not os.path.exists(chroma_path):
        return
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S_%f")
    backup_path = f"{chroma_path}_corrupted_{timestamp}"
    shutil.move(chroma_path, backup_path)
    print(f"[ChromaDB] Moved corrupted DB to {backup_path}", flush=True)


def _heal_chroma_client_locked(chromadb_mod: Any, original_err: Exception, stale_client: Any = None) -> Any:
    """Evicts cached System state, backs up corrupted storage, and re-creates PersistentClient."""
    global _chroma_client, _collection
    print(f"[ChromaDB] Initialization failed: {original_err}. Attempting self-healing...", flush=True)
    _collection = None
    _chroma_client = None
    _evict_shared_system_cache(CHROMA_DB_PATH, client=stale_client)
    _backup_corrupted_chroma_dir(CHROMA_DB_PATH)

    try:
        _chroma_client = chromadb_mod.PersistentClient(path=CHROMA_DB_PATH)
        return _chroma_client
    except Exception as nested_err:
        _evict_shared_system_cache(CHROMA_DB_PATH)
        print(f"[ChromaDB] Fatal: Self-healing failed: {nested_err}", flush=True)
        raise nested_err


def _init_client_with_heal_flag_locked() -> tuple[Any, bool]:
    """Initializes _chroma_client under _init_lock and reports whether self-healing ran."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client, False

    import chromadb

    try:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        return _chroma_client, False
    except Exception as init_err:
        healed_client = _heal_chroma_client_locked(chromadb, init_err)
        return healed_client, True


def get_chroma_client():
    """
    Initializes and returns the ChromaDB PersistentClient instance with self-healing.
    Uses lazy import of chromadb to prevent heavy eager import overhead during application startup.
    """
    if _chroma_client is None:
        with _init_lock:
            client, _ = _init_client_with_heal_flag_locked()
            return client
    return _chroma_client


# Alias for backwards compatibility
_init_chroma_client = get_chroma_client


def _can_self_heal_collection_error(client: Any, already_healed: bool) -> bool:
    """Prevents double backup or touching disk when client is mocked in tests."""
    if already_healed:
        return False
    return isinstance(getattr(client, "_identifier", None), str)


def get_chroma_collection():
    """
    Returns the initialized ChromaDB collection. Lazy loaded with self-healing.
    """
    global _collection
    if _collection is not None:
        return _collection

    with _init_lock:
        if _collection is not None:
            return _collection
        client, already_healed = _init_client_with_heal_flag_locked()
        try:
            _collection = client.get_or_create_collection(
                name="photo_embeddings",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as col_err:
            if not _can_self_heal_collection_error(client, already_healed):
                raise
            import chromadb

            healed_client = _heal_chroma_client_locked(chromadb, col_err, stale_client=client)
            _collection = healed_client.get_or_create_collection(
                name="photo_embeddings",
                metadata={"hnsw:space": "cosine"},
            )
    return _collection
