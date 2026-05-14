# Directory Module — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Wave 1 of RFC 36 — `/directory` shell with Users + Contacts ported into tabs, Companies tab with CRUD backed by a new module, and a scoped dark-command-center theme. No insurance, no bidder info, no groups, no audit log — those are Waves 2 and 3.

**Architecture:** New backend module `backend/app/modules/directory/` exposing `/api/v1/directory/companies/*`. New frontend feature `frontend/src/features/directory/` rendering a 5-tab page. The Users and Contacts tabs are produced by **moving** the existing `UserManagementPage.tsx` and `ContactsPage.tsx` into the new feature directory (not rewriting them); the existing `users/api.ts` and `contacts/api.ts` clients stay where they are and are imported by the moved components. The old `/users` and `/contacts` routes become 301 redirects to `/directory?tab=users` / `?tab=contacts`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (`Mapped[]` / `mapped_column`) + Alembic + Pydantic v2 + Postgres (prod) / SQLite (dev) on backend. React 18 + react-router-dom + Vite + Vitest + TypeScript + Tailwind on frontend. JWT bearer auth via existing `Depends(get_current_user)` and `RequirePermission(...)` from `app.dependencies`.

**RFC clarifications applied here:**
1. **Table naming**: RFC §4 said `directory_companies`. Codebase convention is `oe_<module>_<entity>` singular (`oe_users_user`, `oe_contacts_contact`, `oe_nexus_precon_*`). This plan uses **`oe_directory_company`**.
2. **Permission keys**: RFC §5 said `directory.read` / `directory.write` / `directory.admin`. Existing convention is fine-grained per-action (`users.list`, `users.create`, `users.update`, ...). This plan uses **`companies.list`, `companies.read`, `companies.create`, `companies.update`, `companies.delete`** mapped onto the existing `Role` hierarchy (admin > manager > editor > viewer).
3. **Wave-1 toolbar buttons** that depend on Wave-3 endpoints render with `disabled` state + tooltip "Available in Wave 3".

**Commit shape:** 7 commits on `main`, each a coherent logical unit (matches repo's existing per-feature commit style — see `1804a1bd`, `58f44bc7`, `c641eada`). User triggers `vercel --prod --yes` manually after the final commit lands and CI is green.

---

## File Structure (Wave 1)

```
backend/app/modules/directory/
├─ __init__.py              # empty, marks package
├─ manifest.py              # ModuleManifest registration
├─ permissions.py           # register_companies_permissions()
├─ models.py                # Company ORM model
├─ schemas.py               # CompanyCreate, CompanyUpdate, CompanyResponse, ...
├─ repository.py            # CompanyRepository (data access)
├─ service.py               # CompanyService (business logic)
└─ router.py                # FastAPI router /api/v1/directory/companies

backend/alembic/versions/
└─ v2j0_directory_companies.py  # creates oe_directory_company table

backend/tests/integration/
└─ test_directory_companies.py  # CRUD + RBAC integration tests

frontend/public/fonts/
├─ DMSerifDisplay-Regular.woff2
├─ IBMPlexSans-Regular.woff2
├─ IBMPlexSans-Bold.woff2
└─ JetBrainsMono-Regular.woff2

frontend/src/features/directory/
├─ DirectoryPage.tsx                  # wraps everything with data-route="directory"
├─ DirectoryTabs.tsx                  # tab navigation
├─ index.ts                           # public exports
├─ tabs/
│   ├─ UsersTab.tsx                   # MOVED from features/users/UserManagementPage.tsx
│   ├─ ContactsTab.tsx                # MOVED from features/contacts/ContactsPage.tsx
│   ├─ CompaniesTab.tsx               # NEW
│   ├─ DistributionGroupsTab.tsx      # NEW (placeholder body for Wave 1)
│   └─ InactiveTab.tsx                # NEW (placeholder body for Wave 1)
├─ slideovers/
│   └─ AddEditCompanySlideOver.tsx    # General tab live; 4 others = placeholder
├─ components/
│   ├─ SlideOver.tsx                  # 300ms ease-out from right
│   ├─ DirectoryTable.tsx             # sticky header, hover, mono numerics
│   ├─ StatusBadge.tsx                # dot + text + color
│   └─ KpiRow.tsx                     # 4-up monospace counters
├─ api/
│   └─ companies.ts                   # TS client for /api/v1/directory/companies
└─ theme/
    ├─ tokens.css                     # CSS vars under [data-route="directory"]
    └─ fonts.css                      # @font-face declarations

frontend/src/app/App.tsx               # add /directory route; replace /users + /contacts with redirects
frontend/src/features/users/UserManagementPage.tsx     # DELETE after move
frontend/src/features/users/index.ts                   # update to remove UserManagementPage export
frontend/src/features/contacts/ContactsPage.tsx        # DELETE after move
frontend/src/features/contacts/index.ts                # update to remove ContactsPage export

backend/app/main.py                    # register directory router under /api/v1/directory
```

The existing `frontend/src/features/users/api.ts` and `frontend/src/features/contacts/api.ts` **stay where they are** and are imported by the moved tab components. Backend `backend/app/modules/users/*` is untouched.

---

## Commit Plan

| # | Commit message | Tasks |
|---|---|---|
| 1 | `feat(directory): backend module skeleton + Company model + migration` | 1, 2, 3 |
| 2 | `feat(directory): companies CRUD API + RBAC + integration tests` | 4, 5, 6, 7 |
| 3 | `feat(directory): self-hosted fonts + dark theme tokens` | 8, 9 |
| 4 | `feat(directory): shared UI primitives (SlideOver, table, badge, KPIs)` | 10 |
| 5 | `feat(directory): page shell + companies tab + slide-over` | 11, 12, 13, 14 |
| 6 | `feat(directory): move users + contacts pages into directory tabs` | 15, 16 |
| 7 | `feat(directory): /directory route + 301 redirects from old paths` | 17, 18, 19 |

---

### Task 1: Backend module skeleton (manifest + permissions)

**Files:**
- Create: `backend/app/modules/directory/__init__.py`
- Create: `backend/app/modules/directory/manifest.py`
- Create: `backend/app/modules/directory/permissions.py`

- [ ] **Step 1: Create empty `__init__.py`**

```python
"""Directory module — companies, contacts, users, groups, insurance, audit."""
```

- [ ] **Step 2: Create `manifest.py`**

```python
"""Directory module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_directory",
    version="0.1.0",
    display_name="Project Directory",
    description="Companies, contacts, users, distribution groups, insurance certificates, and audit log",
    author="O'Neill Contractors",
    category="core",
    depends=["oe_users", "oe_contacts"],
    auto_install=True,
    enabled=True,
)
```

- [ ] **Step 3: Create `permissions.py`**

```python
"""Directory module permission definitions."""

from app.core.permissions import Role, permission_registry


def register_directory_permissions() -> None:
    """Register permissions for the directory module."""
    permission_registry.register_module_permissions(
        "directory",
        {
            "companies.list":   Role.VIEWER,
            "companies.read":   Role.VIEWER,
            "companies.create": Role.EDITOR,
            "companies.update": Role.EDITOR,
            "companies.delete": Role.ADMIN,
        },
    )
```

- [ ] **Step 4: Verify module loads without errors**

Run: `cd backend && python -c "from app.modules.directory import manifest, permissions; print(manifest.manifest.name)"`
Expected: `oe_directory`

- [ ] **Step 5: Commit (deferred — bundled into Commit 1 after Task 3)**

---

### Task 2: `Company` ORM model

**Files:**
- Create: `backend/app/modules/directory/models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_directory_companies.py`:

```python
"""Integration tests for the directory companies API and ORM."""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_company_model_persists_with_required_fields(db_session: AsyncSession):
    from app.modules.directory.models import Company

    company = Company(name="Acme Mechanical")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    assert company.id is not None
    assert isinstance(company.id, uuid.UUID)
    assert company.name == "Acme Mechanical"
    assert company.is_active is True
    assert company.tags == []
    assert company.project_roles == []
    assert company.created_at is not None
    assert company.updated_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/integration/test_directory_companies.py::test_company_model_persists_with_required_fields -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.modules.directory.models'`

- [ ] **Step 3: Write `models.py`**

```python
"""Directory ORM models — Wave 1: Company only."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import GUID, Base


class Company(Base):
    """Company / vendor / subcontractor in the project directory."""

    __tablename__ = "oe_directory_company"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    abbreviated_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dba: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    primary_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("oe_users_user.id", ondelete="SET NULL"), nullable=True
    )

    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    labor_union: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    project_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("oe_users_user.id", ondelete="SET NULL"), nullable=True
    )
```

Add `import uuid` at the top.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/integration/test_directory_companies.py::test_company_model_persists_with_required_fields -v`
Expected: PASS. If FAIL with "table does not exist", that's Task 3's job — proceed to Task 3 then re-run.

---

### Task 3: Alembic migration `v2j0_directory_companies.py`

**Files:**
- Create: `backend/alembic/versions/v2j0_directory_companies.py`

- [ ] **Step 1: Write the migration**

```python
"""v2j0 — directory_companies: oe_directory_company table.

Wave 1 of RFC 36. Creates the single new table required by Wave 1.
Subsequent waves add oe_directory_company_bidder_info (Wave 2),
oe_directory_company_insurance (Wave 2), oe_directory_group (Wave 3),
oe_directory_group_member (Wave 3), and oe_directory_audit_log (Wave 3).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.database import GUID


revision: str = "v2j0_directory_companies"
down_revision: Union[str, Sequence[str], None] = "v2i0_null_not_distinct"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oe_directory_company",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("abbreviated_name", sa.String(64), nullable=True),
        sa.Column("dba", sa.String(255), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("fax", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column(
            "primary_contact_id",
            GUID(),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("license_number", sa.String(64), nullable=True),
        sa.Column("labor_union", sa.String(128), nullable=True),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("project_roles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_by",
            GUID(),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_oe_directory_company_active_name",
        "oe_directory_company",
        ["is_active", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_oe_directory_company_active_name", table_name="oe_directory_company")
    op.drop_table("oe_directory_company")
```

- [ ] **Step 2: Run migration up**

Run: `cd backend && alembic upgrade head`
Expected: log line `Running upgrade v2i0_null_not_distinct -> v2j0_directory_companies`

- [ ] **Step 3: Re-run Task 2's test**

Run: `cd backend && pytest tests/integration/test_directory_companies.py::test_company_model_persists_with_required_fields -v`
Expected: PASS.

- [ ] **Step 4: Round-trip the migration**

Run: `cd backend && alembic downgrade -1 && alembic upgrade head`
Expected: both succeed with no errors. This proves `downgrade()` works.

- [ ] **Step 5: Commit (Commit 1)**

```bash
cd C:/dev/ON_NEXUS_ERP
git add backend/app/modules/directory/__init__.py \
        backend/app/modules/directory/manifest.py \
        backend/app/modules/directory/permissions.py \
        backend/app/modules/directory/models.py \
        backend/alembic/versions/v2j0_directory_companies.py \
        backend/tests/integration/test_directory_companies.py
git commit -m "feat(directory): backend module skeleton + Company model + migration

First commit of RFC 36 Wave 1. Adds the oe_directory module manifest,
permission keys (companies.list/read/create/update/delete mapped onto
existing Role hierarchy), the Company ORM model, and the v2j0 migration
creating oe_directory_company.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Pydantic schemas

**Files:**
- Create: `backend/app/modules/directory/schemas.py`

- [ ] **Step 1: Write the schema test**

Append to `backend/tests/integration/test_directory_companies.py`:

```python
def test_company_create_schema_validates_name_required():
    from app.modules.directory.schemas import CompanyCreate
    with pytest.raises(ValueError):
        CompanyCreate(name="")


def test_company_response_schema_serializes_uuid():
    from app.modules.directory.schemas import CompanyResponse

    payload = {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Acme",
        "is_active": True,
        "tags": [],
        "project_roles": [],
        "created_at": "2026-05-13T12:00:00Z",
        "updated_at": "2026-05-13T12:00:00Z",
    }
    parsed = CompanyResponse.model_validate(payload)
    assert str(parsed.id) == "11111111-1111-1111-1111-111111111111"
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -k "schema" -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `schemas.py`**

```python
"""Pydantic schemas for the directory companies API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CompanyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    abbreviated_name: str | None = Field(default=None, max_length=64)
    dba: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=2)
    zip: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=32)
    fax: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)
    primary_contact_id: uuid.UUID | None = None
    entity_type: str | None = Field(default=None, max_length=64)
    license_number: str | None = Field(default=None, max_length=64)
    labor_union: str | None = Field(default=None, max_length=128)
    logo_url: str | None = Field(default=None, max_length=512)
    tags: list[str] = Field(default_factory=list)
    project_roles: list[str] = Field(default_factory=list)


class CompanyCreate(CompanyBase):
    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    abbreviated_name: str | None = Field(default=None, max_length=64)
    dba: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=2)
    zip: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=32)
    fax: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)
    primary_contact_id: uuid.UUID | None = None
    entity_type: str | None = Field(default=None, max_length=64)
    license_number: str | None = Field(default=None, max_length=64)
    labor_union: str | None = Field(default=None, max_length=128)
    logo_url: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    project_roles: list[str] | None = None
    is_active: bool | None = None


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None


class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 4: Tests pass**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -k "schema" -v`
Expected: 2 passed.

---

### Task 5: `CompanyRepository` + `CompanyService`

**Files:**
- Create: `backend/app/modules/directory/repository.py`
- Create: `backend/app/modules/directory/service.py`

- [ ] **Step 1: Write service test**

Append to `backend/tests/integration/test_directory_companies.py`:

```python
@pytest.mark.asyncio
async def test_company_service_creates_and_lists(db_session: AsyncSession):
    from app.modules.directory.service import CompanyService
    from app.modules.directory.schemas import CompanyCreate

    svc = CompanyService(db_session)
    created = await svc.create(CompanyCreate(name="Acme HVAC", state="CA"), created_by=None)

    assert created.id is not None
    assert created.name == "Acme HVAC"

    listed = await svc.list_active(page=1, page_size=20)
    assert listed.total == 1
    assert listed.items[0].name == "Acme HVAC"


@pytest.mark.asyncio
async def test_company_service_soft_deletes(db_session: AsyncSession):
    from app.modules.directory.service import CompanyService
    from app.modules.directory.schemas import CompanyCreate

    svc = CompanyService(db_session)
    company = await svc.create(CompanyCreate(name="Goner Inc"), created_by=None)
    await svc.delete(company.id)

    listed_active = await svc.list_active(page=1, page_size=20)
    assert listed_active.total == 0

    fetched = await svc.get(company.id)
    assert fetched is not None
    assert fetched.is_active is False
```

- [ ] **Step 2: Tests should fail**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -k "service" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write `repository.py`**

```python
"""Data access for directory companies."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directory.models import Company


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, company: Company) -> Company:
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def get(self, company_id: uuid.UUID) -> Company | None:
        return await self._session.get(Company, company_id)

    async def list_active(
        self, *, page: int, page_size: int, q: str | None = None
    ) -> tuple[Sequence[Company], int]:
        stmt = select(Company).where(Company.is_active.is_(True))
        count_stmt = select(func.count()).select_from(Company).where(Company.is_active.is_(True))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Company.name.ilike(like))
            count_stmt = count_stmt.where(Company.name.ilike(like))
        stmt = stmt.order_by(Company.name).offset((page - 1) * page_size).limit(page_size)
        items = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return items, total

    async def soft_delete(self, company_id: uuid.UUID) -> bool:
        company = await self.get(company_id)
        if company is None:
            return False
        company.is_active = False
        await self._session.flush()
        return True
```

- [ ] **Step 4: Write `service.py`**

```python
"""Business logic for directory companies."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directory.models import Company
from app.modules.directory.repository import CompanyRepository
from app.modules.directory.schemas import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CompanyRepository(session)

    async def create(
        self, data: CompanyCreate, *, created_by: uuid.UUID | None
    ) -> CompanyResponse:
        company = Company(**data.model_dump(), created_by=created_by)
        await self._repo.add(company)
        await self._session.commit()
        return CompanyResponse.model_validate(company)

    async def get(self, company_id: uuid.UUID) -> CompanyResponse | None:
        company = await self._repo.get(company_id)
        if company is None:
            return None
        return CompanyResponse.model_validate(company)

    async def list_active(
        self, *, page: int = 1, page_size: int = 50, q: str | None = None
    ) -> CompanyListResponse:
        items, total = await self._repo.list_active(page=page, page_size=page_size, q=q)
        return CompanyListResponse(
            items=[CompanyResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self, company_id: uuid.UUID, data: CompanyUpdate
    ) -> CompanyResponse | None:
        company = await self._repo.get(company_id)
        if company is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self._session.commit()
        await self._session.refresh(company)
        return CompanyResponse.model_validate(company)

    async def delete(self, company_id: uuid.UUID) -> bool:
        ok = await self._repo.soft_delete(company_id)
        if ok:
            await self._session.commit()
        return ok
```

- [ ] **Step 5: Tests pass**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -k "service" -v`
Expected: 2 passed.

---

### Task 6: Companies router

**Files:**
- Create: `backend/app/modules/directory/router.py`

- [ ] **Step 1: Write router test**

Append to `backend/tests/integration/test_directory_companies.py`:

```python
@pytest.mark.asyncio
async def test_companies_router_lists_and_creates(
    authed_editor_client,  # fixture: AsyncClient logged in as editor
):
    res = await authed_editor_client.get("/api/v1/directory/companies/")
    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}

    res = await authed_editor_client.post(
        "/api/v1/directory/companies/",
        json={"name": "Foo Co", "state": "CA"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Foo Co"
    assert body["state"] == "CA"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_companies_router_rejects_viewer_create(authed_viewer_client):
    res = await authed_viewer_client.post(
        "/api/v1/directory/companies/", json={"name": "Forbidden"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_companies_router_soft_delete_admin_only(
    authed_admin_client, authed_editor_client
):
    create = await authed_editor_client.post(
        "/api/v1/directory/companies/", json={"name": "Doomed"}
    )
    company_id = create.json()["id"]

    forbidden = await authed_editor_client.delete(f"/api/v1/directory/companies/{company_id}")
    assert forbidden.status_code == 403

    ok = await authed_admin_client.delete(f"/api/v1/directory/companies/{company_id}")
    assert ok.status_code == 204
```

(`authed_*_client` fixtures already exist in `backend/tests/integration/_auth_helpers.py` — check there for exact fixture names and adjust imports.)

- [ ] **Step 2: Tests fail**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -k "router" -v`
Expected: FAIL (router not registered yet — either ImportError or 404).

- [ ] **Step 3: Write `router.py`**

```python
"""Directory companies API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUserId, RequirePermission, SessionDep
from app.modules.directory.schemas import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.modules.directory.service import CompanyService


router = APIRouter(prefix="/companies", tags=["directory.companies"])


def _svc(session: SessionDep) -> CompanyService:
    return CompanyService(session)


@router.get(
    "/",
    response_model=CompanyListResponse,
    dependencies=[Depends(RequirePermission("companies.list"))],
)
async def list_companies(
    session: SessionDep,
    q: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CompanyListResponse:
    return await _svc(session).list_active(page=page, page_size=page_size, q=q)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[Depends(RequirePermission("companies.read"))],
)
async def get_company(company_id: uuid.UUID, session: SessionDep) -> CompanyResponse:
    company = await _svc(session).get(company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "company not found")
    return company


@router.post(
    "/",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("companies.create"))],
)
async def create_company(
    data: CompanyCreate,
    user_id: CurrentUserId,
    session: SessionDep,
) -> CompanyResponse:
    return await _svc(session).create(data, created_by=uuid.UUID(user_id))


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[Depends(RequirePermission("companies.update"))],
)
async def update_company(
    company_id: uuid.UUID, data: CompanyUpdate, session: SessionDep
) -> CompanyResponse:
    updated = await _svc(session).update(company_id, data)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "company not found")
    return updated


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("companies.delete"))],
)
async def delete_company(company_id: uuid.UUID, session: SessionDep) -> None:
    ok = await _svc(session).delete(company_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "company not found")
```

---

### Task 7: Register directory module in `main.py`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Find the existing router-registration block**

Run: `cd backend && grep -n "register_user_permissions\|users_router" app/main.py | head -10`
Expected: a line like `app.include_router(users_router, prefix="/api/v1/users", tags=["users"])` and an adjacent call to `register_user_permissions()`.

- [ ] **Step 2: Add directory imports**

Add near the other `from app.modules.*` imports in `app/main.py`:

```python
from app.modules.directory.permissions import register_directory_permissions
from app.modules.directory.router import router as directory_companies_router
```

- [ ] **Step 3: Register permissions at app startup**

Find the existing call to `register_user_permissions()` (and similar). Add `register_directory_permissions()` adjacent.

- [ ] **Step 4: Mount the router**

Find the existing `app.include_router(users_router, ...)` line. Add:

```python
app.include_router(
    directory_companies_router, prefix="/api/v1/directory", tags=["directory"]
)
```

- [ ] **Step 5: Run all directory tests**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -v`
Expected: All pass (model + schema + service + router + permission gating).

- [ ] **Step 6: Commit (Commit 2)**

```bash
cd C:/dev/ON_NEXUS_ERP
git add backend/app/modules/directory/schemas.py \
        backend/app/modules/directory/repository.py \
        backend/app/modules/directory/service.py \
        backend/app/modules/directory/router.py \
        backend/app/main.py \
        backend/tests/integration/test_directory_companies.py
git commit -m "feat(directory): companies CRUD API + RBAC + integration tests

Adds /api/v1/directory/companies/{list,read,create,update,delete}
endpoints gated by per-action permissions on the existing Role
hierarchy. CompanyService wraps a CompanyRepository for data access;
DELETE is a soft delete (is_active=false). Integration tests cover
the full CRUD path and the 403 cases for viewer/editor against
admin-only endpoints.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Self-host fonts under `public/fonts/`

**Files:**
- Create: `frontend/public/fonts/DMSerifDisplay-Regular.woff2`
- Create: `frontend/public/fonts/IBMPlexSans-Regular.woff2`
- Create: `frontend/public/fonts/IBMPlexSans-Bold.woff2`
- Create: `frontend/public/fonts/JetBrainsMono-Regular.woff2`

- [ ] **Step 1: Download fonts from Google Fonts (or vendor sources)**

```bash
cd C:/dev/ON_NEXUS_ERP/frontend/public
mkdir -p fonts
# DM Serif Display — open-source via Google Fonts API
curl -fsSL "https://fonts.gstatic.com/s/dmserifdisplay/v15/-nFnOHM81r4j6k0gjAW3mujVU2B2K_d709jy92k.woff2" -o fonts/DMSerifDisplay-Regular.woff2
# IBM Plex Sans Regular
curl -fsSL "https://fonts.gstatic.com/s/ibmplexsans/v19/zYXgKVElMYYaJe8bpLHnCwDKtdbUFI5NadY.woff2" -o fonts/IBMPlexSans-Regular.woff2
# IBM Plex Sans Bold
curl -fsSL "https://fonts.gstatic.com/s/ibmplexsans/v19/zYX9KVElMYYaJe8bpLHnCwDKjQ76M8VFmsg.woff2" -o fonts/IBMPlexSans-Bold.woff2
# JetBrains Mono Regular
curl -fsSL "https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjOVfFI.woff2" -o fonts/JetBrainsMono-Regular.woff2
```

If the exact CDN URLs above 404 (Google Fonts rotates filenames), fall back to https://fonts.bunny.net or https://google-webfonts-helper.herokuapp.com to get current WOFF2 URLs for the same families.

- [ ] **Step 2: Verify file sizes are sane (each 20-60 KB)**

Run: `ls -lah frontend/public/fonts/`
Expected: 4 files, each 15-100 KB.

---

### Task 9: Theme tokens + fonts CSS

**Files:**
- Create: `frontend/src/features/directory/theme/fonts.css`
- Create: `frontend/src/features/directory/theme/tokens.css`

- [ ] **Step 1: Write `fonts.css`**

```css
@font-face {
  font-family: 'DM Serif Display';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/DMSerifDisplay-Regular.woff2') format('woff2');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/IBMPlexSans-Regular.woff2') format('woff2');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/fonts/IBMPlexSans-Bold.woff2') format('woff2');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/JetBrainsMono-Regular.woff2') format('woff2');
}
```

- [ ] **Step 2: Write `tokens.css`**

```css
[data-route="directory"] {
  --bg-base: #0A0E1A;
  --bg-surface: #111827;
  --bg-elevated: #1C2333;
  --border-subtle: #1F2937;
  --border-strong: #374151;
  --text-primary: #E5E7EB;
  --text-secondary: #9CA3AF;
  --text-muted: #6B7280;
  --accent-primary: #3B82F6;
  --accent-secondary: #F59E0B;
  --status-active: #10B981;
  --status-warn: #F59E0B;
  --status-danger: #EF4444;
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-body: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;

  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-body);
  min-height: 100vh;
}

[data-route="directory"] h1,
[data-route="directory"] h2 {
  font-family: var(--font-display);
  color: var(--text-primary);
}

[data-route="directory"] .mono,
[data-route="directory"] td.numeric,
[data-route="directory"] .id,
[data-route="directory"] .date,
[data-route="directory"] .phone {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Wrap Tailwind-default bg-white from ported children */
[data-route="directory"] .bg-white { background: var(--bg-surface) !important; }
[data-route="directory"] .text-gray-900 { color: var(--text-primary) !important; }
[data-route="directory"] .text-gray-700 { color: var(--text-secondary) !important; }
[data-route="directory"] .text-gray-500 { color: var(--text-muted) !important; }
[data-route="directory"] .border-gray-200 { border-color: var(--border-subtle) !important; }
[data-route="directory"] .border-gray-300 { border-color: var(--border-strong) !important; }
```

The last `bg-white` / `text-gray-*` overrides are the Risk-R3 mitigation: they retrofit the Tailwind defaults that `UserManagementPage` and `ContactsPage` use, so the ported tabs render correctly in the dark shell.

- [ ] **Step 3: Commit (Commit 3)**

```bash
git add frontend/public/fonts/ \
        frontend/src/features/directory/theme/fonts.css \
        frontend/src/features/directory/theme/tokens.css
git commit -m "feat(directory): self-hosted fonts + scoped dark theme tokens

DM Serif Display (headings), IBM Plex Sans (body), JetBrains Mono
(monospace) self-hosted under public/fonts/. Theme variables scoped
to [data-route='directory'] so other routes are untouched. Tailwind
default bg-white / text-gray-* are remapped within the scope to handle
ported users/contacts pages without rewriting them.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Shared UI primitives

**Files:**
- Create: `frontend/src/features/directory/components/SlideOver.tsx`
- Create: `frontend/src/features/directory/components/StatusBadge.tsx`
- Create: `frontend/src/features/directory/components/KpiRow.tsx`
- Create: `frontend/src/features/directory/components/DirectoryTable.tsx`

- [ ] **Step 1: Write `SlideOver.tsx`**

```tsx
import { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface SlideOverProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  widthClass?: string; // tailwind width utility, default w-[640px]
}

export function SlideOver({ open, onClose, title, children, widthClass = 'w-[640px]' }: SlideOverProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex" aria-modal="true" role="dialog">
      <div
        className="flex-1 bg-black/40 transition-opacity duration-300"
        onClick={onClose}
        aria-label="Close panel backdrop"
      />
      <aside
        className={`${widthClass} h-full overflow-y-auto shadow-2xl transition-transform duration-300 ease-out`}
        style={{ background: 'var(--bg-surface)', color: 'var(--text-primary)' }}
      >
        <header
          className="sticky top-0 flex items-center justify-between px-6 py-4 border-b"
          style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-elevated)' }}
        >
          <h2 style={{ fontFamily: 'var(--font-display)' }} className="text-xl">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="px-2 py-1 hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
            aria-label="Close"
          >
            ✕
          </button>
        </header>
        <div className="p-6">{children}</div>
      </aside>
    </div>,
    document.body
  );
}
```

- [ ] **Step 2: Write `StatusBadge.tsx`**

```tsx
type StatusKind = 'active' | 'inactive' | 'pending' | 'warn' | 'danger';

const TONE: Record<StatusKind, { dot: string; text: string; bg: string }> = {
  active:   { dot: 'var(--status-active)', text: 'var(--status-active)', bg: 'rgba(16,185,129,0.10)' },
  inactive: { dot: 'var(--text-muted)',    text: 'var(--text-muted)',    bg: 'rgba(107,114,128,0.10)' },
  pending:  { dot: 'var(--accent-primary)',text: 'var(--accent-primary)',bg: 'rgba(59,130,246,0.10)' },
  warn:     { dot: 'var(--status-warn)',   text: 'var(--status-warn)',   bg: 'rgba(245,158,11,0.10)' },
  danger:   { dot: 'var(--status-danger)', text: 'var(--status-danger)', bg: 'rgba(239,68,68,0.10)' },
};

export function StatusBadge({ kind, label }: { kind: StatusKind; label: string }) {
  const tone = TONE[kind];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium"
      style={{ background: tone.bg, color: tone.text }}
    >
      <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: tone.dot }} />
      {label}
    </span>
  );
}
```

- [ ] **Step 3: Write `KpiRow.tsx`**

```tsx
interface Kpi {
  label: string;
  value: number | string;
  trend?: { delta: number; direction: 'up' | 'down' | 'flat' };
}

export function KpiRow({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="p-4 border rounded"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border-subtle)' }}
        >
          <div className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            {k.label}
          </div>
          <div
            className="mt-1 text-2xl"
            style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}
          >
            {k.value}
          </div>
          {k.trend && (
            <div
              className="mt-1 text-xs"
              style={{
                color:
                  k.trend.direction === 'up'
                    ? 'var(--status-active)'
                    : k.trend.direction === 'down'
                    ? 'var(--status-danger)'
                    : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {k.trend.direction === 'up' ? '▲' : k.trend.direction === 'down' ? '▼' : '—'}{' '}
              {Math.abs(k.trend.delta)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Write `DirectoryTable.tsx`**

```tsx
import { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
  numeric?: boolean;
  pinRight?: boolean;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

export function DirectoryTable<T>({ rows, columns, rowKey, onRowClick, emptyMessage = 'No records' }: Props<T>) {
  return (
    <div
      className="overflow-auto border rounded"
      style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-surface)' }}
    >
      <table className="w-full text-sm">
        <thead
          className="sticky top-0 z-10"
          style={{ background: 'var(--bg-elevated)' }}
        >
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`text-left font-semibold px-4 py-3 ${c.align === 'right' ? 'text-right' : ''} ${
                  c.pinRight ? 'sticky right-0' : ''
                } ${c.className ?? ''}`}
                style={{
                  color: 'var(--text-secondary)',
                  borderBottom: '1px solid var(--border-subtle)',
                  background: c.pinRight ? 'var(--bg-elevated)' : undefined,
                }}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="text-center py-12"
                style={{ color: 'var(--text-muted)' }}
              >
                {emptyMessage}
              </td>
            </tr>
          )}
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className="transition-colors duration-150 cursor-pointer"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
              onMouseOver={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseOut={(e) => (e.currentTarget.style.background = '')}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={`px-4 py-3 ${c.align === 'right' ? 'text-right' : ''} ${
                    c.numeric ? 'numeric' : ''
                  } ${c.pinRight ? 'sticky right-0' : ''} ${c.className ?? ''}`}
                  style={{
                    color: 'var(--text-primary)',
                    background: c.pinRight ? 'var(--bg-surface)' : undefined,
                  }}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 5: Quick typecheck**

Run: `cd frontend && npm run typecheck`
Expected: No errors related to the new files. (Other unrelated errors are not Wave 1's job — only fail if our new files are red.)

- [ ] **Step 6: Commit (Commit 4)**

```bash
git add frontend/src/features/directory/components/
git commit -m "feat(directory): shared UI primitives (SlideOver, table, badge, KPIs)

SlideOver animates from right via Tailwind transition; closes on Esc
and backdrop click. StatusBadge enforces dot+text+color rule from the
spec. KpiRow renders 4 monospace cells with trend chevrons.
DirectoryTable supports sticky header, right-pinned actions, mono
numeric columns, and 150ms row hover.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: TypeScript API client for companies

**Files:**
- Create: `frontend/src/features/directory/api/companies.ts`

- [ ] **Step 1: Write the client**

```ts
import { apiDelete, apiGet, apiPatch, apiPost } from '@/shared/lib/api';

export interface Company {
  id: string;
  name: string;
  abbreviated_name: string | null;
  dba: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  phone: string | null;
  fax: string | null;
  email: string | null;
  website: string | null;
  primary_contact_id: string | null;
  entity_type: string | null;
  license_number: string | null;
  labor_union: string | null;
  logo_url: string | null;
  tags: string[];
  project_roles: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface CompanyListResponse {
  items: Company[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompanyCreatePayload {
  name: string;
  abbreviated_name?: string;
  dba?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  phone?: string;
  fax?: string;
  email?: string;
  website?: string;
  primary_contact_id?: string;
  entity_type?: string;
  license_number?: string;
  labor_union?: string;
  logo_url?: string;
  tags?: string[];
  project_roles?: string[];
}

export type CompanyUpdatePayload = Partial<CompanyCreatePayload> & { is_active?: boolean };

export async function listCompanies(params?: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<CompanyListResponse> {
  const search = new URLSearchParams();
  if (params?.q) search.set('q', params.q);
  if (params?.page) search.set('page', String(params.page));
  if (params?.page_size) search.set('page_size', String(params.page_size));
  return apiGet<CompanyListResponse>(`/api/v1/directory/companies/?${search.toString()}`);
}

export async function getCompany(id: string): Promise<Company> {
  return apiGet<Company>(`/api/v1/directory/companies/${id}`);
}

export async function createCompany(payload: CompanyCreatePayload): Promise<Company> {
  return apiPost<Company>(`/api/v1/directory/companies/`, payload);
}

export async function updateCompany(id: string, payload: CompanyUpdatePayload): Promise<Company> {
  return apiPatch<Company>(`/api/v1/directory/companies/${id}`, payload);
}

export async function deleteCompany(id: string): Promise<void> {
  return apiDelete(`/api/v1/directory/companies/${id}`);
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no new errors.

---

### Task 12: `DirectoryPage` + `DirectoryTabs`

**Files:**
- Create: `frontend/src/features/directory/DirectoryPage.tsx`
- Create: `frontend/src/features/directory/DirectoryTabs.tsx`
- Create: `frontend/src/features/directory/index.ts`

- [ ] **Step 1: Write `DirectoryTabs.tsx`**

```tsx
import { useSearchParams } from 'react-router-dom';

export type DirectoryTab = 'users' | 'contacts' | 'companies' | 'groups' | 'inactive';

const TABS: { id: DirectoryTab; label: string }[] = [
  { id: 'users', label: 'Users' },
  { id: 'contacts', label: 'Contacts' },
  { id: 'companies', label: 'Companies' },
  { id: 'groups', label: 'Distribution Groups' },
  { id: 'inactive', label: 'Inactive' },
];

export function useDirectoryTab(): [DirectoryTab, (t: DirectoryTab) => void] {
  const [params, setParams] = useSearchParams();
  const current = (params.get('tab') as DirectoryTab) || 'users';
  const setTab = (t: DirectoryTab) => {
    const next = new URLSearchParams(params);
    next.set('tab', t);
    setParams(next, { replace: false });
  };
  return [current, setTab];
}

export function DirectoryTabs() {
  const [current, setTab] = useDirectoryTab();
  return (
    <nav
      className="flex gap-1 border-b mb-6"
      style={{ borderColor: 'var(--border-subtle)' }}
      role="tablist"
    >
      {TABS.map((t) => {
        const active = current === t.id;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={active}
            onClick={() => setTab(t.id)}
            className="px-4 py-2 transition-colors duration-150"
            style={{
              color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderBottom: active ? '2px solid var(--accent-primary)' : '2px solid transparent',
              fontWeight: active ? 600 : 400,
              marginBottom: '-1px',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Write `DirectoryPage.tsx`**

```tsx
import './theme/fonts.css';
import './theme/tokens.css';

import { DirectoryTabs, useDirectoryTab } from './DirectoryTabs';
import { UsersTab } from './tabs/UsersTab';
import { ContactsTab } from './tabs/ContactsTab';
import { CompaniesTab } from './tabs/CompaniesTab';
import { DistributionGroupsTab } from './tabs/DistributionGroupsTab';
import { InactiveTab } from './tabs/InactiveTab';

export function DirectoryPage() {
  const [tab] = useDirectoryTab();

  return (
    <div data-route="directory" className="min-h-screen px-8 py-6">
      <header className="mb-6 flex items-baseline justify-between">
        <h1 className="text-3xl">Project Directory</h1>
      </header>
      <DirectoryTabs />
      {tab === 'users' && <UsersTab />}
      {tab === 'contacts' && <ContactsTab />}
      {tab === 'companies' && <CompaniesTab />}
      {tab === 'groups' && <DistributionGroupsTab />}
      {tab === 'inactive' && <InactiveTab />}
    </div>
  );
}
```

- [ ] **Step 3: Write placeholder tabs and index**

`frontend/src/features/directory/tabs/DistributionGroupsTab.tsx`:

```tsx
export function DistributionGroupsTab() {
  return (
    <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
      <p>Distribution groups arrive in Wave 3.</p>
    </div>
  );
}
```

`frontend/src/features/directory/tabs/InactiveTab.tsx`:

```tsx
export function InactiveTab() {
  return (
    <div className="py-16 text-center" style={{ color: 'var(--text-muted)' }}>
      <p>Inactive records view arrives in Wave 3.</p>
    </div>
  );
}
```

`frontend/src/features/directory/index.ts`:

```ts
export { DirectoryPage } from './DirectoryPage';
```

(`UsersTab`, `ContactsTab`, `CompaniesTab` will be created in subsequent tasks; the imports will resolve only once those files exist. That's fine — we'll typecheck after Task 16.)

---

### Task 13: `CompaniesTab.tsx`

**Files:**
- Create: `frontend/src/features/directory/tabs/CompaniesTab.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Column, DirectoryTable } from '../components/DirectoryTable';
import { KpiRow } from '../components/KpiRow';
import { StatusBadge } from '../components/StatusBadge';
import { Company, listCompanies } from '../api/companies';
import { AddEditCompanySlideOver } from '../slideovers/AddEditCompanySlideOver';

export function CompaniesTab() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Company | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listCompanies({ q: q || undefined, page: 1, page_size: 50 });
      setCompanies(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    load();
  }, [load]);

  const kpis = useMemo(
    () => [
      { label: 'Total Companies', value: total },
      { label: 'Active', value: companies.filter((c) => c.is_active).length },
      { label: 'With Email', value: companies.filter((c) => c.email).length },
      { label: 'With License', value: companies.filter((c) => c.license_number).length },
    ],
    [companies, total]
  );

  const columns: Column<Company>[] = [
    {
      key: 'name',
      header: 'Company',
      cell: (c) => (
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded flex items-center justify-center text-xs font-semibold"
            style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
          >
            {c.name.slice(0, 2).toUpperCase()}
          </div>
          <button
            className="text-left hover:underline"
            style={{ color: 'var(--accent-primary)' }}
            onClick={(e) => {
              e.stopPropagation();
              setEditing(c);
            }}
          >
            {c.name}
          </button>
        </div>
      ),
    },
    { key: 'entity_type', header: 'Type', cell: (c) => c.entity_type ?? '—' },
    { key: 'phone', header: 'Phone', cell: (c) => c.phone ?? '—', className: 'phone' },
    { key: 'city', header: 'City / State', cell: (c) => `${c.city ?? '—'}, ${c.state ?? '—'}` },
    {
      key: 'status',
      header: 'Status',
      cell: (c) => (
        <StatusBadge
          kind={c.is_active ? 'active' : 'inactive'}
          label={c.is_active ? 'Active' : 'Inactive'}
        />
      ),
    },
  ];

  return (
    <div>
      <KpiRow kpis={kpis} />
      <div className="mb-4 flex items-center justify-between">
        <input
          type="search"
          placeholder="Search companies…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="px-3 py-2 rounded border w-80"
          style={{
            background: 'var(--bg-surface)',
            borderColor: 'var(--border-strong)',
            color: 'var(--text-primary)',
          }}
        />
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2 rounded font-medium"
          style={{ background: 'var(--accent-primary)', color: 'white' }}
        >
          + Add Company
        </button>
      </div>

      <DirectoryTable
        rows={companies}
        columns={columns}
        rowKey={(c) => c.id}
        onRowClick={(c) => setEditing(c)}
        emptyMessage={loading ? 'Loading…' : 'No companies yet. Click "Add Company" to begin.'}
      />

      <AddEditCompanySlideOver
        open={creating || editing !== null}
        company={editing}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSaved={() => {
          setCreating(false);
          setEditing(null);
          load();
        }}
      />
    </div>
  );
}
```

---

### Task 14: `AddEditCompanySlideOver` (General tab + 4 placeholders)

**Files:**
- Create: `frontend/src/features/directory/slideovers/AddEditCompanySlideOver.tsx`

- [ ] **Step 1: Write the slide-over**

```tsx
import { useEffect, useState } from 'react';
import { SlideOver } from '../components/SlideOver';
import {
  Company,
  CompanyCreatePayload,
  createCompany,
  updateCompany,
} from '../api/companies';

type Tab = 'general' | 'users' | 'bidder' | 'insurance' | 'history';

const TABS: { id: Tab; label: string; available: boolean }[] = [
  { id: 'general', label: 'General', available: true },
  { id: 'users', label: 'Users', available: false },
  { id: 'bidder', label: 'Bidder Info', available: false },
  { id: 'insurance', label: 'Insurance', available: false },
  { id: 'history', label: 'Change History', available: false },
];

interface Props {
  open: boolean;
  company: Company | null;
  onClose: () => void;
  onSaved: () => void;
}

export function AddEditCompanySlideOver({ open, company, onClose, onSaved }: Props) {
  const [tab, setTab] = useState<Tab>('general');
  const [form, setForm] = useState<CompanyCreatePayload>({ name: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (company) {
      setForm({
        name: company.name,
        abbreviated_name: company.abbreviated_name ?? undefined,
        dba: company.dba ?? undefined,
        address: company.address ?? undefined,
        city: company.city ?? undefined,
        state: company.state ?? undefined,
        zip: company.zip ?? undefined,
        phone: company.phone ?? undefined,
        fax: company.fax ?? undefined,
        email: company.email ?? undefined,
        website: company.website ?? undefined,
        entity_type: company.entity_type ?? undefined,
        license_number: company.license_number ?? undefined,
        labor_union: company.labor_union ?? undefined,
      });
    } else {
      setForm({ name: '' });
    }
    setTab('general');
    setError(null);
  }, [company, open]);

  const update = <K extends keyof CompanyCreatePayload>(k: K, v: CompanyCreatePayload[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const onSave = async () => {
    setError(null);
    if (!form.name.trim()) {
      setError('Company name is required');
      return;
    }
    setSaving(true);
    try {
      if (company) await updateCompany(company.id, form);
      else await createCompany(form);
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SlideOver
      open={open}
      onClose={onClose}
      title={company ? `Edit Company — ${company.name}` : 'Add Company'}
      widthClass="w-[720px]"
    >
      <nav
        className="flex gap-1 border-b mb-6 -mx-6 px-6"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            disabled={!t.available}
            title={t.available ? '' : 'Available in Wave 2/3'}
            onClick={() => t.available && setTab(t.id)}
            className="px-3 py-2 transition-colors duration-150"
            style={{
              color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: tab === t.id ? '2px solid var(--accent-primary)' : '2px solid transparent',
              cursor: t.available ? 'pointer' : 'not-allowed',
              opacity: t.available ? 1 : 0.5,
              marginBottom: '-1px',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab !== 'general' && (
        <div className="py-12 text-center" style={{ color: 'var(--text-muted)' }}>
          This tab arrives in {tab === 'history' ? 'Wave 3' : 'Wave 2'}.
        </div>
      )}

      {tab === 'general' && (
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Name *" value={form.name} onChange={(v) => update('name', v)} />
          <FormField
            label="Abbreviated Name"
            value={form.abbreviated_name ?? ''}
            onChange={(v) => update('abbreviated_name', v || undefined)}
          />
          <FormField
            label="DBA"
            value={form.dba ?? ''}
            onChange={(v) => update('dba', v || undefined)}
          />
          <FormField
            label="Entity Type"
            value={form.entity_type ?? ''}
            onChange={(v) => update('entity_type', v || undefined)}
          />
          <FormField
            label="Address"
            value={form.address ?? ''}
            onChange={(v) => update('address', v || undefined)}
            colSpan
          />
          <FormField
            label="City"
            value={form.city ?? ''}
            onChange={(v) => update('city', v || undefined)}
          />
          <div className="grid grid-cols-2 gap-2">
            <FormField
              label="State"
              value={form.state ?? ''}
              onChange={(v) => update('state', v || undefined)}
            />
            <FormField
              label="ZIP"
              value={form.zip ?? ''}
              onChange={(v) => update('zip', v || undefined)}
            />
          </div>
          <FormField
            label="Phone"
            value={form.phone ?? ''}
            onChange={(v) => update('phone', v || undefined)}
            mono
          />
          <FormField
            label="Fax"
            value={form.fax ?? ''}
            onChange={(v) => update('fax', v || undefined)}
            mono
          />
          <FormField
            label="Email"
            value={form.email ?? ''}
            onChange={(v) => update('email', v || undefined)}
          />
          <FormField
            label="Website"
            value={form.website ?? ''}
            onChange={(v) => update('website', v || undefined)}
            colSpan
          />
          <FormField
            label="License Number"
            value={form.license_number ?? ''}
            onChange={(v) => update('license_number', v || undefined)}
            mono
          />
          <FormField
            label="Labor Union"
            value={form.labor_union ?? ''}
            onChange={(v) => update('labor_union', v || undefined)}
          />
        </div>
      )}

      {error && (
        <p className="mt-4 text-sm" style={{ color: 'var(--status-danger)' }}>
          {error}
        </p>
      )}

      <footer className="mt-8 flex justify-end gap-2 pt-4 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
        <button
          onClick={onClose}
          className="px-4 py-2 rounded"
          style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
          disabled={saving}
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={saving}
          className="px-4 py-2 rounded font-medium"
          style={{ background: 'var(--accent-primary)', color: 'white', opacity: saving ? 0.6 : 1 }}
        >
          {saving ? 'Saving…' : company ? 'Save Changes' : 'Create Company'}
        </button>
      </footer>
    </SlideOver>
  );
}

function FormField({
  label,
  value,
  onChange,
  mono,
  colSpan,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  mono?: boolean;
  colSpan?: boolean;
}) {
  return (
    <label className={`flex flex-col gap-1 ${colSpan ? 'col-span-2' : ''}`}>
      <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 rounded border"
        style={{
          background: 'var(--bg-elevated)',
          borderColor: 'var(--border-strong)',
          color: 'var(--text-primary)',
          fontFamily: mono ? 'var(--font-mono)' : 'inherit',
        }}
      />
    </label>
  );
}
```

- [ ] **Step 2: Commit (Commit 5)**

```bash
git add frontend/src/features/directory/DirectoryPage.tsx \
        frontend/src/features/directory/DirectoryTabs.tsx \
        frontend/src/features/directory/index.ts \
        frontend/src/features/directory/api/companies.ts \
        frontend/src/features/directory/tabs/CompaniesTab.tsx \
        frontend/src/features/directory/tabs/DistributionGroupsTab.tsx \
        frontend/src/features/directory/tabs/InactiveTab.tsx \
        frontend/src/features/directory/slideovers/AddEditCompanySlideOver.tsx
git commit -m "feat(directory): page shell + companies tab + slide-over

DirectoryPage applies data-route='directory' to scope the theme tokens.
Tab state syncs to ?tab= query param so external links and 301 redirects
work. CompaniesTab lists/searches/creates against /api/v1/directory/
companies; AddEditCompanySlideOver populates the General tab (Wave 1)
and disables Users/Bidder Info/Insurance/History tabs with Wave-2/3
tooltips. Distribution Groups and Inactive tabs render Wave-3
placeholders.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

(The build won't pass yet — `UsersTab` and `ContactsTab` are missing. Tasks 15-16 fix that.)

---

### Task 15: Move `UserManagementPage` to `directory/tabs/UsersTab.tsx`

**Files:**
- Create: `frontend/src/features/directory/tabs/UsersTab.tsx` (via `git mv` then rename export)
- Delete: `frontend/src/features/users/UserManagementPage.tsx`
- Modify: `frontend/src/features/users/index.ts` (remove `UserManagementPage` export)

- [ ] **Step 1: Inspect existing exports**

Run: `cd C:/dev/ON_NEXUS_ERP && cat frontend/src/features/users/index.ts`
Expected output: an `export { UserManagementPage } from './UserManagementPage';` line (and possibly others). Note any other exports so you don't break them.

- [ ] **Step 2: Grep for imports of `UserManagementPage`**

Run: `cd C:/dev/ON_NEXUS_ERP && grep -rn "UserManagementPage" frontend/src --include="*.ts" --include="*.tsx"`
Expected: `frontend/src/app/App.tsx` references it (we'll update in Task 17), plus the source files themselves. If anything else references it, note them — they all need updates.

- [ ] **Step 3: Move the file with `git mv`**

```bash
cd C:/dev/ON_NEXUS_ERP
git mv frontend/src/features/users/UserManagementPage.tsx \
       frontend/src/features/directory/tabs/UsersTab.tsx
```

- [ ] **Step 4: Rename the exported component**

Edit `frontend/src/features/directory/tabs/UsersTab.tsx`:
- Find `export function UserManagementPage(` → replace with `export function UsersTab(`
- If the file exports a named `UserManagementPage` via `export { UserManagementPage }`, change to `UsersTab`
- Fix import paths if the old file used `./` relative imports — paths shift by one directory level. For example, `'./api'` becomes `'@/features/users/api'`, `'./components/UserDetailSlideOver'` becomes `'@/features/users/components/UserDetailSlideOver'`. **Critical: any sibling files (`components/`, `hooks/`, etc.) under `features/users/` stay where they are; the moved file just references them via the `@/` alias.**

Run: `grep -n "from '\." frontend/src/features/directory/tabs/UsersTab.tsx` to find all relative imports that need rewriting.

- [ ] **Step 5: Update `frontend/src/features/users/index.ts`**

Remove the `UserManagementPage` export. If `index.ts` only exported `UserManagementPage`, delete the file entirely. Otherwise leave remaining exports (the `api.ts` types are likely re-exported and should stay).

- [ ] **Step 6: Typecheck (will still fail on App.tsx — that's Task 17)**

Run: `cd frontend && npm run typecheck 2>&1 | grep -E "directory|users" | head -20`
Expected: no errors *inside* `features/directory/tabs/UsersTab.tsx`. App.tsx still has a broken import of `UserManagementPage` — that's expected; Task 17 fixes it.

---

### Task 16: Move `ContactsPage` to `directory/tabs/ContactsTab.tsx`

**Files:**
- Create: `frontend/src/features/directory/tabs/ContactsTab.tsx` (via `git mv`)
- Delete: `frontend/src/features/contacts/ContactsPage.tsx`
- Modify: `frontend/src/features/contacts/index.ts`

- [ ] **Step 1: Grep for imports**

Run: `cd C:/dev/ON_NEXUS_ERP && grep -rn "ContactsPage" frontend/src --include="*.ts" --include="*.tsx"`

- [ ] **Step 2: Move via `git mv`**

```bash
cd C:/dev/ON_NEXUS_ERP
git mv frontend/src/features/contacts/ContactsPage.tsx \
       frontend/src/features/directory/tabs/ContactsTab.tsx
```

- [ ] **Step 3: Rename export + fix relative imports**

Edit `frontend/src/features/directory/tabs/ContactsTab.tsx`:
- `export function ContactsPage(` → `export function ContactsTab(`
- Rewrite any `./` relative imports inside the moved file to `@/features/contacts/...` (e.g., `./api` → `@/features/contacts/api`).

- [ ] **Step 4: Update `frontend/src/features/contacts/index.ts`**

Remove the `ContactsPage` export. Keep any other exports (likely `api.ts` types).

- [ ] **Step 5: Commit (Commit 6)**

```bash
cd C:/dev/ON_NEXUS_ERP
git add -A frontend/src/features/users/ \
          frontend/src/features/contacts/ \
          frontend/src/features/directory/tabs/UsersTab.tsx \
          frontend/src/features/directory/tabs/ContactsTab.tsx
git commit -m "feat(directory): move users + contacts pages into directory tabs

git-mv moves preserve file history. UserManagementPage → UsersTab,
ContactsPage → ContactsTab. Relative imports inside the moved files
rewritten to @/-aliased paths so siblings (api.ts, components/) stay
in their original feature directories. App.tsx still imports the old
names — fixed in the next commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: App.tsx routing — register `/directory`, redirect old paths

**Files:**
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Find the existing route declarations**

Run: `cd C:/dev/ON_NEXUS_ERP && grep -n "UserManagementPage\|ContactsPage\|/users\|/contacts" frontend/src/app/App.tsx`

Expected output identifies:
- Line ~105: `import('@/features/contacts/ContactsPage')` lazy import
- Line ~149-150: `const UserManagementPage = lazy(...)`
- Line ~464: `<Route path="/contacts" element={...} />`
- Line ~484: `<Route path="/users" element={...} />`

- [ ] **Step 2: Replace lazy imports**

In `frontend/src/app/App.tsx`, change the contacts lazy import:

```ts
// OLD
const ContactsPage = lazy(() =>
  import('@/features/contacts/ContactsPage').then((m) => ({ default: m.ContactsPage }))
);

// NEW
const DirectoryPage = lazy(() =>
  import('@/features/directory').then((m) => ({ default: m.DirectoryPage }))
);
```

Delete the `UserManagementPage` lazy import block entirely (lines ~149-150). Delete the `ContactsPage` lazy import block.

- [ ] **Step 3: Replace the routes**

Find `<Route path="/contacts" element={<P title="Contacts"><ContactsPage /></P>} />` and replace with:

```tsx
<Route path="/contacts" element={<Navigate to="/directory?tab=contacts" replace />} />
```

Find `<Route path="/users" element={<P title="User Management"><UserManagementPage /></P>} />` and replace with:

```tsx
<Route path="/users" element={<Navigate to="/directory?tab=users" replace />} />
```

Add a new route adjacent to them:

```tsx
<Route path="/directory" element={<P title="Project Directory"><DirectoryPage /></P>} />
```

(`<P>` and `<Navigate>` are already imported at the top of App.tsx — verify with `grep "import.*Navigate\|^const P =" frontend/src/app/App.tsx`.)

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: clean. If errors, they're either:
- Lingering imports of `UserManagementPage` / `ContactsPage` elsewhere (grep and fix)
- Relative-path issues inside the moved files (revisit Task 15 Step 4 / Task 16 Step 3)

- [ ] **Step 5: Production build**

Run: `cd frontend && npm run build`
Expected: succeeds with no errors. Warnings about chunk size are OK.

---

### Task 18: Top-toolbar buttons (Add User + Add Company live; rest disabled)

**Files:**
- Modify: `frontend/src/features/directory/DirectoryPage.tsx`

- [ ] **Step 1: Add a toolbar to `DirectoryPage`**

Replace the `<header>` block in `DirectoryPage.tsx` with:

```tsx
<header className="mb-6 flex items-baseline justify-between">
  <h1 className="text-3xl">Project Directory</h1>
  <div className="flex items-center gap-2">
    <ToolbarButton primary onClick={() => fireGlobal('add-user')}>+ Add User</ToolbarButton>
    <ToolbarButton onClick={() => fireGlobal('add-company')}>+ Add Company</ToolbarButton>
    <ToolbarButton disabled tooltip="Available in Wave 3">+ Add Distribution Group</ToolbarButton>
    <ToolbarButton disabled tooltip="Available in Wave 3">Bulk Add</ToolbarButton>
    <ToolbarButton disabled tooltip="Available in Wave 3">Import People</ToolbarButton>
    <ToolbarButton disabled tooltip="Available in Wave 3">Import Companies</ToolbarButton>
    <ToolbarButton disabled tooltip="Available in Wave 3">Export</ToolbarButton>
  </div>
</header>
```

Add the `ToolbarButton` component to the same file (or a sibling under `components/`):

```tsx
function ToolbarButton({
  children,
  onClick,
  primary,
  disabled,
  tooltip,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  primary?: boolean;
  disabled?: boolean;
  tooltip?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className="px-3 py-2 rounded text-sm font-medium transition-colors duration-150"
      style={{
        background: primary ? 'var(--accent-primary)' : 'var(--bg-elevated)',
        color: primary ? 'white' : 'var(--text-primary)',
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {children}
    </button>
  );
}

function fireGlobal(action: 'add-user' | 'add-company') {
  window.dispatchEvent(new CustomEvent('directory:toolbar-action', { detail: action }));
}
```

Update `CompaniesTab` to listen for `directory:toolbar-action` and open the slide-over on `add-company`:

```tsx
// inside CompaniesTab, in a useEffect:
useEffect(() => {
  const onAction = (e: Event) => {
    if ((e as CustomEvent).detail === 'add-company') setCreating(true);
  };
  window.addEventListener('directory:toolbar-action', onAction);
  return () => window.removeEventListener('directory:toolbar-action', onAction);
}, []);
```

The `add-user` action is captured by `UsersTab` when it ports the existing "Add User" handler from `UserManagementPage`. If the ported page already has a "+ New User" button inside its own body, the toolbar button serves as a global shortcut — wire it up by adding a similar listener inside `UsersTab` calling whatever its own existing add-user action is. If that proves messy at implementation time, hide the `+ Add User` toolbar button on the `users` tab and let users use the existing in-page button instead — flag this as a small implementation-time decision.

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: clean.

---

### Task 19: Quality gates + final commit + smoke

**Files:** (no new files — verification only)

- [ ] **Step 1: Backend test suite for the directory module**

Run: `cd backend && pytest tests/integration/test_directory_companies.py -v`
Expected: all tests pass.

- [ ] **Step 2: Frontend typecheck**

Run: `cd frontend && npm run typecheck`
Expected: exit 0.

- [ ] **Step 3: Frontend production build**

Run: `cd frontend && npm run build`
Expected: exit 0, build artifacts in `frontend/dist/`.

- [ ] **Step 4: Alembic round-trip on a fresh DB**

```bash
cd backend
# Against a dev DB (set DATABASE_URL appropriately for a throwaway DB)
alembic downgrade base
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```
Expected: all steps succeed.

- [ ] **Step 5: Manual smoke test**

```bash
# Terminal 1
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173/directory and verify:
- [ ] Page loads, dark theme applied
- [ ] All 5 tabs are visible; clicking switches tabs and updates `?tab=` query param
- [ ] Companies tab: "+ Add Company" opens slide-over; creating a company persists and appears in the table after the slide-over closes
- [ ] Companies tab: clicking a company name opens the slide-over in edit mode
- [ ] Companies tab: the 4 non-General slide-over tabs are visibly disabled with "Available in Wave 2/3" tooltips
- [ ] Users tab: existing user management UI renders inside the dark shell (white surfaces should now be dark via the Tailwind overrides in `tokens.css`)
- [ ] Contacts tab: existing contacts page renders likewise
- [ ] Visiting http://localhost:5173/users redirects to `/directory?tab=users`
- [ ] Visiting http://localhost:5173/contacts redirects to `/directory?tab=contacts`
- [ ] DevTools shows DM Serif Display on the page H1, IBM Plex Sans on body, JetBrains Mono on phone/license columns

- [ ] **Step 6: Final commit (Commit 7)**

```bash
cd C:/dev/ON_NEXUS_ERP
git add frontend/src/app/App.tsx \
        frontend/src/features/directory/DirectoryPage.tsx
git commit -m "feat(directory): /directory route + 301 redirects from old paths

App router learns /directory; /users and /contacts become <Navigate>
redirects to /directory?tab=... so saved links keep working. Toolbar
buttons for Add User + Add Company are live (dispatched as global
events so tabs can wire their own create flows); Import / Export /
Bulk Add render disabled with Wave-3 tooltips.

This closes RFC 36 Wave 1 (see docs/rfc/36-directory-module.md and
docs/rfc/36a-directory-wave-1-plan.md). Waves 2 (Bidder Info +
Insurance + cron) and 3 (Groups + Inactive + Audit + parked-branch
cleanup) get their own plans.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Push to origin**

```bash
cd C:/dev/ON_NEXUS_ERP
git push origin main
```

- [ ] **Step 8: Hand off to user for prod deploy**

Tell the user Wave 1 is on `origin/main`. They run `cd frontend && vercel --prod --yes` manually (per RFC 36 L10). After they confirm the prod deploy is healthy, Wave 2 planning can begin.

---

## Spec Coverage Check (self-review)

| RFC §7 Wave 1 requirement | Plan task(s) |
|---|---|
| `directory_companies` migration | Task 3 |
| `backend/app/modules/directory/companies/` (model, schema, service, router) | Tasks 1, 2, 4, 5, 6 |
| Module router mounted under `/api/v1/directory/` | Task 7 |
| RBAC: directory.read/write/admin permissions | Task 1 (re-mapped to `companies.*` per per-module convention) |
| Self-hosted fonts under `public/fonts/` | Task 8 |
| `directory/theme/tokens.css` + `fonts.css` | Task 9 |
| `DirectoryPage.tsx` + `DirectoryTabs.tsx` | Task 12 |
| `UsersTab` port of `UserManagementPage` | Task 15 |
| `ContactsTab` port of contacts page | Task 16 |
| `CompaniesTab` + `AddEditCompanySlideOver` with General live, others placeholder | Tasks 13, 14 |
| `KpiRow`, `DirectoryTable`, `StatusBadge`, `SlideOver` components | Task 10 |
| Toolbar buttons (Wave 1 ships Add User + Add Company live; rest disabled) | Task 18 |
| App router: `/directory` + 301 redirects | Task 17 |
| Delete `features/users/UserManagementPage.tsx` and `features/contacts/ContactsPage.tsx` | Tasks 15, 16 (via `git mv`) |
| Quality gates: tsc, npm run build, pytest, alembic round-trip | Task 19 |

**Gaps surfaced during implementation that the plan flags but does not over-specify:**
1. The `+ Add User` toolbar button wiring depends on how `UserManagementPage`'s existing add-user button is structured after the port. Task 18 Step 1 documents the fallback (hide the toolbar button on Users tab if the ported page already has its own).
2. The "Crews multi-select" field flagged in RFC §9.5 is not implemented in Wave 1 — `UsersTab` ports whatever the existing page renders, which doesn't include a Crews picker. This is a Wave-1 honest gap, not a regression.
3. R9 (SSN handling) — not surfaced in Wave 1 because the ported `UserManagementPage` doesn't currently capture SSN. When Wave 2 or 3 adds the SSN field per RFC §9.5, R9's hash-and-flag policy will need a follow-up RFC.
