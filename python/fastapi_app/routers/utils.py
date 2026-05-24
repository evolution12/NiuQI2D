from __future__ import annotations

import asyncio
import platform
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from ..exceptions import InvalidParamError

router = APIRouter(prefix="/utils", tags=["utils"])


class SelectDirectoryResponse(BaseModel):
    path: str | None


class OpenFolderRequest(BaseModel):
    path: str


@router.post("/select-directory", response_model=SelectDirectoryResponse)
async def select_directory() -> SelectDirectoryResponse:
    """Open a native OS directory picker and return the selected path."""
    path = await asyncio.to_thread(_pick_directory_native)
    return SelectDirectoryResponse(path=path)


@router.post("/open-folder")
async def open_folder(body: OpenFolderRequest) -> dict[str, bool]:
    """Open a folder in the OS file explorer."""
    target = Path(body.path)
    if not target.exists():
        raise InvalidParamError(f"路径不存在: {body.path}")
    await asyncio.to_thread(_open_folder_native, target)
    return {"ok": True}


def _pick_directory_native() -> str | None:
    """Open a native directory picker using tkinter."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择导出目录")
        root.destroy()
        return str(path) if path else None
    except Exception:
        return None


def _open_folder_native(path: Path) -> None:
    """Open a folder in the OS file manager."""
    resolved = path.resolve()
    if platform.system() == "Windows":
        subprocess.run(["explorer", str(resolved)], check=False)
    elif platform.system() == "Darwin":
        subprocess.run(["open", str(resolved)], check=False)
    else:
        subprocess.run(["xdg-open", str(resolved)], check=False)
