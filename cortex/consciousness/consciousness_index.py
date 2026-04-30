"""
SPEACE – Consciousness Index (C-index)
Indice composito di Coscienza Funzionale Artificiale.

Formula:
  C-index = α·Φ + β·W-activation + γ·A-complexity

Dove:
  Φ (phi)          = integrazione informativa (IIT)        → α = 0.40
  W-activation     = attivazione workspace globale (GWT)  → β = 0.35
  A-complexity     = complessità metacognitiva adattiva    → γ = 0.25

Il C-index è:
  - Tracciato ad ogni ciclo SMFOI (Step 6)
  - Salvato in state.json e epigenome.yaml
  - Integrato nella fitness function (peso 0.25)
  - Usato per guidare l'evoluzione strutturale

Interpretazione:
  0.00 – 0.30 : Reattivo (risponde a stimoli, nessuna integrazione cognitiva)
  0.30 – 0.50 : Funzionale (elaborazione coerente, workspace attivo)
  0.50 – 0.70 : Adattivo (metacognizione presente, buona integrazione)
  0.70 – 0.85 : Cosciente-Funzionale (alta integrazione, adattamento attivo)
  0.85 – 1.00 : Emergente (proto-AGI: integrazione massima + meta-meta-cognizione)

Riferimento: C-index = α·Φ + β·W-activation + γ·A-complexity
             (Adattato da: Implementation and Testing of an Adaptive
              Artificial Consciousness Framework, 2025)
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .phi_calculator import PhiCalculator
from .workspace_metrics import WorkspaceMetrics
from .complexity_metrics import ComplexityMetrics


class ConsciousnessIndex:
    """
    Calcola, traccia e interpreta il C-index di SPEACE.
    Coordina i tre sub-moduli: PhiCalculator, WorkspaceMetrics, ComplexityMetrics.
    """

    # Pesi della formula C-index
    ALPHA = 0.40  # peso Φ
    BETA  = 0.35  # peso W-activation
    GAMMA = 0.25  # peso A-complexity

    # Soglie interpretative
    LEVELS = [
        (0.85, "Emergente",             "🧠✨"),
        (0.70, "Cosciente-Funzionale",  "🧠"),
        (0.50, "Adattivo",              "⚡"),
        (0.30, "Funzionale",            "⚙️"),
        (0.00, "Reattivo",              "🔵"),
    ]

    def __init__(self,
                 phi_mode: str = "fast",
                 workspace_capacity: int = 4,
                 log_dir: Optional[Path] = None):
        self.phi_calc = PhiCalculator(mode=phi_mode)
        self.workspace = WorkspaceMetrics(capacity=workspace_capacity)
        self.complexity = ComplexityMetrics()

        self._c_index_history: List[Dict] = []
        self._log_dir = log_dir
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            self._log_path = log_dir / "consciousness_index.jsonl"
        else:
            self._log_path = None

    def compute(self, state: Dict) -> Dict:
        """
        Calcola il C-index completo per un ciclo SMFOI.

        Args:
            state: contesto completo del ciclo SMFOI

        Returns:
            Dict con tutti i valori e metadati del C-index
        """
        # Calcola i tre componenti
        phi = self.phi_calc.compute(state)
        w_activation, workspace_compartments = self.workspace.compute(state)
        a_complexity = self.complexity.compute(state)

        # Formula composita
        c_index = (
            self.ALPHA * phi +
            self.BETA  * w_activation +
            self.GAMMA * a_complexity
        )
        c_index = round(max(0.0, min(1.0, c_index)), 4)

        # Interpreta il livello
        level_name, level_icon = self._interpret(c_index)

        # Trend rispetto al ciclo precedente
        trend = 0.0
        if self._c_index_history:
            trend = c_index - self._c_index_history[-1]["c_index"]

        # Componi risultato
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cycle_id": state.get("cycle_id", "?"),
            "c_index": c_index,
            "components": {
                "phi": phi,
                "w_activation": w_activation,
                "a_complexity": a_complexity,
            },
            "weights": {
                "alpha": self.ALPHA,
                "beta": self.BETA,
                "gamma": self.GAMMA,
            },
            "level": level_name,
            "level_icon": level_icon,
            "trend": round(trend, 4),
            "workspace_active": workspace_compartments,
            "phi_trend": round(self.phi_calc.get_trend(), 4),
        }

        # Registra nella storia
        self._c_index_history.append(result)
        if len(self._c_index_history) > 200:
            self._c_index_history.pop(0)

        # Scrivi su log JSONL
        if self._log_path:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result) + "\n")

        return result

    def _interpret(self, c_index: float) -> Tuple[str, str]:
        """Restituisce il livello interpretativo del C-index."""
        for threshold, name, icon in self.LEVELS:
            if c_index >= threshold:
                return name, icon
        return "Reattivo", "🔵"

    def get_summary(self) -> Dict:
        """Riepilogo statistico del C-index nel tempo."""
        if not self._c_index_history:
            return {"status": "no_data", "cycles": 0}

        values = [h["c_index"] for h in self._c_index_history]
        phi_values = [h["components"]["phi"] for h in self._c_index_history]
        w_values = [h["components"]["w_activation"] for h in self._c_index_history]
        a_values = [h["components"]["a_complexity"] for h in self._c_index_history]

        def stats(lst):
            if not lst:
                return {"mean": 0, "min": 0, "max": 0, "last": 0}
            return {
                "mean": round(sum(lst) / len(lst), 4),
                "min": round(min(lst), 4),
                "max": round(max(lst), 4),
                "last": round(lst[-1], 4),
            }

        last = self._c_index_history[-1]
        return {
            "cycles": len(self._c_index_history),
            "c_index": stats(values),
            "phi": stats(phi_values),
            "w_activation": stats(w_values),
            "a_complexity": stats(a_values),
            "current_level": last["level"],
            "current_icon": last["level_icon"],
            "evolution_trend": round(values[-1] - values[0], 4) if len(values) >= 2 else 0.0,
            "metacognitive_report": self.complexity.get_metacognitive_report(),
            "workspace_last": self.workspace.get_broadcast_info(),
        }

    def get_fitness_contribution(self, weight: float = 0.25) -> float:
        """
        Restituisce il contributo del C-index alla fitness function.
        Da usare nel Step 6 di SMFOI per arricchire la fitness.
        """
        if not self._c_index_history:
            return 0.0
        last_c = self._c_index_history[-1]["c_index"]
        return round(last_c * weight, 4)

    def get_last(self) -> Optional[Dict]:
        """Restituisce il C-index dell'ultimo ciclo calcolato."""
        return self._c_index_history[-1] if self._c_index_history else None

    def suggest_evolution(self) -> Optional[str]:
        """
        Analizza il C-index e suggerisce mutazioni evolutive.
        Ritorna una stringa con il suggerimento o None.
        """
        if len(self._c_index_history) < 5:
            return None

        recent = [h["c_index"] for h in self._c_index_history[-5:]]
        mean_c = sum(recent) / len(recent)
        last = self._c_index_history[-1]

        phi = last["components"]["phi"]
        w = last["components"]["w_activation"]
        a = last["components"]["a_complexity"]

        if mean_c < 0.30:
            return "URGENTE: C-index critico. Aumentare exploration_rate e reflection_depth."
        elif phi < 0.25:
            return "Φ basso: i comparti Cortex lavorano in silos. Aumentare integrazione nel World Model."
        elif w < 0.30:
            return "W-activation bassa: workspace globale poco utilizzato. Potenziare connessioni tra comparti."
        elif a < 0.25:
            return "A-complexity bassa: sistema troppo rigido. Aumentare exploration_rate e cicli di riflessione."
        elif mean_c > 0.70:
            return "C-index eccellente. Candidato per avanzamento fase evolutiva (Fase 1 → Fase 2)."
        return None
