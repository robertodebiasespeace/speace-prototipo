"""
cortex.cognitive_autonomy.swarm.planner
=======================================
M8 — PlannerNeuron: decomposizione task e pianificazione goal.

Port da speaceorganismocibernetico/SPEACE_Cortex/comparti/planner_neuron.py
"""

from __future__ import annotations

import re
from typing import Dict, Any, List

from .neuron_base import NeuronBase, NeuronResult


class PlannerNeuron(NeuronBase):
    """
    Neurone specializzato in pianificazione e decomposizione di task.

    Input:  {"query": "Obiettivo da pianificare", "context": {...}}
    Output: NeuronResult con risposta che include subtask numerati.
    """

    def __init__(self, model: str = "gemma3:4b") -> None:
        super().__init__(model=model)
        self.name = "planner_neuron"
        self.system_prompt = (
            "Sei il Planner Neuron di SPEACE. "
            "Il tuo compito è creare piani chiari, realistici e allineati con il Rigene Project. "
            "Quando ti viene chiesto di pianificare un obiettivo, rispondi con una lista numerata "
            "di subtask concreti (da 2 a 5). Formato: '1. [subtask]\\n2. [subtask]\\n...'. "
            "Ogni subtask deve essere atomico, verificabile e orientato all'azione. "
            "Rispondi in italiano, max 200 parole."
        )
        self.temperature = 0.3  # più deterministico per pianificazione

    def _fallback_response(self, query: str, context: Dict) -> str:
        """Genera subtask deterministici dal testo della query."""
        q = query.strip()[:60]
        return (
            f"[PLANNER FALLBACK] Piano per: '{q}'\n"
            f"1. Analizzare il contesto attuale del sistema\n"
            f"2. Identificare risorse disponibili e vincoli\n"
            f"3. Definire metriche di successo misurabili\n"
            f"4. Eseguire primo passo verificabile\n"
            f"5. Valutare risultato e iterare"
        )

    def extract_subtasks(self, result: NeuronResult) -> List[str]:
        """
        Estrae la lista di subtask dalla risposta del Planner.

        Returns:
            Lista di stringhe (subtask), vuota se parsing fallisce.
        """
        lines = result.response.strip().split("\n")
        subtasks = []
        for line in lines:
            line = line.strip()
            # Rimuove prefissi numerici come "1.", "1)", "- 1."
            match = re.match(r"^[\d]+[.)]\s*(.+)", line)
            if match:
                subtasks.append(match.group(1).strip())
            elif line.startswith("- ") and len(line) > 4:
                subtasks.append(line[2:].strip())
        return subtasks if subtasks else [result.response.strip()]


__all__ = ["PlannerNeuron"]
