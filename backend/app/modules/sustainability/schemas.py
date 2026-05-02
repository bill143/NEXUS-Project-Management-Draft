"""Pydantic schemas for the sustainability module."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── EmissionFactor ──────────────────────────────────────────────────────────


class EmissionFactorBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    material_category: str = Field(..., min_length=1, max_length=64)
    buy_clean_category: str | None = Field(None, max_length=64)
    unit: str = Field("m3", max_length=16)
    factor_kgco2e: Decimal = Field(..., ge=0)
    region: str = Field("US", max_length=8)
    source: str = ""
    notes: str = ""


class EmissionFactorCreate(EmissionFactorBase):
    pass


class EmissionFactorResponse(EmissionFactorBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


# ── ElementGroup ────────────────────────────────────────────────────────────


class ElementGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    material_category: str = Field(..., min_length=1, max_length=64)
    epd_code: str | None = Field(None, max_length=64)
    quantity: Decimal = Field(..., ge=0)
    unit: str = Field("m3", max_length=16)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ElementGroupCreate(ElementGroupBase):
    project_id: UUID


class ElementGroupUpdate(BaseModel):
    name: str | None = None
    material_category: str | None = None
    epd_code: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    metadata: dict[str, Any] | None = None


class ElementGroupResponse(ElementGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


# ── CarbonReport ────────────────────────────────────────────────────────────


class CarbonReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    total_kgco2e: Decimal
    by_category: dict[str, float]
    by_buy_clean_category: dict[str, float]
    methodology: str
    notes: str
    created_at: datetime
    updated_at: datetime


class CalculateRequest(BaseModel):
    project_id: UUID
    title: str = "Embodied Carbon Report"
    methodology: str = "GSA-P100-2023"
