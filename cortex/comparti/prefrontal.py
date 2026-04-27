"""
SPEACE Cortex – Prefrontal Cortex
Comparto 1: Planning & Decision Making

Funzioni:
- Pianificazione task multi-step
- Prioritizzazione obiettivi
- Decision making basato su fitness e constraints

M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
Backward compatible: i metodi plan/decide esistenti restano invariati.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class PrefrontalCortex(BaseCompartment):
    """Planning e decision making di SPEACE."""

    name = "prefrontal_cortex"
    level = 1  # Controllo

    def plan(self, goal: str, context: Dict, world_model=None) -> Dict:
        """
        Genera un piano multi-step per raggiungere un obiettivo.
        """
        plan = {
            "goal": goal,
            "steps": [],
            "priority": self._assess_priority(goal, context),
            "estimated_cycles": 1,
        }

        if "brief" in goal.lower() or "report" in goal.lower():
            plan["steps"] = [
                {"step": 1, "action": "gather_data", "agent": "parietal_lobe"},
                {"step": 2, "action": "analyze", "agent": "temporal_lobe"},
                {"step": 3, "action": "synthesize", "agent": "scientific_team"},
                {"step": 4, "action": "output", "agent": "communication"},
            ]
            plan["estimated_cycles"] = 4

        elif "mutate" in goal.lower() or "evolve" in goal.lower():
            plan["steps"] = [
                {"step": 1, "action": "snapshot", "agent": "safeproactive"},
                {"step": 2, "action": "propose_mutation", "agent": "curiosity_module"},
                {"step": 3, "action": "evaluate_fitness", "agent": "smfoi_kernel"},
                {"step": 4, "action": "approve_or_reject", "agent": "safeproactive"},
            ]
            plan["estimated_cycles"] = 4

        else:
            plan["steps"] = [{"step": 1, "action": goal, "agent": "cortex"}]

        return plan

    def _assess_priority(self, goal: str, context: Dict) -> int:
        """Priorità da 1 (alta) a 5 (bassa)."""
        if "critical" in goal.lower() or "error" in goal.lower():
            return 1
        if "evolve" in goal.lower() or "mutate" in goal.lower():
            return 3
        return 2

    def decide(self, options: List[Dict], criteria: Dict) -> Dict:
        """Seleziona la migliore opzione in base ai criteri."""
        if not options:
            return {}
        # Scoring semplice: ordina per fitness_impact decrescente
        scored = sorted(options, key=lambda x: x.get("fitness_impact", 0), reverse=True)
        return scored[0]

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Consuma interpretation (Temporal) + world_snapshot (World Model) e produce decision.
        Se il state è già bloccato da Safety (safety_flags.blocked=True), non decide nulla.
        """
        if state_bus.is_blocked(state):
            return self._log(state, status="skipped", note="state_blocked")

        interpretation = state.get("interpretation", {}) or {}
        sensory = state.get("sensory_input", {}) or {}

        # Obiettivo deducibile dall'interpretazione o dal sensory_input
        goal = (
            interpretation.get("goal")
            or sensory.get("goal")
            or "maintain_homeostasis"
        )
        context = {
            "sensory": sensory,
            "interpretation": interpretation,
            "world": state.get("world_snapshot", {}),
        }

        plan = self.plan(goal, context)
        decision = state.setdefault("decision", {})
        decision["goal"] = goal
        decision["plan"] = plan
        decision["priority"] = plan.get("priority", 2)
        # Nessuna proposed_action "rischiosa" di default: il Prefrontal in Fase 1
        # si limita a orchestrare comparti interni (non esegue azioni esterne).
        decision.setdefault("proposed_action", None)

        return self._log(state, status="ok", note=f"planned:{goal}")
