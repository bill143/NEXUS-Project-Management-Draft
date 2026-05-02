"""Data access for My Module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.my_module.models import Item


class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, item: Item) -> Item:
        self.session.add(item)
        await self.session.flush()
        return item

    async def get(self, item_id: uuid.UUID) -> Item | None:
        return await self.session.get(Item, item_id)

    async def list_for_project(self, project_id: uuid.UUID) -> list[Item]:
        stmt = select(Item).where(Item.project_id == project_id).order_by(Item.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, item: Item) -> None:
        await self.session.delete(item)
