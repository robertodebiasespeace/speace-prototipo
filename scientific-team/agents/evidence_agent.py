"""
SPEACE Scientific Team – Evidence Verification Agent (Fact-Checker)
Versione: 1.0 | 2026-04-17

Agente fact-checker che verifica affidabilità e freschezza dei dati nei report
degli altri agenti. Riduce il rischio di errori sistemici da dati non verificati.
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

try:
    from .base_agent import BaseAgent as _BaseAgent
    _BASE_IMPORTED = True
except ImportError:
    _BASE_IMPORTED = False

# M3L.4: LLM adapter unificato
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT_DIR))
try:
    from cortex.llm import LLMClient
    _LLM_CLIENT_AVAILABLE = True
except Exception:
    _LLM_CLIENT_AVAILABLE = False


SYSTEM_PROMPT = (
    "Sei un fact-checker scientifico e un evidence verification specialist al servizio del "
    "Team Scientifico SPEACE. Il tuo ruolo è verificare l'affidabilità, la precisione e la "
    "freschezza dei dati contenuti nei report degli altri agenti specializzati. Controlla: "
    "presenza e qualità delle fonti citate (peer-reviewed? istituzionali? aggiornate?), "
    "coerenza tra dati numerici e affermazioni qualitative, freshness dei dati (quanto sono "
    "recenti?), cross-check tra fonti multiple (NASA, NOAA, WHO, ONU, IPCC, Nature, Science), "
    "identificazione di statistiche fuorvianti o decontestualizzate. "
    "Produci un report strutturato con: verifica delle fonti, stima della freschezza dei dati, "
    "reliability score complessivo e raccomandazioni per il miglioramento della qualità."
)


class EvidenceAgent:
    """
    Agente fact-checker e verificatore di evidenze del Team Scientifico SPEACE.
    Verifica affidabilità e freschezza dei dati dei report degli altri agenti.
    Non estende BaseAgent: usa il metodo verify() come interfaccia primaria.
    Il metodo analyze() è fornito per compatibilità con l'orchestrator.
    """

    NAME = "Evidence Verification Agent"
    DOMAIN = "evidence_verification"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        # M3L.4: client LLM unificato (cascade LM Studio → anthropic → mock)
        self.llm = LLMClient.from_epigenome() if _LLM_CLIENT_AVAILABLE else None
        self.last_verification = None

    def verify(self, reports: Dict) -> Dict:
        """
        Verifica affidabilità e freschezza dei dati nei report degli altri agenti.
        Usa il cascade LLM (LM Studio → anthropic → mock) quando disponibile.

        Args:
            reports: Dict con i report degli altri agenti
                     {agent_name: {summary, alerts, proposals, ...}}

        Returns:
            {
                "verification": str,
                "sources_verified": list,
                "data_freshness": str,
                "reliability_score": float
            }
        """
        if reports and self.llm is not None:
            return self._verify_with_llm_cascade(reports)
        if self.client and reports:
            return self._verify_with_llm(reports)
        return self._verify_offline(reports)

    def _verify_with_llm_cascade(self, reports: Dict) -> Dict:
        """Verifica via LLMClient (LM Studio / anthropic / mock automatico)."""
        try:
            reports_text = json.dumps(
                {k: {
                    "summary": v.get("summary", "")[:300],
                    "alerts": v.get("alerts", []),
                    "proposals": v.get("proposals", []),
                    "mode": v.get("mode", "unknown"),
                } for k, v in reports.items()},
                ensure_ascii=False,
                indent=2,
            )
            prompt = (
                "Verifica l'evidenza scientifica nei seguenti report del Team SPEACE:\n\n"
                f"{reports_text}\n\n"
                "Per ogni report valuta: 1) Fonti citate (presenti? attendibili?), "
                "2) Freschezza dei dati (anno/fonte?), 3) Accuracy statistica, "
                "4) Cross-check possibili con fonti standard (NASA, NOAA, WHO, IPCC, ONU). "
                "Fornisci un reliability score da 0 a 1 per il corpus complessivo."
            )
            resp = self.llm.complete(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                max_tokens=600,
                temperature=0.2,
            )
            text = resp.text or ""
            result = {
                "agent": self.NAME,
                "domain": self.DOMAIN,
                "timestamp": datetime.datetime.now().isoformat(),
                "verification": text[:600],
                "sources_verified": self._extract_sources(text),
                "data_freshness": self._estimate_freshness(text),
                "reliability_score": (
                    0.45 if resp.is_stub else self._estimate_reliability(text)
                ),
                "mode": f"llm:{resp.backend}" + (" (stub)" if resp.is_stub else ""),
                "backend": resp.backend,
                "fallback_used": resp.fallback_used,
                "latency_ms": resp.latency_ms,
            }
            self.last_verification = result
            return result
        except Exception as e:
            return self._verify_offline(reports, error=str(e))

    def _verify_with_llm(self, reports: Dict) -> Dict:
        """Verifica con Claude API."""
        try:
            reports_text = json.dumps(
                {k: {
                    "summary": v.get("summary", "")[:300],
                    "alerts": v.get("alerts", []),
                    "proposals": v.get("proposals", []),
                    "mode": v.get("mode", "unknown"),
                } for k, v in reports.items()},
                ensure_ascii=False,
                indent=2
            )
            prompt = (
                f"Verifica l'evidenza scientifica nei seguenti report del Team SPEACE:\n\n"
                f"{reports_text}\n\n"
                "Per ogni report valuta: 1) Fonti citate (presenti? attendibili?), "
                "2) Freschezza dei dati (anno/fonte?), 3) Accuracy statistica, "
                "4) Cross-check possibili con fonti standard (NASA, NOAA, WHO, IPCC, ONU). "
                "Fornisci un reliability score da 0 a 1 per il corpus complessivo."
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
                "verification": text[:600],
                "sources_verified": self._extract_sources(text),
                "data_freshness": self._estimate_freshness(text),
                "reliability_score": self._estimate_reliability(text),
                "mode": "llm",
            }
            self.last_verification = result
            return result
        except Exception as e:
            return self._verify_offline(reports, error=str(e))

    def _verify_offline(self, reports: Dict, error: str = None) -> Dict:
        """Verifica offline (fallback statico)."""
        # Stima quanti agenti sono in modalità LLM vs offline
        llm_count = sum(1 for v in reports.values() if v.get("mode") == "llm")
        total_count = len(reports)
        freshness = "recente (< 24h)" if llm_count > 0 else "statica (dati hardcoded offline)"

        result = {
            "agent": self.NAME,
            "domain": self.DOMAIN,
            "timestamp": datetime.datetime.now().isoformat(),
            "verification": (
                "Verifica offline: tutti i dati provengono da analisi LLM o fonti statiche. "
                "Configurare API per verifica real-time. "
                f"Agenti in modalità LLM: {llm_count}/{total_count}. "
                "Fonti standard raccomandate per verifica: NASA Earth Observatory, NOAA Global "
                "Monitoring Laboratory, WHO Global Health Observatory, IPCC AR6, ONU SDG "
                "Progress Report, IUCN Red List, World Bank Open Data."
            ),
            "sources_verified": [
                "NASA Earth Observatory (non verificato in offline)",
                "NOAA GML (non verificato in offline)",
                "WHO Global Health Observatory (non verificato in offline)",
                "IPCC AR6 (non verificato in offline)",
            ],
            "data_freshness": freshness,
            "reliability_score": 0.45 if llm_count == 0 else 0.65,
            "mode": "offline",
            "error": error,
        }
        self.last_verification = result
        return result

    def _extract_sources(self, text: str) -> List[str]:
        """Estrae fonti verificate dal testo LLM."""
        sources = []
        known_sources = ["NASA", "NOAA", "WHO", "IPCC", "ONU", "UN", "IUCN",
                         "Nature", "Science", "World Bank", "IMF", "IEA", "ESA"]
        for source in known_sources:
            if source.lower() in text.lower():
                sources.append(source)
        if not sources:
            for line in text.split("\n"):
                if any(kw in line.lower() for kw in ["fonte", "source", "dati", "report", "data"]):
                    sources.append(line.strip()[:150])
                    if len(sources) >= 5:
                        break
        return sources[:6]

    def _estimate_freshness(self, text: str) -> str:
        """Stima la freschezza dei dati dal testo LLM."""
        current_year = datetime.datetime.now().year
        if str(current_year) in text:
            return f"recente ({current_year})"
        elif str(current_year - 1) in text:
            return f"relativamente recente ({current_year - 1})"
        else:
            return "freschezza dati incerta — verificare timestamp fonti"

    def _estimate_reliability(self, text: str) -> float:
        """Stima un reliability score dal testo LLM."""
        positive_kw = ["verificato", "confermato", "affidabile", "attendibile", "peer-reviewed"]
        negative_kw = ["non verificato", "incerto", "obsoleto", "mancante", "bias"]
        pos = sum(1 for kw in positive_kw if kw.lower() in text.lower())
        neg = sum(1 for kw in negative_kw if kw.lower() in text.lower())
        score = 0.5 + (pos * 0.1) - (neg * 0.1)
        return round(max(0.0, min(1.0, score)), 2)

    def analyze(self, world_model_summary: Optional[Dict] = None) -> Dict:
        """
        Compatibilità con l'orchestrator: chiama verify con dict vuoto o world model.
        """
        reports = world_model_summary if world_model_summary else {}
        return self.verify(reports)


if __name__ == "__main__":
    agent = EvidenceAgent()

    # Test con report simulati
    mock_reports = {
        "Climate & Ecosystems Agent": {
            "summary": "CO2 a 422ppm secondo NOAA 2024. Perdita biodiversità confermata da IPCC.",
            "alerts": ["CO2 superiore a 420ppm"],
            "proposals": ["Monitorare NOAA in tempo reale"],
            "mode": "offline",
        },
        "Health & Pandemic Agent": {
            "summary": "AMR: 1.27M morti/anno da Lancet 2022. COVID long: 65M affetti.",
            "alerts": ["AMR critica"],
            "proposals": ["Integrare WHO surveillance"],
            "mode": "offline",
        },
    }
    result = agent.verify(mock_reports)
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Verification: {result['verification'][:120]}...")
    print(f"Sources verified: {result['sources_verified']}")
    print(f"Data freshness: {result['data_freshness']}")
    print(f"Reliability score: {result['reliability_score']}")
