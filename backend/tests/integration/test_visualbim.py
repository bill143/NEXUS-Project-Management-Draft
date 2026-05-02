"""Integration tests for the VisualBIM service.

Covers:
* empty project (no BIM models) → CloudResponse with point_count=0
* project with multiple elements → points carry x/y/z from quantities
* falls back to properties when key isn't in quantities, returns 0 if absent
* compare two projects — yields summary with delta_count + shared_categories
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session():
    tmp_db = Path(tempfile.mkdtemp()) / "vb.db"
    url = f"sqlite+aiosqlite:///{tmp_db.as_posix()}"
    engine = create_async_engine(url, future=True)

    import app.modules.bim_hub.models  # noqa: F401
    import app.modules.projects.models  # noqa: F401
    import app.modules.users.models  # noqa: F401
    from app.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()
    try:
        tmp_db.unlink(missing_ok=True)
        tmp_db.parent.rmdir()
    except OSError:
        pass


def _seed_model(session: AsyncSession, project_id: uuid.UUID, name: str = "Test"):
    from app.modules.bim_hub.models import BIMModel

    model = BIMModel(
        id=uuid.uuid4(),
        project_id=project_id,
        name=name,
        version="1",
        status="ready",
    )
    session.add(model)
    return model


def _seed_element(
    session: AsyncSession,
    model_id: uuid.UUID,
    *,
    element_type: str = "IfcWall",
    quantities: dict | None = None,
    properties: dict | None = None,
    name: str | None = None,
):
    from app.modules.bim_hub.models import BIMElement

    elem = BIMElement(
        id=uuid.uuid4(),
        model_id=model_id,
        stable_id=str(uuid.uuid4()),
        element_type=element_type,
        name=name,
        properties=properties or {},
        quantities=quantities or {},
    )
    session.add(elem)
    return elem


# ── Empty project ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cloud_returns_empty_for_project_with_no_models(session):
    from app.modules.visualbim.service import VisualBimService

    pid = uuid.uuid4()
    svc = VisualBimService(session)
    cloud = await svc.cloud(pid)
    assert cloud.point_count == 0
    assert cloud.points == []
    assert cloud.dim_x == "volume"
    assert cloud.dim_y == "area"
    assert cloud.dim_z == "length"


# ── Real data ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cloud_projects_quantities_to_xyz(session):
    from app.modules.visualbim.service import VisualBimService

    pid = uuid.uuid4()
    model = _seed_model(session, pid)
    await session.flush()

    _seed_element(
        session, model.id, element_type="IfcWall",
        quantities={"volume": 12.5, "area": 30.0, "length": 5.0},
        name="W1",
    )
    _seed_element(
        session, model.id, element_type="IfcDoor",
        quantities={"volume": 0.5, "area": 2.0, "length": 1.0},
        name="D1",
    )
    await session.commit()

    svc = VisualBimService(session)
    cloud = await svc.cloud(pid)
    assert cloud.point_count == 2
    by_label = {p.label: p for p in cloud.points}
    assert by_label["W1"].x == 12.5
    assert by_label["W1"].y == 30.0
    assert by_label["W1"].z == 5.0
    assert by_label["W1"].color == "IfcWall"
    assert by_label["D1"].x == 0.5
    assert sorted(cloud.available_dims["color_categories"]) == ["IfcDoor", "IfcWall"]


@pytest.mark.asyncio
async def test_cloud_falls_back_to_properties_then_zero(session):
    from app.modules.visualbim.service import VisualBimService

    pid = uuid.uuid4()
    model = _seed_model(session, pid)
    await session.flush()

    # quantities has no 'cost', properties does — should be picked up
    _seed_element(
        session, model.id, element_type="IfcSlab",
        quantities={"volume": 100.0},
        properties={"cost": 5000.0},
        name="S1",
    )
    # neither has 'mass' — should fall through to 0
    _seed_element(
        session, model.id, element_type="IfcBeam",
        quantities={"volume": 50.0},
        name="B1",
    )
    await session.commit()

    svc = VisualBimService(session)
    cloud = await svc.cloud(pid, dim_x="volume", dim_y="cost", dim_z="mass")
    by_label = {p.label: p for p in cloud.points}
    assert by_label["S1"].y == 5000.0  # from properties
    assert by_label["B1"].y == 0.0     # absent everywhere
    assert by_label["S1"].z == 0.0     # absent everywhere


# ── Compare two projects ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_yields_delta_count_and_shared_categories(session):
    from app.modules.visualbim.service import VisualBimService

    p_a = uuid.uuid4()
    p_b = uuid.uuid4()

    m_a = _seed_model(session, p_a, "A")
    m_b = _seed_model(session, p_b, "B")
    await session.flush()

    _seed_element(session, m_a.id, element_type="IfcWall",
                  quantities={"volume": 10.0, "area": 5.0, "length": 2.0})
    _seed_element(session, m_a.id, element_type="IfcDoor",
                  quantities={"volume": 0.1, "area": 1.0, "length": 0.5})
    _seed_element(session, m_b.id, element_type="IfcWall",
                  quantities={"volume": 12.0, "area": 6.0, "length": 2.5})
    _seed_element(session, m_b.id, element_type="IfcWindow",
                  quantities={"volume": 0.05, "area": 0.5, "length": 0.4})
    _seed_element(session, m_b.id, element_type="IfcWall",
                  quantities={"volume": 14.0, "area": 7.0, "length": 3.0})
    await session.commit()

    svc = VisualBimService(session)
    cmp = await svc.compare(p_a, p_b)
    assert cmp.project_a.point_count == 2
    assert cmp.project_b.point_count == 3
    assert cmp.summary["delta_count"] == 1
    assert "IfcWall" in cmp.summary["shared_categories"]
    assert "IfcDoor" not in cmp.summary["shared_categories"]
    assert "IfcWindow" not in cmp.summary["shared_categories"]
