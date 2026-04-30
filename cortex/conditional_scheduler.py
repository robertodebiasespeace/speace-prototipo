"""
SPEACE Cortex – Conditional Scheduler
Decide dinamicamente quali comparti attivare in un dato ciclo.

Il Cortex NON deve invocare tutti i 9 comparti sempre: sarebbe costoso
e cognitivamente povero. Lo scheduler legge lo state del ciclo e i
segnali sintetici (uncertainty, risk, novelty, sensory_drift) e decide
quali comparti attivare.

Policy canonica (soglie leggibili da epigenome.yaml):
  uncertainty >= 0.7  → Curiosity attivato (Level 5)
  risk        >= 0.5  → Safety prioritizzato (pass aggiuntivo L1)
  novelty     >= 0.6  → Default Mode Network extra pass (Level 2)
  sensory_drift >= 0.4 → WorldModel refresh forzato

Comparti "always on" nel flusso canonico:
  Parietal, Temporal, Prefrontal, Safety, Cerebellum, Hippocampus

Comparti opzionali (gate-driven):
  World Model (se drift >= soglia, oppure almeno ogni N cicli)
  Default Mode Network (se novelty >= soglia, oppure reflect_every_n cicli)
  Curiosity (se uncertainty >= soglia, oppure explore_every_n cicli)

API:
  scheduler.should_run(compartment_name, state) -> bool

Lo scheduler viene passato a NeuralFlow(scheduler=...) e sostituisce
la logica di default (activation_gate del comparto).

Creato: 2026-04-19 | M3L.3 | PROP-CORTEX-NEURAL-M3L
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# Soglie di default (sovrascrivibili da epigenome.yaml -> neural_flow.thresholds)
DEFAULT_THRESHOLDS = {
    "uncertainty_triggers_curiosity": 0.7,
    "risk_prioritizes_safety":         0.5,
    "novelty_triggers_dmn":            0.6,
    "drift_refreshes_world_model":     0.4,
    # Periodici (ogni N cicli): 0 disabilita, > 0 attiva
    "world_model_every_n_cycles":      3,
    "dmn_every_n_cycles":              5,
    "curiosity_every_n_cycles":        10,
}

# Comparti sempre attivi (core loop)
ALWAYS_ON = {
    "parietal_lobe",
    "temporal_lobe",
    "prefrontal_cortex",
    "safety_module",
    "cerebellum",
    "hippocampus",
}

# Comparti condizionali e chiavi soglia associate
CONDITIONAL = {
    "world_model":           ("sensory_drift", "drift_refreshes_world_model",  "world_model_every_n_cycles"),
    "default_mode_network":  ("novelty",        "novelty_triggers_dmn",         "dmn_every_n_cycles"),
    "curiosity_module":      ("uncertainty",    "uncertainty_triggers_curiosity","curiosity_every_n_cycles"),
}


class ConditionalScheduler:
    """
    Scheduler condizionale del neural flow.
    Stateless rispetto ai comparti; tiene un contatore di cicli interno
    per la logica "every N cycles".
    """

    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update({k: v for k, v in thresholds.items() if v is not None})
        self._cycle_counter = 0
        self._last_run_cycle: Dict[str, int] = {}

    @classmethod
    def from_epigenome(cls, epigenome: Optional[Dict] = None) -> "ConditionalScheduler":
        """Istanzia lo scheduler leggendo le soglie da epigenome.yaml."""
        if epigenome is None:
            try:
                import yaml
                epi_path = ROOT_DIR / "digitaldna" / "epigenome.yaml"
                if epi_path.exists():
                    epigenome = yaml.safe_load(epi_path.read_text(encoding="utf-8")) or {}
            except Exception:
                epigenome = {}
        nf_block = (epigenome or {}).get("neural_flow", {}) or {}
        return cls(thresholds=nf_block.get("thresholds"))

    # ------------------------------------------------------------------
    # API PRINCIPALE
    # ------------------------------------------------------------------

    def begin_cycle(self) -> int:
        """Incrementa il contatore ciclo. Ritorna il nuovo valore."""
        self._cycle_counter += 1
        return self._cycle_counter

    def should_run(self, compartment_name: str, state: Dict) -> bool:
        """
        Decide se un comparto va eseguito.
        Criteri in ordine di priorità:
          1. ALWAYS_ON → sempre True.
          2. Comparto condizionale:
             - se il segnale associato supera la soglia → True;
             - se sono trascorsi N cicli dall'ultima esecuzione → True;
             - altrimenti False.
          3. Comparto non noto → ricade su True (fail-open nel flusso canonico,
             ma NeuralFlow comunque rispetta activation_gate del comparto).
        """
        if compartment_name in ALWAYS_ON:
            self._last_run_cycle[compartment_name] = self._cycle_counter
            return True

        if compartment_name in CONDITIONAL:
            signal_key, threshold_key, every_n_key = CONDITIONAL[compartment_name]
            signal = float(state.get(signal_key, 0.0) or 0.0)
            threshold = float(self.thresholds.get(threshold_key, 1.0))
            every_n = int(self.thresholds.get(every_n_key, 0) or 0)

            # Soglia superata → attiva
            if signal >= threshold:
                self._last_run_cycle[compartment_name] = self._cycle_counter
                return True

            # Logica periodica
            if every_n > 0:
                last = self._last_run_cycle.get(compartment_name, 0)
                if self._cycle_counter - last >= every_n:
                    self._last_run_cycle[compartment_name] = self._cycle_counter
                    return True

            return False

        # Default fail-open
        return True

    # ------------------------------------------------------------------
    # DIAGNOSTICA
    # ------------------------------------------------------------------

    def summary(self) -> Dict:
        return {
            "cycle_counter": self._cycle_counter,
            "thresholds": dict(self.thresholds),
            "last_run_cycle": dict(self._last_run_cycle),
            "always_on": sorted(ALWAYS_ON),
            "conditional": {k: {"signal": v[0], "threshold_key": v[1],
                                "every_n_key": v[2]} for k, v in CONDITIONAL.items()},
        }


if __name__ == "__main__":
    import json
    from cortex import state_bus, neural_flow

    sch = ConditionalScheduler.from_epigenome()
    nf = neural_flow.NeuralFlow(scheduler=sch)

    # Ciclo 1: input banale, uncertainty e novelty bassi → Curiosity/DMN skip
    sch.begin_cycle()
    s1 = state_bus.new_state("SCHED_T1", sensory_input={"text": "hello planet"})
    s1 = nf.run(s1)
    print("--- Cycle 1 ---")
    for e in s1["compartment_log"]:
        print(f"  [{e['level']}] {e['name']} -> {e['status']} ({e.get('note','-')})")

    # Ciclo 2: alta uncertainty manuale → Curiosity attivato
    sch.begin_cycle()
    s2 = state_bus.new_state("SCHED_T2", sensory_input={"text": "x"})
    s2["uncertainty"] = 0.85
    s2 = nf.run(s2)
    print("\n--- Cycle 2 (high uncertainty) ---")
    for e in s2["compartment_log"]:
        print(f"  [{e['level']}] {e['name']} -> {e['status']} ({e.get('note','-')})")

    print("\nScheduler summary:", json.dumps(sch.summary(), indent=2, ensure_ascii=False))
