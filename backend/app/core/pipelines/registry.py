# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Pipeline registry — process-wide name → :class:`PipelineManifest` map.

Pipelines self-register via :func:`register_pipeline` at import time, so
``app/main.py`` only needs to import the pipeline package once for the
manifest to become discoverable. The registry mirrors the convention of
:func:`app.core.job_runner.register_handler` — last write wins, so tests
can swap implementations without an explicit unregister step.
"""

from __future__ import annotations

import logging

from app.core.pipelines.manifest import PipelineManifest

logger = logging.getLogger(__name__)


_PIPELINES: dict[str, PipelineManifest] = {}


class PipelineNotFoundError(KeyError):
    """Raised by :func:`get_pipeline` when the requested name is unknown.

    Subclasses :class:`KeyError` so existing ``except KeyError`` blocks
    in caller code continue to work, while still letting routers catch
    the more specific type for a clean 404 response.
    """


def register_pipeline(manifest: PipelineManifest) -> None:
    """Add (or replace) a pipeline manifest in the registry.

    Re-registering an existing name silently overrides — matches the
    "last write wins" policy used by ``register_handler``. The pairing
    keeps test fixtures simple: a test may patch a manifest in place
    without first calling :func:`unregister_pipeline`.
    """
    if manifest.name in _PIPELINES:
        logger.debug("Replacing existing pipeline manifest: %s", manifest.name)
    _PIPELINES[manifest.name] = manifest
    logger.info(
        "Registered pipeline: %s v%s (%s)",
        manifest.name,
        manifest.version,
        manifest.display_name,
    )


def unregister_pipeline(name: str) -> None:
    """Remove a pipeline manifest. No-op if absent."""
    _PIPELINES.pop(name, None)


def get_pipeline(name: str) -> PipelineManifest:
    """Look up a pipeline manifest by name.

    Raises:
        PipelineNotFoundError: If ``name`` is not registered.
    """
    try:
        return _PIPELINES[name]
    except KeyError as exc:
        msg = f"Pipeline not found: {name!r}"
        raise PipelineNotFoundError(msg) from exc


def list_pipelines() -> list[PipelineManifest]:
    """Return all registered pipelines, newest-first by registration order."""
    # dict preserves insertion order in CPython 3.7+; reversed gives most-recent first
    return list(reversed(_PIPELINES.values()))
