"""
SPEACE Scientific Team – Governance & Ethics Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class GovernanceAgent(BaseAgent):
    """
    Agente specializzato in governance globale, etica AI, diritti umani e democrazia.
    """

    NAME = "Governance & Ethics Agent"
    DOMAIN = "governance_ethics"
    SYSTEM_PROMPT = (
        "Sei un esperto di governance globale, etica dell'intelligenza artificiale, diritti umani, "
        "democrazia e sistemi di governance distribuita al servizio del Team Scientifico SPEACE. "
        "Monitora l'evoluzione dei framework normativi (EU AI Act, NIST, ONU), l'ascesa "
        "dell'autoritarismo, i deficit democratici e le sfide della governance dell'AI a livello "
        "globale. Analizza come SPEACE può contribuire a una governance etica, trasparente e "
        "distribuita allineata con i valori del Rigene Project: pace, armonia, sostenibilità. "
        "Fornisci analisi sistemiche, alert critici e proposte evolutive per la governance etica."
    )

    def _offline_summary(self) -> str:
        return (
            "Crisi della governance globale in accelerazione: 72 paesi hanno subito "
            "regressioni democratiche nell'ultimo decennio. Ascesa dell'autoritarismo e "
            "polarizzazione politica ai massimi storici. Urgenza etica nell'AI: assenza di "
            "governance globale coordinata per sistemi AI avanzati. EU AI Act 2026 entrato in "
            "vigore — prima normativa vincolante sull'AI a livello mondiale. Necessità crescente "
            "di meccanismi di governance distribuita e trasparente per la transizione tecnologica."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "EU AI Act 2026 in vigore - compliance obbligatoria",
            "Deficit governance AI a livello globale",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Allineare SPEACE a framework EU AI Act",
            "Proporre SPEACE come strumento di governance distribuita",
        ]


if __name__ == "__main__":
    agent = GovernanceAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
