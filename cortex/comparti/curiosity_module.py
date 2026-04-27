"""
SPEACE Cortex – Curiosity Module
Comparto 8: Exploration & Novel Mutation Generation

Funzioni:
- Generazione mutazioni epigenetiche creative
- Esplorazione di nuovi pattern evolutivi
- Proposte sperimentali a SafeProactive

M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
  Curiosity è Level 5 (Evolution) — attivato condizionalmente su high uncertainty.
"""

import sys
import random
import datetime
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class CuriosityModule(BaseCompartment):
    """Esplorazione e generazione di nuove mutazioni."""

    name = "curiosity_module"
    level = 5  # Evoluzione

    EXPLORABLE_PARAMETERS = [
        ("learning.learning_rate", 0.01, 0.3, 0.01),
        ("learning.exploration_rate", 0.05, 0.5, 0.05),
        ("learning.yield_priority", 1, 10, 1),
        ("evolution.heartbeat_interval_min", 30, 120, 10),
        ("world_model.update_interval_min", 15, 60, 5),
    ]

    def generate_mutation_proposal(self, epigenome: Dict, fitness_current: float) -> Dict:
        """
        Genera una proposta di mutazione epigenetica.
        Seleziona un parametro casuale e propone una variazione.
        """
        # Seleziona parametro da mutare
        param_name, min_val, max_val, step = random.choice(self.EXPLORABLE_PARAMETERS)

        # Recupera valore corrente
        keys = param_name.split(".")
        current = epigenome
        for k in keys:
            current = current.get(k, {})
        if not isinstance(current, (int, float)):
            current = min_val

        # Genera nuovo valore (piccola variazione ±20%)
        delta = (max_val - min_val) * 0.1 * random.choice([-1, 1])
        new_val = max(min_val, min(max_val, round(current + delta, 3)))

        return {
            "type": "epigenetic_mutation",
            "parameter": param_name,
            "current_value": current,
            "proposed_value": new_val,
            "delta": round(new_val - current, 3),
            "rationale": f"Esplorazione: variazione {'+' if delta > 0 else ''}{delta:.3f} per migliorare adattabilità",
            "generated_at": datetime.datetime.now().isoformat(),
            "fitness_at_generation": fitness_current,
        }

    def explore_novel_patterns(self, world_model_summary: Dict) -> List[str]:
        """
        Genera idee esplorative basate sullo stato del World Model.
        """
        ideas = []

        if world_model_summary.get("rigene_objectives_count", 0) > 0:
            ideas.append("Analizzare correlazione tra obiettivi Rigene e metriche fitness SPEACE")

        if world_model_summary.get("knowledge_nodes", 0) < 10:
            ideas.append("Espandere Knowledge Graph con dati climatici e SDG progress")

        ideas.append("Simulare scenario: cosa succede se aumentiamo exploration_rate del 20%?")
        ideas.append("Proporre integrazione dati NOAA per aggiornare stato clima nel World Model")

        return ideas

    # ------------------------------------------------------------------
    # ACTIVATION GATE (attivazione condizionale)
    # ------------------------------------------------------------------

    def activation_gate(self, state: Dict) -> bool:
        """
        Curiosity si attiva quando:
         - uncertainty >= 0.7, OR
         - novelty >= 0.6, OR
         - lo state la richiede esplicitamente (decision.request == 'explore')
        """
        unc = float(state.get("uncertainty", 0.0) or 0.0)
        nov = float(state.get("novelty", 0.0) or 0.0)
        req = (state.get("decision", {}) or {}).get("request")
        return unc >= 0.7 or nov >= 0.6 or req == "explore"

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Genera una mutation_proposal leggera basata sullo state.
        Non muta direttamente l'epigenome: propone soltanto (a SafeProactive).
        """
        if state_bus.is_blocked(state):
            return self._log(state, status="skipped", note="state_blocked")

        # In assenza di epigenome completo nello state, genera una proposta
        # template agganciata a parametri esplorabili.
        param_name, min_val, max_val, step = random.choice(self.EXPLORABLE_PARAMETERS)
        current = (min_val + max_val) / 2
        delta = (max_val - min_val) * 0.1 * random.choice([-1, 1])
        new_val = max(min_val, min(max_val, round(current + delta, 3)))

        proposal = {
            "type": "epigenetic_mutation_hint",
            "parameter": param_name,
            "current_value_estimate": current,
            "proposed_value": new_val,
            "rationale": (
                f"Trigger esplorativo: uncertainty={state.get('uncertainty', 0.0):.2f}, "
                f"novelty={state.get('novelty', 0.0):.2f}"
            ),
            "generated_at": datetime.datetime.now().isoformat(),
            "requires_safeproactive_approval": True,
        }

        state["mutation_proposal"] = proposal
        return self._log(state, status="ok", note=f"mut_hint:{param_name}")
