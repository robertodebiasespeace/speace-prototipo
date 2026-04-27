"""
SPEACE Morphogenesis Engine - Bio-inspired Structural Plasticity
Implements Homeodyna and Kinetica for adaptive architecture.
Version: 1.0
Data: 25 Aprile 2026

Homeodyna: Maintains adaptive structural equilibrium (biological homeostasis)
Kinetica: Governs internal reconfiguration between cognitive regimes
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent


class CognitiveRegime(Enum):
    """Regimi cognitivi - transizioni Kinetica"""
    REACTIVE_PARSING = "reactive_parsing"           # Risposta immediata
    DELIBERATIVE_REASONING = "deliberative_reasoning" # Ragionamento approfondito
    RECURSIVE_ABSTRACTION = "recursive_abstraction"   # Astrazione ricorsiva
    CREATIVE_SYNTHESIS = "creative_synthesis"       # Sintesi creativa
    META_COGNITION = "meta_cognition"               # Auto-riflessione

    # Regimi speciali
    EMERGENCY = "emergency"                         # Overload handling
    IDLE = "idle"                                  # Riposo/background


@dataclass
class RegimeTransition:
    """Record di transizione tra regimi"""
    from_regime: CognitiveRegime
    to_regime: CognitiveRegime
    trigger: str
    timestamp: str
    phi_before: float
    phi_after: float


@dataclass
class StructuralConstraint:
    """Vincolo strutturale per Homeodyna"""
    name: str
    type: str  # 'balance', 'threshold', 'ratio'
    target_value: float
    tolerance: float = 0.1
    weight: float = 1.0


@dataclass
class MorphogenicSignal:
    """Segnale morfogenetico"""
    type: str  # 'growth', 'prune', 'reconfigure', 'stabilize'
    source_neuron: str
    target_neuron: Optional[str]
    strength: float
    timestamp: str


class HomeodynaController:
    """
    L4 - Equilibrio strutturale adattivo.
    Simile all'omeostasi biologica, bilancia attivazioni contrastanti
    e rerouta percorsi quando overload.
    """

    def __init__(self, morphogenesis_engine):
        self.morpho = morphogenesis_engine
        self.constraints: List[StructuralConstraint] = []
        self.balance_history: deque = deque(maxlen=100)
        self.stress_responses: Dict[str, float] = {}
        self._init_default_constraints()

    def _init_default_constraints(self):
        """Inizializza vincoli strutturali default"""
        self.constraints = [
            StructuralConstraint("phi_stability", "threshold", 0.65, 0.15),
            StructuralConstraint("excitation_inhibition_balance", "balance", 0.5, 0.2),
            StructuralConstraint("resource_ratio", "ratio", 0.7, 0.15),
            StructuralConstraint("activation_spread", "threshold", 0.8, 0.1),
        ]

    def evaluate_balance(self, system_state: Dict) -> Tuple[float, List[str]]:
        """
        Valuta equilibrio omeostatico.
        Returns: (balance_score, list_of_violations)
        """
        phi = system_state.get("phi", 0.7)
        excitation = system_state.get("excitation_level", 0.5)
        inhibition = system_state.get("inhibition_level", 0.5)
        resource_usage = system_state.get("resource_usage", 0.6)

        violations = []
        balance_score = 1.0

        # Check phi stability
        for constraint in self.constraints:
            if constraint.type == "threshold":
                deviation = abs(phi - constraint.target_value)
                if deviation > constraint.tolerance:
                    violations.append(f"{constraint.name}: deviation {deviation:.3f}")
                    balance_score -= constraint.weight * min(1.0, deviation)

        # Check excitation/inhibition balance
        ei_balance = 1.0 - abs(excitation - inhibition)
        if ei_balance < 0.4:
            violations.append(f"excitation_inhibition_imbalance: {ei_balance:.3f}")
            balance_score *= ei_balance

        # Check resource ratio
        if resource_usage > 0.95:
            violations.append("resource_overload")
            balance_score *= 0.5
        elif resource_usage > 0.85:
            violations.append("resource_high")
            balance_score *= 0.8

        balance_score = max(0.0, min(1.0, balance_score))
        self.balance_history.append({"timestamp": datetime.now().isoformat(), "score": balance_score, "violations": violations})

        return balance_score, violations

    def generate_compensation_signals(self, violations: List[str]) -> List[MorphogenicSignal]:
        """Genera segnali di compensazione per violazioni"""
        signals = []

        for violation in violations:
            if "phi_stability" in violation:
                signals.append(MorphogenicSignal(
                    type="stabilize",
                    source_neuron="homeodyna",
                    target_neuron=None,
                    strength=0.7,
                    timestamp=datetime.now().isoformat()
                ))
            elif "excitation_inhibition" in violation:
                signals.append(MorphogenicSignal(
                    type="reconfigure",
                    source_neuron="homeodyna",
                    target_neuron=None,
                    strength=0.5,
                    timestamp=datetime.now().isoformat()
                ))
            elif "resource" in violation:
                signals.append(MorphogenicSignal(
                    type="prune",
                    source_neuron="homeodyna",
                    target_neuron=None,
                    strength=0.8,
                    timestamp=datetime.now().isoformat()
                ))

        return signals

    def reroute_path(self, current_path: List[str], overload_node: str) -> List[str]:
        """Rerouta percorsi quando overload"""
        if overload_node not in current_path:
            return current_path

        # Trova nodo alternativo
        idx = current_path.index(overload_node)
        alternative_path = current_path[:idx]

        # Aggiungi nodo bypass (se disponibile)
        if hasattr(self.morpho, 'bridge') and self.morpho.bridge:
            compartments = list(self.morpho.bridge.compartments.keys())
            available = [c for c in compartments if c not in alternative_path]
            if available:
                alternative_path.append(available[0])

        alternative_path.extend(current_path[idx+1:])
        return alternative_path


class KineticaController:
    """
    L4 - Riconfigurazione interna del sistema.
    Permette transizioni tra regimi cognitivi.
    """

    def __init__(self, morphogenesis_engine):
        self.morpho = morphogenesis_engine
        self.current_regime = CognitiveRegime.IDLE
        self.regime_history: deque = deque(maxlen=50)
        self.transition_rules: Dict[Tuple[CognitiveRegime, str], CognitiveRegime] = {}
        self._init_transition_rules()

    def _init_transition_rules(self):
        """Definisce regole di transizione tra regimi"""
        self.transition_rules = {
            (CognitiveRegime.IDLE, "task_start"): CognitiveRegime.REACTIVE_PARSING,
            (CognitiveRegime.REACTIVE_PARSING, "complex_reasoning"): CognitiveRegime.DELIBERATIVE_REASONING,
            (CognitiveRegime.DELIBERATIVE_REASONING, "pattern_found"): CognitiveRegime.RECURSIVE_ABSTRACTION,
            (CognitiveRegime.RECURSIVE_ABSTRACTION, "creative_needed"): CognitiveRegime.CREATIVE_SYNTHESIS,
            (CognitiveRegime.CREATIVE_SYNTHESIS, "self_reflection"): CognitiveRegime.META_COGNITION,
            (CognitiveRegime.META_COGNITION, "task_complete"): CognitiveRegime.IDLE,
            (CognitiveRegime.REACTIVE_PARSING, "overload"): CognitiveRegime.EMERGENCY,
            (CognitiveRegime.DELIBERATIVE_REASONING, "overload"): CognitiveRegime.EMERGENCY,
            (CognitiveRegime.EMERGENCY, "stabilized"): CognitiveRegime.REACTIVE_PARSING,
        }

    def evaluate_transition(self, trigger: str, context: Dict) -> Optional[CognitiveRegime]:
        """
        Valuta se transizione a nuovo regime.
        Returns: nuovo regime o None se non serve transizione
        """
        new_regime = self.transition_rules.get((self.current_regime, trigger))

        if new_regime is None:
            return None

        # Validazione con contesto
        phi = context.get("phi", 0.7)
        resource_usage = context.get("resource_usage", 0.6)

        # Non transizione se risorse insufficienti
        if new_regime in [CognitiveRegime.DELIBERATIVE_REASONING, CognitiveRegime.RECURSIVE_ABSTRACTION]:
            if resource_usage > 0.9:
                return CognitiveRegime.EMERGENCY

        # Non transizione se phi troppo basso per meta-cognizione
        if new_regime == CognitiveRegime.META_COGNITION and phi < 0.6:
            return None

        return new_regime

    def execute_transition(self, new_regime: CognitiveRegime, phi_before: float) -> RegimeTransition:
        """Esegue transizione regime"""
        old_regime = self.current_regime

        self.regime_history.append({
            "from": old_regime.value,
            "to": new_regime.value,
            "timestamp": datetime.now().isoformat()
        })

        self.current_regime = new_regime

        logger.info(f"Kinetica: {old_regime.value} -> {new_regime.value}")

        return RegimeTransition(
            from_regime=old_regime,
            to_regime=new_regime,
            trigger="auto_transition",
            timestamp=datetime.now().isoformat(),
            phi_before=phi_before,
            phi_after=phi_before
        )

    def get_regime_config(self, regime: CognitiveRegime) -> Dict[str, Any]:
        """Configurazione per regime"""
        configs = {
            CognitiveRegime.REACTIVE_PARSING: {
                "parallel_neurons": 3,
                "depth_limit": 2,
                "timeout_ms": 500,
                "exploration_rate": 0.1
            },
            CognitiveRegime.DELIBERATIVE_REASONING: {
                "parallel_neurons": 5,
                "depth_limit": 5,
                "timeout_ms": 5000,
                "exploration_rate": 0.3
            },
            CognitiveRegime.RECURSIVE_ABSTRACTION: {
                "parallel_neurons": 4,
                "depth_limit": 8,
                "timeout_ms": 10000,
                "exploration_rate": 0.5
            },
            CognitiveRegime.CREATIVE_SYNTHESIS: {
                "parallel_neurons": 6,
                "depth_limit": 6,
                "timeout_ms": 15000,
                "exploration_rate": 0.8
            },
            CognitiveRegime.META_COGNITION: {
                "parallel_neurons": 2,
                "depth_limit": 3,
                "timeout_ms": 20000,
                "exploration_rate": 0.4
            },
            CognitiveRegime.EMERGENCY: {
                "parallel_neurons": 1,
                "depth_limit": 1,
                "timeout_ms": 200,
                "exploration_rate": 0.0
            },
            CognitiveRegime.IDLE: {
                "parallel_neurons": 0,
                "depth_limit": 0,
                "timeout_ms": 0,
                "exploration_rate": 0.05
            }
        }
        return configs.get(regime, configs[CognitiveRegime.IDLE])


class HebbianPlasticityController:
    """
    L5 - Apprendimento Hebbian: neuroni che si attivano insieme si rafforzano.
    'Cells that fire together, wire together'
    """

    def __init__(self, morphogenesis_engine):
        self.morpho = morphogenesis_engine
        self.synapse_weights: Dict[Tuple[str, str], float] = {}
        self.coactivation_history: deque = deque(maxlen=500)
        self.learning_rate = 0.1
        self.decay_rate = 0.01
        self.potential_threshold = 0.7

    def record_coactivation(self, neuron_a: str, neuron_b: str, activation: float):
        """Registra co-attivazione tra neuroni"""
        key = tuple(sorted([neuron_a, neuron_b]))
        timestamp = datetime.now().isoformat()

        self.coactivation_history.append({
            "pair": key,
            "activation": activation,
            "timestamp": timestamp
        })

        # Update peso sinaptico
        current_weight = self.synapse_weights.get(key, 0.5)
        delta = self.learning_rate * activation * (1 - current_weight)
        new_weight = min(1.0, max(0.0, current_weight + delta))

        self.synapse_weights[key] = new_weight

    def get_strongest_synapses(self, top_n: int = 10) -> List[Tuple[str, str, float]]:
        """Ritorna le sinapsi più forti"""
        sorted_weights = sorted(self.synapse_weights.items(), key=lambda x: x[1], reverse=True)
        return [(k[0], k[1], w) for k, w in sorted_weights[:top_n]]

    def prune_weak_synapses(self, threshold: float = 0.2) -> int:
        """Rimuove sinapsi deboli"""
        to_prune = [k for k, w in self.synapse_weights.items() if w < threshold]
        for key in to_prune:
            del self.synapse_weights[key]
        return len(to_prune)

    def apply_decay(self):
        """Applica decadimento ai pesi sinaptici"""
        for key in self.synapse_weights:
            self.synapse_weights[key] = max(0.1, self.synapse_weights[key] - self.decay_rate)


class MorphogenesisEngine:
    """
    Motore di Morfogenesi - orchestratore principale.
    Combina Homeodyna (equilibrio) + Kinetica (transizioni) + Hebbian (apprendimento)
    """

    VERSION = "1.0"

    def __init__(self, bridge=None):
        self.bridge = bridge
        self.running = False

        # Sub-controllers
        self.homeodyna = HomeodynaController(self)
        self.kinetica = KineticaController(self)
        self.hebbian = HebbianPlasticityController(self)

        # State
        self.morphogenic_signals: deque = deque(maxlen=100)
        self.last_evaluation = datetime.now()
        self.evaluation_interval = 30  # secondi

        # Stats
        self.transitions_count = 0
        self.signals_generated = 0

    def start(self):
        self.running = True
        logger.info("Morphogenesis Engine started (Homeodyna + Kinetica + Hebbian)")

    def stop(self):
        self.running = False
        logger.info("Morphogenesis Engine stopped")

    def evaluate_and_adapt(self, system_state: Dict) -> Dict[str, Any]:
        """
        Ciclo principale di valutazione e adattamento.
        Esegue Homeodyna + Kinetica in sequenza.
        """
        self.last_evaluation = datetime.now()

        # --- HOMEODYNA: Valuta equilibrio ---
        balance_score, violations = self.homeodyna.evaluate_balance(system_state)
        compensation_signals = []

        if violations:
            compensation_signals = self.homeodyna.generate_compensation_signals(violations)
            self.signals_generated += len(compensation_signals)

        # --- KINETICA: Valuta transizioni regime ---
        trigger = self._determine_trigger(system_state)
        new_regime = self.kinetica.evaluate_transition(trigger, system_state)
        transition_record = None

        if new_regime:
            transition_record = self.kinetica.execute_transition(
                new_regime,
                system_state.get("phi", 0.7)
            )
            self.transitions_count += 1

        # --- Esegui compensazioni ---
        self._apply_signals(compensation_signals, system_state)

        # --- HEBBIAN: decay periodico ---
        self.hebbian.apply_decay()

        return {
            "timestamp": datetime.now().isoformat(),
            "balance_score": balance_score,
            "violations": violations,
            "current_regime": self.kinetica.current_regime.value,
            "regime_config": self.kinetica.get_regime_config(self.kinetica.current_regime),
            "transition": transition_record,
            "compensation_signals": len(compensation_signals),
            "strongest_synapses": self.hebbian.get_strongest_synapses(5),
            "morpho_stats": self.get_morpho_stats()
        }

    def _determine_trigger(self, state: Dict) -> str:
        """Determina trigger per transizione regime"""
        phi = state.get("phi", 0.7)
        resource_usage = state.get("resource_usage", 0.6)
        task_complexity = state.get("task_complexity", 0.5)

        if resource_usage > 0.9:
            return "overload"
        elif phi < 0.5:
            return "degraded"
        elif task_complexity > 0.8:
            return "complex_task"
        elif "creative" in str(state.get("context", "")):
            return "creative_needed"
        elif "reflection" in str(state.get("context", "")):
            return "self_reflection"

        return "periodic_check"

    def _apply_signals(self, signals: List[MorphogenicSignal], state: Dict):
        """Applica segnali morfogenetici al sistema"""
        for signal in signals:
            self.morphogenic_signals.append(signal)

            if signal.type == "prune":
                self._handle_prune_signal(signal, state)
            elif signal.type == "reconfigure":
                self._handle_reconfigure_signal(signal, state)
            elif signal.type == "stabilize":
                self._handle_stabilize_signal(signal, state)

    def _handle_prune_signal(self, signal: MorphogenicSignal, state: Dict):
        """Gestisce segnale di pruning"""
        logger.debug(f"Morphogenetic PRUNE signal: {signal.source_neuron}")

    def _handle_reconfigure_signal(self, signal: MorphogenicSignal, state: Dict):
        """Gestisce segnale di riconfigurazione"""
        logger.debug(f"Morphogenetic RECONFIGURE signal: {signal.source_neuron}")

    def _handle_stabilize_signal(self, signal: MorphogenicSignal, state: Dict):
        """Gestisce segnale di stabilizzazione"""
        logger.debug(f"Morphogenetic STABILIZE signal: {signal.source_neuron}")

    def process(self, input_data: Dict) -> Dict[str, Any]:
        """Processa input e applica morfogenesi"""
        return self.evaluate_and_adapt(input_data)

    def request_regime_transition(self, trigger: str, context: Dict) -> Optional[RegimeTransition]:
        """Richiede esplicitamente una transizione di regime"""
        new_regime = self.kinetica.evaluate_transition(trigger, context)
        if new_regime:
            return self.kinetica.execute_transition(new_regime, context.get("phi", 0.7))
        return None

    def record_neuron_coactivation(self, neuron_a: str, neuron_b: str, activation: float):
        """Registra co-attivazione per apprendimento Hebbian"""
        self.hebbian.record_coactivation(neuron_a, neuron_b, activation)

    def get_morpho_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche morfogenesi"""
        return {
            "transitions_count": self.transitions_count,
            "signals_generated": self.signals_generated,
            "current_regime": self.kinetica.current_regime.value,
            "synapses_count": len(self.hebbian.synapse_weights),
            "signals_pending": len(self.morphogenic_signals),
            "balance_history_len": len(self.homeodyna.balance_history)
        }

    def get_status(self) -> Dict:
        """Stato completo del motore"""
        return {
            "version": self.VERSION,
            "running": self.running,
            "homeodyna": {
                "balance_score": self.homeodyna.balance_history[-1]["score"] if self.homeodyna.balance_history else 0.0,
                "constraints_count": len(self.homeodyna.constraints)
            },
            "kinetica": {
                "current_regime": self.kinetica.current_regime.value,
                "transitions_count": self.transitions_count
            },
            "hebbian": {
                "synapses_count": len(self.hebbian.synapse_weights),
                "coactivation_records": len(self.hebbian.coactivation_history)
            },
            "last_evaluation": self.last_evaluation.isoformat()
        }


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Morphogenesis Engine - Test")
    print("=" * 60)

    morpho = MorphogenesisEngine()
    morpho.start()

    # Test system state
    test_state = {
        "phi": 0.72,
        "excitation_level": 0.55,
        "inhibition_level": 0.48,
        "resource_usage": 0.75,
        "task_complexity": 0.6,
        "context": "deliberative reasoning task"
    }

    result = morpho.evaluate_and_adapt(test_state)

    print(f"\nRegime attuale: {result['current_regime']}")
    print(f"Balance score: {result['balance_score']:.3f}")
    print(f"Violations: {result['violations']}")
    print(f"Transitions: {morpho.transitions_count}")
    print(f"Strongest synapses: {result['strongest_synapses'][:3]}")

    # Test regime transition
    print("\n--- Test transizione regime ---")
    transition = morpho.request_regime_transition("overload", {"phi": 0.4, "resource_usage": 0.95})
    if transition:
        print(f"Transizione eseguita: {transition.from_regime.value} -> {transition.to_regime.value}")

    print(f"\nStatus: {json.dumps(morpho.get_status(), indent=2)}")