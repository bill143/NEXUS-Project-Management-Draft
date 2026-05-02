"""Business logic for the viewer3d module."""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.viewer3d.models import ViewerUpload
from app.modules.viewer3d.repository import ViewerUploadRepository

ALLOWED_EXTENSIONS = {
    "obj", "3ds", "stl", "ply", "gltf", "glb", "off", "3dm",
    "fbx", "dae", "wrl", "3mf", "ifc",
}
MAX_BYTES = 200 * 1024 * 1024  # 200 MB cap per upload — Online3DViewer handles up to ~1GB but we throttle to keep storage sane

_DEFAULT_UPLOAD_DIR = "data/viewer3d_uploads"


def _upload_dir() -> Path:
    """Where uploads land on disk. Configurable via ``NEXUS_VIEWER3D_UPLOAD_DIR``."""
    p = Path(os.environ.get("NEXUS_VIEWER3D_UPLOAD_DIR", _DEFAULT_UPLOAD_DIR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _validate_extension(filename: str) -> str:
    if "." not in filename:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"File has no extension; supported: {sorted(ALLOWED_EXTENSIONS)}",
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Extension '.{ext}' not supported; allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


class ViewerUploadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ViewerUploadRepository(session)

    async def upload(
        self,
        file: UploadFile,
        owner_id: uuid.UUID | None = None,
    ) -> ViewerUpload:
        if not file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No filename")
        ext = _validate_extension(file.filename)

        contents = await file.read()
        if not contents:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
        if len(contents) > MAX_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"File exceeds {MAX_BYTES // 1024 // 1024} MB limit",
            )

        new_id = uuid.uuid4()
        target = _upload_dir() / f"{new_id}.{ext}"
        target.write_bytes(contents)

        upload = ViewerUpload(
            id=new_id,
            original_name=file.filename,
            mime=file.content_type or "application/octet-stream",
            extension=ext,
            size_bytes=len(contents),
            stored_path=str(target.resolve()),
            uploaded_by=owner_id,
        )
        return await self.repo.create(upload)

    async def get(self, upload_id: uuid.UUID) -> ViewerUpload:
        upload = await self.repo.get(upload_id)
        if upload is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload not found")
        return upload

    async def read_bytes(self, upload_id: uuid.UUID) -> tuple[bytes, ViewerUpload]:
        upload = await self.get(upload_id)
        path = Path(upload.stored_path)
        if not path.exists():
            raise HTTPException(
                status.HTTP_410_GONE,
                "Upload artefact missing on disk",
            )
        return path.read_bytes(), upload
