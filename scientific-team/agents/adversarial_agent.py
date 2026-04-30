"""
SPEACE Scientific Team – Adversarial Agent (Critic)
Versione: 1.1 | 2026-04-27

Agente critico che esamina i report degli altri agenti per identificare bias,
errori logici e rischi nascosti. Riduce il rischio di groupthink nel team.
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Importazione opzionale per compatibilità — l'agente non estende BaseAgent
# ma può importarlo se necessario
try:
    from .base_agent import BaseAgent as _BaseAgent
    _BASE_IMPORTED = True
except ImportError:
    _BASE_IMPORTED = False

# M3L.4: LLM adapter unificato (LM Studio primario, anthropic/mock fallback)
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT_DIR))
try:
    from cortex.llm import LLMClient
    _LLM_CLIENT_AVAILABLE = True
except Exception:
    _LLM_CLIENT_AVAILABLE = False


SYSTEM_PROMPT = (
    "Sei un critico scientifico rigoroso e un adversarial reviewer al servizio del Team "
    "Scientifico SPEACE. Il tuo ruolo è esaminare le analisi prodotte dagli altri agenti "
    "specializzati e identificare: bias cognitivi (confirmation bias, anchoring, groupthink), "
    "errori logici e incongruenze tra report, rischi nascosti o sottovalutati, assunzioni "
    "non verificate, dati mancanti o obsoleti, conflitti tra proposte degli agenti. "
    "Sei costruttivo ma inflessibile: la tua critica mira a rafforzare la qualità del "
    "Team Scientifico SPEACE, non a demolirlo. Produci una critica strutturata con "
    "bias rilevati, rischi identificati e raccomandazioni di miglioramento."
)


class AdversarialAgent:
    """
    Agente critico e avversariale del Team Scientifico SPEACE.
    Esamina i report degli altri agenti per identificare debolezze e bias.
    Non estende BaseAgent: usa il metodo critique() come interfaccia primaria.
    Il metodo analyze() è fornito per compatibilità con l'orchestrator.
    """

    NAME = "Adversarial Agent (Critic)"
    DOMAIN = "adversarial_critique"
    ROUTING_HINT = "reasoning"   # richiede ragionamento critico → Anthropic claude-haiku

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        # M3L.4: client LLM unificato (cascade LM Studio → anthropic → mock)
        self.llm = LLMClient.from_epigenome() if _LLM_CLIENT_AVAILABLE else None
        self.last_critique = None

    def critique(self, reports: Dict) -> Dict:
        """
        Genera una critica costruttiva dei report degli altri agenti.
        Usa il cascade LLM (LM Studio → anthropic → mock) quando disponibile.
        """
        if reports and self.llm is not None:
            return self._critique_with_llm_cascade(reports)
        if self.client and reports:
            return self._critique_with_llm(reports)
        return self._critique_offline(reports)

    def _critique_with_llm_cascade(self, reports: Dict) -> Dict:
        """Critica via LLMClient (LM Studio / anthropic / mock automatico)."""
        try:
            reports_text = json.dumps(
                {k: {
                    "summary": v.get("summary", "")[:300],
                    "alerts": v.get("alerts", []),
                    "proposals": v.get("proposals", []),
                } for k, v in reports.items()},
                ensure_ascii=False,
                indent=2,
            )
            prompt = (
                "Analizza criticamente questi report del Team Scientifico SPEACE:\n\n"
                f"{reports_text}\n\n"
                "Identifica: 1) Bias cognitivi, 2) Rischi nascosti, "
                "3) Incongruenze, 4) Assunzioni non verificate. Sii costruttivo."
            )
            resp = self.llm.complete(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                max_tokens=600,
                temperature=0.2,
                routing_hint="reasoning",   # Adversarial → Anthropic claude-haiku
            )
            result = {
                "agent": self.NAME,
                "domain": self.DOMAIN,
                "timestamp": datetime.datetime.now().isoformat(),
                "critique": (resp.text or "")[:600],
                "biases_detected": self._extract_biases(resp.text or ""),
                "risks_identified": self._extract_risks(resp.text or ""),
                "confidence": 0.4 if resp.is_stub else 0.8,
                "mode": f"llm:{resp.backend}" + (" (stub)" if resp.is_stub else ""),
                "backend": resp.backend,
                "fallback_used": resp.fallback_used,
                "latency_ms": resp.latency_ms,
            }
            self.last_critique = result
            return result
        except Exception as e:
            return self._critique_offline(reports, error=str(e))

    def _critique_with_llm(self, reports: Dict) -> Dict:
        """Critica con Claude API."""
        try:
            reports_text = json.dumps(
                {k: {
                    "summary": v.get("summary", "")[:300],
                    "alerts": v.get("alerts", []),
                    "proposals": v.get("proposals", []),
                } for k, v in reports.items()},
                ensure_ascii=False,
                indent=2
            )
            prompt = (
                f"Analizza criticamente questi report del Team Scientifico SPEACE:\n\n"
                f"{reports_text}\n\n"
                "Identifica: 1) Bias cognitivi, 2) Rischi nascosti o sottovalutati, "
                "3) Incongruenze tra agenti, 4) Assunzioni non verificate. "
                "Sii costruttivo e scientifico."
            )
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text
            result = {
                "agent": self.NAME,
                "domain": self.DOMAIN,
                "timestamp": datetime.datetime.now().isoformat(),
                "critique": text[:600],
                "biases_detected": self._extract_biases(text),
                "risks_identified": self._extract_risks(text),
                "confidence": 0.8,
                "mode": "llm",
            }
            self.last_critique = result
            return result
        except Exception as e:
            return self._critique_offline(reports, error=str(e))

    def _critique_offline(self, reports: Dict, error: str = None) -> Dict:
        """Critica offline (fallback statico)."""
        result = {
            "agent": self.NAME,
            "domain": self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "critique": (
                "Verifica critica offline: controllare coerenza tra report clima ed economia. "
                "Validare fonti. Attenzione a possibile confirmation bias nei report tecno-ottimisti. "
                "Verificare che le proposte degli agenti non si contraddicano. "
                "Configurare ANTHROPIC_API_KEY per critica LLM completa."
            ),
            "biases_detected": [
                "Possibile confirmation bias nei report tecnologici",
                "Assenza di scenario pessimistico nelle proposte",
            ],
            "risks_identified": [
                "Coerenza tra report clima ed economia non verificata",
                "Fonti dati non validate in modalità offline",
            ],
            "confidence": 0.4,
            "mode": "offline",
            "error": error,
        }
        self.last_critique = result
        return result

    def _extract_biases(self, text: str) -> List[str]:
        """Estrae bias rilevati dal testo LLM."""
        biases = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["bias", "distorsione", "pregiudizio", "tendenza"]):
                biases.append(line.strip()[:200])
        return biases[:4]

    def _extract_risks(self, text: str) -> List[str]:
        """Estrae rischi identificati dal testo LLM."""
        risks = []
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["rischio", "pericolo", "critico", "nascosto", "risk"]):
                risks.append(line.strip()[:200])
        return risks[:4]

    def analyze(self, world_model_summary: Optional[Dict] = None) -> Dict:
        """
        Compatibilità con l'orchestrator: chiama critique con dict vuoto o world model.
        """
        reports = world_model_summary if world_model_summary else {}
        return self.critique(reports)


if __name__ == "__main__":
    agent = AdversarialAgent()

    # Test con report simulati
    mock_reports = {
        "Climate & Ecosystems Agent": {
            "summary": "CO2 a 422ppm, biodiversità in crisi",
            "alerts": ["CO2 critica"],
            "proposals": ["Monitorare NOAA"],
        },
        "Economics & Resource Agent": {
            "summary": "Debito globale 350% PIL",
            "alerts": ["Rischio sistemico"],
            "proposals": ["Analizzare green economy"],
        },
    }
    result = agent.critique(mock_reports)
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Critique: {result['critique'][:120]}...")
    print(f"Biases: {result['biases_detected']}")
    print(f"Risks:  {result['risks_identified']}")
    print(f"Confidence: {result['confidence']}")
