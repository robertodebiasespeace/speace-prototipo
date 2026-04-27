"""
LLMClient – facade unificato sui backend LLM.

Politica di selezione:
  1. Backend primario (da epigenome.yaml → llm.primary, default "openai_compat")
  2. Fallback: lista di backend (default: ["anthropic", "mock"])
  3. Se tutti falliscono, ritorna LLMResponse con is_stub=True da mock_backend

Il client NON pensa al posto del comparto: si limita a produrre risposte
testuali. È il Temporal Lobe (o altri consumer) che decide come usarle.

Configurazione in epigenome.yaml (M3L.4 / EPI-003):
  llm:
    primary: openai_compat
    fallback: [anthropic, mock]
    openai_compat:
      base_url: http://localhost:1234/v1
      model: local-model
      api_key: lm-studio
      timeout_s: 30
    ollama_native:
      base_url: http://localhost:11434
      model: llama3
    anthropic:
      model: claude-sonnet-4-6
      # api_key letta da env ANTHROPIC_API_KEY
    mock: {}
"""

from __future__ import annotations
import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex.llm.types import LLMRequest, LLMResponse, LLMError
from cortex.llm.backends import openai_compat, ollama_native, anthropic_backend, mock_backend

log = logging.getLogger("speace.llm")

_BACKENDS = {
    "openai_compat":  (openai_compat.complete,   openai_compat.health_check),
    "ollama_native":  (ollama_native.complete,   ollama_native.health_check),
    "anthropic":      (anthropic_backend.complete, anthropic_backend.health_check),
    "mock":           (mock_backend.complete,    lambda cfg: True),
}


class LLMClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.primary = self.config.get("primary", "openai_compat")
        self.fallback_chain: List[str] = list(
            self.config.get("fallback", ["anthropic", "mock"])
        )
        # Cache ultima risposta per diagnostica
        self.last_response: Optional[LLMResponse] = None

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
    # API PRINCIPALE
    # ------------------------------------------------------------------

    def _call_backend(self, name: str, req: LLMRequest) -> LLMResponse:
        entry = _BACKENDS.get(name)
        if entry is None:
            raise LLMError(f"unknown_backend:{name}")
        complete_fn, _ = entry
        backend_cfg = self.config.get(name, {}) or {}
        # mock non prende config, openai_compat/ollama_native/anthropic sì
        if name == "mock":
            return complete_fn(req)
        return complete_fn(req, backend_cfg)

    def complete(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: int = 256,
                 temperature: float = 0.3,
                 stop: Optional[List[str]] = None,
                 extra: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Completa un prompt tentando primary → fallback chain → mock finale.
        Non solleva mai: in peggior scenario ritorna una LLMResponse is_stub=True.
        """
        req = LLMRequest(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            extra=extra or {},
        )
        attempts: List[Dict[str, Any]] = []
        chain = [self.primary] + [b for b in self.fallback_chain if b != self.primary]
        # Sempre assicurare mock in coda come ultima rete di sicurezza
        if "mock" not in chain:
            chain.append("mock")

        for backend_name in chain:
            t0 = time.time()
            try:
                resp = self._call_backend(backend_name, req)
                resp.fallback_used = (backend_name != self.primary)
                resp.latency_ms = resp.latency_ms or round((time.time() - t0) * 1000, 2)
                self.last_response = resp
                attempts.append({"backend": backend_name, "status": "ok",
                                 "latency_ms": resp.latency_ms})
                log.debug("llm.complete ok via %s (fallback=%s)",
                          backend_name, resp.fallback_used)
                return resp
            except LLMError as e:
                attempts.append({"backend": backend_name, "status": "error",
                                 "reason": str(e)})
                log.warning("llm backend %s failed: %s", backend_name, e)
                continue
            except Exception as e:
                attempts.append({"backend": backend_name, "status": "error",
                                 "reason": repr(e)})
                continue

        # Non dovrebbe mai arrivare qui perché mock sempre disponibile,
        # ma per sicurezza forziamo un mock
        resp = mock_backend.complete(req)
        resp.fallback_used = True
        self.last_response = resp
        return resp

    def health(self) -> Dict[str, bool]:
        """Health check di tutti i backend configurati."""
        out: Dict[str, bool] = {}
        for name, (_, health_fn) in _BACKENDS.items():
            try:
                out[name] = bool(health_fn(self.config.get(name, {}) or {}))
            except Exception:
                out[name] = False
        return out


if __name__ == "__main__":
    c = LLMClient.from_epigenome()
    print("configured primary:", c.primary)
    print("fallback chain:", c.fallback_chain)
    print("health:", c.health())
    r = c.complete("Dimmi in una frase cosa è SPEACE.", max_tokens=64)
    print("---")
    print(f"backend={r.backend} stub={r.is_stub} latency={r.latency_ms}ms")
    print(r.text)
