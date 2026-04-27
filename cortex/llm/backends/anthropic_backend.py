"""
Backend Anthropic (stub).
Richiede la SDK `anthropic` e una ANTHROPIC_API_KEY.
In assenza di entrambi, solleva LLMError e il client fa fallback.

Roberto ha segnalato (2026-04-19) che al momento non dispone di chiave
Anthropic: questo backend è presente per completezza architetturale e
si attiverà appena la chiave sarà disponibile. La Fase 1 opera
prevalentemente su LM Studio (openai_compat).
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any

from cortex.llm.types import LLMRequest, LLMResponse, LLMError


def complete(req: LLMRequest, config: Dict[str, Any]) -> LLMResponse:
    api_key = (config or {}).get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("anthropic: ANTHROPIC_API_KEY not set")

    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise LLMError(f"anthropic SDK not installed: {e}")

    model = (config or {}).get("model", "claude-sonnet-4-6")
    timeout = (config or {}).get("timeout_s", 30)

    client = anthropic.Anthropic(api_key=api_key)
    t0 = time.time()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=req.max_tokens,
            system=req.system or "",
            messages=[{"role": "user", "content": req.prompt}],
            temperature=req.temperature,
            timeout=timeout,
        )
    except Exception as e:
        raise LLMError(f"anthropic request failed: {e}")
    latency_ms = round((time.time() - t0) * 1000, 2)

    # Concatenate all text blocks
    parts = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    text = "\n".join(parts).strip()

    return LLMResponse(
        text=text,
        backend="anthropic",
        model=model,
        finish_reason=getattr(resp, "stop_reason", "stop") or "stop",
        usage={
            "input_tokens": getattr(getattr(resp, "usage", None), "input_tokens", 0),
            "output_tokens": getattr(getattr(resp, "usage", None), "output_tokens", 0),
        },
        latency_ms=latency_ms,
        is_stub=False,
    )


def health_check(config: Dict[str, Any]) -> bool:
    api_key = (config or {}).get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False
