import os
import hashlib
from typing import List

# Supported file extensions (Standard and RAW formats)
SUPPORTED_EXTENSIONS = {
    # Standard formats
    ".jpg", ".jpeg", ".png", ".webp",
    # RAW formats
    ".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".rw2", ".pef", ".raf"
}

def calculate_sha256(file_path: str) -> str:
    """
    Computes SHA-256 checksum of the file in chunks to optimize memory usage.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_directory(folder_paths: List[str]) -> List[str]:
    """
    Recursively scans targeted folders and extracts supported image file paths.
    """
    files_to_index = []
    for folder in folder_paths:
        if not os.path.exists(folder):
            print(f"[Indexer] Target folder does not exist: {folder}", flush=True)
            continue
        for root, _, files in os.walk(folder):
            for file in files:
                if file.startswith(".") or file.startswith("._"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files_to_index.append(os.path.join(root, file))
    return files_to_index
