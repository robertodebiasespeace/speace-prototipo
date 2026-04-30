"""
cortex.cognitive_autonomy.swarm.neuron_base
===========================================
M8 — NeuronBase: base class per i neuroni Ollama del Swarm.

Port adattato da speaceorganismocibernetico/SPEACE_Cortex/comparti/ollama_neuron_base.py

Differenze rispetto all'originale:
  - Nessuna dipendenza da "bridge" (usa LLMClient di cortex/llm)
  - Fallback deterministico integrato (per test offline)
  - API sincrona (oltre a async) per compatibilità con SwarmOrchestrator
  - NeuronResult dataclass per output tipizzato
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NeuronResult:
    """Output tipizzato di un NeuronBase.process()."""
    neuron_name: str
    status: str                          # "complete" | "fallback" | "error"
    response: str
    ollama_used: bool = False
    model: str = "gemma3:4b"
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "neuron_name": self.neuron_name,
            "status":      self.status,
            "response":    self.response,
            "ollama_used": self.ollama_used,
            "model":       self.model,
            "latency_ms":  self.latency_ms,
            "metadata":    self.metadata,
            "timestamp":   self.timestamp,
        }


class NeuronBase:
    """
    Classe base per tutti i neuroni Ollama del SPEACE Swarm.

    Ogni neurone specializzato (Planner, Critic, Executor, Researcher)
    eredita da questa classe e sovrascrive `system_prompt` e opzionalmente
    `_fallback_response()`.

    Uso:
        neuron = PlannerNeuron()
        result = neuron.run({"query": "Decompormi questo obiettivo: X"})
        # result.response contiene l'output (da Ollama o fallback)
    """

    DEFAULT_MODEL = "gemma3:4b"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.name    = "neuron_base"
        self.version = "1.1"
        self.model   = model
        self.system_prompt = "Sei un neurone intelligente di SPEACE."
        self.temperature = 0.4
        self.num_ctx     = 4096
        self.num_predict = 512
        self._ollama_available: Optional[bool] = None  # lazy check

    # ── API pubblica ──────────────────────────────────────────────────────────

    def run(self, context: Dict[str, Any]) -> NeuronResult:
        """
        Versione sincrona di process().
        Chiama Ollama se disponibile, altrimenti usa fallback deterministico.
        """
        return asyncio.run(self.process(context))

    async def process(self, context: Dict[str, Any]) -> NeuronResult:
        """
        Versione asincrona — chiamata dall'Orchestrator.

        Args:
            context: dict con almeno {"query": str}

        Returns:
            NeuronResult con response e metadata.
        """
        query = str(context.get("query", "")).strip() or "Descrivi il tuo stato."
        t0 = time.monotonic()

        if self._is_ollama_available():
            try:
                response = await self._call_ollama(query, context)
                latency = (time.monotonic() - t0) * 1000
                return NeuronResult(
                    neuron_name=self.name,
                    status="complete",
                    response=response,
                    ollama_used=True,
                    model=self.model,
                    latency_ms=latency,
                    metadata={"query_len": len(query)},
                )
            except Exception as e:
                logger.warning("[%s] Ollama error: %s — usando fallback", self.name, e)

        # Fallback deterministico
        response = self._fallback_response(query, context)
        latency = (time.monotonic() - t0) * 1000
        return NeuronResult(
            neuron_name=self.name,
            status="fallback",
            response=response,
            ollama_used=False,
            model=self.model,
            latency_ms=latency,
            metadata={"query_len": len(query), "fallback": True},
        )

    def get_status(self) -> dict:
        return {
            "name":             self.name,
            "version":          self.version,
            "model":            self.model,
            "temperature":      self.temperature,
            "ollama_available": self._is_ollama_available(),
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _is_ollama_available(self) -> bool:
        if self._ollama_available is None:
            try:
                import ollama
                ollama.list()
                self._ollama_available = True
                logger.info("[%s] Ollama disponibile (model=%s)", self.name, self.model)
            except Exception:
                self._ollama_available = False
                logger.debug("[%s] Ollama non disponibile — fallback attivo", self.name)
        return self._ollama_available

    async def _call_ollama(self, query: str, context: Dict) -> str:
        import ollama
        resp = await asyncio.to_thread(
            ollama.chat,
            model=self.model,
            messages=[
                {"role": "system",  "content": self.system_prompt},
                {"role": "user",    "content": f"Query: {query}"},
            ],
            options={
                "temperature": self.temperature,
                "num_ctx":     self.num_ctx,
                "num_predict": self.num_predict,
            },
        )
        return resp["message"]["content"].strip()

    def _fallback_response(self, query: str, context: Dict) -> str:
        """
        Risposta deterministica quando Ollama non è disponibile.
        Ogni sottoclasse può sovrascrivere per risposte più specifiche.
        """
        return (
            f"[{self.name.upper()} FALLBACK] "
            f"Query ricevuta: '{query[:80]}'. "
            f"Ollama non disponibile — risposta simulata per continuità del ciclo."
        )


__all__ = ["NeuronBase", "NeuronResult"]
