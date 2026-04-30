"""
SPEACE Neural Engine - Structural Plasticity
Plasticità strutturale guidata da feedback.
Gestisce creazione, modifica e rimozione di neuroni e sinapsi.
"""

from __future__ import annotations

import uuid
import time
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable, Tuple
from collections import defaultdict

from .neuron_base import BaseNeuron, NeuronType, NeuronState
from .graph_core import ComputationalGraph, EdgeType
from .synapse import SynapseManager, Synapse, SynapticPlasticity, SynapseState


class PlasticityRule(Enum):
    HEBDARIAN = auto()
    NEUROGENESIS = auto()
    PRUNING = auto()
    SPLITTING = auto()
    MERGING = auto()
    FUSION = auto()


@dataclass
class PlasticityEvent:
    event_id: str
    rule: PlasticityRule
    timestamp: float
    target_id: str
    action: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FitnessScore:
    neuron_id: str
    execution_score: float = 0.0
    connectivity_score: float = 0.0
    energy_score: float = 0.0
    contribution_score: float = 0.0
    total: float = 0.0
    timestamp: float = field(default_factory=time.time)


class StructuralPlasticity:
    VERSION = "1.0.0"

    def __init__(self, graph: ComputationalGraph, synapse_manager: SynapseManager):
        self.graph = graph
        self.synapse_manager = synapse_manager
        self._events: List[PlasticityEvent] = []
        self._fitness_cache: Dict[str, FitnessScore] = {}
        self._enabled_rules: Set[PlasticityRule] = {
            PlasticityRule.HEBDARIAN,
            PlasticityRule.PRUNING,
            PlasticityRule.NEUROGENESIS
        }
        self._thresholds = {
            "pruning_weight": 0.3,
            "pruning_age": 3600,
            "neurogenesis_connectivity": 2,
            "splitting_fitness": 0.8,
            "merging_similarity": 0.7
        }
        self._creation_probabilities = {
            "neurogenesis": 0.01,
            "splitting": 0.005,
            "merging": 0.002
        }
        self._lock_callbacks: List[Callable] = []

    def set_rule_enabled(self, rule: PlasticityRule, enabled: bool):
        if enabled:
            self._enabled_rules.add(rule)
        else:
            self._enabled_rules.discard(rule)

    def evaluate_fitness(self, neuron_id: str) -> FitnessScore:
        neuron = self.graph.get_neuron(neuron_id)
        if not neuron:
            return FitnessScore(neuron_id=neuron_id)

        exec_score = self._execution_score(neuron)
        conn_score = self._connectivity_score(neuron_id)
        energy_score = self._energy_score(neuron)
        contrib_score = self._contribution_score(neuron_id)

        total = (exec_score * 0.3 + conn_score * 0.2 + energy_score * 0.2 + contrib_score * 0.3)

        fitness = FitnessScore(
            neuron_id=neuron_id,
            execution_score=exec_score,
            connectivity_score=conn_score,
            energy_score=energy_score,
            contribution_score=contrib_score,
            total=total
        )

        self._fitness_cache[neuron_id] = fitness
        return fitness

    def _execution_score(self, neuron: BaseNeuron) -> float:
        if neuron._total_executions == 0:
            return 0.5

        error_rate = neuron._error_count / neuron._total_executions
        success_rate = 1.0 - error_rate

        recent_activity = 0.0
        if neuron._last_activation > 0:
            time_factor = min(1.0, (time.time() - neuron._last_activation) / 3600)
            recent_activity = 1.0 - time_factor

        return (success_rate * 0.7 + recent_activity * 0.3)

    def _connectivity_score(self, neuron_id: str) -> float:
        incoming = len(self.synapse_manager.get_synapses_for_target(neuron_id))
        outgoing = len(self.synapse_manager.get_synapses_for_source(neuron_id))

        if incoming == 0 and outgoing == 0:
            return 0.0

        balance = 1.0 - abs(incoming - outgoing) / max(incoming + outgoing, 1)
        total = min(1.0, (incoming + outgoing) / 10)

        return (balance * 0.5 + total * 0.5)

    def _energy_score(self, neuron: BaseNeuron) -> float:
        if neuron.state == NeuronState.DORMANT:
            return 1.0
        elif neuron.state == NeuronState.ERROR:
            return 0.0
        elif neuron.state == NeuronState.RUNNING:
            return 0.5

        return 0.8

    def _contribution_score(self, neuron_id: str) -> float:
        synapses_from = self.synapse_manager.get_synapses_for_source(neuron_id)
        if not synapses_from:
            return 0.3

        avg_weight = sum(s.strength.current_weight for s in synapses_from) / len(synapses_from)
        return min(1.0, avg_weight)

    def apply_hebbian_rule(self, source_id: str, target_id: str, success: bool) -> bool:
        if PlasticityRule.HEBDARIAN not in self._enabled_rules:
            return False

        synapses = self.synapse_manager.get_synapses_for_source(source_id)
        for synapse in synapses:
            if synapse.target_id == target_id:
                if success:
                    synapse.strength.current_weight = min(
                        synapse.strength.max_weight,
                        synapse.strength.current_weight * 1.05
                    )
                else:
                    synapse.strength.current_weight = max(
                        synapse.strength.min_weight,
                        synapse.strength.current_weight * 0.95
                    )

                self._record_event(
                    PlasticityRule.HEBDARIAN, source_id, "weight_update", True,
                    {"target_id": target_id, "new_weight": synapse.strength.current_weight}
                )
                return True

        return False

    def apply_neurogenesis(self, neuron_factory: Callable[[], BaseNeuron]) -> Optional[str]:
        if PlasticityRule.NEUROGENESIS not in self._enabled_rules:
            return None

        if random.random() > self._creation_probabilities["neurogenesis"]:
            return None

        low_fitness_neurons = []
        for nid, fitness in self._fitness_cache.items():
            if fitness.total < 0.4:
                low_fitness_neurons.append((nid, fitness.total))

        if len(low_fitness_neurons) < 2:
            candidate_neurons = list(self.graph._neurons.keys())
            if len(candidate_neurons) < 2:
                return None

            n1, n2 = random.sample(candidate_neurons, 2)
        else:
            n1, _ = min(low_fitness_neurons, key=lambda x: x[1])
            remaining = [(n, f) for n, f in low_fitness_neurons if n != n1]
            if remaining:
                n2, _ = random.choice(remaining)
            else:
                n2 = random.choice([n for n in self.graph._neurons.keys() if n != n1])

        try:
            new_neuron = neuron_factory()
            self.graph.add_neuron(new_neuron)

            self.synapse_manager.create_synapse(n1, new_neuron.id, weight=0.5)
            self.synapse_manager.create_synapse(new_neuron.id, n2, weight=0.5)

            self._record_event(
                PlasticityRule.NEUROGENESIS, new_neuron.id, "created", True,
                {"from": n1, "to": n2}
            )

            return new_neuron.id
        except Exception as e:
            self._record_event(
                PlasticityRule.NEUROGENESIS, "unknown", "creation_failed", False,
                {"error": str(e)}
            )
            return None

    def apply_pruning(self) -> List[str]:
        if PlasticityRule.PRUNING not in self._enabled_rules:
            return []

        removed_neurons = []
        removed_synapses = 0

        synapse_stats = self.synapse_manager.get_synapse_stats()
        if synapse_stats["average_weight"] < self._thresholds["pruning_weight"]:
            removed_synapses = self.synapse_manager.prune_inactive_synapses(
                self._thresholds["pruning_age"]
            )

        for neuron_id, fitness in list(self._fitness_cache.items()):
            if fitness.total < 0.2:
                connections = len(self.synapse_manager.get_synapses_for_source(neuron_id))
                connections += len(self.synapse_manager.get_synapses_for_target(neuron_id))

                if connections > 0:
                    continue

                if self.graph.remove_neuron(neuron_id):
                    removed_neurons.append(neuron_id)
                    del self._fitness_cache[neuron_id]

                    self._record_event(
                        PlasticityRule.PRUNING, neuron_id, "pruned", True,
                        {"fitness": fitness.total}
                    )

        return removed_neurons

    def apply_splitting(self, neuron_id: str) -> Optional[Tuple[str, str]]:
        if PlasticityRule.SPLITTING not in self._enabled_rules:
            return None

        fitness = self._fitness_cache.get(neuron_id)
        if not fitness or fitness.total < self._thresholds["splitting_fitness"]:
            return None

        neuron = self.graph.get_neuron(neuron_id)
        if not neuron or len(neuron._execution_history) < 10:
            return None

        incoming = self.synapse_manager.get_synapses_for_target(neuron_id)
        outgoing = self.synapse_manager.get_synapses_for_source(neuron_id)

        if len(incoming) < 2 or len(outgoing) < 2:
            return None

        return None

    def apply_merging(self, neuron_ids: List[str]) -> Optional[str]:
        if PlasticityRule.MERGING not in self._enabled_rules:
            return None

        if len(neuron_ids) < 2:
            return None

        return None

    def suggest_connections(self, neuron_id: str, max_connections: int = 3) -> List[str]:
        neuron = self.graph.get_neuron(neuron_id)
        if not neuron:
            return []

        suggestions = []

        for other_id, other_neuron in self.graph._neurons.items():
            if other_id == neuron_id:
                continue

            existing_incoming = self.synapse_manager.get_synapses_for_target(neuron_id)
            existing_outgoing = self.synapse_manager.get_synapses_for_source(neuron_id)

            if any(s.source_id == other_id for s in existing_incoming):
                continue
            if any(s.target_id == other_id for s in existing_outgoing):
                continue

            similarity = self._calculate_similarity(neuron, other_neuron)
            if similarity > 0.5:
                suggestions.append((other_id, similarity))

        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:max_connections]]

    def _calculate_similarity(self, n1: BaseNeuron, n2: BaseNeuron) -> float:
        if n1.type == n2.type:
            type_score = 1.0
        else:
            type_score = 0.3

        shared_tags = len(set(n1.metadata.tags) & set(n2.metadata.tags))
        tag_score = min(1.0, shared_tags / 3)

        n1_conn = len(self.synapse_manager.get_synapses_for_source(n1.id)) + \
                  len(self.synapse_manager.get_synapses_for_target(n1.id))
        n2_conn = len(self.synapse_manager.get_synapses_for_source(n2.id)) + \
                  len(self.synapse_manager.get_synapses_for_target(n2.id))

        conn_diff = abs(n1_conn - n2_conn) / max(n1_conn + n2_conn, 1)
        conn_score = 1.0 - conn_diff

        return type_score * 0.4 + tag_score * 0.3 + conn_score * 0.3

    def _record_event(
        self,
        rule: PlasticityRule,
        target_id: str,
        action: str,
        success: bool,
        details: Dict[str, Any] = None
    ):
        event = PlasticityEvent(
            event_id=f"pe_{uuid.uuid4().hex[:12]}",
            rule=rule,
            timestamp=time.time(),
            target_id=target_id,
            action=action,
            success=success,
            details=details or {}
        )
        self._events.append(event)

    def get_plasticity_report(self) -> Dict[str, Any]:
        total_events = len(self._events)
        successful = sum(1 for e in self._events if e.success)
        by_rule = defaultdict(int)
        for e in self._events:
            by_rule[e.rule.name] += 1

        avg_fitness = sum(f.total for f in self._fitness_cache.values()) / len(self._fitness_cache) if self._fitness_cache else 0

        return {
            "total_events": total_events,
            "successful_events": successful,
            "by_rule": dict(by_rule),
            "enabled_rules": [r.name for r in self._enabled_rules],
            "average_fitness": avg_fitness,
            "neurons_tracked": len(self._fitness_cache)
        }

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [
            {
                "id": e.event_id,
                "rule": e.rule.name,
                "timestamp": e.timestamp,
                "target_id": e.target_id,
                "action": e.action,
                "success": e.success,
                "details": e.details
            }
            for e in self._events[-limit:]
        ]

    def update_fitness_batch(self, neuron_ids: List[str]):
        for nid in neuron_ids:
            if nid in self.graph._neurons:
                self.evaluate_fitness(nid)

    def reset(self):
        self._events.clear()
        self._fitness_cache.clear()
