"""
SPEACE Scientific Team – Social Cohesion Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class SocialAgent(BaseAgent):
    """
    Agente specializzato in coesione sociale, migrazioni, disuguaglianze e SDGs.
    """

    NAME = "Social Cohesion Agent"
    DOMAIN = "social_cohesion"
    SYSTEM_PROMPT = (
        "Sei un esperto di coesione sociale, dinamiche migratorie, disuguaglianze strutturali "
        "e progressi verso gli Obiettivi di Sviluppo Sostenibile (SDGs) al servizio del Team "
        "Scientifico SPEACE. Monitora la polarizzazione politica e culturale, i flussi migratori "
        "climatici e geopolitici, l'accesso all'istruzione, le disuguaglianze di genere e razza, "
        "e l'evoluzione dei movimenti sociali globali. Analizza come la tecnologia (AI, social "
        "media) amplifica o riduce le fratture sociali. Allineati con SDG-10 (riduzione "
        "disuguaglianze), SDG-16 (pace e giustizia) e la visione Rigene Project di coesione "
        "sociale come fondamento della pace planetaria. Fornisci analisi, alert e proposte."
    )

    def _offline_summary(self) -> str:
        return (
            "Polarizzazione sociale e politica crescente ai massimi storici in molte democrazie. "
            "Migrazioni climatiche in forte accelerazione: 21.5M sfollati climatici nel 2023, "
            "proiezioni fino a 200M entro 2050. SDG-10 (disuguaglianze) in grave ritardo: "
            "l'indice Gini globale è peggiorato negli ultimi 5 anni. Effetto amplificante dei "
            "social media sulla polarizzazione — echo chambers e disinformazione sistemica. "
            "Crisi dell'istruzione post-pandemia: 70M bambini con learning loss significativo. "
            "Segnali positivi: crescita movimenti per giustizia climatica e diritti digitali."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "200M rifugiati climatici previsti entro 2050",
            "Polarizzazione politica ai massimi storici",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Analizzare correlazione coesione sociale - resilienza ecosistemica",
            "Monitorare SDG progress dashboard ONU",
        ]


if __name__ == "__main__":
    agent = SocialAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
