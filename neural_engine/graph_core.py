"""
SPEACE Neural Engine - Computational Graph Core
Grafo computazionale tipizzato con neuroni funzionali come nodi.
"""

from __future__ import annotations

import uuid
import time
import json
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Tuple, Callable
from collections import defaultdict, deque

from .neuron_base import (
    BaseNeuron, NeuronType, NeuronState, SignalType,
    ExecutionContext, Contract, NeuronMetadata
)


class EdgeType(Enum):
    DATA = auto()
    CONTROL = auto()
    FEEDBACK = auto()
    BIDIRECTIONAL = auto()


@dataclass
class Edge:
    source_id: str
    target_id: str
    source_port: str
    target_port: str
    edge_type: EdgeType = EdgeType.DATA
    weight: float = 1.0
    delay_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphMetadata:
    id: str
    name: str
    version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    total_executions: int = 0
    total_errors: int = 0


class GraphState(Enum):
    IDLE = auto()
    EXECUTING = auto()
    PAUSED = auto()
    ERROR = auto()
    TERMINATED = auto()


class ComputationalGraph:
    VERSION = "1.0.0"

    def __init__(self, graph_id: Optional[str] = None, name: str = "SPEACE_Graph"):
        self.id = graph_id or f"graph_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.metadata = GraphMetadata(id=self.id, name=name)

        self._neurons: Dict[str, BaseNeuron] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._in_degree: Dict[str, int] = defaultdict(int)
        self._out_degree: Dict[str, int] = defaultdict(int)

        self._execution_queue: deque = deque()
        self._running_neurons: Set[str] = set()
        self._completed_executions: Dict[str, Dict[str, Any]] = {}
        self._pending_signals: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)

        self._lock = threading.RLock()
        self._state = GraphState.IDLE

        self._execution_callbacks: Dict[str, Callable] = {}
        self._topological_cache: Optional[List[str]] = None

    def add_neuron(self, neuron: BaseNeuron) -> bool:
        with self._lock:
            if neuron.id in self._neurons:
                return False
            self._neurons[neuron.id] = neuron
            self._adjacency[neuron.id] = []
            self._reverse_adjacency[neuron.id] = []
            self._in_degree[neuron.id] = 0
            self._out_degree[neuron.id] = 0
            self._topological_cache = None
            return True

    def remove_neuron(self, neuron_id: str) -> bool:
        with self._lock:
            if neuron_id not in self._neurons:
                return False

            for target_id in list(self._adjacency.get(neuron_id, [])):
                self._remove_edge_internal(neuron_id, target_id)

            for source_id in list(self._reverse_adjacency.get(neuron_id, [])):
                self._remove_edge_internal(source_id, neuron_id)

            del self._neurons[neuron_id]
            self._topological_cache = None
            return True

    def _remove_edge_internal(self, source_id: str, target_id: str):
        for edge_id, edge in list(self._edges.items()):
            if edge.source_id == source_id and edge.target_id == target_id:
                del self._edges[edge_id]
                self._adjacency[source_id].remove(target_id)
                self._reverse_adjacency[target_id].remove(source_id)
                self._out_degree[source_id] -= 1
                self._in_degree[target_id] -= 1

    def connect(
        self,
        source_id: str,
        target_id: str,
        source_port: str = "output",
        target_port: str = "input",
        edge_type: EdgeType = EdgeType.DATA,
        weight: float = 1.0
    ) -> Optional[str]:
        with self._lock:
            if source_id not in self._neurons or target_id not in self._neurons:
                return None

            edge_id = f"edge_{uuid.uuid4().hex[:12]}"
            edge = Edge(
                source_id=source_id,
                target_id=target_id,
                source_port=source_port,
                target_port=target_port,
                edge_type=edge_type,
                weight=weight
            )

            self._edges[edge_id] = edge
            self._adjacency[source_id].append(target_id)
            self._reverse_adjacency[target_id].append(source_id)
            self._out_degree[source_id] += 1
            self._in_degree[target_id] += 1
            self._topological_cache = None

            return edge_id

    def disconnect(self, edge_id: str) -> bool:
        with self._lock:
            if edge_id not in self._edges:
                return False

            edge = self._edges[edge_id]
            if edge.source_id in self._adjacency:
                self._adjacency[edge.source_id].remove(edge.target_id)
            if edge.target_id in self._reverse_adjacency:
                self._reverse_adjacency[edge.target_id].remove(edge.source_id)

            self._out_degree[edge.source_id] -= 1
            self._in_degree[edge.target_id] -= 1

            del self._edges[edge_id]
            self._topological_cache = None
            return True

    def get_topological_order(self) -> List[str]:
        if self._topological_cache is not None:
            return self._topological_cache

        in_degree = dict(self._in_degree)
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in self._adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._neurons):
            raise ValueError("Graph contains a cycle")

        self._topological_cache = result
        return result

    def get_neuron(self, neuron_id: str) -> Optional[BaseNeuron]:
        return self._neurons.get(neuron_id)

    def get_outgoing_edges(self, neuron_id: str) -> List[Edge]:
        return [e for e in self._edges.values() if e.source_id == neuron_id]

    def get_incoming_edges(self, neuron_id: str) -> List[Edge]:
        return [e for e in self._edges.values() if e.target_id == neuron_id]

    def execute(
        self,
        start_neurons: Optional[List[str]] = None,
        end_neurons: Optional[List[str]] = None,
        context_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self._state = GraphState.EXECUTING
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        context_metadata = context_metadata or {}

        try:
            if start_neurons:
                order = self._get_subgraph_order(start_neurons, end_neurons)
            else:
                order = self.get_topological_order()

            execution_results = {}

            for neuron_id in order:
                neuron = self._neurons[neuron_id]

                inputs = self._gather_inputs(neuron_id, execution_results)

                ctx = ExecutionContext(
                    execution_id=execution_id,
                    neuron_id=neuron_id,
                    inputs=inputs,
                    metadata={**context_metadata, "graph_id": self.id}
                )

                try:
                    result = neuron.execute(ctx)
                    execution_results[neuron_id] = {
                        "success": True,
                        "result": result,
                        "timestamp": time.time()
                    }
                    self._propagate_outputs(neuron_id, result, execution_results)
                except Exception as e:
                    execution_results[neuron_id] = {
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    }
                    self.metadata.total_errors += 1

            self.metadata.total_executions += 1
            self._state = GraphState.IDLE
            return {
                "execution_id": execution_id,
                "results": execution_results,
                "success": all(r.get("success", False) for r in execution_results.values())
            }

        except Exception as e:
            self._state = GraphState.ERROR
            return {
                "execution_id": execution_id,
                "success": False,
                "error": str(e)
            }

    def _gather_inputs(self, neuron_id: str, execution_results: Dict) -> Dict[str, Any]:
        inputs = {}
        for edge in self.get_incoming_edges(neuron_id):
            if edge.edge_type in (EdgeType.DATA, EdgeType.BIDIRECTIONAL):
                source_result = execution_results.get(edge.source_id)
                if source_result and source_result.get("success"):
                    inputs[edge.target_port] = source_result["result"].get(edge.source_port)
        return inputs

    def _propagate_outputs(self, neuron_id: str, result: Dict, execution_results: Dict):
        for edge in self.get_outgoing_edges(neuron_id):
            if edge.edge_type in (EdgeType.DATA, EdgeType.BIDIRECTIONAL):
                if edge.target_id not in execution_results:
                    execution_results[edge.target_id] = {"success": True, "result": {}}
                execution_results[edge.target_id]["result"][edge.target_port] = result.get(edge.source_port)

    def _get_subgraph_order(self, start_neurons: List[str], end_neurons: List[str]) -> List[str]:
        reachable = set()
        for start in start_neurons:
            reachable.add(start)

        for _ in range(len(self._neurons)):
            for neuron_id in list(reachable):
                for neighbor in self._adjacency.get(neuron_id, []):
                    reachable.add(neighbor)

        if end_neurons:
            to_remove = set(self._neurons.keys()) - reachable
            for end in end_neurons:
                if end in to_remove:
                    to_remove.remove(end)
            for nid in to_remove:
                del self._neurons[nid]

        return self.get_topological_order()

    def get_state(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self._state.name,
            "neuron_count": len(self._neurons),
            "edge_count": len(self._edges),
            "total_executions": self.metadata.total_executions,
            "total_errors": self.metadata.total_errors
        }

    def get_graph_data(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "id": self.id,
                "name": self.name,
                "version": self.metadata.version,
                "created_at": self.metadata.created_at
            },
            "neurons": {nid: n.to_dict() for nid, n in self._neurons.items()},
            "edges": [
                {
                    "id": eid,
                    "source": e.source_id,
                    "target": e.target_id,
                    "source_port": e.source_port,
                    "target_port": e.target_port,
                    "type": e.edge_type.name,
                    "weight": e.weight
                }
                for eid, e in self._edges.items()
            ]
        }

    def export_to_dict(self) -> Dict[str, Any]:
        return self.get_graph_data()

    def import_from_dict(self, data: Dict):
        self._neurons.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()

        self.id = data["metadata"]["id"]
        self.name = data["metadata"]["name"]

        for eid, edge_data in data.get("edges", {}).items():
            pass

    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        if source_id not in self._neurons or target_id not in self._neurons:
            return None

        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return path

            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def detect_cycles(self) -> List[List[str]]:
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)
            return False

        for node in self._neurons:
            if node not in visited:
                dfs(node, [node])

        return cycles
