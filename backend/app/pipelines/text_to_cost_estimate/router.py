# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""HTTP route for the text_to_cost_estimate pipeline.

Mounted under ``/api/v1/pipelines`` by :func:`mount_pipeline_routers`.
Sync execution today (Decision 2 of Sweep B); async-by-job-id is the
v1.1 enhancement.

The route owns the JobRun lifecycle directly because we are not handing
the work to Celery in this sweep — the runtime updates the row's
telemetry, but the route still has to insert the row and surface the
``job_run_id`` so polling clients can find it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.job_run import JobRun
from app.core.pipelines import get_pipeline_runtime
from app.pipelines.text_to_cost_estimate.schemas import (
    TextToCostEstimateRequest,
    TextToCostEstimateResponse,
)

logger = logging.getLogger(__name__)

# Note: prefix is set by the parent router that mounts this one. Keeping
# the per-pipeline router prefix-free lets the parent decide whether to
# version on ``/api/v1/pipelines/<name>`` or some other shape later.
router = APIRouter(tags=["Pipelines"])


PIPELINE_NAME = "text_to_cost_estimate"


def _get_session_factory() -> async_sessionmaker:
    from app.database import async_session_factory

    return async_session_factory


@router.post(
    "/text_to_cost_estimate",
    response_model=TextToCostEstimateResponse,
    summary="Estimate construction costs from a free-text work description",
)
async def post_text_to_cost_estimate(
    body: TextToCostEstimateRequest,
) -> TextToCostEstimateResponse:
    """Run the text_to_cost_estimate pipeline synchronously.

    Creates a JobRun row first so observers polling
    ``GET /api/v1/jobs/{id}`` can correlate the run. The response
    payload includes ``job_run_id`` even on success so the same
    correlation works without the caller needing a second round trip.
    """
    runtime = get_pipeline_runtime()
    factory = _get_session_factory()

    # Insert a JobRun row so the runtime has somewhere to record telemetry.
    job_run_id = uuid.uuid4()
    async with factory() as session:
        row = JobRun(
            id=job_run_id,
            kind=f"pipeline.{PIPELINE_NAME}",
            status="started",
            progress_percent=0,
            payload_jsonb=body.model_dump(),
            started_at=datetime.now(UTC),
            pipeline_name=PIPELINE_NAME,
        )
        session.add(row)
        await session.commit()

    try:
        result = await runtime.execute(
            PIPELINE_NAME,
            body.model_dump(),
            job_run_id=job_run_id,
            session_factory=factory,
        )
    except Exception as exc:
        logger.exception("text_to_cost_estimate failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {type(exc).__name__}",
        ) from exc

    return TextToCostEstimateResponse(
        job_run_id=str(job_run_id),
        pipeline_name=PIPELINE_NAME,
        work_items=result.get("work_items", []),
        classified_items=result.get("classified_items", []),
        matched_costs=result.get("matched_costs", []),
        estimate=result.get("estimate", {}),
        confidence=float(result.get("confidence", 0.0)),
        notes=list(result.get("notes", [])),
    )
