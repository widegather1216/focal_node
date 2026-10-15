import PyInstaller.__main__
import os
import sys
import shutil
import platform

def build():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    script_path = os.path.join(backend_dir, "app", "main.py")
    dist_dir = os.path.join(backend_dir, "dist")
    work_dir = os.path.join(backend_dir, "build")
    cache_dir = os.path.join(backend_dir, ".pyinstaller_cache")
    os.environ["PYINSTALLER_CONFIG_DIR"] = cache_dir
    
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
        "torchvision",
        "torchvision.transforms",
        "torchvision.transforms.functional",
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
        "chromadb.telemetry.product.posthog",
        "hf_transfer"
    ]
    
    args = [
        script_path,
        "--name=focal_node_backend",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--log-level=INFO",
        f"--distpath={dist_dir}",
        f"--workpath={work_dir}",
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
        "torch",
        "torchvision",
        "pydantic_core",
        "pydantic",
        "fastapi"
    ]
    
    for mod in collect_all_modules:
        args.extend(["--collect-all", mod])
        args.extend(["--copy-metadata", mod])
        
    # MLX metallib detection
    mlx_found = False
    try:
        import mlx
        for p in mlx.__path__:
            candidate = os.path.join(p, "lib", "mlx.metallib")
            if os.path.exists(candidate):
                args.extend(["--add-data", f"{candidate}:mlx/lib"])
                args.extend(["--add-data", f"{candidate}:."])
                mlx_found = True
                break
    except Exception:
        pass

    if not mlx_found:
        import site
        for sp in site.getsitepackages():
            mlx_metallib = os.path.join(sp, "mlx", "lib", "mlx.metallib")
            if os.path.exists(mlx_metallib):
                args.extend(["--add-data", f"{mlx_metallib}:mlx/lib"])
                args.extend(["--add-data", f"{mlx_metallib}:."])
                break

    print(f"[Build] Running PyInstaller with args: {args}")
    PyInstaller.__main__.run(args)

    # Copy build artifacts to src-tauri/binaries
    built_backend_dir = os.path.join(dist_dir, "focal_node_backend")
    if not os.path.exists(built_backend_dir):
        raise RuntimeError(f"Build output not found at: {built_backend_dir}")

    tauri_binaries_dir = os.path.join(project_root, "src-tauri", "binaries")
    os.makedirs(tauri_binaries_dir, exist_ok=True)

    machine = platform.machine()
    system = platform.system().lower()
    if system == "darwin":
        triple_arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
        target_name = f"focal_node_backend-{triple_arch}-apple-darwin"
    elif system == "windows":
        target_name = f"focal_node_backend-{machine}-pc-windows-msvc.exe"
    else:
        target_name = f"focal_node_backend-{machine}-unknown-linux-gnu"

    src_binary = os.path.join(built_backend_dir, "focal_node_backend.exe" if system == "windows" else "focal_node_backend")
    dst_binary = os.path.join(tauri_binaries_dir, target_name)

    print(f"[Build] Copying binary from {src_binary} to {dst_binary}")
    shutil.copy2(src_binary, dst_binary)
    if system != "windows":
        os.chmod(dst_binary, 0o755)

    src_internal = os.path.join(built_backend_dir, "_internal")
    dst_internal = os.path.join(tauri_binaries_dir, "_internal")
    if os.path.exists(src_internal):
        print(f"[Build] Syncing _internal folder to {dst_internal}")
        if os.path.exists(dst_internal):
            shutil.rmtree(dst_internal)
        shutil.copytree(src_internal, dst_internal, symlinks=True)

    print("[Build] Sidecar backend successfully built and synced to src-tauri/binaries!")

if __name__ == "__main__":
    build()
