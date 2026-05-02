# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""``persist_pipeline_run`` — finalise a pipeline run on its JobRun row.

A pipeline that runs synchronously inside an HTTP request still needs
the JobRun row updated with the structured result so observers polling
``GET /api/v1/jobs/{id}`` see ``status='success'`` and the output JSON.
This helper handles that update in one place. It is exposed both as a
plain coroutine (for the sync path) and as a registered job handler
(``pipeline.persist``) so a future async path can dispatch it via
``submit_job`` without re-implementing the body.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def persist_pipeline_run(
    job_run_id: uuid.UUID,
    *,
    pipeline_name: str,
    output: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Mark a JobRun as ``success`` with the supplied output and pipeline name.

    No-op when the row is missing (best-effort semantics — tests delete
    rows out from under handlers and the system must not crash).

    Args:
        job_run_id: The row to update.
        pipeline_name: Pipeline manifest name; copied to the
            ``pipeline_name`` column when present (migration v2f0).
        output: Structured result, written to ``result_jsonb``.
        session_factory: Override for testing.
    """
    from app.core.job_run import JobRun

    if session_factory is None:
        from app.database import async_session_factory as session_factory  # type: ignore

    async with session_factory() as session:
        row = await session.get(JobRun, job_run_id)
        if row is None:
            logger.debug("persist_pipeline_run: JobRun %s not found", job_run_id)
            return
        row.status = "success"
        row.completed_at = datetime.now(UTC)
        # Merge with any progress_message already on the row so the
        # final state still includes intermediate breadcrumbs.
        merged = dict(row.result_jsonb or {})
        merged.update(output)
        row.result_jsonb = merged
        if hasattr(row, "pipeline_name"):
            row.pipeline_name = pipeline_name
        await session.commit()


def register() -> None:
    """Register the synchronous wrapper as a generic job handler.

    A future async path will ``submit_job(kind='pipeline.persist', ...)``
    instead of calling :func:`persist_pipeline_run` directly. The handler
    body simply unwraps the payload and delegates.
    """
    from app.core.job_runner import register_handler

    async def _handler(_job_run, payload: dict[str, Any]) -> dict[str, Any]:
        # job_run.id IS the row we update — re-query inside the helper.
        target_id = uuid.UUID(payload["target_job_run_id"])
        await persist_pipeline_run(
            target_id,
            pipeline_name=payload["pipeline_name"],
            output=payload.get("output", {}),
        )
        return {"persisted": str(target_id)}

    register_handler("pipeline.persist", _handler)


# Side-effect registration on import — matches the convention of
# ``app/core/jobs_tasks.py`` which auto-registers ``oe.dispatch_job``.
register()
