"""
cortex.cognitive_autonomy.swarm.researcher
===========================================
M8 — ResearcherNeuron: ricerca informazioni e cross-check.

Port da speaceorganismocibernetico/SPEACE_Cortex/comparti/researcher_neuron.py
"""

from __future__ import annotations

from typing import Dict, Any
from .neuron_base import NeuronBase, NeuronResult


class ResearcherNeuron(NeuronBase):
    """
    Neurone specializzato in ricerca informazioni e arricchimento World Model.

    Input:  {"query": "Cosa devo ricercare", "context": {world_model_snapshot}}
    Output: NeuronResult con informazioni sintetizzate e fonti suggerite.
    """

    def __init__(self, model: str = "gemma3:4b") -> None:
        super().__init__(model=model)
        self.name = "researcher_neuron"
        self.system_prompt = (
            "Sei il Researcher Neuron di SPEACE. "
            "Analizzi informazioni in profondità e arricchisci il World Model di SPEACE. "
            "Ricerca fatti, colleghi concetti, identifica connessioni non ovvie. "
            "Per ogni query fornisci: (1) sintesi delle informazioni chiave, "
            "(2) connessioni con altri domini, (3) fonti suggerite per approfondire. "
            "Rispondi in italiano, max 200 parole, basandoti su conoscenza verificabile."
        )
        self.temperature = 0.4

    def _fallback_response(self, query: str, context: Dict) -> str:
        q = query.strip()[:60]
        return (
            f"[RESEARCHER FALLBACK] Ricerca per: '{q}'\n"
            f"Sintesi: Informazioni sul topic ricercato. Dipendente da conoscenza disponibile.\n"
            f"Connessioni: Relazione con WorldModel SPEACE, obiettivi Rigene Project, SDG ONU.\n"
            f"Fonti suggerite: rigeneproject.org, arxiv.org, NASA/NOAA data feeds."
        )


__all__ = ["ResearcherNeuron"]
