"""Pydantic schemas for the ddc_revit_export module."""

from typing import Any

from pydantic import BaseModel, Field


class RevitExportRequest(BaseModel):
    model_name: str = Field(..., min_length=1)
    rows: list[dict[str, Any]] = Field(..., description="One dict per Revit element")
    id_field: str = Field(default="ElementId")
    extra_columns: list[str] = Field(default_factory=list)
    add_string_type_annotation: bool = False
