"""ML Price-Prediction API routes.

Auto-mounted at ``/api/v1/ml_price_prediction/``.
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.dependencies import SessionDep
from app.modules.ml_price_prediction.schemas import (
    PredictionResponse,
    PredictRequest,
    TrainedModelResponse,
    TrainRequest,
)
from app.modules.ml_price_prediction.service import ModelService

router = APIRouter()


def _service(session: SessionDep) -> ModelService:
    return ModelService(session)


@router.post(
    "/models/train",
    response_model=TrainedModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def train_model(
    req: TrainRequest,
    service: ModelService = Depends(_service),
) -> TrainedModelResponse:
    """Train a new model from inline rows. Returns the registered model."""
    model = await service.train(req)
    return TrainedModelResponse.model_validate(model)


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def predict(
    req: PredictRequest,
    service: ModelService = Depends(_service),
) -> PredictionResponse:
    prediction = await service.predict(req)
    return PredictionResponse.model_validate(prediction)


@router.get("/models", response_model=list[TrainedModelResponse])
async def list_models(
    service: ModelService = Depends(_service),
) -> list[TrainedModelResponse]:
    return [TrainedModelResponse.model_validate(m) for m in await service.list_models()]


@router.get("/models/{model_id}", response_model=TrainedModelResponse)
async def get_model(
    model_id: uuid.UUID,
    service: ModelService = Depends(_service),
) -> TrainedModelResponse:
    return TrainedModelResponse.model_validate(await service.get_model(model_id))
