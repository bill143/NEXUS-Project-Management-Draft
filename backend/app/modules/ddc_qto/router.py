"""DDC QTO API routes.

Auto-mounted at ``/api/v1/ddc_qto/``.
"""

from fastapi import APIRouter

from app.modules.ddc_qto.schemas import (
    QtoBatchRequest,
    QtoBatchResponse,
    QtoRequest,
    QtoResponse,
)
from app.modules.ddc_qto.service import batch_summarize, group_and_aggregate

router = APIRouter()


@router.post("/summarize", response_model=QtoResponse)
async def summarize(req: QtoRequest) -> QtoResponse:
    """Group + aggregate one element list. Stateless transformation."""
    summary = group_and_aggregate(
        req.elements,
        group_by=req.group_by,
        sum_columns=req.sum_columns,
        where=req.where,
    )
    return QtoResponse(summary=summary)


@router.post("/batch", response_model=QtoBatchResponse)
async def batch(req: QtoBatchRequest) -> QtoBatchResponse:
    """Group + aggregate many element lists at once with a roll-up."""
    result = batch_summarize(
        req.files,
        group_by=req.group_by,
        sum_columns=req.sum_columns,
        where=req.where,
    )
    return QtoBatchResponse(**result)
