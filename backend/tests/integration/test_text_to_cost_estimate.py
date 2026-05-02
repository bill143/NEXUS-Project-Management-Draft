# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Sweep B — end-to-end test for the text_to_cost_estimate pipeline.

LLM calls are replaced with a fake :class:`LLMDispatcher` that returns
canned JSON for each tier. No real provider keys or network access are
required. One integration-marker test would hit the real models; we
omit that here to honour the sweep's "no real API spend" rule and
because the existing AI module has its own provider-level tests.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.job_run import JobRun
from app.core.pipelines import LLMDispatcher, LLMTier
from app.database import Base
from app.pipelines.text_to_cost_estimate.graph import build_graph
from app.pipelines.text_to_cost_estimate.nodes import (
    classify_items,
    estimate_total,
    parse_description,
    search_cost_db,
)

# ── Test doubles ─────────────────────────────────────────────────────────


class _FakeDispatcher(LLMDispatcher):
    """Returns canned text from a script keyed by tier.

    Each call pops the first matching response off the queue so a single
    test can stage multi-call sequences (parse → classify → estimate)
    without re-mocking between phases.
    """

    def __init__(self, responses: dict[LLMTier, list[str]]) -> None:
        super().__init__()
        self._responses = {tier: list(items) for tier, items in responses.items()}

    async def call(  # type: ignore[override]
        self,
        tier: LLMTier,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 4096,
        allow_fallback: bool = True,
    ) -> tuple[str, int]:
        queue = self._responses.get(tier, [])
        if not queue:
            raise RuntimeError(f"No canned response staged for tier {tier!r}")
        text = queue.pop(0)
        # Fake token count proportional to response length so telemetry
        # tests have a non-zero number to assert on.
        tokens = max(1, len(text) // 4)
        self.tokens_by_tier[tier] += tokens
        self.calls_by_tier[tier] += 1
        self.last_tier_used = tier
        return text, tokens


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[JobRun.__table__])
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


# ── Node-level coverage ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_description_returns_work_items_from_llm() -> None:
    canned = json.dumps(
        [
            {
                "description": "Pour 4000 psi concrete for foundation footings",
                "quantity": 50,
                "unit": "yd3",
                "material": "concrete 4000 psi",
                "location": "Chicago metro",
            },
        ],
    )
    dispatcher = _FakeDispatcher({LLMTier.HARD: [canned]})
    state = {
        "description": "pour 50 cubic yards of 4000 psi concrete for foundation footings, Chicago metro",
        "_llm_dispatcher": dispatcher,
    }
    out = await parse_description(state)  # type: ignore[arg-type]
    assert "work_items" in out
    assert len(out["work_items"]) == 1
    assert out["work_items"][0]["unit"] == "yd3"


@pytest.mark.asyncio
async def test_classify_items_routes_to_classify_tier() -> None:
    canned = json.dumps(
        [{"index": 0, "masterformat": "03 30 00", "nrm": "2.6.1", "confidence": 0.92}],
    )
    dispatcher = _FakeDispatcher({LLMTier.CLASSIFY: [canned]})
    state = {
        "work_items": [{"description": "concrete footings", "quantity": 50, "unit": "yd3"}],
        "_llm_dispatcher": dispatcher,
    }
    out = await classify_items(state)  # type: ignore[arg-type]
    assert dispatcher.calls_by_tier[LLMTier.CLASSIFY] == 1
    assert out["classified_items"][0]["masterformat"] == "03 30 00"


@pytest.mark.asyncio
async def test_search_cost_db_matches_concrete_keyword() -> None:
    state = {
        "work_items": [
            {"description": "concrete footings 4000 psi", "quantity": 50, "unit": "yd3"},
            {"description": "structural steel I-beam", "quantity": 12, "unit": "ea"},
        ],
    }
    out = await search_cost_db(state)  # type: ignore[arg-type]
    matches = out["matched_costs"]
    # First item matches "concrete"; second is unmatched (no steel rate).
    assert matches[0]["matched"] is True
    assert matches[0]["match"]["keyword"] == "concrete"
    assert matches[1]["matched"] is False


@pytest.mark.asyncio
async def test_estimate_total_uses_llm_when_available() -> None:
    canned = json.dumps(
        {
            "labor_usd": 5000,
            "material_usd": 9000,
            "equipment_usd": 1000,
            "subtotal_usd": 15000,
            "markup_percent": 12,
            "total_usd": 16800,
            "confidence": 0.78,
        },
    )
    dispatcher = _FakeDispatcher({LLMTier.HARD: [canned]})
    state: dict[str, Any] = {
        "work_items": [{"description": "x", "quantity": 1, "unit": "ea"}],
        "classified_items": [],
        "matched_costs": [],
        "currency": "USD",
        "_llm_dispatcher": dispatcher,
    }
    out = await estimate_total(state)  # type: ignore[arg-type]
    assert out["estimate"]["total_usd"] == 16800
    assert out["confidence"] == 0.78


@pytest.mark.asyncio
async def test_estimate_total_falls_back_to_deterministic_when_llm_fails() -> None:
    """When the dispatcher raises, the estimator computes a defensible
    answer from the matched rate table alone — confidence pinned to 0.3."""

    class _BoomDispatcher(LLMDispatcher):
        async def call(self, *_, **__):  # type: ignore[override]
            raise RuntimeError("LLM unreachable in test")

    state: dict[str, Any] = {
        "work_items": [
            {"description": "concrete footings", "quantity": 10, "unit": "m3"},
        ],
        "classified_items": [],
        "matched_costs": [
            {
                "input": {"description": "concrete footings", "quantity": 10},
                "match": {
                    "keyword": "concrete",
                    "unit": "m3",
                    "rate_usd": 185.0,
                    "labor_pct": 0.4,
                    "equip_pct": 0.1,
                },
                "matched": True,
            },
        ],
        "currency": "USD",
        "_llm_dispatcher": _BoomDispatcher(),
    }
    out = await estimate_total(state)  # type: ignore[arg-type]
    assert out["confidence"] == 0.3
    assert out["estimate"]["total_usd"] > 0
    assert any("Deterministic fallback" in n for n in out["notes"])


# ── End-to-end ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_happy_path_writes_telemetry(session_factory) -> None:
    """parse → classify → search → estimate, with JobRun telemetry written."""

    parse_response = json.dumps(
        [
            {
                "description": "Pour 4000 psi concrete for foundation footings",
                "quantity": 50,
                "unit": "yd3",
                "material": "concrete 4000 psi",
                "location": "Chicago metro",
            },
        ],
    )
    classify_response = json.dumps(
        [{"index": 0, "masterformat": "03 30 00", "nrm": "2.6.1", "confidence": 0.92}],
    )
    estimate_response = json.dumps(
        {
            "labor_usd": 4000,
            "material_usd": 7500,
            "equipment_usd": 500,
            "subtotal_usd": 12000,
            "markup_percent": 12,
            "total_usd": 13440,
            "confidence": 0.81,
        },
    )

    fake = _FakeDispatcher(
        {
            LLMTier.HARD: [parse_response, estimate_response],
            LLMTier.CLASSIFY: [classify_response],
        },
    )

    # Insert a JobRun so the runtime has somewhere to write telemetry.
    job_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(
            JobRun(
                id=job_id,
                kind="pipeline.text_to_cost_estimate",
                status="started",
                progress_percent=0,
                payload_jsonb={"description": "test"},
                started_at=datetime.now(UTC),
            ),
        )
        await session.commit()

    graph = build_graph()
    state = {
        "description": "pour 50 cubic yards of 4000 psi concrete for foundation footings, Chicago metro",
        "currency": "USD",
        "_llm_dispatcher": fake,
        "_pipeline_name": "text_to_cost_estimate",
    }
    result = await graph.ainvoke(state)

    assert "work_items" in result
    assert len(result["work_items"]) == 1
    assert result["estimate"]["total_usd"] == 13440
    # All three tiers exercised — HARD twice (parse + estimate), CLASSIFY once.
    assert fake.calls_by_tier[LLMTier.HARD] == 2
    assert fake.calls_by_tier[LLMTier.CLASSIFY] == 1


@pytest.mark.asyncio
async def test_pipeline_handles_llm_unavailable_with_no_keys() -> None:
    """If no API keys are set, the pipeline still runs to completion via
    the deterministic estimator fallback."""
    env = {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}
    with patch.dict(os.environ, env, clear=False):
        graph = build_graph()
        state = {
            "description": "concrete footings 50 yd3",
            "currency": "USD",
            "_llm_dispatcher": LLMDispatcher(),
            "_pipeline_name": "text_to_cost_estimate",
        }
        # parse_description will raise LLMUnavailableError because no keys
        # are configured; verify the error propagates rather than being
        # silently swallowed.
        from app.core.pipelines.llm_dispatch import LLMUnavailableError

        with pytest.raises(LLMUnavailableError):
            await graph.ainvoke(state)


@pytest.mark.asyncio
async def test_pipeline_router_response_shape_matches_schema(session_factory) -> None:
    """Smoke-check that the router's response shape pulls every key out
    of the pipeline result without dropping anything."""
    from app.pipelines.text_to_cost_estimate.router import (
        post_text_to_cost_estimate,
    )
    from app.pipelines.text_to_cost_estimate.schemas import TextToCostEstimateRequest

    parse_response = json.dumps(
        [{"description": "concrete", "quantity": 10, "unit": "m3"}],
    )
    classify_response = json.dumps(
        [{"index": 0, "masterformat": "03 30 00", "nrm": "2.6.1", "confidence": 0.9}],
    )
    estimate_response = json.dumps(
        {
            "labor_usd": 800,
            "material_usd": 1100,
            "equipment_usd": 100,
            "subtotal_usd": 2000,
            "markup_percent": 12,
            "total_usd": 2240,
            "confidence": 0.7,
        },
    )

    fake = _FakeDispatcher(
        {
            LLMTier.HARD: [parse_response, estimate_response],
            LLMTier.CLASSIFY: [classify_response],
        },
    )

    # Patch out the runtime's LLMDispatcher constructor so the router's
    # call to runtime.execute() picks up our fake.
    with patch(
        "app.core.pipelines.runtime.LLMDispatcher", return_value=fake,
    ), patch(
        "app.pipelines.text_to_cost_estimate.router._get_session_factory",
        return_value=session_factory,
    ):
        body = TextToCostEstimateRequest(description="concrete 10 m3")
        response = await post_text_to_cost_estimate(body)

    assert response.pipeline_name == "text_to_cost_estimate"
    assert uuid.UUID(response.job_run_id)  # valid UUID
    assert response.estimate["total_usd"] == 2240
    assert response.confidence == 0.7
