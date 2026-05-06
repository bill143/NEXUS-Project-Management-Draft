# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""PipelineRuntime — executes a registered pipeline and traces it on JobRun.

The runtime is the bridge between the FastAPI request layer and the
LangGraph execution layer. It:

    1. Looks up the manifest by name (``PipelineNotFoundError`` on miss).
    2. Builds the graph via the manifest's ``graph_factory``.
    3. Optionally creates an ``oe_job_run`` row so the run is queryable
       via the existing ``GET /api/v1/jobs/{id}`` endpoint.
    4. Invokes the graph with the supplied input, awaiting the result.
    5. Writes ``llm_tier_used`` / ``total_tokens`` / ``total_cost_usd``
       back to the JobRun row (columns added by migration v2f0).
    6. Returns the graph's final state to the caller.

Sync now, async later
    The current implementation runs the graph inline inside the request
    coroutine. Async-by-job-id is a v1.1 enhancement: swap step 4 for
    ``submit_job(kind=f'pipeline.{name}', payload=input)`` once the
    handler indirection is wired up. The shape of the public method
    does not change; only the return semantics shift from "result" to
    "job id".
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.pipelines.llm_dispatch import LLMDispatcher
from app.core.pipelines.registry import get_pipeline

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


# Heuristic cost estimate per 1k tokens — used only for the JobRun
# ``total_cost_usd`` column (informational; not for billing). Numbers
# are blended input+output for the default provider per tier and are
# intentionally rough — 2 sig figs is enough for an internal dashboard.
_COST_PER_1K_TOKENS_USD: dict[str, float] = {
    "hard": 0.030,      # Claude Opus blended
    "classify": 0.0003, # Gemini Flash blended
    "fallback": 0.005,  # GPT-4o blended
}


def _estimate_cost_usd(tokens_by_tier: dict) -> float:
    """Sum the per-tier cost estimate. Rounds to 4 decimal places."""
    total = 0.0
    for tier, tokens in tokens_by_tier.items():
        # tier is LLMTier; use .value for the lookup key
        rate = _COST_PER_1K_TOKENS_USD.get(getattr(tier, "value", str(tier)), 0.0)
        total += (tokens / 1000.0) * rate
    return round(total, 4)


class PipelineRuntime:
    """Executes a named pipeline and writes telemetry to the JobRun row.

    Stateless across runs — safe to use as a process-wide singleton
    (see :func:`get_pipeline_runtime`).
    """

    async def execute(
        self,
        name: str,
        input_payload: dict[str, Any],
        *,
        job_run_id: uuid.UUID | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline ``name`` with ``input_payload`` and return its result.

        Args:
            name: Pipeline manifest name (e.g. ``"text_to_cost_estimate"``).
            input_payload: Dict matching the pipeline's input schema. Passed
                through to the LangGraph graph as its initial state.
            job_run_id: Optional pre-existing JobRun row to update with
                the run's telemetry. When None the runtime executes the
                pipeline without DB persistence (useful in tests).
            session_factory: Override for testing. Defaults to the platform's
                global async session factory.

        Returns:
            The final state dict produced by the LangGraph graph.

        Raises:
            PipelineNotFoundError: ``name`` is not registered.
            RuntimeError: Manifest has no ``graph_factory``.
        """
        manifest = get_pipeline(name)
        graph = manifest.build_graph()
        dispatcher = LLMDispatcher()

        # Inject the dispatcher into the input so nodes can reach it
        # without importing globals. LangGraph state is just a dict.
        merged_input = dict(input_payload)
        merged_input.setdefault("_llm_dispatcher", dispatcher)
        merged_input.setdefault("_pipeline_name", name)

        started_at = datetime.now(UTC)
        wall_clock_start = time.perf_counter()

        try:
            # LangGraph compiled graphs expose ``ainvoke`` for async runs.
            result = await graph.ainvoke(merged_input)
            ok = True
            error_data: dict[str, Any] | None = None
        except Exception as exc:  # noqa: BLE001 — we re-raise after recording
            logger.exception("Pipeline %s failed", name)
            result = {}
            ok = False
            error_data = {"type": type(exc).__name__, "message": str(exc)}
            await self._write_telemetry(
                job_run_id=job_run_id,
                manifest_name=name,
                started_at=started_at,
                duration_s=time.perf_counter() - wall_clock_start,
                dispatcher=dispatcher,
                error=error_data,
                session_factory=session_factory,
            )
            raise

        await self._write_telemetry(
            job_run_id=job_run_id,
            manifest_name=name,
            started_at=started_at,
            duration_s=time.perf_counter() - wall_clock_start,
            dispatcher=dispatcher,
            error=None,
            session_factory=session_factory,
        )

        # Strip the injected helpers so callers see a clean output dict.
        if isinstance(result, dict):
            result = {k: v for k, v in result.items() if not k.startswith("_")}
        return result

    async def _write_telemetry(
        self,
        *,
        job_run_id: uuid.UUID | None,
        manifest_name: str,
        started_at: datetime,
        duration_s: float,
        dispatcher: LLMDispatcher,
        error: dict[str, Any] | None,
        session_factory: async_sessionmaker[AsyncSession] | None,
    ) -> None:
        """Persist the run's LLM telemetry onto the JobRun row.

        No-op when ``job_run_id`` is None (test path) or the row was
        deleted between submit and complete (best-effort, never fatal).
        """
        if job_run_id is None:
            return

        from app.core.job_run import JobRun

        if session_factory is None:
            from app.database import async_session_factory as session_factory  # type: ignore

        try:
            async with session_factory() as session:
                row = await session.get(JobRun, job_run_id)
                if row is None:
                    return

                tier_used = (
                    dispatcher.last_tier_used.value
                    if dispatcher.last_tier_used is not None
                    else None
                )

                # New columns from migration v2f0; ``getattr`` keeps the
                # runtime working on databases that have not been migrated
                # yet (the column is just dropped on write in that case).
                if hasattr(row, "pipeline_name"):
                    row.pipeline_name = manifest_name
                if hasattr(row, "llm_tier_used"):
                    row.llm_tier_used = tier_used
                if hasattr(row, "total_tokens"):
                    row.total_tokens = dispatcher.total_tokens
                if hasattr(row, "total_cost_usd"):
                    row.total_cost_usd = _estimate_cost_usd(dispatcher.tokens_by_tier)

                # Lifecycle columns — runtime owns these only when running
                # outside the job_runner dispatch path (sync HTTP route).
                if row.started_at is None:
                    row.started_at = started_at
                row.completed_at = datetime.now(UTC)
                row.status = "failed" if error else "success"
                if error is not None:
                    row.error_jsonb = error

                await session.commit()
        except Exception:  # noqa: BLE001 — telemetry is best-effort
            logger.exception(
                "Failed to write pipeline telemetry for job_run_id=%s", job_run_id,
            )


_runtime: PipelineRuntime | None = None


def get_pipeline_runtime() -> PipelineRuntime:
    """Return the process-wide runtime singleton, lazily constructed."""
    global _runtime
    if _runtime is None:
        _runtime = PipelineRuntime()
    return _runtime
