# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Application-level pipelines (Sweep B onwards).

Each subpackage is a self-contained pipeline:

    text_to_cost_estimate    Free-text construction work description
                             → parsed work items → classified → matched
                             against the cost database → estimated.

Pipelines self-register on import. Adding ``import app.pipelines`` to
``app/main.py`` is enough to make them discoverable via
``app.core.pipelines.get_pipeline``.
"""

from __future__ import annotations

# Import each pipeline submodule for its side-effect registration.
from app.pipelines import text_to_cost_estimate  # noqa: F401

__all__ = ["text_to_cost_estimate"]
