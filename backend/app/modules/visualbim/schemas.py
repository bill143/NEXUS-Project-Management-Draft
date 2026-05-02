"""Pydantic schemas for the visualbim module."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CloudPoint(BaseModel):
    """One BIM element rendered as a single 3D-scatter point."""

    id: UUID
    label: str
    x: float
    y: float
    z: float
    color: str
    size: float


class CloudResponse(BaseModel):
    project_id: UUID
    point_count: int
    dim_x: str = Field(..., description="Source field for the x axis")
    dim_y: str
    dim_z: str
    dim_color: str
    dim_size: str
    points: list[CloudPoint]
    available_dims: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Lists of values seen for each dim — drives frontend selectors",
    )


class CompareRequest(BaseModel):
    """Two-project comparison ('DNA snapshot' mode)."""

    project_a: UUID
    project_b: UUID
    dim_x: str = "volume"
    dim_y: str = "area"
    dim_z: str = "length"


class CompareResponse(BaseModel):
    project_a: CloudResponse
    project_b: CloudResponse
    summary: dict[str, Any] = Field(default_factory=dict)
