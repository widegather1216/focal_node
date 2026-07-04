import PyInstaller.__main__
import os
import sys

def build():
    script_path = os.path.join(os.path.dirname(__file__), "app", "main.py")
    
    hidden_imports = [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "sqlalchemy.sql.default_comparator",
        "fastapi",
        "pydantic",
        "pydantic.deprecated.decorator",
        "chromadb",
        "torch",
        "mlx",
        "mlx.core",
        "mlx_lm",
        "mlx_vlm",
        "transformers",
        "rawpy",
        "exifread",
        "PIL",
        "sqlite3",
        "chromadb.api",
        "chromadb.telemetry.product.posthog"
    ]
    
    args = [
        script_path,
        "--name=focal_node_backend",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--log-level=INFO",
        # "--noconsole", # Sidecar stdout is used, so we need console
    ]
    
    for imp in hidden_imports:
        args.extend(["--hidden-import", imp])
        
    collect_all_modules = [
        "transformers",
        "huggingface_hub",
        "mlx",
        "mlx_lm",
        "mlx_vlm",
        "chromadb",
        "torch"
    ]
    
    for mod in collect_all_modules:
        args.extend(["--collect-all", mod])
        args.extend(["--copy-metadata", mod])
        
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build()
