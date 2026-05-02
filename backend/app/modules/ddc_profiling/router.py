"""DDC profiling API.

Auto-mounted at ``/api/v1/ddc_profiling/``.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.modules.ddc_profiling.schemas import CategoryQuery, ColumnQuery, RowsRequest
from app.modules.ddc_profiling.service import (
    AnalyticsExtrasMissing,
    category_bar_data,
    column_summary,
    correlation_matrix,
    histogram_bins,
    missing_value_map,
)

router = APIRouter()


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AnalyticsExtrasMissing as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/summary", response_model=list[dict[str, Any]])
async def summary(req: RowsRequest) -> list[dict[str, Any]]:
    return _wrap(column_summary, req.rows)


@router.post("/histogram", response_model=dict[str, Any])
async def histogram(req: ColumnQuery) -> dict[str, Any]:
    return _wrap(histogram_bins, req.rows, req.column, req.bins)


@router.post("/categories", response_model=dict[str, Any])
async def categories(req: CategoryQuery) -> dict[str, Any]:
    return _wrap(category_bar_data, req.rows, req.column, req.top_n)


@router.post("/correlation", response_model=dict[str, dict[str, float]])
async def correlation(req: RowsRequest) -> dict[str, dict[str, float]]:
    return _wrap(correlation_matrix, req.rows)


@router.post("/missing", response_model=list[dict[str, Any]])
async def missing(req: RowsRequest) -> list[dict[str, Any]]:
    return _wrap(missing_value_map, req.rows)
