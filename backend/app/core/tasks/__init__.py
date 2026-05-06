# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Celery task definitions for pipeline-side deterministic work.

The Celery transport itself lives in :mod:`app.core.jobs` and the generic
dispatch task in :mod:`app.core.jobs_tasks`. This package adds *pipeline*-
flavoured tasks: handlers that are invoked from a LangGraph node (or
directly from a router) when the work is deterministic, side-effect-y,
or compute-bound enough that running it inside the request coroutine
would be wrong.

Module-specific tasks live in submodules so the dispatcher's registry
stays a single, predictable namespace:

    persist_pipeline_run     Writes a pipeline run's structured output
                             to the JobRun row's ``result_jsonb`` and
                             marks the row ``success``. Used by sync
                             pipeline routes that own the row's
                             lifecycle directly (no Celery hand-off).

Importing this package registers the task handlers with the platform's
job runner via :func:`register_handler`. Do not gate the registration
behind a feature flag — handlers are cheap and tests always rely on a
predictable registry.
"""

from app.core.tasks.pipeline_persistence import persist_pipeline_run

__all__ = ["persist_pipeline_run"]
