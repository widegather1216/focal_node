"""
Facade module for indexing service functions, delegating to modular components inside `services.indexer`.
Maintains 100% backward compatibility for all importers.
"""

from database import SessionLocal
from services.indexer.scanner import (
    SUPPORTED_EXTENSIONS,
    calculate_sha256,
    scan_directory,
)

from services.indexer.status import (
    indexing_status,
    pause_event,
    cancel_requested,
    pause_indexing,
    resume_indexing,
    cancel_indexing,
)

from services.indexer.cleaner import (
    delete_photo_atomic_sync,
    cleanup_zombie_records,
    remove_folder_data,
)
from services.indexer.worker import (
    run_ai_pipeline_sync,
    index_single_file_sync,
    reindex_single_photo_inplace,
    run_indexing_background,
)

# AI factory helpers re-exposed for compatibility
from services.ai_factory import get_siglip_adapter, get_gemma_adapter

__all__ = [
    "SessionLocal",
    "SUPPORTED_EXTENSIONS",
    "indexing_status",

    "pause_event",
    "cancel_requested",
    "pause_indexing",
    "resume_indexing",
    "cancel_indexing",

    "get_siglip_adapter",
    "get_gemma_adapter",
    "calculate_sha256",
    "scan_directory",
    "delete_photo_atomic_sync",
    "run_ai_pipeline_sync",
    "index_single_file_sync",
    "reindex_single_photo_inplace",
    "cleanup_zombie_records",
    "remove_folder_data",
    "run_indexing_background",
]
