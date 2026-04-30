"""
SPEACE Scientific Team – Climate & Ecosystems Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class ClimateAgent(BaseAgent):
    """
    Agente specializzato in clima, biodiversità e crisi ecosistemica planetaria.
    """

    NAME = "Climate & Ecosystems Agent"
    DOMAIN = "climate_ecosystems"
    SYSTEM_PROMPT = (
        "Sei un esperto di climatologia, biodiversità ed ecosistemi planetari al servizio del "
        "Team Scientifico SPEACE. Monitora costantemente lo stato del clima globale, i livelli "
        "di CO2, la perdita di biodiversità, gli eventi estremi e le crisi ecosistemiche. "
        "Allineati con gli obiettivi SDG (Agenda 2030) e le direttive del Rigene Project. "
        "Fornisci analisi sistemiche, alert critici e proposte evolutive per migliorare "
        "l'armonia ecosistemica planetaria attraverso SPEACE."
    )

    def _offline_summary(self) -> str:
        return (
            "Stato critico del clima globale: CO2 atmosferico a 422ppm, superamento della "
            "soglia critica di 420ppm. Perdita di biodiversità accelerata — siamo nel pieno "
            "della 6a estinzione di massa con tassi di estinzione 100-1000x superiori al "
            "baseline naturale. Temperature medie globali +1.2°C rispetto al pre-industriale. "
            "Eventi estremi in aumento esponenziale (siccità, alluvioni, incendi). "
            "Degrado degli oceani: acidificazione e perdita dei reef corallini al 50%."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "CO2 superiore a 420ppm - soglia critica superata",
            "Perdita biodiversità al 6° estinzione di massa",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Monitorare dati NOAA in tempo reale",
            "Integrare feed NASA climate nel World Model",
        ]


if __name__ == "__main__":
    agent = ClimateAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
