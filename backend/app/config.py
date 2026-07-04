import os
import sys

# Determine environment
IS_PROD = getattr(sys, 'frozen', False)

# Set base config directory based on environment to ensure Data Isolation
if IS_PROD:
    CONFIG_DIR = os.path.expanduser("~/.config/focal_node")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/focal_node_dev")

os.makedirs(CONFIG_DIR, exist_ok=True)

# Define specialized paths
DATABASE_URL = f"sqlite:///{os.path.join(CONFIG_DIR, 'focal_node.db')}"
CHROMA_DIR = os.path.join(CONFIG_DIR, "chroma")
THUMBNAILS_DIR = os.path.join(CONFIG_DIR, "thumbnails")
METAL_CACHE_DIR = os.path.join(CONFIG_DIR, "metal_cache")

# Ensure directories exist
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(METAL_CACHE_DIR, exist_ok=True)
