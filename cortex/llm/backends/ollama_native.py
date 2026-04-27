"""
Backend LLM Ollama nativo (non OpenAI-compat).
Usa l'endpoint http://localhost:11434/api/generate.
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

    base_url = (config or {}).get("base_url", "http://localhost:11434").rstrip("/")
    model = (config or {}).get("model", "llama3")
    timeout = (config or {}).get("timeout_s", 30)

    prompt = req.prompt
    if req.system:
        prompt = f"System: {req.system}\n\nUser: {req.prompt}"

    body = {
        "model": model,
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
        raise LLMError(f"ollama_native request failed: {e}")

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
            "input_tokens": data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
        },
        latency_ms=latency_ms,
        is_stub=False,
    )


def health_check(config: Dict[str, Any]) -> bool:
    try:
        import requests
        base_url = (config or {}).get("base_url", "http://localhost:11434").rstrip("/")
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
