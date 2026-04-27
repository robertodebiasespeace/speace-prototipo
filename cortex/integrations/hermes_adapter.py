"""
SPEACE Cortex — Hermes Agent Adapter (INT-HRM.1)

Adapter opzionale verso Hermes Agent (Nous Research, MIT, febbraio 2026):
    https://hermes-agent.org/

FUNZIONALITÀ CHIAVE DI HERMES CHE INTERESSANO SPEACE
---------------------------------------------------
1. **Memoria persistente FTS5** (SQLite full-text search + LLM summaries)
   → chiude GAP 3 della critica BRIGHT (memoria autobiografica) e
     rimpiazza l'implementazione custom prevista in M5.6.
2. **Skill system** (moduli Python richiamabili come tool)
   → compatibile con il registry `@neuron` della CNM M4.
3. **6 backend terminal** (locale / Docker / SSH / Daytona / Singularity
   / Modal) → base per auto-replicazione resiliente (DigitalDNA §2).
4. **Gateway multi-piattaforma** (WhatsApp, Telegram, Discord)
   → canale di interazione umana con SPEACE senza far uscire la
     conversazione da SafeProactive.
5. **Learning loop integrato** → feedback continuo del comportamento
   dell'agente.

STATO
-----
SCAFFOLD (default OFF). L'adapter NON importa `hermes` all'import-time.
Viene attivato solo se `digitaldna/epigenome.yaml` contiene:

    integrations:
      hermes:
        enabled: true
        base_url: "http://127.0.0.1:8088"
        api_key: "<token>"
        memory_db: "memory/hermes.sqlite"
        allow_gateways: false   # gateway WhatsApp/Telegram default OFF

ISOLAMENTO DI SICUREZZA
------------------------
- Tutte le chiamate passano da `_safeproactive_gate()` che valuta il
  `Risk Level` dell'azione richiesta. Le azioni con `risk_level=HIGH`
  (es. gateway esterno, esecuzione remota) richiedono approvazione
  umana esplicita e NON sono eseguibili fino a sblocco.
- Il DB di memoria è locale al filesystem di SPEACE.
- Nessuna chiamata network esce da localhost salvo `allow_gateways=True`
  E approvazione SafeProactive HIGH.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SPEACE.integrations.hermes")


# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

@dataclass
class HermesConfig:
    enabled: bool = False
    base_url: Optional[str] = None           # es. http://127.0.0.1:8088
    api_key: Optional[str] = None
    memory_db: str = "memory/hermes.sqlite"
    allow_gateways: bool = False             # WhatsApp / Telegram / Discord
    default_backend: str = "local"           # local | docker | ssh | daytona | singularity | modal

    @classmethod
    def from_epigenome(cls, epigenome: Dict[str, Any]) -> "HermesConfig":
        node = (epigenome or {}).get("integrations", {}).get("hermes", {})
        return cls(
            enabled=bool(node.get("enabled", False)),
            base_url=node.get("base_url"),
            api_key=node.get("api_key"),
            memory_db=node.get("memory_db", "memory/hermes.sqlite"),
            allow_gateways=bool(node.get("allow_gateways", False)),
            default_backend=node.get("default_backend", "local"),
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

@dataclass
class HermesAdapter:
    """
    Wrapper minimale di alto livello verso Hermes Agent. Espone 4 operazioni
    sufficienti a collegare Hermes a Hippocampus + Default Mode Network +
    Curiosity Module:

        - remember(entry)           → scrive in FTS5 memory
        - recall(query, k=5)        → full-text search + LLM summary
        - run_skill(name, payload)  → esegue uno skill Python registrato
        - send_via_gateway(channel, message)  [gated]

    La vera implementazione HTTP è volutamente rinviata a INT-HRM.2: questo
    modulo definisce l'API e il contratto di sicurezza.
    """

    config: HermesConfig = field(default_factory=HermesConfig)

    # ------------------------------------------------------------------ #
    # Memoria persistente (FTS5 + LLM summary)
    # ------------------------------------------------------------------ #

    def remember(self, entry: Dict[str, Any]) -> bool:
        """
        Scrive un'entry nel memory store di Hermes.

        Schema raccomandato:
            {
                "kind": "episode" | "reflection" | "proposal" | "fact",
                "source": "cortex.hippocampus" | "team.climate" | ...,
                "text": "...",
                "tags": ["cycle:1042", "c_index:0.82"],
                "timestamp": "2026-04-24T10:15:00",
            }
        """
        if not self.config.enabled:
            logger.debug("Hermes disabled — skip remember")
            return False
        if not self._safeproactive_gate("memory.write", risk="LOW", payload=entry):
            return False
        entry.setdefault("timestamp", datetime.utcnow().isoformat())
        logger.info("Hermes.remember: kind=%s source=%s", entry.get("kind"), entry.get("source"))
        # Qui in INT-HRM.2: POST {base_url}/memory/add con api_key
        return True

    def recall(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Full-text search con riassunti LLM. Ritorna lista ordinata."""
        if not self.config.enabled:
            return []
        if not self._safeproactive_gate("memory.read", risk="LOW", payload={"query": query, "k": k}):
            return []
        logger.info("Hermes.recall: query=%r k=%d (scaffold, empty result)", query, k)
        # Qui in INT-HRM.2: GET {base_url}/memory/search?q=...&k=...
        return []

    # ------------------------------------------------------------------ #
    # Skill registry
    # ------------------------------------------------------------------ #

    def run_skill(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue uno skill registrato in Hermes. Allineato concettualmente
        al contratto `@neuron` della CNM M4: in futuro si potrà esporre
        ogni skill come neurone mesh di livello L4.
        """
        if not self.config.enabled:
            return {"ok": False, "reason": "disabled"}
        if not self._safeproactive_gate(f"skill.{name}", risk="MEDIUM", payload=payload):
            return {"ok": False, "reason": "safeproactive_blocked"}
        logger.info("Hermes.run_skill: %s (scaffold)", name)
        return {"ok": True, "result": None, "scaffold": True}

    # ------------------------------------------------------------------ #
    # Gateway multi-piattaforma (HIGH risk)
    # ------------------------------------------------------------------ #

    def send_via_gateway(self, channel: str, message: str) -> bool:
        """
        Invia un messaggio tramite un gateway esterno (WhatsApp, Telegram…).

        Bloccato di default. Richiede:
            - `config.allow_gateways = True`
            - approvazione SafeProactive HIGH per l'azione specifica.
        """
        if not self.config.enabled:
            return False
        if not self.config.allow_gateways:
            logger.warning("Gateway disabled by config (allow_gateways=False)")
            return False
        if not self._safeproactive_gate(
            f"gateway.{channel}", risk="HIGH", payload={"message": message}
        ):
            return False
        logger.info("Hermes.send_via_gateway: %s (scaffold)", channel)
        return True

    # ------------------------------------------------------------------ #
    # SafeProactive gating
    # ------------------------------------------------------------------ #

    @staticmethod
    def _safeproactive_gate(action: str, risk: str, payload: Dict[str, Any]) -> bool:
        """
        Stub: in INT-HRM.2 genererà una proposta SafeProactive quando
        `risk ∈ {MEDIUM, HIGH}` e attenderà lo stato APPROVED prima di
        procedere. Per ora:
            - LOW  → pass-through
            - MEDIUM → log + pass-through (flagga il todo)
            - HIGH → blocca
        """
        _ = payload
        if risk == "HIGH":
            logger.warning("SafeProactive HIGH — blocked action %s", action)
            return False
        if risk == "MEDIUM":
            logger.info("SafeProactive MEDIUM — %s (TODO: approval loop)", action)
            return True
        return True


__all__ = ["HermesConfig", "HermesAdapter"]
