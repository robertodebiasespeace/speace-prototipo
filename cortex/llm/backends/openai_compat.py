"""
Backend LLM OpenAI-compatible.

Copre:
  - LM Studio         (default: http://localhost:1234/v1)
  - Ollama OpenAI-mode (http://localhost:11434/v1)
  - vLLM, OpenRouter, qualsiasi endpoint /v1/chat/completions

Non richiede la SDK OpenAI: usa solo `requests` (HTTP puro).
Se il server non risponde o non è installato, solleva LLMError — il
client si occupa del fallback.
"""

from __future__ import annotations
import time
import json
from typing import Dict, Any

from cortex.llm.types import LLMRequest, LLMResponse, LLMError


def complete(req: LLMRequest, config: Dict[str, Any]) -> LLMResponse:
    try:
        import requests
    except ImportError as e:
        raise LLMError(f"requests not available: {e}")

    base_url = (config or {}).get("base_url", "http://localhost:1234/v1").rstrip("/")
    model = (config or {}).get("model", "local-model")
    api_key = (config or {}).get("api_key", "lm-studio")  # LM Studio accetta dummy
    timeout = (config or {}).get("timeout_s", 30)

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
    }
    if req.stop:
        body["stop"] = req.stop
    # Extra passthrough (top_p, presence_penalty, ...)
    for k, v in (req.extra or {}).items():
        body.setdefault(k, v)

    t0 = time.time()
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            data=json.dumps(body),
            timeout=timeout,
        )
    except Exception as e:
        raise LLMError(f"openai_compat request failed: {e}")

    latency_ms = round((time.time() - t0) * 1000, 2)

    if resp.status_code != 200:
        raise LLMError(
            f"openai_compat http {resp.status_code}: {resp.text[:200]}"
        )
    try:
        data = resp.json()
    except Exception as e:
        raise LLMError(f"openai_compat invalid json: {e}")

    try:
        choice = data["choices"][0]
        text = choice.get("message", {}).get("content", "") or ""
        finish = choice.get("finish_reason", "stop")
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"openai_compat unexpected payload: {e}")

    usage = data.get("usage", {}) or {}
    return LLMResponse(
        text=text.strip(),
        backend="openai_compat",
        model=data.get("model", model),
        finish_reason=finish,
        usage=usage,
        latency_ms=latency_ms,
        is_stub=False,
    )


def health_check(config: Dict[str, Any]) -> bool:
    """Verifica se l'endpoint risponde a /models senza errori."""
    try:
        import requests
        base_url = (config or {}).get("base_url", "http://localhost:1234/v1").rstrip("/")
        r = requests.get(f"{base_url}/models", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
