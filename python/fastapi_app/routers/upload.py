from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from PIL import Image

from ..exceptions import InvalidParamError
from ..schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    purpose: str = Form(...),
    project_id: str | None = Form(default=None),
    style_id: str | None = Form(default=None),
) -> UploadResponse:
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED_EXTENSIONS:
        raise InvalidParamError("仅支持 png/jpg/jpeg/webp 图片上传")

    image_data = await file.read()
    size = len(image_data)
    if size > MAX_UPLOAD_SIZE:
        raise InvalidParamError("上传文件不能超过 10MB", {"max_size": MAX_UPLOAD_SIZE, "size": size})
    if not _is_valid_image(image_data):
        raise InvalidParamError("上传文件内容不是有效图片")

    storage = request.app.state.storage
    filename = f"{uuid.uuid4()}.{_normalize_extension(suffix)}"
    if purpose == "reference":
        relative_path = f"references/{filename}"
    elif purpose == "raw_image":
        if project_id is None:
            raise InvalidParamError("purpose=raw_image 时必须提供 project_id")
        relative_path = f"{project_id}/raw/{filename}"
    else:
        raise InvalidParamError("purpose 仅支持 reference 或 raw_image")

    stored_path = await storage.save_uploaded_image(relative_path, image_data)
    return UploadResponse(
        path=stored_path,
        url=f"/images/{stored_path}",
        filename=filename,
        size=size,
        content_type=file.content_type or "image/png",
    )


def _normalize_extension(suffix: str) -> str:
    return "jpg" if suffix == "jpeg" else suffix


def _is_valid_image(image_data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            img.verify()
        return True
    except Exception:
        return False
