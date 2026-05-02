# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Sweep B — pipeline runtime + LLM dispatcher integration."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.job_run import JobRun
from app.core.pipelines import (
    LLMDispatcher,
    LLMTier,
    PipelineManifest,
    PipelineNotFoundError,
    get_pipeline,
    get_pipeline_runtime,
    list_pipelines,
    register_pipeline,
    unregister_pipeline,
)
from app.core.pipelines.llm_dispatch import LLMUnavailableError
from app.database import Base

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[JobRun.__table__])
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    for name in ("test.echo", "test.broken", "test.with_telemetry"):
        unregister_pipeline(name)


def _stub_graph(transform):
    """Return a fake compiled graph whose ``ainvoke`` calls ``transform``."""

    class _StubGraph:
        async def ainvoke(self, state):
            return await transform(state)

    return _StubGraph()


# ── Registry ─────────────────────────────────────────────────────────────


def test_register_and_lookup_roundtrip() -> None:
    manifest = PipelineManifest(
        name="test.echo",
        version="0.1.0",
        display_name="Test Echo",
        graph_factory=lambda: _stub_graph(lambda s: s),
    )
    register_pipeline(manifest)

    fetched = get_pipeline("test.echo")
    assert fetched is manifest
    assert fetched.display_name == "Test Echo"
    assert "test.echo" in {m.name for m in list_pipelines()}


def test_lookup_missing_raises_pipeline_not_found() -> None:
    with pytest.raises(PipelineNotFoundError):
        get_pipeline("definitely.does.not.exist.here")


def test_manifest_without_graph_factory_cannot_build() -> None:
    """Bare-metadata manifests are useful for dashboards but not executable."""
    manifest = PipelineManifest(name="test.broken", version="0.1.0", display_name="Broken")
    with pytest.raises(RuntimeError, match="graph_factory"):
        manifest.build_graph()


# ── Runtime ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_runtime_executes_graph_and_returns_clean_state() -> None:
    """ainvoke runs; injected helpers (`_llm_dispatcher`, `_pipeline_name`) are
    stripped from the returned dict."""

    async def passthrough(state):
        return {**state, "result": "ok"}

    register_pipeline(
        PipelineManifest(
            name="test.echo",
            version="0.1.0",
            display_name="Test Echo",
            graph_factory=lambda: _stub_graph(passthrough),
        ),
    )

    runtime = get_pipeline_runtime()
    out = await runtime.execute("test.echo", {"description": "x"})
    assert out["result"] == "ok"
    # Injected keys are stripped from the response.
    assert "_llm_dispatcher" not in out
    assert "_pipeline_name" not in out


@pytest.mark.asyncio
async def test_runtime_writes_telemetry_to_jobrun(session_factory) -> None:
    """When a job_run_id is supplied, the runtime updates pipeline_name,
    llm_tier_used, total_tokens, and total_cost_usd on completion."""

    async def graph_body(state):
        # Simulate one HARD-tier call.
        dispatcher: LLMDispatcher = state["_llm_dispatcher"]
        # Bump the counters by hand so we don't need real LLM credentials.
        dispatcher.tokens_by_tier[LLMTier.HARD] += 250
        dispatcher.calls_by_tier[LLMTier.HARD] += 1
        dispatcher.last_tier_used = LLMTier.HARD
        return {**state, "answer": 7}

    register_pipeline(
        PipelineManifest(
            name="test.with_telemetry",
            version="0.1.0",
            display_name="Telemetry Test",
            graph_factory=lambda: _stub_graph(graph_body),
        ),
    )

    job_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(
            JobRun(
                id=job_id,
                kind="pipeline.test.with_telemetry",
                status="started",
                progress_percent=0,
                payload_jsonb={"description": "hello"},
                started_at=datetime.now(UTC),
            ),
        )
        await session.commit()

    runtime = get_pipeline_runtime()
    out = await runtime.execute(
        "test.with_telemetry",
        {"description": "hello"},
        job_run_id=job_id,
        session_factory=session_factory,
    )
    assert out["answer"] == 7

    async with session_factory() as session:
        row = (
            await session.execute(select(JobRun).where(JobRun.id == job_id))
        ).scalar_one()
        assert row.status == "success"
        assert row.pipeline_name == "test.with_telemetry"
        assert row.llm_tier_used == "hard"
        assert row.total_tokens == 250
        assert row.total_cost_usd is not None
        assert float(row.total_cost_usd) > 0


# ── LLM dispatcher ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatcher_routes_to_correct_provider_per_tier() -> None:
    """Each tier dispatch resolves to the env-overridable provider/model
    and forwards to ``call_ai`` with the env-supplied API key."""

    captured: list[tuple[str, str]] = []

    async def fake_call_ai(
        *, provider, api_key, system, prompt, max_tokens, image_base64=None,
        image_media_type="image/jpeg",
    ):
        captured.append((provider, api_key))
        return f"[{provider} response]", 100

    env = {
        "ANTHROPIC_API_KEY": "anthropic-key",
        "GEMINI_API_KEY": "gemini-key",
        "OPENAI_API_KEY": "openai-key",
    }
    with patch.dict(os.environ, env, clear=False), patch(
        "app.modules.ai.ai_client.call_ai", side_effect=fake_call_ai,
    ):
        dispatcher = LLMDispatcher()
        await dispatcher.call(LLMTier.HARD, "system", "prompt-1")
        await dispatcher.call(LLMTier.CLASSIFY, "system", "prompt-2")

    providers = [p for p, _ in captured]
    keys = [k for _, k in captured]
    assert providers == ["anthropic", "gemini"]
    assert keys == ["anthropic-key", "gemini-key"]
    assert dispatcher.tokens_by_tier[LLMTier.HARD] == 100
    assert dispatcher.tokens_by_tier[LLMTier.CLASSIFY] == 100
    assert dispatcher.last_tier_used == LLMTier.CLASSIFY


@pytest.mark.asyncio
async def test_dispatcher_falls_back_when_preferred_tier_has_no_key() -> None:
    """No HARD key + fallback enabled = automatic retry on FALLBACK."""

    async def fake_call_ai(*, provider, **_):
        return f"[{provider}]", 50

    env = {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "openai-key"}
    with patch.dict(os.environ, env, clear=False), patch(
        "app.modules.ai.ai_client.call_ai", side_effect=fake_call_ai,
    ):
        dispatcher = LLMDispatcher()
        text, _ = await dispatcher.call(LLMTier.HARD, "sys", "prompt")

    assert "[openai]" in text
    assert dispatcher.last_tier_used == LLMTier.FALLBACK


@pytest.mark.asyncio
async def test_dispatcher_raises_when_no_keys_anywhere() -> None:
    env = {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}
    with patch.dict(os.environ, env, clear=False):
        dispatcher = LLMDispatcher()
        with pytest.raises(LLMUnavailableError):
            await dispatcher.call(LLMTier.HARD, "sys", "prompt")
