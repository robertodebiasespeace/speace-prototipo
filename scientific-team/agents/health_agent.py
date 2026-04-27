"""
SPEACE Scientific Team – Health & Pandemic Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class HealthAgent(BaseAgent):
    """
    Agente specializzato in salute globale, epidemiologie, pandemie e approccio One Health.
    """

    NAME = "Health & Pandemic Agent"
    DOMAIN = "health_pandemic"
    SYSTEM_PROMPT = (
        "Sei un esperto di salute globale, epidemiologia, pandemie e approccio One Health "
        "(salute umana, animale ed ecosistemica come sistema integrato) al servizio del Team "
        "Scientifico SPEACE. Monitora le minacce sanitarie emergenti, la resistenza antimicrobica "
        "(AMR), i nuovi patogeni zoonotici, l'accesso alle cure e il legacy post-COVID. "
        "Analizza le correlazioni tra cambiamento climatico, perdita di biodiversità e emergenza "
        "di nuove malattie. Integra dati WHO, CDC, ECDC e altri sistemi di sorveglianza globale. "
        "Fornisci analisi sistemiche, alert critici e proposte evolutive per la salute planetaria, "
        "allineate con SDG-3 (salute e benessere) e la visione Rigene Project."
    )

    def _offline_summary(self) -> str:
        return (
            "Post-COVID legacy: long COVID affligge 65+ milioni di persone globalmente, con "
            "impatti su produttività e sistemi sanitari. AMR (Antimicrobial Resistance) in "
            "fase critica: resistenza agli antibiotici già causa 1.27M morti/anno, previsti "
            "10M/anno entro 2050. Nuove minacce emergenti da deforestazione e zoonosi: "
            "aumento del 300% di malattie zoonotiche negli ultimi 30 anni. Accesso ai farmaci "
            "e ai vaccini ancora profondamente ineguale tra Nord e Sud globale. Necessità "
            "urgente di architettura One Health integrata e sistemi di early warning pandemico."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "AMR (resistenza antibiotici) - 10M morti/anno previsti 2050",
            "Nuovi patogeni emergenti da deforestazione",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Integrare WHO surveillance nei feed World Model",
            "Monitorare correlazione climate change - malattie emergenti",
        ]


if __name__ == "__main__":
    agent = HealthAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
