# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Node implementations for the text_to_cost_estimate pipeline.

Each node is an ``async`` function that takes the current graph state
(a TypedDict) and returns a partial state update. LangGraph merges the
update into the shared state and routes to the next node.

Three of the four nodes call the LLM tier dispatcher:
    parse_description   → :data:`LLMTier.HARD`     (Claude Opus)
    classify_items      → :data:`LLMTier.CLASSIFY` (Gemini Flash)
    estimate_total      → :data:`LLMTier.HARD`     (Claude Opus)

The fourth (``search_cost_db``) is a pure deterministic search; it
honours the Celery side of the architecture decision (no LLM call). For
this sweep the search is a tiny in-memory rate-table; subsequent sweeps
will swap it for the existing ``app.modules.costs`` Qdrant integration.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from app.core.pipelines.llm_dispatch import LLMDispatcher, LLMTier

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    """Shared LangGraph state for text_to_cost_estimate.

    Marked ``total=False`` so individual nodes can return a partial
    update without re-stating every key. The runtime injects two
    helpers (`_llm_dispatcher`, `_pipeline_name`) which the nodes read
    but do not pass through to the final result.
    """

    # Inputs
    description: str
    location: str | None
    currency: str
    # Helpers injected by the runtime
    _llm_dispatcher: LLMDispatcher
    _pipeline_name: str
    # Intermediate state populated by the nodes
    work_items: list[dict[str, Any]]
    classified_items: list[dict[str, Any]]
    matched_costs: list[dict[str, Any]]
    # Final output
    estimate: dict[str, Any]
    confidence: float
    notes: list[str]


# ── Prompts ──────────────────────────────────────────────────────────────

_PARSE_SYSTEM = (
    "You are a construction cost estimator's parsing assistant. "
    "Extract every distinct work item from a free-text description and "
    "return a strict JSON array. Each element must include: "
    "description (string), quantity (number), unit (string, e.g. m3, sf, ea), "
    "material (string or null), and location (string or null). "
    "Do not invent items; if information is missing, use null. "
    "Respond ONLY with the JSON array — no prose, no code fences."
)

_CLASSIFY_SYSTEM = (
    "You are a construction classification assistant. For every input "
    "work item, assign the closest CSI MasterFormat division and the "
    "closest UK NRM2 category. Return a JSON array of objects with the "
    "keys: index (int, matching input order), masterformat (string, "
    "e.g. '03 30 00'), nrm (string, e.g. '2.6.1'), and confidence "
    "(float between 0 and 1). Respond ONLY with the JSON array."
)

_ESTIMATE_SYSTEM = (
    "You are a construction cost estimator. Given parsed work items, "
    "their classifications, and matched historical unit rates, produce "
    "a cost estimate as a strict JSON object with the keys: "
    "labor_usd (number), material_usd (number), equipment_usd (number), "
    "subtotal_usd (number), markup_percent (number, default 12), "
    "total_usd (number), and confidence (float between 0 and 1). "
    "If matched rates are present, use them as the primary anchor and "
    "adjust for stated location. Respond ONLY with the JSON object."
)


def _extract_json(text: str) -> Any:
    """Reuse the AI module's JSON extractor — handles markdown fences."""
    from app.modules.ai.ai_client import extract_json

    return extract_json(text)


# ── Nodes ────────────────────────────────────────────────────────────────


async def parse_description(state: PipelineState) -> dict[str, Any]:
    """Extract structured work items from the free-text description.

    Uses :data:`LLMTier.HARD` because partial parses produce silent
    downstream errors that are expensive to detect — better to spend a
    few cents on the strong model than re-run the whole pipeline.
    """
    description = state.get("description", "")
    location = state.get("location")
    dispatcher: LLMDispatcher = state["_llm_dispatcher"]

    if not description.strip():
        return {"work_items": [], "notes": ["Empty description; nothing to parse."]}

    user_prompt = (
        f"DESCRIPTION:\n{description}\n\n"
        f"DEFAULT LOCATION (use when items don't specify their own): {location or 'unspecified'}"
    )
    text, _ = await dispatcher.call(
        LLMTier.HARD, system=_PARSE_SYSTEM, prompt=user_prompt, max_tokens=1024,
    )
    parsed = _extract_json(text)
    if not isinstance(parsed, list):
        logger.warning("parse_description: LLM returned non-list JSON: %r", parsed)
        return {"work_items": [], "notes": ["Parse failed; LLM did not return a list."]}

    return {"work_items": parsed}


async def classify_items(state: PipelineState) -> dict[str, Any]:
    """Tag each work item with MasterFormat + NRM codes via the cheap tier.

    Classification is a closed-vocabulary task; Gemini Flash handles it
    at ~1% of the price of the strong model. If classification fails
    we still proceed — downstream estimation can compensate by relying
    on the description text.
    """
    items = state.get("work_items", [])
    if not items:
        return {"classified_items": []}

    dispatcher: LLMDispatcher = state["_llm_dispatcher"]
    user_prompt = (
        "Classify each of the following work items. "
        "Return one classification per item, in input order:\n\n"
        + json.dumps(items, ensure_ascii=False, indent=2)
    )
    try:
        text, _ = await dispatcher.call(
            LLMTier.CLASSIFY, system=_CLASSIFY_SYSTEM, prompt=user_prompt, max_tokens=1024,
        )
    except Exception:  # noqa: BLE001 — degrade gracefully
        logger.exception("classify_items: dispatcher failed; continuing without classifications")
        return {"classified_items": [{"index": i} for i, _ in enumerate(items)]}

    parsed = _extract_json(text)
    if not isinstance(parsed, list):
        logger.warning("classify_items: LLM returned non-list JSON: %r", parsed)
        return {"classified_items": [{"index": i} for i, _ in enumerate(items)]}

    # Index-align so the estimator can zip items with classifications
    # even if the LLM dropped or reordered some entries.
    by_index = {entry.get("index", i): entry for i, entry in enumerate(parsed)}
    aligned = [by_index.get(i, {"index": i}) for i in range(len(items))]
    return {"classified_items": aligned}


# Tiny in-memory rate table — enough to make the search node deterministic
# for tests and demos. Sweep C will swap this for the Qdrant cost DB
# integration that already exists in ``app/modules/costs``.
_BUILT_IN_RATES: dict[str, dict[str, Any]] = {
    "concrete": {"unit": "m3", "rate_usd": 185.0, "labor_pct": 0.40, "equip_pct": 0.10},
    "rebar": {"unit": "kg", "rate_usd": 1.85, "labor_pct": 0.35, "equip_pct": 0.05},
    "formwork": {"unit": "m2", "rate_usd": 42.5, "labor_pct": 0.55, "equip_pct": 0.05},
    "footing": {"unit": "m3", "rate_usd": 220.0, "labor_pct": 0.45, "equip_pct": 0.10},
    "wall": {"unit": "m2", "rate_usd": 95.0, "labor_pct": 0.50, "equip_pct": 0.05},
    "slab": {"unit": "m2", "rate_usd": 110.0, "labor_pct": 0.45, "equip_pct": 0.05},
}


async def search_cost_db(state: PipelineState) -> dict[str, Any]:
    """Match each classified item to a historical unit rate.

    Deterministic / no LLM. The current implementation hits the small
    in-memory rate table above; the same function signature lets a
    later sweep swap in the existing ``costs`` module Qdrant search
    without touching the graph topology.

    The match key is a substring scan over the item description — naive
    but adequate for the demo. Real implementations will use vector
    similarity against the CWICR catalogue.
    """
    items = state.get("work_items", [])
    matched: list[dict[str, Any]] = []
    for item in items:
        description = str(item.get("description") or "").lower()
        material = str(item.get("material") or "").lower()
        haystack = f"{description} {material}".strip()
        match: dict[str, Any] | None = None
        for keyword, rate in _BUILT_IN_RATES.items():
            if keyword in haystack:
                match = {"keyword": keyword, **rate}
                break
        matched.append(
            {
                "input": item,
                "match": match,
                "matched": match is not None,
            },
        )
    return {"matched_costs": matched}


async def estimate_total(state: PipelineState) -> dict[str, Any]:
    """Compute the final cost estimate from the matched rates and items.

    Routes through :data:`LLMTier.HARD`. Falls back to a deterministic
    ratio-based calculation if the LLM call fails so the pipeline still
    produces a usable answer when the strong model is rate-limited.
    """
    items = state.get("work_items", [])
    classified = state.get("classified_items", [])
    matched = state.get("matched_costs", [])
    currency = state.get("currency", "USD")
    location = state.get("location")
    dispatcher: LLMDispatcher = state["_llm_dispatcher"]

    if not items:
        return {
            "estimate": {
                "labor_usd": 0.0,
                "material_usd": 0.0,
                "equipment_usd": 0.0,
                "subtotal_usd": 0.0,
                "markup_percent": 0.0,
                "total_usd": 0.0,
                "currency": currency,
            },
            "confidence": 0.0,
            "notes": ["No work items parsed; estimate is zero."],
        }

    user_prompt = (
        f"ITEMS:\n{json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
        f"CLASSIFICATIONS:\n{json.dumps(classified, ensure_ascii=False, indent=2)}\n\n"
        f"MATCHED RATES (USD):\n{json.dumps(matched, ensure_ascii=False, indent=2)}\n\n"
        f"LOCATION: {location or 'unspecified'}"
    )

    try:
        text, _ = await dispatcher.call(
            LLMTier.HARD, system=_ESTIMATE_SYSTEM, prompt=user_prompt, max_tokens=1024,
        )
        parsed = _extract_json(text)
    except Exception:  # noqa: BLE001 — fall back to deterministic compute
        logger.exception("estimate_total: LLM failed; falling back to deterministic compute")
        parsed = None

    if not isinstance(parsed, dict):
        # Deterministic fallback — sum matched-rate × quantity, split via
        # the rate table's labour/equipment percentages.
        return _deterministic_estimate(items, matched, currency=currency)

    parsed.setdefault("currency", currency)
    return {
        "estimate": parsed,
        "confidence": float(parsed.get("confidence", 0.5)),
        "notes": list(state.get("notes", [])),
    }


def _deterministic_estimate(
    items: list[dict[str, Any]],
    matched: list[dict[str, Any]],
    *,
    currency: str,
) -> dict[str, Any]:
    """Emergency fallback when the LLM cannot be reached.

    Computes a defensible estimate from the matched rate table alone so
    the pipeline never returns an empty answer. Confidence is forced to
    0.3 to signal the caller should treat the output as a rough order
    of magnitude.
    """
    labor = 0.0
    material = 0.0
    equipment = 0.0
    notes: list[str] = ["Deterministic fallback used (LLM unavailable)."]

    for item, match_row in zip(items, matched, strict=False):
        match = match_row.get("match")
        try:
            qty = float(item.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if not match or qty <= 0:
            continue
        line_total = qty * float(match["rate_usd"])
        labor += line_total * float(match.get("labor_pct", 0.4))
        equipment += line_total * float(match.get("equip_pct", 0.1))
        material += line_total - (line_total * float(match.get("labor_pct", 0.4)))
        material -= line_total * float(match.get("equip_pct", 0.1))

    subtotal = labor + material + equipment
    markup_pct = 12.0
    total = subtotal * (1 + markup_pct / 100.0)
    return {
        "estimate": {
            "labor_usd": round(labor, 2),
            "material_usd": round(material, 2),
            "equipment_usd": round(equipment, 2),
            "subtotal_usd": round(subtotal, 2),
            "markup_percent": markup_pct,
            "total_usd": round(total, 2),
            "currency": currency,
        },
        "confidence": 0.3,
        "notes": notes,
    }
