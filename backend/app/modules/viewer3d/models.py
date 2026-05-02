"""3D Viewer ORM models.

Tables:
    oe_viewer3d_upload — upload metadata (uuid, original name, mime, size, owner).
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base


class ViewerUpload(Base):
    """A single uploaded 3D model file.

    ``id`` is the public-facing UUID used in download URLs. ``stored_path``
    is a server-internal absolute path; never exposed to the client.
    """

    __tablename__ = "oe_viewer3d_upload"

    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    extension: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ViewerUpload {self.original_name} ({self.size_bytes}B)>"
