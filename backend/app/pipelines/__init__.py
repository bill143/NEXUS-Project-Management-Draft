# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Application-level pipelines (Sweep B onwards).

Each subpackage is a self-contained pipeline:

    text_to_cost_estimate    Free-text construction work description
                             → parsed work items → classified → matched
                             against the cost database → estimated.

Pipelines self-register on import. Adding ``import app.pipelines`` to
``app/main.py`` is enough to make them discoverable via
``app.core.pipelines.get_pipeline``.

Each subpackage import is wrapped in try/except — pipelines may have
optional heavy deps (langgraph, etc.) that aren't part of the base
install. If a dep is missing the pipeline silently fails to register;
``app.core.pipelines.get_pipeline(name)`` then returns ``None``, and
the route mount in ``app.main`` is wrapped in its own try/except so
the app keeps booting.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Import each pipeline submodule for its side-effect registration.
try:
    from app.pipelines import text_to_cost_estimate  # noqa: F401
except ImportError as exc:
    logger.info(
        "Pipeline 'text_to_cost_estimate' unavailable: %s. "
        "Install with: pip install nexus[langgraph]",
        exc,
    )

__all__ = ["text_to_cost_estimate"]
