"""
SPEACE Neural Engine - Synapse System
Sistema di connessioni e feedback tra neuroni.
Gestisce plasticità sinaptica e propagazione di segnali.
"""

from __future__ import annotations

import uuid
import time
import math
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable
from collections import defaultdict, deque

from .neuron_base import NeuronType, SignalType, ExecutionContext
from .graph_core import Edge, EdgeType


class SynapseState(Enum):
    INACTIVE = auto()
    ACTIVE = auto()
    DEPRESSED = auto()
    POTENTIATED = auto()
    BLOCKED = auto()


@dataclass
class SynapseStrength:
    base_weight: float = 1.0
    current_weight: float = 1.0
    plasticity_factor: float = 0.1
    min_weight: float = 0.1
    max_weight: float = 2.0


@dataclass
class Synapse:
    synapse_id: str
    source_id: str
    target_id: str
    source_port: str
    target_port: str
    edge_type: EdgeType = EdgeType.DATA
    strength: SynapseStrength = field(default_factory=SynapseStrength)
    state: SynapseState = SynapseState.ACTIVE
    signal_history: List[Dict[str, Any]] = field(default_factory=list)
    last_signal_time: float = 0
    activation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    signal_id: str
    source_id: str
    target_id: str
    signal_type: SignalType
    payload: Any
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    priority: int = 0
    ttl: int = 1


class SynapticPlasticity:
    STDP_WINDOW_MS = 100.0
    HOMEOSTATIC_TARGET = 100

    def __init__(self):
        self._learning_rate = 0.01
        self._decay_rate = 0.95
        self._potentation_threshold = 0.8
        self._depression_threshold = 0.3

    def apply_stdp(
        self,
        synapse: Synapse,
        pre_time: float,
        post_time: float,
        post_spike: bool
    ) -> float:
        dt = post_time - pre_time

        if abs(dt) > self.STDP_WINDOW_MS:
            return synapse.strength.current_weight

        if dt > 0:
            weight_change = self._learning_rate * math.exp(-dt / self.STDP_WINDOW_MS)
        else:
            weight_change = -self._learning_rate * math.exp(dt / self.STDP_WINDOW_MS)

        new_weight = synapse.strength.current_weight + weight_change
        synapse.strength.current_weight = max(
            synapse.strength.min_weight,
            min(synapse.strength.max_weight, new_weight)
        )

        return synapse.strength.current_weight

    def apply_homeostatic(self, synapse: Synapse, target_activity: float = None) -> float:
        target = target_activity or self.HOMEOSTATIC_TARGET
        current = synapse.activation_count

        if current > target * 1.2:
            synapse.strength.current_weight *= self._decay_rate
        elif current < target * 0.8:
            synapse.strength.current_weight *= (1 + self._learning_rate)

        synapse.strength.current_weight = max(
            synapse.strength.min_weight,
            min(synapse.strength.max_weight, synapse.strength.current_weight)
        )

        return synapse.strength.current_weight

    def calculate_fitness_contribution(
        self,
        synapse: Synapse,
        execution_success: bool,
        outcome_metric: float
    ) -> float:
        contribution = 0.0

        if execution_success:
            contribution += 0.3 * synapse.strength.current_weight
            contribution += 0.7 * outcome_metric
        else:
            contribution -= 0.2 * synapse.strength.current_weight

        if synapse.state == SynapseState.POTENTIATED:
            contribution *= 1.2
        elif synapse.state == SynapseState.DEPRESSED:
            contribution *= 0.5

        return max(-1.0, min(1.0, contribution))


class SynapseManager:
    VERSION = "1.0.0"

    def __init__(self, plasticity: Optional[SynapticPlasticity] = None):
        self._synapses: Dict[str, Synapse] = {}
        self._source_to_synapses: Dict[str, List[str]] = defaultdict(list)
        self._target_to_synapses: Dict[str, List[str]] = defaultdict(list)
        self._plasticity = plasticity or SynapticPlasticity()
        self._signal_queue: deque = deque()
        self._lock = threading.RLock()
        self._propagation_enabled = True

    def create_synapse(
        self,
        source_id: str,
        target_id: str,
        source_port: str = "output",
        target_port: str = "input",
        edge_type: EdgeType = EdgeType.DATA,
        initial_weight: float = 1.0
    ) -> Synapse:
        synapse_id = f"syn_{uuid.uuid4().hex[:12]}"

        synapse = Synapse(
            synapse_id=synapse_id,
            source_id=source_id,
            target_id=target_id,
            source_port=source_port,
            target_port=target_port,
            edge_type=edge_type,
            strength=SynapseStrength(base_weight=initial_weight, current_weight=initial_weight)
        )

        with self._lock:
            self._synapses[synapse_id] = synapse
            self._source_to_synapses[source_id].append(synapse_id)
            self._target_to_synapses[target_id].append(synapse_id)

        return synapse

    def get_synapse(self, synapse_id: str) -> Optional[Synapse]:
        return self._synapses.get(synapse_id)

    def get_synapses_for_source(self, source_id: str) -> List[Synapse]:
        return [self._synapses[sid] for sid in self._source_to_synapses.get(source_id, [])]

    def get_synapses_for_target(self, target_id: str) -> List[Synapse]:
        return [self._synapses[sid] for sid in self._target_to_synapses.get(target_id, [])]

    def remove_synapse(self, synapse_id: str) -> bool:
        with self._lock:
            if synapse_id not in self._synapses:
                return False

            synapse = self._synapses[synapse_id]
            if synapse_id in self._source_to_synapses[synapse.source_id]:
                self._source_to_synapses[synapse.source_id].remove(synapse_id)
            if synapse_id in self._target_to_synapses[synapse.target_id]:
                self._target_to_synapses[synapse.target_id].remove(synapse_id)

            del self._synapses[synapse_id]
            return True

    def propagate_signal(
        self,
        source_id: str,
        signal_type: SignalType,
        payload: Any,
        target_ids: Optional[List[str]] = None
    ) -> List[str]:
        if not self._propagation_enabled:
            return []

        delivered_to = []

        with self._lock:
            synapses = self.get_synapses_for_source(source_id)
            if target_ids:
                synapses = [s for s in synapses if s.target_id in target_ids]

        for synapse in synapses:
            if synapse.state == SynapseState.BLOCKED:
                continue

            signal = Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                source_id=source_id,
                target_id=synapse.target_id,
                signal_type=signal_type,
                payload=payload,
                weight=synapse.strength.current_weight
            )

            self._signal_queue.append(signal)
            synapse.signal_history.append({
                "signal_id": signal.signal_id,
                "timestamp": signal.timestamp,
                "type": signal.signal_type.name,
                "weight": signal.weight
            })
            synapse.last_signal_time = signal.timestamp
            synapse.activation_count += 1

            delivered_to.append(synapse.target_id)

        return delivered_to

    def propagate_feedback(
        self,
        target_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any]
    ) -> List[str]:
        delivered_to = []

        with self._lock:
            synapses = self.get_synapses_for_target(target_id)

        for synapse in synapses:
            signal = Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                source_id=target_id,
                target_id=synapse.source_id,
                signal_type=SignalType.FEEDBACK,
                payload={"feedback_type": feedback_type, "data": feedback_data},
                weight=synapse.strength.current_weight
            )

            self._signal_queue.append(signal)
            delivered_to.append(synapse.source_id)

        return delivered_to

    def apply_plasticity_update(
        self,
        synapse_id: str,
        pre_time: float,
        post_time: float,
        post_spike: bool = False
    ) -> Optional[float]:
        synapse = self._synapses.get(synapse_id)
        if not synapse:
            return None

        new_weight = self._plasticity.apply_stdp(synapse, pre_time, post_time, post_spike)
        synapse.strength.current_weight = new_weight

        if new_weight >= synapse.strength.max_weight * 0.9:
            synapse.state = SynapseState.POTENTIATED
        elif new_weight <= synapse.strength.min_weight * 1.1:
            synapse.state = SynapseState.DEPRESSED
        else:
            synapse.state = SynapseState.ACTIVE

        return new_weight

    def update_from_outcome(
        self,
        synapse_id: str,
        execution_success: bool,
        outcome_metric: float
    ) -> Optional[float]:
        synapse = self._synapses.get(synapse_id)
        if not synapse:
            return None

        contribution = self._plasticity.calculate_fitness_contribution(
            synapse, execution_success, outcome_metric
        )

        synapse.strength.current_weight += contribution * synapse.strength.plasticity_factor
        synapse.strength.current_weight = max(
            synapse.strength.min_weight,
            min(synapse.strength.max_weight, synapse.strength.current_weight)
        )

        return synapse.strength.current_weight

    def get_pending_signals(self, target_id: str) -> List[Signal]:
        pending = []
        temp_queue = deque()

        while self._signal_queue:
            signal = self._signal_queue.popleft()
            if signal.target_id == target_id and signal.ttl > 0:
                pending.append(signal)
            elif signal.ttl > 0:
                temp_queue.append(signal)

        self._signal_queue = temp_queue
        return pending

    def enable_propagation(self):
        self._propagation_enabled = True

    def disable_propagation(self):
        self._propagation_enabled = False

    def get_synapse_stats(self) -> Dict[str, Any]:
        total = len(self._synapses)
        by_state = defaultdict(int)
        total_activation = 0

        for synapse in self._synapses.values():
            by_state[synapse.state.name] += 1
            total_activation += synapse.activation_count

        avg_weight = sum(s.strength.current_weight for s in self._synapses.values()) / total if total > 0 else 0

        return {
            "total_synapses": total,
            "by_state": dict(by_state),
            "total_activations": total_activation,
            "average_weight": avg_weight,
            "pending_signals": len(self._signal_queue)
        }

    def prune_inactive_synapses(self, max_age_seconds: float = 3600) -> int:
        removed = 0
        current_time = time.time()

        for synapse_id in list(self._synapses.keys()):
            synapse = self._synapses[synapse_id]
            if (current_time - synapse.last_signal_time) > max_age_seconds:
                if synapse.strength.current_weight < synapse.strength.base_weight * 0.5:
                    self.remove_synapse(synapse_id)
                    removed += 1

        return removed

    def reset_synapse(self, synapse_id: str) -> bool:
        synapse = self._synapses.get(synapse_id)
        if not synapse:
            return False

        synapse.strength.current_weight = synapse.strength.base_weight
        synapse.state = SynapseState.ACTIVE
        synapse.signal_history.clear()
        synapse.activation_count = 0
        return True
