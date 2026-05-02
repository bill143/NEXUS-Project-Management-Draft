# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Sweep B — Celery foundation regression coverage.

The Celery transport itself was wired up in v260_jobs_runner; this
suite verifies the pipeline-flavoured additions in :mod:`app.core.tasks`
do not regress that wiring. Three checks:

    1. The Celery app singleton boots in eager mode without external
       infrastructure (no real Redis required).
    2. ``app.core.tasks.persist_pipeline_run`` flips a JobRun row from
       ``started`` to ``success`` and writes the supplied output to
       ``result_jsonb``.
    3. Importing :mod:`app.core.tasks` registers the
       ``pipeline.persist`` handler against the existing job runner.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.job_run import JobRun
from app.core.job_runner import get_handler
from app.core.jobs import get_celery_app
from app.core.tasks import persist_pipeline_run
from app.database import Base


@pytest.fixture
async def session_factory():
    """In-memory SQLite with the JobRun table created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[JobRun.__table__])
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


def test_celery_app_singleton_boots_eagerly() -> None:
    """The Celery app exists and can be configured for synchronous tests."""
    app = get_celery_app()
    assert app is not None
    # Eager mode should be togglable without raising — same flag the
    # existing test_jobs_celery_redis suite relies on.
    prev = app.conf.task_always_eager
    try:
        app.conf.task_always_eager = True
        assert app.conf.task_always_eager is True
    finally:
        app.conf.task_always_eager = prev


def test_pipeline_persist_handler_is_registered() -> None:
    """Importing app.core.tasks attaches ``pipeline.persist`` to the registry."""
    handler = get_handler("pipeline.persist")
    assert handler is not None, "pipeline.persist handler should auto-register on import"


@pytest.mark.asyncio
async def test_persist_pipeline_run_marks_success_and_writes_output(session_factory) -> None:
    """The helper flips status, sets completed_at, and writes result_jsonb."""
    job_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(
            JobRun(
                id=job_id,
                kind="pipeline.demo",
                status="started",
                progress_percent=50,
                payload_jsonb={"input": "x"},
                started_at=datetime.now(UTC),
                pipeline_name="demo",
            ),
        )
        await session.commit()

    output = {"answer": 42, "details": ["step-a", "step-b"]}
    await persist_pipeline_run(
        job_id,
        pipeline_name="demo",
        output=output,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        row = (
            await session.execute(select(JobRun).where(JobRun.id == job_id))
        ).scalar_one()
        assert row.status == "success"
        assert row.completed_at is not None
        assert row.result_jsonb is not None
        assert row.result_jsonb["answer"] == 42
        assert row.result_jsonb["details"] == ["step-a", "step-b"]
        assert row.pipeline_name == "demo"


@pytest.mark.asyncio
async def test_persist_pipeline_run_is_noop_for_missing_row(session_factory) -> None:
    """Best-effort semantics: missing row must not raise."""
    # Should silently no-op rather than blow up — the handler must not
    # crash if its row was deleted by an upstream cancel.
    await persist_pipeline_run(
        uuid.uuid4(),  # fresh id, never inserted
        pipeline_name="demo",
        output={"x": 1},
        session_factory=session_factory,
    )


@pytest.mark.asyncio
async def test_persist_pipeline_run_merges_with_progress_message(session_factory) -> None:
    """Existing progress_message on result_jsonb must survive the merge."""
    job_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(
            JobRun(
                id=job_id,
                kind="pipeline.demo",
                status="started",
                progress_percent=80,
                result_jsonb={"progress_message": "almost there"},
                started_at=datetime.now(UTC),
            ),
        )
        await session.commit()

    await persist_pipeline_run(
        job_id,
        pipeline_name="demo",
        output={"answer": "done"},
        session_factory=session_factory,
    )

    async with session_factory() as session:
        row = (
            await session.execute(select(JobRun).where(JobRun.id == job_id))
        ).scalar_one()
        assert row.result_jsonb["progress_message"] == "almost there"
        assert row.result_jsonb["answer"] == "done"
