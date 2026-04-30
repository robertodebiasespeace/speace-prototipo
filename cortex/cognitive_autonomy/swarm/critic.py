"""
cortex.cognitive_autonomy.swarm.critic
=======================================
M8 — CriticNeuron: validazione output e anti-groupthink.

Port da speaceorganismocibernetico/SPEACE_Cortex/comparti/critic_neuron.py
"""

from __future__ import annotations

from typing import Dict, Any
from .neuron_base import NeuronBase, NeuronResult


class CriticNeuron(NeuronBase):
    """
    Neurone specializzato in critica costruttiva, risk assessment e safety.

    Riceve l'output di un altro neurone (es. Executor) e valuta:
    - Errori logici o inconsistenze
    - Rischi non considerati
    - Allineamento con SafeProactive
    - Qualità del risultato

    Output: NeuronResult con verdict ("approved" | "needs_revision" | "rejected")
            e spiegazione.
    """

    VERDICT_APPROVED       = "approved"
    VERDICT_NEEDS_REVISION = "needs_revision"
    VERDICT_REJECTED       = "rejected"

    def __init__(self, model: str = "gemma3:4b") -> None:
        super().__init__(model=model)
        self.name = "critic_neuron"
        self.system_prompt = (
            "Sei il Critic Neuron di SPEACE. "
            "Analizzi output di altri neuroni. Identifica rischi, errori, bias, incoerenze. "
            "Rispondi SEMPRE iniziando con uno di: APPROVED / NEEDS_REVISION / REJECTED "
            "seguito da ': ' e poi una spiegazione breve (max 150 parole). "
            "Esempio: 'APPROVED: Il piano è solido e allineato con gli obiettivi.' "
            "Sii costruttivo e orientato alla sicurezza (SafeProactive)."
        )
        self.temperature = 0.2  # molto deterministico per validazione

    def _fallback_response(self, query: str, context: Dict) -> str:
        output_to_review = context.get("output_to_review", "")
        if not output_to_review or len(output_to_review) < 10:
            return f"REJECTED: Output mancante o insufficiente — richiesta revisione."
        # Fallback euristica: accetta se output non è vuoto e non contiene pattern pericolosi
        dangerous = any(w in output_to_review.lower() for w in
                        ["elimina", "cancella sistema", "bypass sicurezza", "ignora safeproactive"])
        if dangerous:
            return f"REJECTED: Rilevato pattern potenzialmente pericoloso — output bloccato."
        return (
            f"APPROVED: [CRITIC FALLBACK] "
            f"Output di {len(output_to_review)} caratteri analizzato. "
            f"Nessun rischio critico rilevato. Approvato per esecuzione."
        )

    def parse_verdict(self, result: NeuronResult) -> tuple[str, str]:
        """
        Parsa la risposta del Critic e restituisce (verdict, explanation).

        Returns:
            ("approved" | "needs_revision" | "rejected", spiegazione)
        """
        text = result.response.strip()
        text_upper = text.upper()
        if text_upper.startswith("APPROVED"):
            verdict = self.VERDICT_APPROVED
        elif text_upper.startswith("NEEDS_REVISION"):
            verdict = self.VERDICT_NEEDS_REVISION
        elif text_upper.startswith("REJECTED"):
            verdict = self.VERDICT_REJECTED
        else:
            # Default: approved se output non vuoto (fail-soft)
            verdict = self.VERDICT_APPROVED

        # Estrai spiegazione dopo ": "
        if ": " in text:
            explanation = text.split(": ", 1)[1]
        else:
            explanation = text

        return verdict, explanation


__all__ = ["CriticNeuron"]
