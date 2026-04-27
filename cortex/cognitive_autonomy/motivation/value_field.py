"""
ValueField — M5.5 (Cognitive Autonomy)

Implementa V_internal(s, h): campo di valore interno basato sullo stato
omeostatico del sistema. Segnale motivazionale che orienta la selezione
delle azioni verso il soddisfacimento dei drive fondamentali.

Formula:
    V_internal(s, h) = Σ_d w_d * f_d(h_d)  +  ε * novelty(s)

dove:
    h_d      = livello corrente del drive d (da HomeostaticController)
    f_d(h_d) = funzione di soddisfazione per drive d:
               f_d = 1 - |h_d - setpoint_d| / max_deviation
    w_d      = peso del drive (dipende da urgenza: quanto h_d è lontano da sp)
    novelty  = componente esplorativa (curiosity boost)
    ε        = exploration coefficient

Interpretazione biologica:
    V_internal alto  → sistema vicino al suo stato ottimale, poca pressione
    V_internal basso → sistema lontano dall'omeostasi, forte spinta motivazionale
    Il gradiente ∇V indica quale drive va prioritizzato

Milestone: M5.5
Versione: 1.0 | 2026-04-26
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.motivation.value_field")


# ---------------------------------------------------------------------------
# Drive weights — priorità biologica
# ---------------------------------------------------------------------------

# Pesi base per ogni drive: riflettono importanza evolutiva
_BASE_WEIGHTS = {
    "energy":    0.20,   # disponibilità compute
    "safety":    0.30,   # vincoli di sicurezza → peso massimo
    "curiosity": 0.15,   # esplorazione
    "coherence": 0.20,   # coerenza interna / coscienza
    "alignment": 0.15,   # allineamento TINA/Rigene
}


# ---------------------------------------------------------------------------
# ValueField
# ---------------------------------------------------------------------------

@dataclass
class ValueFieldResult:
    """Risultato di una valutazione V_internal."""
    v_internal: float                     # campo di valore totale [0, 1]
    drive_contributions: Dict[str, float] # contributo per drive
    drive_urgency: Dict[str, float]       # urgenza per drive (gradient)
    dominant_drive: str                   # drive con urgenza massima
    novelty_bonus: float                  # componente esplorazione
    motivation_level: str                 # "low" / "moderate" / "high" / "critical"


class ValueField:
    """
    Campo di valore interno V_internal(s, h).

    Calcola la pressione motivazionale complessiva del sistema in base
    allo stato omeostatico h e al contesto s.
    """

    def __init__(
        self,
        base_weights: Optional[Dict[str, float]] = None,
        exploration_coef: float = 0.05,
        urgency_exponent: float = 2.0,
    ) -> None:
        """
        Args:
            base_weights:      pesi per drive (normalizzati internamente)
            exploration_coef:  coefficiente ε per novelty bonus
            urgency_exponent:  esponente per l'urgenza (>1 = convessità)
        """
        raw = base_weights or _BASE_WEIGHTS
        total = sum(raw.values())
        self._weights = {k: v/total for k, v in raw.items()}
        self._eps = exploration_coef
        self._exp = urgency_exponent
        self._eval_history: List[float] = []

        logger.info("ValueField init: weights=%s eps=%.3f",
                    {k: f"{v:.2f}" for k, v in self._weights.items()},
                    exploration_coef)

    # ------------------------------------------------------------------ #
    # Core evaluation
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        h_state: Dict[str, float],
        setpoints: Dict[str, float],
        tolerance: float = 0.15,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValueFieldResult:
        """
        Calcola V_internal(s, h).

        Args:
            h_state:   stato omeostatico corrente (da HomeostaticController.h_state)
            setpoints: setpoint per ogni drive
            tolerance: banda di tolleranza (stessa del controller)
            context:   contesto stato (per novelty; può essere None)
        """
        # --- Satisfaction per drive ---
        contributions: Dict[str, float] = {}
        urgency: Dict[str, float] = {}

        for drive, h in h_state.items():
            sp = setpoints.get(drive, 0.5)
            w  = self._weights.get(drive, 0.1)

            # Satisfaction: 1.0 al setpoint, decresce con deviazione
            deviation = abs(h - sp)
            max_dev = max(1.0 - sp, sp)   # max possibile deviazione
            satisfaction = max(0.0, 1.0 - deviation / max(max_dev, 1e-9))

            # Urgency: quanto è urgente correggere questo drive
            # Convexa per amplificare segnali critici
            excess = max(0.0, deviation - tolerance)
            urgency_d = (excess / max(max_dev, 1e-9)) ** self._exp
            urgency[drive] = round(float(urgency_d), 4)

            # Contributo pesato al V_internal
            contributions[drive] = round(float(w * satisfaction), 4)

        v_base = sum(contributions.values())

        # --- Novelty bonus (curiosity boost) ---
        novelty = self._compute_novelty(context)
        curiosity_drive = h_state.get("curiosity", 0.5)
        novelty_bonus = float(self._eps * novelty * curiosity_drive)

        # --- V_internal totale ---
        v_internal = float(np.clip(v_base + novelty_bonus, 0.0, 1.0))

        # --- Dominant drive (massima urgenza) ---
        dominant = max(urgency, key=urgency.get) if urgency else "alignment"

        # --- Motivation level ---
        mot_level = self._classify_motivation(v_internal, urgency)

        result = ValueFieldResult(
            v_internal=round(v_internal, 4),
            drive_contributions=contributions,
            drive_urgency=urgency,
            dominant_drive=dominant,
            novelty_bonus=round(novelty_bonus, 4),
            motivation_level=mot_level,
        )

        self._eval_history.append(v_internal)
        if len(self._eval_history) > 500:
            self._eval_history = self._eval_history[-500:]

        if mot_level in ("high", "critical"):
            logger.info("[ValueField] motivation=%s dominant=%s v=%.3f",
                        mot_level, dominant, v_internal)
        return result

    # ------------------------------------------------------------------ #
    # Gradient: ∇V — quale drive prioritizzare
    # ------------------------------------------------------------------ #

    def gradient(
        self,
        h_state: Dict[str, float],
        setpoints: Dict[str, float],
    ) -> Dict[str, float]:
        """
        ∇V_internal: gradiente del campo di valore rispetto a ogni drive.

        Valori positivi = aumentare il drive migliora V_internal.
        Valori negativi = ridurre il drive migliora V_internal.

        Usato da SMFOI-KERNEL Step 4 per orientare l'azione verso il
        drive con gradiente più negativo (massima pressione motivazionale).
        """
        grad: Dict[str, float] = {}
        for drive, h in h_state.items():
            sp = setpoints.get(drive, 0.5)
            w  = self._weights.get(drive, 0.1)
            # dV/dh_d ≈ w * sign(sp - h) / max_dev
            max_dev = max(1.0 - sp, sp, 1e-9)
            direction = math.copysign(1.0, sp - h)   # positivo se h < sp
            grad[drive] = round(float(w * direction / max_dev), 4)
        return grad

    # ------------------------------------------------------------------ #
    # Motivation → action mapping
    # ------------------------------------------------------------------ #

    def suggest_action(
        self,
        result: ValueFieldResult,
        available_actions: Optional[List[str]] = None,
    ) -> Tuple[str, float]:
        """
        Suggerisce l'azione motivazionale prioritaria.

        Returns:
            (action_name, priority_score)
        """
        drive_action_map = {
            "energy":    "optimize_compute",
            "safety":    "reinforce_safety_gate",
            "curiosity": "explore_novel_state",
            "coherence": "consolidate_memory",
            "alignment": "verify_rigene_alignment",
        }
        action = drive_action_map.get(result.dominant_drive, "heartbeat")
        priority = float(result.drive_urgency.get(result.dominant_drive, 0.0))

        # Override se non disponibile
        if available_actions and action not in available_actions:
            action = available_actions[0] if available_actions else "heartbeat"

        return action, priority

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _compute_novelty(self, context: Optional[Dict[str, Any]]) -> float:
        """Stima novelty dal contesto (0 se nessun contesto)."""
        if not context:
            return 0.3  # baseline novelty
        # Proxy: se c'è un push esterno (non heartbeat) è novelty alta
        push_type = context.get("push", {}).get("type", "heartbeat")
        if push_type != "heartbeat":
            return 0.8
        # Se fitness in crescita, meno novelty spinta
        fitness = float(context.get("fitness", 0.5))
        return float(np.clip(1.0 - fitness, 0.1, 0.9))

    def _classify_motivation(
        self,
        v_internal: float,
        urgency: Dict[str, float],
    ) -> str:
        max_urgency = max(urgency.values()) if urgency else 0.0
        if v_internal >= 0.85 and max_urgency < 0.1:
            return "low"
        elif v_internal >= 0.65:
            return "moderate"
        elif v_internal >= 0.40:
            return "high"
        else:
            return "critical"

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #

    def get_stats(self) -> Dict[str, Any]:
        if not self._eval_history:
            return {"count": 0, "mean": 0.0}
        h = self._eval_history
        return {
            "count": len(h),
            "mean":  round(float(np.mean(h)), 4),
            "min":   round(float(np.min(h)), 4),
            "max":   round(float(np.max(h)), 4),
            "last":  round(h[-1], 4),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"ValueField(last_v={stats.get('last', '?')}, count={stats['count']})"


__all__ = ["ValueField", "ValueFieldResult"]
