"""
LLM Router — routing selettivo per agenti SPEACE (2026-04-27).

Problema risolto:
  Alcuni agenti richiedono capacità di reasoning avanzato (AdversarialAgent,
  EvidenceAgent) che un modello 4B locale non fornisce in modo affidabile.
  Il Router seleziona il backend appropriato per ogni tipo di agente:
    - standard   → backend primario (Ollama gemma3:4b — locale, gratuito)
    - reasoning  → backend reasoning (Anthropic claude-haiku — API, più capace)

Integrazione:
  LLMRequest.routing_hint: str  →  "standard" | "reasoning" | "creative" | ...
  LLMClient.complete() chiama Router.resolve() prima di selezionare il backend.

Configurazione epigenome.yaml:
  llm:
    routing:
      reasoning_agents: ["adversarial", "evidence"]
      reasoning_backend: "anthropic"
      creative_backend: "ollama_native"   # futuro
      default_backend: null               # null = usa llm.primary

Estendibilità:
  Aggiungere nuovi hint è semplice: basta aggiungere una entry in
  `routing_rules` o nel blocco routing dell'epigenome.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# Mapping hint → chiave config epigenome
_HINT_TO_CONFIG_KEY: Dict[str, str] = {
    "reasoning": "reasoning_backend",
    "creative":  "creative_backend",
}


class LLMRouter:
    """
    Risolve routing_hint → nome backend da usare.

    Args:
        routing_config: dict dal blocco `llm.routing` dell'epigenome.
        primary:        backend primario di default (da llm.primary).
    """

    def __init__(
        self,
        routing_config: Optional[Dict[str, Any]] = None,
        primary: str = "ollama_native",
    ) -> None:
        self._cfg     = routing_config or {}
        self._primary = primary

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def resolve(self, routing_hint: Optional[str] = None) -> str:
        """
        Dato un routing_hint, ritorna il nome del backend da usare.

        Regole (in ordine di priorità):
          1. routing_hint in _HINT_TO_CONFIG_KEY → cerca la chiave in routing_config
          2. routing_config.default_backend (se impostato)
          3. self._primary (fallback assoluto)

        Esempio:
          resolve("reasoning")  →  "anthropic"  (se reasoning_backend: anthropic)
          resolve("standard")   →  "ollama_native"
          resolve(None)         →  "ollama_native"
        """
        if routing_hint and routing_hint in _HINT_TO_CONFIG_KEY:
            config_key = _HINT_TO_CONFIG_KEY[routing_hint]
            backend = self._cfg.get(config_key)
            if backend:
                return str(backend)

        default = self._cfg.get("default_backend")
        if default:
            return str(default)

        return self._primary

    def is_reasoning_agent(self, agent_name: str) -> bool:
        """
        Verifica se un agente è classificato come reasoning-intensive.
        agent_name: nome lowercase (es. "adversarial", "evidence").
        """
        reasoning_agents = self._cfg.get("reasoning_agents", [])
        return agent_name.lower() in [a.lower() for a in reasoning_agents]

    def hint_for_agent(self, agent_name: str) -> str:
        """
        Ritorna il routing_hint appropriato per un agente dato il suo nome.
        Usato da BaseAgent per auto-classificarsi.
        """
        if self.is_reasoning_agent(agent_name):
            return "reasoning"
        return "standard"

    @classmethod
    def from_epigenome(cls, epigenome: Optional[Dict[str, Any]] = None) -> "LLMRouter":
        """Costruisce il router dalla configurazione epigenome."""
        llm_cfg      = (epigenome or {}).get("llm", {}) or {}
        routing_cfg  = llm_cfg.get("routing", {}) or {}
        primary      = llm_cfg.get("primary", "ollama_native")
        return cls(routing_config=routing_cfg, primary=primary)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "primary":           self._primary,
            "reasoning_backend": self._cfg.get("reasoning_backend", "anthropic"),
            "reasoning_agents":  self._cfg.get("reasoning_agents", []),
            "default_backend":   self._cfg.get("default_backend"),
        }


__all__ = ["LLMRouter"]
