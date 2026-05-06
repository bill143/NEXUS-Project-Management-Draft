# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""text_to_cost_estimate — port of DDC n8n workflow #6.1.

Construction-price-estimation pipeline. Caller posts a free-text
description ("pour 50 cubic yards of 4000 psi concrete for foundation
footings, Chicago metro"); the pipeline returns a structured estimate
with parsed work items, MasterFormat / NRM classification, retrieved
historical rates from the cost database, and an LLM-computed total.

Architecture
~~~~~~~~~~~~
LangGraph state machine with four nodes (Sweep B, Decision 2):

    parse_description    LLM (HARD) — extracts work items, quantities,
                         units, location, materials.
    classify_items       LLM (CLASSIFY) — assigns MasterFormat / NRM
                         categories per item.
    search_cost_db       Celery-style deterministic vector search
                         against the cost database.
    estimate_total       LLM (HARD) — computes labor / material /
                         equipment costs and the total.

Each node updates the shared graph state. The runtime in
:mod:`app.core.pipelines.runtime` records LLM tier usage and token
counts onto the JobRun row.
"""

from __future__ import annotations

from app.core.pipelines import (
    LLMTier,
    PipelineManifest,
    register_pipeline,
)
from app.pipelines.text_to_cost_estimate.graph import build_graph

manifest = PipelineManifest(
    name="text_to_cost_estimate",
    version="1.0.0",
    display_name="Text → Cost Estimate",
    description=(
        "Free-text construction work description → parsed → classified → "
        "cost-matched → LLM-estimated total. Port of DDC n8n workflow #6.1."
    ),
    category="ai",
    graph_factory=build_graph,
    tier_map={
        "parse_description": LLMTier.HARD,
        "classify_items": LLMTier.CLASSIFY,
        "estimate_total": LLMTier.HARD,
    },
    timeout_seconds=120,
)

register_pipeline(manifest)

__all__ = ["manifest"]
