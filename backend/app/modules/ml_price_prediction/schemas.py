"""Pydantic schemas for the ml_price_prediction module."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainedModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    version: str
    algorithm: str
    feature_columns: list[str]
    target_column: str
    artifact_path: str
    metrics: dict[str, Any]
    sample_size: int
    notes: str
    created_at: datetime
    updated_at: datetime


class TrainRequest(BaseModel):
    """Inline training request — caller provides the data as JSON.

    For larger datasets use the CSV-upload endpoint instead.
    """

    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field("1.0.0", max_length=32)
    algorithm: str = Field("LinearRegression", max_length=64)
    feature_columns: list[str] = Field(..., min_length=1)
    target_column: str = Field("price")
    rows: list[dict[str, Any]] = Field(..., min_length=2)


class PredictRequest(BaseModel):
    model_id: UUID
    features: dict[str, Any]
    project_id: UUID | None = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    model_id: UUID
    project_id: UUID | None
    features: dict[str, Any]
    predicted_price: Decimal
    confidence: Decimal | None
    created_at: datetime
