"""
Mock backend deterministico. Fallback offline-safe.
Usa regex/keyword per generare una risposta sintetica riconoscibile
("is_stub=True") senza mai chiamare la rete.
"""

from __future__ import annotations
import time
import re
from typing import Dict
from collections import Counter

from cortex.llm.types import LLMRequest, LLMResponse


_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "and", "or",
    "il", "la", "lo", "le", "gli", "i", "un", "una", "di", "in", "con", "su",
    "per", "tra", "e", "ed", "o", "che", "non", "è", "sono",
}


def complete(req: LLMRequest) -> LLMResponse:
    t0 = time.time()
    text = req.prompt or ""
    tokens = re.findall(r"\w+", text.lower())
    meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) > 3]
    top = [w for w, _ in Counter(meaningful).most_common(5)]
    summary = ", ".join(top) if top else "(input vuoto)"

    reply = (
        f"[mock] Sintesi offline: concetti chiave = {summary}. "
        f"Lunghezza input={len(text)} char. Nessun LLM remoto contattato."
    )
    # Tronca in base a max_tokens (approx word count)
    words = reply.split()
    if len(words) > req.max_tokens:
        reply = " ".join(words[: req.max_tokens])

    return LLMResponse(
        text=reply,
        backend="mock",
        model="mock-deterministic-v1",
        finish_reason="stop",
        usage={"input_tokens": len(tokens), "output_tokens": len(reply.split())},
        latency_ms=round((time.time() - t0) * 1000, 2),
        is_stub=True,
    )
