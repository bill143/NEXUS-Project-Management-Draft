"""Pydantic schemas for the viewer3d module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ViewerUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_name: str
    mime: str
    extension: str
    size_bytes: int
    download_url: str
    created_at: datetime
