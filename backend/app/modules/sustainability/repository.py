"""Data access for the sustainability module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sustainability.models import CarbonReport, ElementGroup, EmissionFactor


class EmissionFactorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, factor: EmissionFactor) -> EmissionFactor:
        self.session.add(factor)
        await self.session.flush()
        return factor

    async def get_by_code(self, code: str) -> EmissionFactor | None:
        stmt = select(EmissionFactor).where(EmissionFactor.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_all(self) -> list[EmissionFactor]:
        result = await self.session.execute(select(EmissionFactor).order_by(EmissionFactor.code))
        return list(result.scalars().all())


class ElementGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, group: ElementGroup) -> ElementGroup:
        self.session.add(group)
        await self.session.flush()
        return group

    async def get(self, group_id: uuid.UUID) -> ElementGroup | None:
        return await self.session.get(ElementGroup, group_id)

    async def list_for_project(self, project_id: uuid.UUID) -> list[ElementGroup]:
        stmt = (
            select(ElementGroup)
            .where(ElementGroup.project_id == project_id)
            .order_by(ElementGroup.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, group: ElementGroup) -> None:
        await self.session.delete(group)


class CarbonReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, report: CarbonReport) -> CarbonReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_for_project(self, project_id: uuid.UUID) -> list[CarbonReport]:
        stmt = (
            select(CarbonReport)
            .where(CarbonReport.project_id == project_id)
            .order_by(CarbonReport.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
