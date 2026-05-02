"""Integration tests for the my_module example module.

Covers:
* Service-layer CRUD against a fresh SQLite DB
* Validation rules registered by ``register_my_module_rules`` flag
  blank/oversized item names
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest_asyncio.fixture
async def session():
    """Per-test fresh SQLite DB with users, projects, and my_module tables."""
    tmp_db = Path(tempfile.mkdtemp()) / "my_module.db"
    url = f"sqlite+aiosqlite:///{tmp_db.as_posix()}"
    engine = create_async_engine(url, future=True)

    import app.modules.my_module.models  # noqa: F401
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


def _new_user(email: str):
    from app.modules.users.models import User
    from app.modules.users.service import hash_password

    return User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("MyModulePass1234!"),
        full_name="My Module Tester",
        role="editor",
        locale="en",
        is_active=True,
        metadata_={},
    )


def _new_project(owner_id: uuid.UUID, name: str = "Test Project"):
    from app.modules.projects.models import Project

    return Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=name,
        status="active",
    )


# ── Service / Router ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_item(session):
    from app.modules.my_module.schemas import ItemCreate
    from app.modules.my_module.service import ItemService

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@my.io")
    session.add(user)
    await session.flush()

    project = _new_project(user.id)
    session.add(project)
    await session.flush()

    service = ItemService(session)
    created = await service.create_item(
        ItemCreate(
            project_id=project.id,
            name="Widget",
            description="A widget",
            metadata={"colour": "red"},
        ),
    )
    await session.commit()

    fetched = await service.get_item(created.id)
    assert fetched.id == created.id
    assert fetched.name == "Widget"
    assert fetched.description == "A widget"
    assert fetched.project_id == project.id


@pytest.mark.asyncio
async def test_list_items_scoped_by_project(session):
    from app.modules.my_module.schemas import ItemCreate
    from app.modules.my_module.service import ItemService

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@my.io")
    session.add(user)
    await session.flush()

    proj_a = _new_project(user.id, "Project A")
    proj_b = _new_project(user.id, "Project B")
    session.add_all([proj_a, proj_b])
    await session.flush()

    service = ItemService(session)
    await service.create_item(ItemCreate(project_id=proj_a.id, name="A1"))
    await service.create_item(ItemCreate(project_id=proj_a.id, name="A2"))
    await service.create_item(ItemCreate(project_id=proj_b.id, name="B1"))
    await session.commit()

    a_items = await service.list_items(proj_a.id)
    b_items = await service.list_items(proj_b.id)

    assert {i.name for i in a_items} == {"A1", "A2"}
    assert {i.name for i in b_items} == {"B1"}


@pytest.mark.asyncio
async def test_update_and_delete_item(session):
    from app.modules.my_module.schemas import ItemCreate, ItemUpdate
    from app.modules.my_module.service import ItemService

    user = _new_user(f"u-{uuid.uuid4().hex[:6]}@my.io")
    session.add(user)
    await session.flush()

    project = _new_project(user.id)
    session.add(project)
    await session.flush()

    service = ItemService(session)
    created = await service.create_item(
        ItemCreate(project_id=project.id, name="Old"),
    )
    await session.commit()

    updated = await service.update_item(created.id, ItemUpdate(name="New", description="d"))
    assert updated.name == "New"
    assert updated.description == "d"

    await service.delete_item(created.id)
    await session.commit()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await service.get_item(created.id)
    assert exc.value.status_code == 404


# ── Validation rules ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validation_rule_blank_name_fails():
    from app.core.validation.engine import ValidationContext
    from app.modules.my_module.validators import ItemNameRequired

    rule = ItemNameRequired()
    context = ValidationContext(data={"items": [{"id": "1", "name": ""}, {"id": "2", "name": "ok"}]})
    results = await rule.validate(context)

    assert len(results) == 2
    assert results[0].passed is False
    assert results[0].element_ref == "1"
    assert results[1].passed is True


@pytest.mark.asyncio
async def test_validation_rule_max_length_warns():
    from app.core.validation.engine import Severity, ValidationContext
    from app.modules.my_module.validators import ItemNameMaxLength

    rule = ItemNameMaxLength()
    long_name = "x" * 256
    context = ValidationContext(data={"items": [{"id": "1", "name": long_name}]})
    results = await rule.validate(context)

    assert results[0].passed is False
    assert results[0].severity == Severity.WARNING


def test_register_rules_populates_rule_set():
    from app.core.validation.engine import rule_registry
    from app.modules.my_module.validators import register_my_module_rules

    register_my_module_rules()
    rule_ids = {r["rule_id"] for r in rule_registry.list_rules(rule_set="my_module")}
    assert {"my_module.item_name_required", "my_module.item_name_max_length"} <= rule_ids
