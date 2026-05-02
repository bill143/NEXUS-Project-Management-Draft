"""Pydantic schemas for the ddc_profiling module."""

from typing import Any

from pydantic import BaseModel, Field


class RowsRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., description="One dict per row")


class ColumnQuery(RowsRequest):
    column: str
    bins: int = Field(default=10, ge=2, le=100)


class CategoryQuery(RowsRequest):
    column: str
    top_n: int = Field(default=10, ge=1, le=100)
