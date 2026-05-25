"""Build the NiuQI2D backend as a standalone executable using PyInstaller."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> None:
    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "niuqi2d-backend",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--clean",
        # Hidden imports for uvicorn async workers
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "aiosqlite",
        # Bundle preset styles data
        "--add-data", f"fastapi_app{Path.sep}data{Path.pathsep}fastapi_app{Path.sep}data",
        # Entry point
        str(ROOT / "fastapi_app" / "__main__.py"),
    ]

    print(f"[build_exe] Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    exe_path = dist_dir / "niuqi2d-backend.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[build_exe] Success: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"[build_exe] ERROR: {exe_path} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
