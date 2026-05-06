# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""LangGraph state machine for text_to_cost_estimate.

Topology::

    parse_description → classify_items → search_cost_db → estimate_total → END

Linear today; later sweeps may add a conditional edge (e.g. "if no
items parsed, skip classification") but the linear path keeps the
mental model — and the test surface — small for the foundational sweep.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.pipelines.text_to_cost_estimate.nodes import (
    PipelineState,
    classify_items,
    estimate_total,
    parse_description,
    search_cost_db,
)


def build_graph() -> Any:
    """Construct and compile the LangGraph state machine.

    Returns the compiled graph (LangGraph 1.x exposes ``.ainvoke`` for
    async execution). The factory pattern keeps construction lazy so
    tests can swap nodes without re-importing the module.
    """
    builder: StateGraph = StateGraph(PipelineState)
    builder.add_node("parse_description", parse_description)
    builder.add_node("classify_items", classify_items)
    builder.add_node("search_cost_db", search_cost_db)
    builder.add_node("estimate_total", estimate_total)

    builder.set_entry_point("parse_description")
    builder.add_edge("parse_description", "classify_items")
    builder.add_edge("classify_items", "search_cost_db")
    builder.add_edge("search_cost_db", "estimate_total")
    builder.add_edge("estimate_total", END)

    return builder.compile()
