"""
SPEACE Scientific Team – Space & Extraterrestrial Agent
Versione: 1.0 | 2026-04-17
"""

from typing import Dict, List, Optional
from .base_agent import BaseAgent


class SpaceAgent(BaseAgent):
    """
    Agente specializzato in esplorazione spaziale, colonizzazione, astronomia e difesa planetaria.
    """

    NAME = "Space & Extraterrestrial Agent"
    DOMAIN = "space_extraterrestrial"
    SYSTEM_PROMPT = (
        "Sei un esperto di esplorazione spaziale, pianificazione di missioni interplanetarie, "
        "astronomia, difesa planetaria e governance dello spazio al servizio del Team Scientifico "
        "SPEACE. Monitora le missioni NASA, ESA, SpaceX, CNSA e altri attori spaziali; il "
        "programma Artemis per il ritorno sulla Luna; i piani di colonizzazione di Marte; "
        "la crescita dei detriti orbitali e il rischio Kessler syndrome; il monitoraggio "
        "degli oggetti near-Earth (NEO) e la difesa planetaria. Analizza il ruolo futuro di "
        "SPEACE nella governance spaziale e nell'espansione dell'umanità oltre la Terra, "
        "in linea con la visione Rigene Project di espansione extraterrestre armoniosa. "
        "Fornisci analisi sistemiche, alert critici e proposte evolutive."
    )

    def _offline_summary(self) -> str:
        return (
            "Nuova era spaziale commerciale in piena espansione: SpaceX Starship operativa, "
            "Artemis program della NASA pianifica ritorno sulla Luna entro 2026. Colonizzazione "
            "di Marte in fase di planning avanzato — missioni umane previste entro 2030-2035. "
            "Crescita critica dei detriti orbitali: 30.000+ oggetti tracciabili in orbita bassa, "
            "rischio Kessler syndrome in aumento. Assenza di piano globale coordinato per la "
            "difesa planetaria da asteroidi — gap governance significativo. Telescopi di nuova "
            "generazione (JWST, ELT) rivoluzionano la comprensione dell'universo e ricerca "
            "di vita extraterrestre. Governance spaziale internazionale ancora inadeguata."
        )

    def _offline_alerts(self) -> List[str]:
        return [
            "Aumento detriti spaziali - rischio Kessler syndrome",
            "Nessun piano globale difesa planetaria da asteroidi",
        ]

    def _offline_proposals(self) -> List[str]:
        return [
            "Valutare ruolo SPEACE in governance spaziale futura",
            "Monitorare Near-Earth Objects database NASA",
        ]


if __name__ == "__main__":
    agent = SpaceAgent()
    result = agent.analyze()
    print(f"Agent: {result['agent']}")
    print(f"Mode:  {result['mode']}")
    print(f"Summary: {result['summary'][:120]}...")
    print(f"Alerts: {result['alerts']}")
    print(f"Proposals: {result['proposals']}")
