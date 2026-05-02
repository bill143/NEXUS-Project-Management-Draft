"""Data access for the ml_price_prediction module."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ml_price_prediction.models import Prediction, TrainedModel


class TrainedModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, model: TrainedModel) -> TrainedModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def get(self, model_id: uuid.UUID) -> TrainedModel | None:
        return await self.session.get(TrainedModel, model_id)

    async def get_by_name_version(self, name: str, version: str) -> TrainedModel | None:
        stmt = (
            select(TrainedModel)
            .where(TrainedModel.name == name)
            .where(TrainedModel.version == version)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_all(self) -> list[TrainedModel]:
        result = await self.session.execute(
            select(TrainedModel).order_by(TrainedModel.created_at.desc())
        )
        return list(result.scalars().all())


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, prediction: Prediction) -> Prediction:
        self.session.add(prediction)
        await self.session.flush()
        return prediction

    async def list_for_model(self, model_id: uuid.UUID) -> list[Prediction]:
        stmt = (
            select(Prediction)
            .where(Prediction.model_id == model_id)
            .order_by(Prediction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
