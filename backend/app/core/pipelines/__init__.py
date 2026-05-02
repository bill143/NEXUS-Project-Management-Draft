# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Pipeline foundation — Sweep B (DDC AI/LLM workflow port).

Replaces DDC's n8n-based AI pipelines with a native LangGraph + Celery
hybrid. LangGraph handles AI agent flows (LLM reasoning, classification,
estimation). Celery handles deterministic backend work (file I/O, DB
writes, report generation). Pipelines plug into the existing
``app.core.job_runner`` so every run is tracked as an ``oe_job_run`` row.

Public API:
    PipelineManifest    Metadata for a named pipeline.
    register_pipeline   Add a manifest to the registry.
    get_pipeline        Look up a manifest by name.
    list_pipelines      Enumerate all registered pipelines.
    LLMTier             Tier enum (HARD / CLASSIFY / FALLBACK).
    LLMDispatcher       Tier → provider → call_ai shim.
    PipelineRuntime     LangGraph execution wrapper with JobRun tracing.
    get_pipeline_runtime  Process-wide runtime singleton.
"""

from app.core.pipelines.llm_dispatch import LLMDispatcher, LLMTier
from app.core.pipelines.manifest import PipelineManifest
from app.core.pipelines.registry import (
    PipelineNotFoundError,
    get_pipeline,
    list_pipelines,
    register_pipeline,
    unregister_pipeline,
)
from app.core.pipelines.runtime import PipelineRuntime, get_pipeline_runtime

__all__ = [
    "LLMDispatcher",
    "LLMTier",
    "PipelineManifest",
    "PipelineNotFoundError",
    "PipelineRuntime",
    "get_pipeline",
    "get_pipeline_runtime",
    "list_pipelines",
    "register_pipeline",
    "unregister_pipeline",
]
