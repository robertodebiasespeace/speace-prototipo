"""
LLMClient — facade unificato sui backend LLM (v1.1, 2026-04-27).

Routing policy:
  1. LLMRouter.resolve(routing_hint) → sceglie il backend effettivo
     - "standard"  → primary (Ollama gemma3:4b, locale, gratuito)
     - "reasoning" → reasoning_backend (Anthropic claude-haiku)
  2. Fallback: lista di backend (default: ["anthropic", "mock"])
  3. Se tutti falliscono, mock safety net (is_stub=True)

Configurazione epigenome.yaml:
  llm:
    primary: "ollama_native"
    fallback_chain: ["anthropic", "mock"]
    routing:
      reasoning_agents:  ["adversarial", "evidence"]
      reasoning_backend: "anthropic"
    backends:
      ollama_native:
        base_url: "http://localhost:11434"
        model: "gemma3:4b"
        timeout_s: 60
        use_chat_api: true
      anthropic:
        model: "claude-haiku-4-5-20251001"
      mock: {}
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex.llm.types  import LLMRequest, LLMResponse, LLMError
from cortex.llm.router import LLMRouter
from cortex.llm.backends import openai_compat, ollama_native, anthropic_backend, mock_backend

log = logging.getLogger("speace.llm")

_BACKENDS = {
    "openai_compat": (openai_compat.complete,    openai_compat.health_check),
    "ollama_native": (ollama_native.complete,    ollama_native.health_check),
    "anthropic":     (anthropic_backend.complete, anthropic_backend.health_check),
    "mock":          (mock_backend.complete,      lambda cfg: True),
}


class LLMClient:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.primary: str = self.config.get("primary", "ollama_native")
        self.fallback_chain: List[str] = list(
            self.config.get("fallback_chain",
                self.config.get("fallback", ["anthropic", "mock"]))
        )
        self.router = LLMRouter(
            routing_config=self.config.get("routing", {}),
            primary=self.primary,
        )
        self.last_response: Optional[LLMResponse] = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_epigenome(cls, epigenome: Optional[Dict] = None) -> "LLMClient":
        if epigenome is None:
            try:
                import yaml
                epi_path = ROOT_DIR / "digitaldna" / "epigenome.yaml"
                if epi_path.exists():
                    epigenome = yaml.safe_load(epi_path.read_text(encoding="utf-8")) or {}
            except Exception:
                epigenome = {}
        return cls(config=(epigenome or {}).get("llm", {}) or {})

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def _call_backend(self, name: str, req: LLMRequest) -> LLMResponse:
        entry = _BACKENDS.get(name)
        if entry is None:
            raise LLMError(f"unknown_backend:{name}")
        complete_fn, _ = entry
        backend_cfg = self.config.get("backends", {}).get(name) \
                   or self.config.get(name, {}) or {}
        if name == "mock":
            return complete_fn(req)
        return complete_fn(req, backend_cfg)

    def complete(
        self,
        prompt:       str,
        system:       Optional[str]       = None,
        max_tokens:   int                 = 256,
        temperature:  float               = 0.3,
        stop:         Optional[List[str]] = None,
        routing_hint: str                 = "standard",
        extra:        Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Completa un prompt con routing selettivo.

        routing_hint:
          "standard"  → Ollama gemma3:4b (locale, gratuito)
          "reasoning" → Anthropic claude-haiku (API, per agenti critici)
        """
        req = LLMRequest(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            routing_hint=routing_hint,
            extra=extra or {},
        )

        # Risolvi backend di partenza tramite router
        routed_primary = self.router.resolve(routing_hint)

        # Catena: routed_primary → fallback_chain (deduplicata) → mock
        chain: List[str] = [routed_primary]
        for b in self.fallback_chain:
            if b not in chain:
                chain.append(b)
        if "mock" not in chain:
            chain.append("mock")

        for backend_name in chain:
            t0 = time.time()
            try:
                resp = self._call_backend(backend_name, req)
                resp.fallback_used = (backend_name != routed_primary)
                resp.routing_hint  = routing_hint
                resp.latency_ms    = resp.latency_ms or round((time.time() - t0) * 1000, 2)
                self.last_response = resp
                log.debug(
                    "llm.complete ok via %s (hint=%s fallback=%s latency=%.0fms)",
                    backend_name, routing_hint, resp.fallback_used, resp.latency_ms,
                )
                return resp
            except LLMError as e:
                log.warning("llm backend %s failed (hint=%s): %s", backend_name, routing_hint, e)
                continue
            except Exception as e:
                log.warning("llm backend %s unexpected error: %r", backend_name, e)
                continue

        # Safety net — non dovrebbe mai arrivare qui
        resp = mock_backend.complete(req)
        resp.fallback_used = True
        resp.routing_hint  = routing_hint
        self.last_response = resp
        return resp

    # ------------------------------------------------------------------
    # Diagnostica
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, bool]:
        """Health check di tutti i backend configurati."""
        out: Dict[str, bool] = {}
        for name, (_, health_fn) in _BACKENDS.items():
            try:
                backend_cfg = self.config.get("backends", {}).get(name) \
                           or self.config.get(name, {}) or {}
                out[name] = bool(health_fn(backend_cfg))
            except Exception:
                out[name] = False
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {
            "primary":        self.primary,
            "fallback_chain": self.fallback_chain,
            "router":         self.router.get_stats(),
            "last_backend":   self.last_response.backend if self.last_response else None,
        }


if __name__ == "__main__":
    c = LLMClient.from_epigenome()
    print("primary:       ", c.primary)
    print("fallback_chain:", c.fallback_chain)
    print("router stats:  ", c.router.get_stats())
    print("health:        ", c.health())
    r = c.complete(
        "In una frase: cos'è SPEACE?",
        max_tokens=64,
        routing_hint="standard",
    )
    print(f"\nbackend={r.backend} hint={r.routing_hint} stub={r.is_stub} "
          f"latency={r.latency_ms:.0f}ms")
    print(r.text)
