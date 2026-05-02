"""Pydantic schemas for the ddc_qto module."""

from typing import Any

from pydantic import BaseModel, Field


class QtoRequest(BaseModel):
    """Single-file QTO request."""

    elements: list[dict[str, Any]] = Field(..., description="List of element dicts")
    group_by: list[str] = Field(..., min_length=1)
    sum_columns: list[str] = Field(default_factory=lambda: ["Volume", "Area", "Length"])
    where: dict[str, Any] | None = None


class QtoBatchRequest(BaseModel):
    """Multi-file QTO request — Quick-QTO 'folder of files' pattern."""

    files: dict[str, list[dict[str, Any]]] = Field(
        ..., description="filename -> list of elements"
    )
    group_by: list[str] = Field(..., min_length=1)
    sum_columns: list[str] = Field(default_factory=lambda: ["Volume", "Area", "Length"])
    where: dict[str, Any] | None = None


class QtoSummary(BaseModel):
    """One row of the QTO output: group keys + count + sum columns."""

    model_config = {"extra": "allow"}


class QtoResponse(BaseModel):
    summary: list[dict[str, Any]]


class QtoBatchResponse(BaseModel):
    per_file: dict[str, list[dict[str, Any]]]
    combined: list[dict[str, Any]]
