"""
Tipi comuni per il layer LLM di SPEACE.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMRequest:
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 256
    temperature: float = 0.3
    stop: Optional[List[str]] = None
    # Metadata opaca per backend specifici (es. model=, top_p=...)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    backend: str
    model: str
    finish_reason: str = "stop"
    usage: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    fallback_used: bool = False
    # Segnale se la risposta è "offline/regex" vs "vera"
    is_stub: bool = False


class LLMError(Exception):
    """Errore interno del layer LLM."""
