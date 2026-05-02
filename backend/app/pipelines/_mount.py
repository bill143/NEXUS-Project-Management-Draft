# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Mount helper — wires every pipeline router into the FastAPI app.

Pipelines export a ``router`` attribute from a ``router.py`` submodule
in their package. The mount helper imports each pipeline (which triggers
``register_pipeline``) and includes its router under
``/api/v1/pipelines``. Authoring a new pipeline = drop a package under
``app/pipelines/<name>/`` with a ``router.py``; no main-app edits needed
once a pipeline already exists.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def mount_pipeline_routers(app: FastAPI) -> int:
    """Mount every pipeline's router under ``/api/v1/pipelines``.

    Returns the number of routers mounted so the caller can log a
    sensible startup line. Failures in any single pipeline are caught
    and logged so one broken pipeline doesn't take down the others.
    """
    mounted = 0

    # Each entry: (module path, attribute name on the router module).
    # Adding a new pipeline = append one row here.
    _PIPELINES: list[tuple[str, str]] = [
        ("app.pipelines.text_to_cost_estimate.router", "router"),
    ]

    for module_path, attr_name in _PIPELINES:
        try:
            module = __import__(module_path, fromlist=[attr_name])
            pipeline_router = getattr(module, attr_name)
            app.include_router(
                pipeline_router,
                prefix="/api/v1/pipelines",
                tags=["Pipelines"],
            )
            mounted += 1
        except Exception:  # noqa: BLE001 — non-fatal at startup
            logger.exception("Failed to mount pipeline router from %s", module_path)

    return mounted
