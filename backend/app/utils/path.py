"""Path normalization and slash-bounded containment helpers."""

import logging
import os
import unicodedata

logger = logging.getLogger("focal_node.path_utils")


def resolve_path_without_leaf_symlink(path: str) -> str:
    """Normalizes path and resolves parent symlinks without expanding a leaf symlink."""
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith("//"):
        normalized_path = "/" + normalized_path.lstrip("/")
    if normalized_path == os.sep:
        return os.sep
    if os.path.islink(normalized_path):
        resolved_parent = os.path.realpath(os.path.dirname(normalized_path))
        return os.path.join(resolved_parent, os.path.basename(normalized_path))
    return os.path.realpath(normalized_path)


def normalize_path_preserving_leaf_symlink(path: str) -> str:
    """Normalizes path to NFC lowercase without expanding a leaf symlink."""
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        resolved_path = resolve_path_without_leaf_symlink(path)
    except Exception as path_err:
        logger.debug("Safe path resolution failed for %s; falling back to normpath: %s", path, path_err)
        resolved_path = os.path.normpath(path)
    # macOS APFS stores paths in NFD while UI/Tauri passes NFC strings; unify to NFC before comparing.
    return unicodedata.normalize("NFC", resolved_path).lower()


def to_slash_bounded_prefix(normalized_root: str) -> str:
    """Returns a directory prefix ending with os.sep so sibling names cannot bleed."""
    return normalized_root if normalized_root.endswith(os.sep) else normalized_root + os.sep


def is_path_within_folder(
    candidate_path: str,
    normalized_root: str,
    bounded_prefix: str,
) -> bool:
    """Checks whether candidate_path equals normalized_root or resides beneath bounded_prefix."""
    normalized_candidate = normalize_path_preserving_leaf_symlink(candidate_path)
    if not normalized_candidate:
        return False
    return normalized_candidate == normalized_root or normalized_candidate.startswith(bounded_prefix)
