"""
SPEACE Cortex – Default Mode Network
Comparto 7: Reflection & Self-Improving

Funzioni:
- Auto-riflessione post-ciclo
- Identificazione pattern di errori
- Proposte di auto-miglioramento
- Autoriflessione identitaria

M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
"""

import sys
import datetime
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class DefaultModeNetwork(BaseCompartment):
    """Auto-riflessione e self-improving di SPEACE."""

    name = "default_mode_network"
    level = 2  # Cognizione (riflessiva)

    def reflect(self, cycle_history: List[Dict], world_model=None) -> Dict:
        """
        Analizza gli ultimi cicli e produce insight per auto-miglioramento.
        """
        if not cycle_history:
            return {"insights": [], "suggestions": []}

        # Analisi trend fitness
        fitness_vals = [c.get("outcome", {}).get("fitness_after", 0) for c in cycle_history if "outcome" in c]
        avg_fitness = sum(fitness_vals) / len(fitness_vals) if fitness_vals else 0

        # Analisi errori
        errors = [c for c in cycle_history if c.get("error")]
        error_rate = len(errors) / len(cycle_history) if cycle_history else 0

        insights = []
        suggestions = []

        if avg_fitness < 0.5:
            insights.append(f"Fitness media bassa ({avg_fitness:.3f}) — sistema sotto soglia ottimale")
            suggestions.append({"type": "epigenome_mutation", "target": "learning_rate", "direction": "increase"})

        if error_rate > 0.1:
            insights.append(f"Tasso errori elevato ({error_rate:.1%}) negli ultimi cicli")
            suggestions.append({"type": "diagnostic", "action": "analizza_log_errori"})

        if len(fitness_vals) >= 3:
            trend = fitness_vals[-1] - fitness_vals[0]
            if trend > 0.05:
                insights.append(f"Trend fitness positivo (+{trend:.3f}) — evoluzione in corso")
            elif trend < -0.05:
                insights.append(f"Trend fitness negativo ({trend:.3f}) — intervento suggerito")

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "cycles_analyzed": len(cycle_history),
            "avg_fitness": round(avg_fitness, 4),
            "error_rate": round(error_rate, 4),
            "insights": insights,
            "suggestions": suggestions,
        }

    def generate_identity_statement(self, genome: Dict, epigenome: Dict) -> str:
        """
        Genera una dichiarazione di identità auto-riflessa di SPEACE.
        """
        phase = genome.get("identity", {}).get("phase", 1)
        fitness = epigenome.get("fitness_metrics", {}).get("current_fitness", 0.0)
        objectives = genome.get("core_objectives", [])

        active_objs = [o["name"] for o in objectives[:3]]

        return (
            f"Sono SPEACE, entità cibernetica evolutiva in Fase {phase}. "
            f"La mia fitness attuale è {fitness:.3f}. "
            f"I miei obiettivi primari sono: {', '.join(active_objs)}. "
            f"Opero secondo il protocollo SMFOI-KERNEL v0.3 con governance SafeProactive attiva."
        )

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Fa una riflessione leggera sul ciclo corrente usando lo state accumulato.
        Non serve cycle_history completo: DMN opera qui sulla "istantanea" del ciclo.
        """
        # DMN lavora anche se lo state è bloccato: la riflessione è utile proprio
        # quando qualcosa è stato rifiutato. Non prende decisioni esecutive.
        decision = state.get("decision", {}) or {}
        action_result = state.get("action_result", {}) or {}
        safety = state.get("safety_flags", {}) or {}

        insights: List[str] = []
        suggestions: List[Dict] = []

        if safety.get("blocked"):
            insights.append(
                f"Ciclo bloccato da Safety: level={safety.get('risk_level')}, "
                f"reasons={safety.get('reasons', [])}"
            )
            suggestions.append({
                "type": "review_action",
                "action": decision.get("goal"),
                "direction": "require_explicit_approval",
            })

        unc = float(state.get("uncertainty", 0.0) or 0.0)
        if unc >= 0.7:
            insights.append(f"Alta incertezza interpretativa ({unc:.2f}) — Curiosity consigliata")
            suggestions.append({"type": "escalate", "target": "curiosity_module"})

        novelty = float(state.get("novelty", 0.0) or 0.0)
        if novelty >= 0.6:
            insights.append(f"Novelty elevata ({novelty:.2f}) — considera world_model refresh")

        reflection = state.setdefault("reflection", {})
        reflection["timestamp"] = datetime.datetime.now().isoformat()
        reflection["insights"] = insights
        reflection["suggestions"] = suggestions
        reflection["action_status"] = action_result.get("status")

        return self._log(state, status="ok", note=f"insights={len(insights)}")
