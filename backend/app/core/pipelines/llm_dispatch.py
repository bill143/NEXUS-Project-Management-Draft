# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""LLM tier dispatcher — Decision 3 of Sweep B.

Tier-based provider selection lets pipelines route easy classification
work to a cheap fast model (Gemini Flash) and reserve the expensive
reasoning model (Claude Opus) for hard tasks. Each tier maps to a
``(provider, model, env_var_name)`` triple; the dispatcher pulls the API
key from the environment and forwards to the existing
:func:`app.modules.ai.ai_client.call_ai` HTTP shim — no SDK dependency.

Why not reuse the AI module's :func:`resolve_provider_and_key`?
    That function reads a per-user ``AISettings`` row encrypted with the
    JWT secret. Pipelines run server-side without a user context, so we
    take API keys from the environment and skip the decryption step.
    Both paths converge on ``call_ai`` so we still benefit from the
    error handling and provider quirks already encoded there.

Tier defaults can be overridden per-deployment via env vars without
touching code:

    OE_LLM_TIER_HARD_PROVIDER, OE_LLM_TIER_HARD_MODEL
    OE_LLM_TIER_CLASSIFY_PROVIDER, OE_LLM_TIER_CLASSIFY_MODEL
    OE_LLM_TIER_FALLBACK_PROVIDER, OE_LLM_TIER_FALLBACK_MODEL
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class LLMTier(StrEnum):
    """Pipeline-side tiers for routing LLM calls to the right model.

    HARD     Heavy reasoning — cost estimation, multi-step inference.
             Defaults to Claude Opus 4.7.
    CLASSIFY Cheap classification — categorise into MasterFormat / NRM.
             Defaults to Gemini 2.5 Flash.
    FALLBACK Used when the preferred tier is unavailable (rate-limited,
             bad key). Defaults to GPT-4o.
    """

    HARD = "hard"
    CLASSIFY = "classify"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class TierConfig:
    """A tier's resolved provider, model, and env-var name."""

    provider: str
    model: str
    api_key_env: str


# Defaults per Decision 3. Provider names match the keys in
# ``app.modules.ai.ai_client``'s dispatcher.
_DEFAULT_TIER_CONFIG: dict[LLMTier, TierConfig] = {
    LLMTier.HARD: TierConfig(
        provider="anthropic",
        model="claude-opus-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    LLMTier.CLASSIFY: TierConfig(
        provider="gemini",
        model="gemini-2.5-flash",
        api_key_env="GEMINI_API_KEY",
    ),
    LLMTier.FALLBACK: TierConfig(
        provider="openai",
        model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
    ),
}


def _resolve_tier_config(tier: LLMTier) -> TierConfig:
    """Apply env-var overrides on top of the hard-coded defaults."""
    base = _DEFAULT_TIER_CONFIG[tier]
    provider = os.environ.get(f"OE_LLM_TIER_{tier.name}_PROVIDER", base.provider)
    model = os.environ.get(f"OE_LLM_TIER_{tier.name}_MODEL", base.model)
    return TierConfig(provider=provider, model=model, api_key_env=base.api_key_env)


class LLMUnavailableError(RuntimeError):
    """No tier (preferred or fallback) had a usable API key configured.

    Distinct from ``ValueError`` so router code can distinguish a "no
    keys configured at all" deployment problem from a malformed user
    input problem.
    """


class LLMDispatcher:
    """Route an LLM call to the configured provider for a given tier.

    The dispatcher is stateless except for the (cached) tier config and
    a tiny per-call usage counter that the runtime aggregates into the
    JobRun row. Construct one per-pipeline-execution if you want isolated
    token accounting; the default singleton is fine for one-shot calls.
    """

    def __init__(self) -> None:
        self.tokens_by_tier: dict[LLMTier, int] = dict.fromkeys(LLMTier, 0)
        self.calls_by_tier: dict[LLMTier, int] = dict.fromkeys(LLMTier, 0)
        self.last_tier_used: LLMTier | None = None

    @property
    def total_tokens(self) -> int:
        return sum(self.tokens_by_tier.values())

    @property
    def total_calls(self) -> int:
        return sum(self.calls_by_tier.values())

    async def call(
        self,
        tier: LLMTier,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 4096,
        allow_fallback: bool = True,
    ) -> tuple[str, int]:
        """Call the model configured for ``tier`` and return (text, tokens).

        Args:
            tier: Which tier to use for this call.
            system: System prompt.
            prompt: User prompt.
            max_tokens: Cap on response tokens.
            allow_fallback: When True, a missing API key or transport
                error in the preferred tier transparently retries on
                :data:`LLMTier.FALLBACK`. Set to False for tests that
                want to assert on a specific provider.

        Raises:
            LLMUnavailableError: No provider could service the call.
            ValueError: Provider returned a 4xx surfaced through call_ai.
        """
        from app.modules.ai.ai_client import call_ai

        config = _resolve_tier_config(tier)
        api_key = os.environ.get(config.api_key_env, "").strip()

        if not api_key:
            logger.warning(
                "LLM tier %s has no API key (env=%s); %s",
                tier.value,
                config.api_key_env,
                "trying fallback" if allow_fallback and tier != LLMTier.FALLBACK else "no fallback",
            )
            if not allow_fallback or tier == LLMTier.FALLBACK:
                msg = (
                    f"No API key configured for tier {tier.value!r} "
                    f"(env var {config.api_key_env!r} unset)"
                )
                raise LLMUnavailableError(msg)
            # Tail-call into the fallback tier; do NOT recurse infinitely.
            return await self.call(
                LLMTier.FALLBACK,
                system,
                prompt,
                max_tokens=max_tokens,
                allow_fallback=False,
            )

        text, tokens = await call_ai(
            provider=config.provider,
            api_key=api_key,
            system=system,
            prompt=prompt,
            max_tokens=max_tokens,
        )
        self.tokens_by_tier[tier] += int(tokens or 0)
        self.calls_by_tier[tier] += 1
        self.last_tier_used = tier
        logger.debug(
            "LLM call: tier=%s provider=%s model=%s tokens=%s",
            tier.value,
            config.provider,
            config.model,
            tokens,
        )
        return text, tokens
