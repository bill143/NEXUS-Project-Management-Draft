# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""PipelineManifest — metadata describing a named pipeline.

Mirrors :class:`app.core.module_loader.ModuleManifest` so authoring a
pipeline feels like authoring a module: drop a ``manifest.py`` next to a
``graph.py`` under ``app/pipelines/<name>/`` and the runtime picks it up.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.pipelines.llm_dispatch import LLMTier


@dataclass
class PipelineManifest:
    """Metadata for a registered pipeline.

    Attributes:
        name: Unique pipeline key, e.g. ``"text_to_cost_estimate"``. The
            HTTP endpoint mounts at ``/api/v1/pipelines/{name}``.
        version: SemVer string. Bump when the graph topology or the
            input/output schema changes in a way that breaks consumers.
        display_name: Human-readable label for the UI / docs.
        description: One-line summary; longer prose lives in module
            docstrings.
        category: ``"ai"`` (LLM-driven) / ``"conversion"`` (file
            transform) / ``"report"`` (export rendering). Used for
            dashboard filtering, no behavioural meaning yet.
        graph_factory: Callable returning a compiled LangGraph graph.
            Lazy so importing ``manifest`` does not pull LangGraph if the
            consumer just wants metadata.
        tier_map: Optional mapping from internal node name to
            :class:`LLMTier`. Lets the runtime route each LLM call to a
            cheap or expensive provider per Decision 3 of the sweep.
        timeout_seconds: Hard timeout for the whole graph execution.
            Defaults to 300 s — long enough for a multi-step LLM chain,
            short enough to expose runaway loops.
    """

    name: str
    version: str
    display_name: str
    description: str = ""
    category: str = "ai"
    graph_factory: Callable[[], Any] | None = None
    tier_map: dict[str, LLMTier] = field(default_factory=dict)
    timeout_seconds: int = 300

    def build_graph(self) -> Any:
        """Construct the LangGraph graph for this pipeline.

        Raises:
            RuntimeError: If ``graph_factory`` was not supplied at
                registration time. Bare-metadata manifests are useful
                for dashboards but cannot be executed.
        """
        if self.graph_factory is None:
            msg = f"Pipeline {self.name!r} has no graph_factory; cannot execute"
            raise RuntimeError(msg)
        return self.graph_factory()
