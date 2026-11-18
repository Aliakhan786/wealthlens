"""Thin wrapper around the Anthropic SDK. Returns None when no API key is configured, so every AI feature
has a deterministic, data-driven fallback and the app works without paid services."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from core.config import get_settings

log = logging.getLogger("wealthlens.llm")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@lru_cache
def get_client():
    settings = get_settings()
    key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic

    return anthropic.Anthropic(api_key=key, timeout=60.0, max_retries=2)


def llm_available() -> bool:
    return get_client() is not None


def create_message(system: str, messages: list[dict[str, Any]], tools: list[dict] | None = None,
                   max_tokens: int = 4000, effort: str = "low"):
    """One Messages API call. `effort=low` keeps latency/cost down for short educational answers.

    Server-side refusal fallbacks are enabled ('default' routing) so a safety-classifier decline on the
    primary model is retried on a fallback model automatically.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("LLM not configured")
    kwargs: dict[str, Any] = dict(
        model=get_settings().llm_model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    if tools:
        kwargs["tools"] = tools
    return client.beta.messages.create(**kwargs)


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()
