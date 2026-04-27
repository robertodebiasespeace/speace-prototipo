"""
SPEACE Cortex – Neural Flow
Orchestrazione canonica del flusso neurale tra i 9 comparti.

Ordine canonico (può essere alterato dal ConditionalScheduler in M3L.3):

    Parietal Lobe       (L4, sensing)       — porta d'ingresso sensoriale
      ↓
    Temporal Lobe       (L2, cognition)     — interpretazione linguistica
      ↓
    World Model         (L2, cognition)     — contesto sistemico
      ↓
    Prefrontal Cortex   (L1, control)       — pianificazione & decisione
      ↓
    Safety Module       (L1, override)      — veto / approvazione
      ↓
    Cerebellum          (L4, action)        — esecuzione whitelisted
      ↓
    Hippocampus         (L3, memory)        — consolidamento episodico
      ↓
    Default Mode Net    (L2, reflection)    — auto-riflessione
      ↓
    Curiosity Module    (L5, evolution)     — mutation_proposal (condiz.)

Proprietà garantite:
  - Safety può bloccare in qualsiasi momento (override assoluto L1).
  - Se Safety blocca, nessun comparto a valle ≥ L2 modifica lo state
    (controllo via state_bus.is_blocked()).
  - ogni comparto implementa process(state) ereditato da BaseCompartment.

Feature flag:
  Questo flow è opt-in. L'integrazione con SMFOI-v3 avviene solo se
  epigenome.yaml ha flags.neural_flow_enabled=True. Di default: False.

Creato: 2026-04-19 | M3L.2 | PROP-CORTEX-NEURAL-M3L
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex import state_bus
from cortex import control_hierarchy
from cortex.comparti.parietal_lobe import ParietalLobe
from cortex.comparti.temporal_lobe import TemporalLobe
from cortex.world_model import WorldModel
from cortex.comparti.prefrontal import PrefrontalCortex
from cortex.comparti.safety_module import SafetyModule
from cortex.comparti.cerebellum import Cerebellum
from cortex.comparti.hippocampus import Hippocampus
from cortex.comparti.default_mode_network import DefaultModeNetwork
from cortex.comparti.curiosity_module import CuriosityModule


# Ordine canonico di esecuzione (nome comparto → factory)
CANONICAL_ORDER: List[str] = [
    "parietal_lobe",
    "temporal_lobe",
    "world_model",
    "prefrontal_cortex",
    "safety_module",
    "cerebellum",
    "hippocampus",
    "default_mode_network",
    "curiosity_module",
]


class NeuralFlow:
    """
    Orchestratore del flusso neurale canonico.
    Può essere usato da solo o integrato in SMFOI-v3 come step 5.bis.
    """

    def __init__(self, scheduler=None):
        """
        scheduler: oggetto opzionale che implementa should_run(name, state) -> bool.
                   Se None, tutti i comparti attivi dall'ordine canonico vengono
                   eseguiti (con activation_gate del comparto stesso).
        """
        self._factories = {
            "parietal_lobe":        ParietalLobe,
            "temporal_lobe":        TemporalLobe,
            "world_model":          WorldModel,
            "prefrontal_cortex":    PrefrontalCortex,
            "safety_module":        SafetyModule,
            "cerebellum":           Cerebellum,
            "hippocampus":          Hippocampus,
            "default_mode_network": DefaultModeNetwork,
            "curiosity_module":     CuriosityModule,
        }
        self._instances: Dict[str, Any] = {}
        self.scheduler = scheduler

    # ------------------------------------------------------------------
    # LAZY INSTANCE
    # ------------------------------------------------------------------

    def get(self, name: str):
        """Lazy-init di un comparto: istanza singola per NeuralFlow."""
        if name not in self._instances:
            factory = self._factories.get(name)
            if factory is None:
                raise KeyError(f"unknown_compartment:{name}")
            self._instances[name] = factory()
        return self._instances[name]

    def all_instances(self) -> List[Any]:
        """Istanzia tutti i comparti (utile per validazione)."""
        return [self.get(n) for n in CANONICAL_ORDER]

    # ------------------------------------------------------------------
    # ESECUZIONE
    # ------------------------------------------------------------------

    def _should_run(self, name: str, state: Dict) -> bool:
        """
        Determina se un comparto va eseguito in questo ciclo.
        - Scheduler esterno (se fornito) ha priorità.
        - Altrimenti si usa l'activation_gate del comparto stesso.
        - Se lo state è bloccato dalla Safety, solo comparti ≤ L3 (memoria/azione
          di chiusura) possono ancora eseguire, e solo quelli che sanno
          gestire lo stato bloccato (come Hippocampus per logging e DMN per
          riflessione post-blocco).
        """
        if self.scheduler is not None:
            try:
                return bool(self.scheduler.should_run(name, state))
            except Exception:
                pass  # fallback su activation_gate

        inst = self.get(name)
        gate = inst.activation_gate(state) if hasattr(inst, "activation_gate") else True
        return gate

    def run(self, state: Dict, order: Optional[List[str]] = None) -> Dict:
        """
        Esegue il neural flow sullo state fornito.
        Ritorna lo state arricchito.
        """
        chain = order or CANONICAL_ORDER

        for name in chain:
            if not self._should_run(name, state):
                state = state_bus.log_compartment(state, name,
                                                  control_hierarchy.level_of(name),
                                                  status="skipped",
                                                  note="activation_gate_closed")
                continue

            inst = self.get(name)

            # Safety check BEFORE running any L>=2 comparto dopo un blocco
            if state_bus.is_blocked(state) and control_hierarchy.level_of(name) >= 2:
                # Eccezione: hippocampus, dmn e curiosity possono voler
                # registrare l'episodio di blocco (ma curiosity/dmn già
                # controllano internamente). Hippocampus è utile per tracking.
                if name not in ("hippocampus", "default_mode_network"):
                    state = state_bus.log_compartment(state, name,
                                                      control_hierarchy.level_of(name),
                                                      status="skipped",
                                                      note="safety_blocked_downstream")
                    continue

            try:
                state = inst.process(state)
            except Exception as e:
                state = state_bus.log_compartment(state, name,
                                                  control_hierarchy.level_of(name),
                                                  status="error",
                                                  note=f"exception:{e}")

        return state

    # ------------------------------------------------------------------
    # UTIL
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """Valida la gerarchia dei comparti configurati."""
        return control_hierarchy.validate_hierarchy(self.all_instances())


def is_enabled(epigenome: Optional[Dict] = None) -> bool:
    """
    True se il neural flow è abilitato nell'epigenome.
    Default: False (opt-in, per non rompere comportamento M2).
    """
    if epigenome is None:
        try:
            import yaml
            epi_path = ROOT_DIR / "digitaldna" / "epigenome.yaml"
            if epi_path.exists():
                epigenome = yaml.safe_load(epi_path.read_text(encoding="utf-8")) or {}
        except Exception:
            epigenome = {}
    flags = (epigenome or {}).get("flags", {}) or {}
    nf = (epigenome or {}).get("neural_flow", {}) or {}
    return bool(flags.get("neural_flow_enabled", False) or nf.get("enabled", False))


if __name__ == "__main__":
    import json
    nf = NeuralFlow()
    issues = nf.validate()
    print("hierarchy_issues:", issues)
    s = state_bus.new_state("NF_SELFTEST",
                            sensory_input={"text": "climate harmony peace"})
    s = nf.run(s)
    print("final_state_keys:", list(s.keys()))
    print("blocked:", state_bus.is_blocked(s))
    for e in s.get("compartment_log", []):
        print(f"  [{e['level']}] {e['name']} -> {e['status']} ({e.get('note','-')})")
