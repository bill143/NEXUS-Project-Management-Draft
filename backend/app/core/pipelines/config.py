# DDC-CWICR-OE: DataDrivenConstruction · NEXUS
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Pipeline configuration constants — Sweep B Decision 3.

Centralised tier-default exports so dashboards and docs can render the
exact provider/model strings used in production without duplicating
the logic in :mod:`app.core.pipelines.llm_dispatch`.

Env-var override semantics live in :mod:`llm_dispatch`. This module is
read-only; downstream code that wants the resolved (post-override) tier
config should call :func:`app.core.pipelines.llm_dispatch._resolve_tier_config`.
"""

from __future__ import annotations

from app.core.pipelines.llm_dispatch import _DEFAULT_TIER_CONFIG, LLMTier

# Public read-only view of the default tier config. Cast to a regular
# dict so callers can iterate without exposing the private name.
DEFAULT_TIER_CONFIG = dict(_DEFAULT_TIER_CONFIG)

# Provider/model strings exported individually for dashboard rendering.
DEFAULT_HARD_PROVIDER = _DEFAULT_TIER_CONFIG[LLMTier.HARD].provider
DEFAULT_HARD_MODEL = _DEFAULT_TIER_CONFIG[LLMTier.HARD].model
DEFAULT_CLASSIFY_PROVIDER = _DEFAULT_TIER_CONFIG[LLMTier.CLASSIFY].provider
DEFAULT_CLASSIFY_MODEL = _DEFAULT_TIER_CONFIG[LLMTier.CLASSIFY].model
DEFAULT_FALLBACK_PROVIDER = _DEFAULT_TIER_CONFIG[LLMTier.FALLBACK].provider
DEFAULT_FALLBACK_MODEL = _DEFAULT_TIER_CONFIG[LLMTier.FALLBACK].model

__all__ = [
    "DEFAULT_CLASSIFY_MODEL",
    "DEFAULT_CLASSIFY_PROVIDER",
    "DEFAULT_FALLBACK_MODEL",
    "DEFAULT_FALLBACK_PROVIDER",
    "DEFAULT_HARD_MODEL",
    "DEFAULT_HARD_PROVIDER",
    "DEFAULT_TIER_CONFIG",
]
