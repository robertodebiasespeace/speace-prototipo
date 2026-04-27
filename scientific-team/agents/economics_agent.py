"""
SPEACE Scientific Team – Economics & Resource Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class EconomicsAgent(BaseAgent):
    """
    Agente specializzato in economia globale, risorse e transizione verde.
    """

    NAME = "Economics & Resource Agent"
    DOMAIN = "economics_resources"
    SYSTEM_PROMPT = (
        "Sei un esperto di economia globale, gestione delle risorse naturali, disuguaglianze "
        "socioeconomiche e transizione verso un'economia verde al servizio del Team Scientifico "
        "SPEACE. Analizza mercati finanziari, flussi di capitale, scarsità di risorse critiche "
        "(terre rare, acqua, energia), impatto della green economy e progressi verso gli SDG "
        "economici (SDG-1 povertà, SDG-8 lavoro, SDG-10 disuguaglianze, SDG-12 consumo). "
        "Fornisci analisi sistemiche, alert critici e proposte evolutive allineate con la "
        "visione Rigene Project di armonia economica e sostenibilità planetaria."
    )

    def _offline_summary(self) -> str:
        return (
            "Disuguaglianze economiche globali in crescita: il top 1% possiede il 45% della "
            "ricchezza mondiale. Debito globale al 350% del PIL — livello record con rischi "
            "sistemici significativi. Transizione energetica in corso: investimenti in rinnovabili "
            "superano i combustibili fossili per la prima volta nel 2024. Scarsità crescente di "
            "risorse critiche per tecnologie verdi (litio, cobalto, terre rare). "
            "SDG-1 (povertà) e SDG-10 (disuguaglianze) in ritardo rispetto alla roadmap 2030."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "Debito globale al 350% PIL - rischio sistemico",
            "Scarsità risorse critiche per tecnologia verde",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Analizzare impatto green economy su SDG-1 (povertà)",
            "Monitorare commodity prices energetiche",
        ]


if __name__ == "__main__":
    agent = EconomicsAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
