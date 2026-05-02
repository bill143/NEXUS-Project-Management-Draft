"""3D Viewer API routes.

Auto-mounted at ``/api/v1/viewer3d/``.
"""

import uuid

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import Response

from app.dependencies import SessionDep
from app.modules.viewer3d.schemas import ViewerUploadResponse
from app.modules.viewer3d.service import ViewerUploadService

router = APIRouter()


def _service(session: SessionDep) -> ViewerUploadService:
    return ViewerUploadService(session)


def _to_response(upload) -> ViewerUploadResponse:  # noqa: ANN001
    return ViewerUploadResponse(
        id=upload.id,
        original_name=upload.original_name,
        mime=upload.mime,
        extension=upload.extension,
        size_bytes=upload.size_bytes,
        download_url=f"/api/v1/viewer3d/files/{upload.id}",
        created_at=upload.created_at,
    )


@router.post(
    "/upload", response_model=ViewerUploadResponse, status_code=status.HTTP_201_CREATED,
)
async def upload(
    file: UploadFile,
    service: ViewerUploadService = Depends(_service),
) -> ViewerUploadResponse:
    """Upload a 3D model file. Returns an UUID + download URL."""
    saved = await service.upload(file)
    return _to_response(saved)


@router.get("/files/{upload_id}")
async def download(
    upload_id: uuid.UUID,
    service: ViewerUploadService = Depends(_service),
) -> Response:
    """Stream the previously-uploaded model bytes back."""
    data, upload = await service.read_bytes(upload_id)
    return Response(
        content=data,
        media_type=upload.mime,
        headers={
            "Content-Disposition": f'inline; filename="{upload.original_name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/files/{upload_id}/info", response_model=ViewerUploadResponse)
async def info(
    upload_id: uuid.UUID,
    service: ViewerUploadService = Depends(_service),
) -> ViewerUploadResponse:
    """Metadata-only lookup (no file payload)."""
    upload = await service.get(upload_id)
    return _to_response(upload)
