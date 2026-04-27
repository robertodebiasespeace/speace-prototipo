"""
SPEACE Scientific Team – Base Agent
Classe base per tutti gli agenti del team scientifico.
Versione: 1.0 | 2026-04-17
"""

import os
import json
import datetime
from typing import Dict, List, Optional
from pathlib import Path

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class BaseAgent:
    """
    Agente base del Team Scientifico SPEACE.
    Ogni agente specializzato eredita da questa classe.
    Usa Claude API se disponibile, altrimenti modalità offline.
    """

    NAME = "Base Agent"
    DOMAIN = "general"
    SYSTEM_PROMPT = "Sei un agente del Team Scientifico SPEACE."

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.last_analysis = None

    def analyze(self, world_model_summary: Optional[Dict] = None) -> Dict:
        """
        Esegue l'analisi del dominio.
        Override in ogni agente specializzato.
        """
        context = self._build_context(world_model_summary)

        if self.client:
            return self._analyze_with_llm(context)
        else:
            return self._analyze_offline(context)

    def _analyze_with_llm(self, context: str) -> Dict:
        """Analisi con Claude API."""
        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )
            text = message.content[0].text
            return self._parse_llm_response(text)
        except Exception as e:
            return self._analyze_offline(context, error=str(e))

    def _analyze_offline(self, context: str, error: str = None) -> Dict:
        """Analisi offline con dati statici (fallback)."""
        return {
            "agent": self.NAME,
            "domain": self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": self._offline_summary(),
            "alerts": self._offline_alerts(),
            "proposals": self._offline_proposals(),
            "confidence": 0.5,
            "mode": "offline",
            "error": error,
        }

    def _parse_llm_response(self, text: str) -> Dict:
        """Parsa la risposta LLM in struttura standardizzata."""
        return {
            "agent": self.NAME,
            "domain": self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": text[:500],
            "alerts": self._extract_alerts(text),
            "proposals": self._extract_proposals(text),
            "confidence": 0.8,
            "mode": "llm",
            "raw": text,
        }

    def _build_context(self, world_model_summary: Optional[Dict]) -> str:
        """Costruisce il contesto per l'analisi."""
        base = f"Analizza lo stato attuale del dominio: {self.DOMAIN}. "
        if world_model_summary:
            base += f"Contesto World Model: {json.dumps(world_model_summary, indent=2)[:500]}. "
        base += "Fornisci: 1) Sommario stato attuale, 2) Alert critici, 3) Proposte evolutive per SPEACE."
        return base

    def _extract_alerts(self, text: str) -> List[str]:
        """Estrae alert dal testo LLM."""
        alerts = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["alert", "critico", "urgente", "pericolo", "warning"]):
                alerts.append(line.strip()[:200])
        return alerts[:3]

    def _extract_proposals(self, text: str) -> List[str]:
        """Estrae proposte dal testo LLM."""
        proposals = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["proposta", "suggest", "raccomanda", "dovrebbe", "propone"]):
                proposals.append(line.strip()[:200])
        return proposals[:3]

    def _offline_summary(self) -> str:
        return f"Analisi offline {self.DOMAIN} — configura ANTHROPIC_API_KEY per analisi LLM completa."

    def _offline_alerts(self) -> List[str]:
        return []

    def _offline_proposals(self) -> List[str]:
        return [f"Configurare API key per abilitare analisi AI del dominio {self.DOMAIN}"]
