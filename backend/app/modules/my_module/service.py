"""Business logic for My Module."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.my_module.models import Item
from app.modules.my_module.repository import ItemRepository
from app.modules.my_module.schemas import ItemCreate, ItemUpdate


class ItemService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ItemRepository(session)

    async def create_item(self, data: ItemCreate) -> Item:
        item = Item(
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            metadata_=data.metadata,
        )
        return await self.repo.create(item)

    async def get_item(self, item_id: uuid.UUID) -> Item:
        item = await self.repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    async def list_items(self, project_id: uuid.UUID) -> list[Item]:
        return await self.repo.list_for_project(project_id)

    async def update_item(self, item_id: uuid.UUID, data: ItemUpdate) -> Item:
        item = await self.get_item(item_id)
        if data.name is not None:
            item.name = data.name
        if data.description is not None:
            item.description = data.description
        if data.metadata is not None:
            item.metadata_ = data.metadata
        await self.session.flush()
        return item

    async def delete_item(self, item_id: uuid.UUID) -> None:
        item = await self.get_item(item_id)
        await self.repo.delete(item)
