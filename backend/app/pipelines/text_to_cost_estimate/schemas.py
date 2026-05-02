# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Request / response schemas for the text_to_cost_estimate endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TextToCostEstimateRequest(BaseModel):
    """Caller-supplied input.

    ``description`` is the only required field; the others narrow the
    estimate. The schema lives next to the pipeline (not in a shared
    schemas module) so each pipeline can evolve its inputs without a
    cross-module migration.
    """

    description: str = Field(
        ...,
        min_length=3,
        max_length=8000,
        description="Free-text construction work description.",
    )
    location: str | None = Field(
        default=None,
        max_length=200,
        description="Default location/region (overridden per-item if specified).",
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO-4217 currency code for the estimate.",
    )


class TextToCostEstimateResponse(BaseModel):
    """Pipeline output returned to the caller."""

    job_run_id: str = Field(
        ...,
        description="UUID of the JobRun row recording this run; query "
        "GET /api/v1/jobs/{id} for full telemetry.",
    )
    pipeline_name: str
    work_items: list[dict[str, Any]]
    classified_items: list[dict[str, Any]]
    matched_costs: list[dict[str, Any]]
    estimate: dict[str, Any]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)
