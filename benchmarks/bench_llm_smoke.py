"""
Benchmark 7/8 — LLM cascade smoke (M3L.6).

Verifica che l'adapter `cortex/llm` esegua la cascade primary→fallback→mock
sempre producendo una LLMResponse sensata, e che l'API di health/complete
resti stabile anche in assenza di backend reali.

Non richiede LM Studio/Anthropic attivi: mock_backend garantisce la coda.
Questo bench è parte del gate di maturità M3L (non blocca se tutti i
backend reali sono off — mock è il safety net).
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run() -> dict:
    from cortex.llm import LLMClient

    client = LLMClient.from_epigenome()

    # 1. Health check di tutti i backend
    t0 = time.perf_counter()
    health = client.health()
    health_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # 2. Chiamata complete minimale
    t0 = time.perf_counter()
    resp = client.complete(
        prompt="Rispondi con una parola: SPEACE.",
        system="Sei un test probe. Risposta brevissima.",
        max_tokens=24,
        temperature=0.0,
    )
    complete_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # 3. Sanity checks
    text = (resp.text or "").strip()
    has_text = len(text) > 0
    backend_reported = resp.backend
    is_stub = bool(resp.is_stub)
    fallback_used = bool(resp.fallback_used)

    # 4. Almeno un backend ha risposto (anche se "mock")
    any_responded = has_text and backend_reported in ("openai_compat",
                                                      "ollama_native",
                                                      "anthropic",
                                                      "mock")

    # 5. Health format check: dict di bool
    health_dict_ok = isinstance(health, dict) and all(
        isinstance(v, bool) for v in health.values()
    )
    any_real_backend_up = any(
        health.get(k, False) for k in ("openai_compat", "ollama_native", "anthropic")
    )

    return {
        "name": "bench_llm_smoke",
        "primary": client.primary,
        "fallback_chain": client.fallback_chain,
        "health": health,
        "health_latency_ms": health_latency_ms,
        "health_dict_ok": health_dict_ok,
        "any_real_backend_up": any_real_backend_up,
        "complete_latency_ms": complete_latency_ms,
        "backend_used": backend_reported,
        "is_stub": is_stub,
        "fallback_used": fallback_used,
        "text_len": len(text),
        "any_responded": any_responded,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
