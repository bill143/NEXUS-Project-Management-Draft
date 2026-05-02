"""Business logic for the sustainability / CO₂ module.

Carbon-footprint formula (per element group):

    co2e_kg = quantity × factor_kgco2e

where ``factor_kgco2e`` comes from an EPD lookup keyed by the group's
``epd_code``. If no EPD code is set, we fall back to the first factor
matching ``material_category``. If no factor is found at all, the group
contributes 0 and is flagged in the report's ``notes``.

The report aggregates totals two ways:

* ``by_category`` — keyed by the EPD's ``material_category`` (e.g. concrete,
  steel, timber).
* ``by_buy_clean_category`` — keyed by the EPD's ``buy_clean_category`` field,
  which maps onto the four federal Buy Clean Act material categories
  (concrete, steel, glass, asphalt) plus an ``other`` bucket.
"""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sustainability.models import CarbonReport, ElementGroup, EmissionFactor
from app.modules.sustainability.repository import (
    CarbonReportRepository,
    ElementGroupRepository,
    EmissionFactorRepository,
)
from app.modules.sustainability.schemas import (
    ElementGroupCreate,
    ElementGroupUpdate,
    EmissionFactorCreate,
)


class EmissionFactorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmissionFactorRepository(session)

    async def create_factor(self, data: EmissionFactorCreate) -> EmissionFactor:
        existing = await self.repo.get_by_code(data.code)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"EmissionFactor with code '{data.code}' already exists",
            )
        factor = EmissionFactor(**data.model_dump())
        return await self.repo.create(factor)

    async def list_factors(self) -> list[EmissionFactor]:
        return await self.repo.list_all()


class ElementGroupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ElementGroupRepository(session)

    async def create_group(self, data: ElementGroupCreate) -> ElementGroup:
        payload = data.model_dump()
        meta = payload.pop("metadata")
        group = ElementGroup(**payload, metadata_=meta)
        return await self.repo.create(group)

    async def get_group(self, group_id: uuid.UUID) -> ElementGroup:
        group = await self.repo.get(group_id)
        if group is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ElementGroup not found")
        return group

    async def list_groups(self, project_id: uuid.UUID) -> list[ElementGroup]:
        return await self.repo.list_for_project(project_id)

    async def update_group(self, group_id: uuid.UUID, data: ElementGroupUpdate) -> ElementGroup:
        group = await self.get_group(group_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "metadata":
                group.metadata_ = value
            else:
                setattr(group, field, value)
        await self.session.flush()
        return group

    async def delete_group(self, group_id: uuid.UUID) -> None:
        group = await self.get_group(group_id)
        await self.repo.delete(group)


class CarbonCalculationService:
    """Computes the embodied-carbon footprint for a project."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.groups = ElementGroupRepository(session)
        self.factors = EmissionFactorRepository(session)
        self.reports = CarbonReportRepository(session)

    async def _factor_for(self, group: ElementGroup) -> EmissionFactor | None:
        if group.epd_code:
            factor = await self.factors.get_by_code(group.epd_code)
            if factor is not None:
                return factor
        # Fallback: first factor that matches the material_category
        for f in await self.factors.list_all():
            if f.material_category == group.material_category:
                return f
        return None

    async def calculate(
        self,
        project_id: uuid.UUID,
        title: str = "Embodied Carbon Report",
        methodology: str = "GSA-P100-2023",
    ) -> CarbonReport:
        groups = await self.groups.list_for_project(project_id)
        total = Decimal(0)
        by_category: dict[str, float] = {}
        by_buy_clean: dict[str, float] = {}
        unmatched: list[str] = []

        for g in groups:
            factor = await self._factor_for(g)
            if factor is None:
                unmatched.append(g.name)
                continue
            contribution = g.quantity * factor.factor_kgco2e
            total += contribution
            cat = factor.material_category
            by_category[cat] = float(by_category.get(cat, 0.0) + float(contribution))
            bcc = factor.buy_clean_category or "other"
            by_buy_clean[bcc] = float(by_buy_clean.get(bcc, 0.0) + float(contribution))

        notes = ""
        if unmatched:
            notes = f"No EPD match for {len(unmatched)} group(s): {', '.join(unmatched[:10])}"

        report = CarbonReport(
            project_id=project_id,
            title=title,
            total_kgco2e=total,
            by_category=by_category,
            by_buy_clean_category=by_buy_clean,
            methodology=methodology,
            notes=notes,
        )
        return await self.reports.create(report)

    async def list_reports(self, project_id: uuid.UUID) -> list[CarbonReport]:
        return await self.reports.list_for_project(project_id)
