"""My Module API routes.

Auto-mounted at ``/api/v1/my_module/`` by the module loader.

Endpoints:
    POST   /             — Create item
    GET    /             — List items for a project
    GET    /{item_id}    — Get one item
    PATCH  /{item_id}    — Update item
    DELETE /{item_id}    — Delete item
"""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import SessionDep
from app.modules.my_module.schemas import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.modules.my_module.service import ItemService

router = APIRouter()


def _get_service(session: SessionDep) -> ItemService:
    return ItemService(session)


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    service: ItemService = Depends(_get_service),
) -> ItemResponse:
    """Create a new item."""
    item = await service.create_item(data)
    return ItemResponse.model_validate(item)


@router.get("/", response_model=list[ItemResponse])
async def list_items(
    project_id: uuid.UUID = Query(..., description="Project to list items for"),
    service: ItemService = Depends(_get_service),
) -> list[ItemResponse]:
    """List items belonging to a project."""
    items = await service.list_items(project_id)
    return [ItemResponse.model_validate(i) for i in items]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    service: ItemService = Depends(_get_service),
) -> ItemResponse:
    """Fetch a single item by id."""
    item = await service.get_item(item_id)
    return ItemResponse.model_validate(item)


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    data: ItemUpdate,
    service: ItemService = Depends(_get_service),
) -> ItemResponse:
    """Update fields on an item."""
    item = await service.update_item(item_id, data)
    return ItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    service: ItemService = Depends(_get_service),
) -> None:
    """Delete an item."""
    await service.delete_item(item_id)
