"""
Tipi comuni per il layer LLM di SPEACE.
Versione: 1.1 (2026-04-27) — aggiunto routing_hint a LLMRequest.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMRequest:
    prompt:      str
    system:      Optional[str]       = None
    max_tokens:  int                 = 256
    temperature: float               = 0.3
    stop:        Optional[List[str]] = None

    # routing_hint: direttiva per LLMRouter — "standard" | "reasoning" | "creative"
    # "standard"  → usa backend primario (Ollama gemma3:4b)
    # "reasoning" → usa backend reasoning (Anthropic claude-haiku)
    routing_hint: str = "standard"

    # Metadata opaca per backend specifici (es. model=, top_p=...)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text:         str
    backend:      str
    model:        str
    finish_reason: str             = "stop"
    usage:        Dict[str, Any]  = field(default_factory=dict)
    latency_ms:   float           = 0.0
    fallback_used: bool           = False
    routing_hint: str             = "standard"   # hint usato per questa risposta
    # Segnale se la risposta e` "offline/regex" vs "vera"
    is_stub:      bool            = False


class LLMError(Exception):
    """Errore interno del layer LLM."""
