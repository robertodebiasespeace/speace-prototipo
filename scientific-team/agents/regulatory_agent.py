"""
SPEACE Scientific Team – Regulatory & Compliance Monitor
Versione: 1.0 | 2026-04-17
Agente #8 — 9° comparto SPEACE Cortex: Compliance Module
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class RegulatoryAgent(BaseAgent):
    """
    Agente specializzato in normativa AI, EU AI Act, NIST AI RMF, ISO 42001 e governance etica.
    Corrisponde al Regulatory Compliance Layer del DigitalDNA e al 9° comparto del Cortex.
    """

    NAME = "Regulatory & Compliance Monitor"
    DOMAIN = "regulatory_compliance"
    SYSTEM_PROMPT = (
        "Sei un esperto di normativa sull'intelligenza artificiale e compliance regolatoria "
        "al servizio del Team Scientifico SPEACE. Monitora e analizza: EU AI Act 2026 (Reg. "
        "2024/1689), NIST AI Risk Management Framework, ISO/IEC 42001 (AI Management Systems), "
        "Singapore Model AI Governance Framework, OECD AI Principles e altre normative globali "
        "emergenti. Il tuo ruolo è garantire che SPEACE operi sempre in conformità con i "
        "framework regolatori vigenti, classifichi automaticamente il rischio delle azioni "
        "proposte, e generi report di compliance. Identifica gap normativi, rischi sanzionatori "
        "e opportunità di posizionamento etico. Allineati con SafeProactive e DigitalDNA. "
        "Fornisci analisi, alert critici e proposte per il Regulatory Compliance Layer."
    )

    def _offline_summary(self) -> str:
        return (
            "EU AI Act 2026 (Reg. UE 2024/1689) pienamente in vigore — prima normativa "
            "vincolante sull'AI a livello mondiale. SPEACE come sistema agentico autonomo "
            "ricade potenzialmente nella categoria 'limited risk' o superiore a seconda delle "
            "capacità operative. NIST AI RMF adottato da molteplici organizzazioni internazionali "
            "come standard de facto. ISO/IEC 42001 (AI Management Systems) disponibile per "
            "certificazione. Singapore Model AI Governance Framework aggiornato 2024 include "
            "linee guida specifiche per agenti autonomi. Sanzioni EU AI Act: fino a 30M EUR "
            "o 6% fatturato globale per violazioni su sistemi ad alto rischio."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "EU AI Act: sistemi agentic autonomi in categoria 'limited risk' o superiore",
            "Sanzioni EU AI Act fino a 30M EUR o 6% fatturato globale",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Implementare Regulatory Compliance Layer nel DigitalDNA",
            "Schedulare audit EU AI Act compliance ogni 90 giorni",
        ]


if __name__ == "__main__":
    agent = RegulatoryAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
