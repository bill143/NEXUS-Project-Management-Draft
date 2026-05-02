"""Data access for the viewer3d module."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.viewer3d.models import ViewerUpload


class ViewerUploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, upload: ViewerUpload) -> ViewerUpload:
        self.session.add(upload)
        await self.session.flush()
        return upload

    async def get(self, upload_id: uuid.UUID) -> ViewerUpload | None:
        return await self.session.get(ViewerUpload, upload_id)
