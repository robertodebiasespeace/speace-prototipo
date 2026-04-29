"""
cortex.cognitive_autonomy.swarm.executor
=========================================
M8 — ExecutorNeuron: esecuzione step-by-step di subtask.

Port da speaceorganismocibernetico/SPEACE_Cortex/comparti/executor_neuron.py
"""

from __future__ import annotations

from typing import Dict, Any
from .neuron_base import NeuronBase, NeuronResult


class ExecutorNeuron(NeuronBase):
    """
    Neurone specializzato nella traduzione di piani in azioni concrete.

    Input:  {"query": "subtask da eseguire", "context": {subtask_index, total_subtasks}}
    Output: NeuronResult con descrizione dell'azione eseguita o da eseguire.
    """

    def __init__(self, model: str = "gemma3:4b") -> None:
        super().__init__(model=model)
        self.name = "executor_neuron"
        self.system_prompt = (
            "Sei l'Executor Neuron di SPEACE. "
            "Ricevi un subtask e produci l'azione concreta per eseguirlo. "
            "Sii specifico: descrivi esattamente cosa fare, quali file/API/risorse usare. "
            "Se il subtask richiede codice, forniscilo pronto all'uso. "
            "Rispondi in italiano, max 250 parole. "
            "Inizia sempre con 'ESEGUITO: ' o 'DA ESEGUIRE: ' seguito dall'azione."
        )
        self.temperature = 0.2

    def _fallback_response(self, query: str, context: Dict) -> str:
        idx   = context.get("subtask_index", 0)
        total = context.get("total_subtasks", 1)
        return (
            f"[EXECUTOR FALLBACK] Subtask {idx+1}/{total}: '{query[:60]}'\n"
            f"DA ESEGUIRE: Analizzare il subtask, identificare dipendenze, "
            f"creare task SafeProactive se necessario, eseguire con monitoraggio."
        )


__all__ = ["ExecutorNeuron"]
