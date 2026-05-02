"""Integration tests for the sustainability / CO₂ module.

Mirrors the my_module test pattern: per-test fresh SQLite DB with users +
projects + sustainability tables, then exercise the service layer end-to-end.

Covers:
* EmissionFactor create + list
* ElementGroup CRUD
* CarbonCalculationService.calculate (the main DDC-port deliverable —
  verifies that quantity × factor aggregates correctly into by_category /
  by_buy_clean_category).
* Validation rules (quantity > 0, EPD/category required)
"""

from __future__ import annotations

import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session():
    tmp_db = Path(tempfile.mkdtemp()) / "sustain.db"
    url = f"sqlite+aiosqlite:///{tmp_db.as_posix()}"
    engine = create_async_engine(url, future=True)

    import app.modules.projects.models  # noqa: F401
    import app.modules.sustainability.models  # noqa: F401
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


def _new_user(email: str):
    from app.modules.users.models import User
    from app.modules.users.service import hash_password

    return User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("SustainPass1234!"),
        full_name="Sustainability Tester",
        role="editor",
        locale="en",
        is_active=True,
        metadata_={},
    )


def _new_project(owner_id: uuid.UUID, name: str = "Carbon Test Project"):
    from app.modules.projects.models import Project

    return Project(id=uuid.uuid4(), owner_id=owner_id, name=name, status="active")


# ── Emission factors ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_emission_factors(session):
    from app.modules.sustainability.schemas import EmissionFactorCreate
    from app.modules.sustainability.service import EmissionFactorService

    svc = EmissionFactorService(session)
    await svc.create_factor(
        EmissionFactorCreate(
            code="CONC-30",
            name="Concrete C30/37",
            material_category="concrete",
            buy_clean_category="concrete",
            unit="m3",
            factor_kgco2e=Decimal("310.0"),
            region="US",
            source="EC3",
        ),
    )
    await svc.create_factor(
        EmissionFactorCreate(
            code="STEEL-RB",
            name="Reinforcing steel",
            material_category="steel",
            buy_clean_category="steel",
            unit="kg",
            factor_kgco2e=Decimal("1.85"),
        ),
    )
    await session.commit()

    factors = await svc.list_factors()
    assert {f.code for f in factors} == {"CONC-30", "STEEL-RB"}


@pytest.mark.asyncio
async def test_duplicate_emission_factor_code_is_409(session):
    from fastapi import HTTPException

    from app.modules.sustainability.schemas import EmissionFactorCreate
    from app.modules.sustainability.service import EmissionFactorService

    svc = EmissionFactorService(session)
    await svc.create_factor(
        EmissionFactorCreate(
            code="DUP-1",
            name="Dup",
            material_category="concrete",
            unit="m3",
            factor_kgco2e=Decimal("100"),
        ),
    )
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await svc.create_factor(
            EmissionFactorCreate(
                code="DUP-1",
                name="Dup again",
                material_category="concrete",
                unit="m3",
                factor_kgco2e=Decimal("999"),
            ),
        )
    assert exc.value.status_code == 409


# ── Element group CRUD ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_element_group_crud(session):
    from app.modules.sustainability.schemas import (
        ElementGroupCreate,
        ElementGroupUpdate,
    )
    from app.modules.sustainability.service import ElementGroupService

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@s.io")
    session.add(user)
    await session.flush()
    project = _new_project(user.id)
    session.add(project)
    await session.flush()

    svc = ElementGroupService(session)
    g = await svc.create_group(
        ElementGroupCreate(
            project_id=project.id,
            name="Foundation walls",
            material_category="concrete",
            epd_code="CONC-30",
            quantity=Decimal("125.5"),
            unit="m3",
        ),
    )
    await session.commit()

    fetched = await svc.get_group(g.id)
    assert fetched.name == "Foundation walls"

    updated = await svc.update_group(g.id, ElementGroupUpdate(quantity=Decimal("200")))
    assert updated.quantity == Decimal("200")

    listed = await svc.list_groups(project.id)
    assert len(listed) == 1

    await svc.delete_group(g.id)
    await session.commit()
    assert await svc.list_groups(project.id) == []


# ── Carbon calculation (the main DDC port) ──────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_carbon_footprint_aggregates_by_category(session):
    from app.modules.sustainability.schemas import (
        ElementGroupCreate,
        EmissionFactorCreate,
    )
    from app.modules.sustainability.service import (
        CarbonCalculationService,
        ElementGroupService,
        EmissionFactorService,
    )

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@s.io")
    session.add(user)
    await session.flush()
    project = _new_project(user.id)
    session.add(project)
    await session.flush()

    factors = EmissionFactorService(session)
    await factors.create_factor(
        EmissionFactorCreate(
            code="CONC-30",
            name="Concrete C30/37",
            material_category="concrete",
            buy_clean_category="concrete",
            unit="m3",
            factor_kgco2e=Decimal("310"),
        ),
    )
    await factors.create_factor(
        EmissionFactorCreate(
            code="STEEL-RB",
            name="Reinforcing steel",
            material_category="steel",
            buy_clean_category="steel",
            unit="kg",
            factor_kgco2e=Decimal("1.85"),
        ),
    )

    groups = ElementGroupService(session)
    await groups.create_group(
        ElementGroupCreate(
            project_id=project.id,
            name="Foundation",
            material_category="concrete",
            epd_code="CONC-30",
            quantity=Decimal("100"),
            unit="m3",
        ),
    )
    await groups.create_group(
        ElementGroupCreate(
            project_id=project.id,
            name="Walls",
            material_category="concrete",
            epd_code="CONC-30",
            quantity=Decimal("50"),
            unit="m3",
        ),
    )
    await groups.create_group(
        ElementGroupCreate(
            project_id=project.id,
            name="Rebar",
            material_category="steel",
            epd_code="STEEL-RB",
            quantity=Decimal("5000"),
            unit="kg",
        ),
    )
    await session.commit()

    calc = CarbonCalculationService(session)
    report = await calc.calculate(project.id)
    await session.commit()

    # 100*310 + 50*310 + 5000*1.85 = 31000 + 15500 + 9250 = 55750
    assert report.total_kgco2e == Decimal("55750.0000")
    # Aggregates by material_category
    assert report.by_category["concrete"] == pytest.approx(46500.0)
    assert report.by_category["steel"] == pytest.approx(9250.0)
    # Buy Clean Act category rollup
    assert report.by_buy_clean_category["concrete"] == pytest.approx(46500.0)
    assert report.by_buy_clean_category["steel"] == pytest.approx(9250.0)
    assert report.notes == ""


@pytest.mark.asyncio
async def test_calculate_flags_unmatched_groups_in_notes(session):
    from app.modules.sustainability.schemas import ElementGroupCreate
    from app.modules.sustainability.service import (
        CarbonCalculationService,
        ElementGroupService,
    )

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@s.io")
    session.add(user)
    await session.flush()
    project = _new_project(user.id)
    session.add(project)
    await session.flush()

    groups = ElementGroupService(session)
    await groups.create_group(
        ElementGroupCreate(
            project_id=project.id,
            name="Mystery material",
            material_category="unobtainium",
            epd_code=None,
            quantity=Decimal("42"),
        ),
    )
    await session.commit()

    calc = CarbonCalculationService(session)
    report = await calc.calculate(project.id)
    assert report.total_kgco2e == Decimal(0)
    assert "No EPD match" in report.notes
    assert "Mystery material" in report.notes


# ── Validation rules ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validation_rule_quantity_must_be_positive():
    from app.core.validation.engine import ValidationContext
    from app.modules.sustainability.validators import ElementGroupQuantityPositive

    rule = ElementGroupQuantityPositive()
    context = ValidationContext(
        data={
            "groups": [
                {"id": "1", "name": "ok", "quantity": 10},
                {"id": "2", "name": "bad", "quantity": 0},
                {"id": "3", "name": "negative", "quantity": -5},
            ],
        },
    )
    results = await rule.validate(context)
    assert [r.passed for r in results] == [True, False, False]


@pytest.mark.asyncio
async def test_validation_rule_epd_or_known_category():
    from app.core.validation.engine import ValidationContext
    from app.modules.sustainability.validators import ElementGroupHasEpdOrCategory

    rule = ElementGroupHasEpdOrCategory()
    context = ValidationContext(
        data={
            "groups": [
                {"id": "1", "name": "explicit-epd", "epd_code": "X-1", "material_category": "weird"},
                {"id": "2", "name": "fallback", "material_category": "concrete"},
                {"id": "3", "name": "no-match", "material_category": "unobtainium"},
            ],
        },
    )
    results = await rule.validate(context)
    assert [r.passed for r in results] == [True, True, False]
