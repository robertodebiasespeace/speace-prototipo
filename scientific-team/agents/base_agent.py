"""
SPEACE Scientific Team — Base Agent (v1.1, 2026-04-27)

Migrato da Anthropic SDK diretto a LLMClient unificato.
Routing selettivo: ROUTING_HINT controlla il backend usato.

  ROUTING_HINT = "standard"   → Ollama gemma3:4b (default per tutti gli agenti)
  ROUTING_HINT = "reasoning"  → Anthropic claude-haiku (AdversarialAgent, EvidenceAgent)

Agenti che ereditano da BaseAgent non devono modificare il codice LLM:
basta settare ROUTING_HINT = "reasoning" nella sottoclasse.
"""

import json
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Optional

# ---- LLMClient path setup ----
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT_DIR))

try:
    from cortex.llm import LLMClient
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False


class BaseAgent:
    """
    Agente base del Team Scientifico SPEACE.

    Sottoclassi:
      - Impostare NAME, DOMAIN, SYSTEM_PROMPT
      - Impostare ROUTING_HINT = "reasoning" se l'agente richiede
        capacità avanzate (AdversarialAgent, EvidenceAgent)
      - Override _offline_summary / _offline_alerts / _offline_proposals
        per dati di fallback domain-specific
    """

    NAME          : str = "Base Agent"
    DOMAIN        : str = "general"
    SYSTEM_PROMPT : str = "Sei un agente del Team Scientifico SPEACE."
    ROUTING_HINT  : str = "standard"   # "standard" | "reasoning"

    def __init__(self, api_key: Optional[str] = None):
        # api_key mantenuto per backward-compat, LLMClient lo legge da env
        self._api_key = api_key
        self._llm: Optional[LLMClient] = None
        if _LLM_AVAILABLE:
            try:
                self._llm = LLMClient.from_epigenome()
            except Exception:
                self._llm = None
        self.last_analysis: Optional[Dict] = None

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def analyze(self, world_model_summary: Optional[Dict] = None) -> Dict:
        """Esegue l'analisi del dominio. Override in ogni agente specializzato."""
        context = self._build_context(world_model_summary)
        if self._llm is not None:
            return self._analyze_with_llm(context)
        return self._analyze_offline(context)

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _analyze_with_llm(self, context: str) -> Dict:
        """Analisi tramite LLMClient con routing selettivo."""
        try:
            resp = self._llm.complete(
                prompt       = context,
                system       = self.SYSTEM_PROMPT,
                max_tokens   = 800,
                temperature  = 0.3,
                routing_hint = self.ROUTING_HINT,
            )
            result = self._parse_llm_response(resp.text)
            result["llm_backend"]  = resp.backend
            result["llm_model"]    = resp.model
            result["routing_hint"] = resp.routing_hint
            result["latency_ms"]   = resp.latency_ms
            self.last_analysis = result
            return result
        except Exception as e:
            return self._analyze_offline(context, error=str(e))

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _analyze_offline(self, context: str, error: Optional[str] = None) -> Dict:
        result = {
            "agent":     self.NAME,
            "domain":    self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "summary":   self._offline_summary(),
            "alerts":    self._offline_alerts(),
            "proposals": self._offline_proposals(),
            "confidence": 0.5,
            "mode":      "offline",
            "error":     error,
        }
        self.last_analysis = result
        return result

    # ------------------------------------------------------------------
    # Parsing risposta LLM
    # ------------------------------------------------------------------

    def _parse_llm_response(self, text: str) -> Dict:
        return {
            "agent":     self.NAME,
            "domain":    self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "summary":   text[:500],
            "alerts":    self._extract_alerts(text),
            "proposals": self._extract_proposals(text),
            "confidence": 0.8,
            "mode":      "llm",
            "raw":       text,
        }

    def _build_context(self, world_model_summary: Optional[Dict]) -> str:
        base = f"Analizza lo stato attuale del dominio: {self.DOMAIN}. "
        if world_model_summary:
            base += (
                "Contesto World Model: "
                + json.dumps(world_model_summary, indent=2)[:500]
                + ". "
            )
        base += (
            "Fornisci: 1) Sommario stato attuale, "
            "2) Alert critici, "
            "3) Proposte evolutive per SPEACE."
        )
        return base

    def _extract_alerts(self, text: str) -> List[str]:
        alerts = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in
                   ["alert", "critico", "urgente", "pericolo", "warning"]):
                alerts.append(line.strip()[:200])
        return alerts[:3]

    def _extract_proposals(self, text: str) -> List[str]:
        proposals = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in
                   ["proposta", "suggest", "raccomanda", "dovrebbe", "propone"]):
                proposals.append(line.strip()[:200])
        return proposals[:3]

    # ------------------------------------------------------------------
    # Offline stubs (override in sottoclassi)
    # ------------------------------------------------------------------

    def _offline_summary(self) -> str:
        return (
            f"Analisi offline {self.DOMAIN} — Ollama non disponibile "
            f"o backend non raggiungibile."
        )

    def _offline_alerts(self) -> List[str]:
        return []

    def _offline_proposals(self) -> List[str]:
        return [
            f"Avviare Ollama (ollama serve) e caricare gemma3:4b "
            f"per analisi AI del dominio {self.DOMAIN}"
        ]
