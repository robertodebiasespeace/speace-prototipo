"""
Backend LLM Ollama nativo — M3L / aggiornato a /api/chat (2026-04-27).

Supporta due endpoint Ollama:
  /api/chat     (default, use_chat_api=True)  → formato messaggi, ideale
                per chat/instruct models (gemma3, llama3, mistral, phi4)
  /api/generate (legacy, use_chat_api=False)  → prompt stringa concatenata

Configurazione epigenome.yaml:
  ollama_native:
    base_url: "http://localhost:11434"
    model: "gemma3:4b"
    timeout_s: 60
    use_chat_api: true     # default true — usa /api/chat
    num_ctx: 4096          # context window override

Note:
  - Ollama >= 0.1.14 supporta /api/chat con message format.
  - Per OpenAI-compat usa openai_compat con base_url=localhost:11434/v1.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict

from cortex.llm.types import LLMRequest, LLMResponse, LLMError


def _complete_chat(req: LLMRequest, config: Dict[str, Any]) -> LLMResponse:
    """Usa /api/chat (messages format — consigliato per gemma3:4b)."""
    import requests

    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    model    = config.get("model", "gemma3:4b")
    timeout  = config.get("timeout_s", 60)
    num_ctx  = config.get("num_ctx", 4096)

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    body: Dict[str, Any] = {
        "model":    model,
        "messages": messages,
        "stream":   False,
        "options":  {
            "temperature": req.temperature,
            "num_predict": req.max_tokens,
            "num_ctx":     num_ctx,
        },
    }
    if req.stop:
        body["options"]["stop"] = req.stop

    t0 = time.time()
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except Exception as e:
        raise LLMError(f"ollama_native /api/chat request failed: {e}")

    latency_ms = round((time.time() - t0) * 1000, 2)

    if resp.status_code != 200:
        raise LLMError(f"ollama_native http {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
    except Exception as e:
        raise LLMError(f"ollama_native invalid json: {e}")

    try:
        text = data["message"]["content"]
    except (KeyError, TypeError):
        text = data.get("response", "") or ""

    return LLMResponse(
        text=text.strip(),
        backend="ollama_native",
        model=data.get("model", model),
        finish_reason="stop" if data.get("done") else "length",
        usage={
            "input_tokens":  data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
        },
        latency_ms=latency_ms,
        is_stub=False,
    )


def _complete_generate(req: LLMRequest, config: Dict[str, Any]) -> LLMResponse:
    """Usa /api/generate (prompt stringa — legacy)."""
    import requests

    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    model    = config.get("model", "gemma3:4b")
    timeout  = config.get("timeout_s", 60)

    prompt = req.prompt
    if req.system:
        prompt = f"System: {req.system}\n\nUser: {req.prompt}"

    body: Dict[str, Any] = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": req.temperature,
            "num_predict": req.max_tokens,
        },
    }
    if req.stop:
        body["options"]["stop"] = req.stop

    t0 = time.time()
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except Exception as e:
        raise LLMError(f"ollama_native /api/generate request failed: {e}")

    latency_ms = round((time.time() - t0) * 1000, 2)

    if resp.status_code != 200:
        raise LLMError(f"ollama_native http {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
    except Exception as e:
        raise LLMError(f"ollama_native invalid json: {e}")

    text = data.get("response", "") or ""
    return LLMResponse(
        text=text.strip(),
        backend="ollama_native",
        model=data.get("model", model),
        finish_reason="stop" if data.get("done") else "length",
        usage={
            "input_tokens":  data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
        },
        latency_ms=latency_ms,
        is_stub=False,
    )


def complete(req: LLMRequest, config: Dict[str, Any]) -> LLMResponse:
    """
    Dispatch su /api/chat o /api/generate in base a use_chat_api.
    Default: use_chat_api=True (consigliato per gemma3:4b e modelli chat).
    """
    try:
        import requests  # noqa: F401 — early import check
    except ImportError as e:
        raise LLMError(f"requests not available: {e}")

    use_chat = (config or {}).get("use_chat_api", True)
    if use_chat:
        return _complete_chat(req, config)
    return _complete_generate(req, config)


def health_check(config: Dict[str, Any]) -> bool:
    """
    Verifica che Ollama risponda e che il modello configurato sia disponibile.
    GET /api/tags → lista modelli installati.
    """
    try:
        import requests
        base_url = (config or {}).get("base_url", "http://localhost:11434").rstrip("/")
        model    = (config or {}).get("model", "gemma3:4b")
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        if r.status_code != 200:
            return False
        models = [m.get("name", "") for m in r.json().get("models", [])]
        # confronto flessibile: "gemma3:4b" in "gemma3:4b" o "gemma3"
        model_base = model.split(":")[0]
        return any(model_base in m for m in models) or len(models) > 0
    except Exception:
        return False
