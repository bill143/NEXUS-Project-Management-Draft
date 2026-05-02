"""Integration tests for the viewer3d module.

Covers:
* upload happy path — saves bytes to disk, returns a row with download URL
* retrieve happy path — loads the saved bytes back and the metadata matches
* retrieve 404 — unknown UUID returns 404
* upload rejects unsupported extensions
"""

from __future__ import annotations

import io
import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_and_dir(monkeypatch):
    """Per-test fresh DB + isolated upload dir."""
    tmp_db = Path(tempfile.mkdtemp()) / "viewer.db"
    upload_dir = tmp_db.parent / "uploads"
    monkeypatch.setenv("NEXUS_VIEWER3D_UPLOAD_DIR", str(upload_dir))

    url = f"sqlite+aiosqlite:///{tmp_db.as_posix()}"
    engine = create_async_engine(url, future=True)

    import app.modules.users.models  # noqa: F401
    import app.modules.viewer3d.models  # noqa: F401
    from app.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s, upload_dir

    await engine.dispose()
    try:
        tmp_db.unlink(missing_ok=True)
        for f in upload_dir.glob("*"):
            f.unlink(missing_ok=True)
        upload_dir.rmdir()
        tmp_db.parent.rmdir()
    except OSError:
        pass


def _upload_file(name: str, body: bytes, mime: str = "application/octet-stream") -> UploadFile:
    return UploadFile(file=io.BytesIO(body), filename=name, headers={"content-type": mime})


# ── Upload happy path ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_writes_file_to_disk_and_creates_row(session_and_dir):
    from app.modules.viewer3d.service import ViewerUploadService

    session, upload_dir = session_and_dir
    svc = ViewerUploadService(session)

    body = b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
    upload = await svc.upload(_upload_file("triangle.obj", body, "model/obj"))
    await session.commit()

    assert upload.id is not None
    assert upload.original_name == "triangle.obj"
    assert upload.extension == "obj"
    assert upload.size_bytes == len(body)
    # the bytes are on disk under a UUID-named file
    on_disk = list(upload_dir.glob(f"{upload.id}.obj"))
    assert len(on_disk) == 1
    assert on_disk[0].read_bytes() == body


# ── Retrieve happy path ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_bytes_returns_uploaded_payload(session_and_dir):
    from app.modules.viewer3d.service import ViewerUploadService

    session, _ = session_and_dir
    svc = ViewerUploadService(session)
    body = b"PLY\nformat ascii 1.0\n"
    saved = await svc.upload(_upload_file("model.ply", body))
    await session.commit()

    data, upload = await svc.read_bytes(saved.id)
    assert data == body
    assert upload.id == saved.id
    assert upload.extension == "ply"


# ── 404 ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_bytes_404_for_unknown_id(session_and_dir):
    from app.modules.viewer3d.service import ViewerUploadService

    session, _ = session_and_dir
    svc = ViewerUploadService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.read_bytes(uuid.uuid4())
    assert exc.value.status_code == 404


# ── Unsupported extension ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_extension(session_and_dir):
    from app.modules.viewer3d.service import ViewerUploadService

    session, _ = session_and_dir
    svc = ViewerUploadService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.upload(_upload_file("evil.exe", b"MZ..."))
    assert exc.value.status_code == 415
    assert "exe" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(session_and_dir):
    from app.modules.viewer3d.service import ViewerUploadService

    session, _ = session_and_dir
    svc = ViewerUploadService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.upload(_upload_file("empty.obj", b""))
    assert exc.value.status_code == 400
