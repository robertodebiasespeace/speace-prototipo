"""
SPEACE Neural Engine - Base Neuron
Fondamento del grafo computazionale tipizzato.
Ogni script/algoritmo/skills/plugin è un neurone funzionale.
"""

from __future__ import annotations

import uuid
import time
import hashlib
import json
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Callable, Type, Set


class NeuronType(Enum):
    SCRIPT = auto()
    ALGORITHM = auto()
    SKILL = auto()
    PLUGIN = auto()
    CORTEX_MODULE = auto()
    DNA_OPERATOR = auto()
    MEMORY_UNIT = auto()
    SENSOR = auto()
    ACTUATOR = auto()
    ABSTRACT = auto()


class NeuronState(Enum):
    DORMANT = auto()
    IDLE = auto()
    RUNNING = auto()
    WAITING = auto()
    ERROR = auto()
    TERMINATED = auto()


class SignalType(Enum):
    EXECUTE = auto()
    RESULT = auto()
    ERROR = auto()
    HEARTBEAT = auto()
    SYNC = auto()
    FEEDBACK = auto()
    METADATA = auto()


@dataclass
class Port:
    name: str
    data_type: str
    direction: str
    schema: Optional[Dict[str, Any]] = None


@dataclass
class Contract:
    input_ports: List[Port]
    output_ports: List[Port]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    execution_timeout: float = 30.0


@dataclass
class ExecutionContext:
    execution_id: str
    neuron_id: str
    inputs: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    parent_context: Optional[str] = None


@dataclass
class NeuronMetadata:
    version: str = "1.0.0"
    author: str = "SPEACE"
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    stability: float = 1.0
    last_modified: str = field(default_factory=lambda: time.time())


class BaseNeuron(ABC):
    VERSION = "1.0.0"

    def __init__(
        self,
        neuron_id: Optional[str] = None,
        name: Optional[str] = None,
        neuron_type: NeuronType = NeuronType.SCRIPT,
        contract: Optional[Contract] = None,
    ):
        self.id = neuron_id or f"neuron_{uuid.uuid4().hex[:12]}"
        self.name = name or self.__class__.__name__
        self.type = neuron_type
        self.contract = contract or self._default_contract()
        self.state = NeuronState.IDLE
        self.metadata = NeuronMetadata()

        self._input_buffer: Dict[str, Any] = {}
        self._output_buffer: Dict[str, Any] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._subscriptions: Dict[SignalType, List[str]] = {s: [] for s in SignalType}
        self._error_count: int = 0
        self._total_executions: int = 0
        self._activation_count: int = 0
        self._last_activation: float = 0
        self._fitness_score: float = 1.0

    @abstractmethod
    def _default_contract(self) -> Contract:
        pass

    @abstractmethod
    def _execute(self, context: ExecutionContext) -> Dict[str, Any]:
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        if not self.contract:
            return True
        for port in self.contract.input_ports:
            if port.required and port.name not in inputs:
                return False
        return True

    def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        self.state = NeuronState.RUNNING
        self._total_executions += 1
        self._activation_count += 1
        self._last_activation = time.time()

        try:
            if not self.validate_inputs(context.inputs):
                raise ValueError(f"Input validation failed for neuron {self.id}")

            result = self._execute(context)

            self._output_buffer = result
            self._execution_history.append({
                "execution_id": context.execution_id,
                "timestamp": time.time(),
                "duration": time.time() - context.start_time,
                "success": True,
                "output_keys": list(result.keys()) if result else []
            })
            self._error_count = 0
            self.state = NeuronState.IDLE
            return result

        except Exception as e:
            self._error_count += 1
            self.state = NeuronState.ERROR
            self._execution_history.append({
                "execution_id": context.execution_id,
                "timestamp": time.time(),
                "duration": time.time() - context.start_time,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            raise

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "state": self.state.name,
            "activation_count": self._activation_count,
            "total_executions": self._total_executions,
            "error_count": self._error_count,
            "fitness_score": self._fitness_score,
            "last_activation": self._last_activation
        }

    def subscribe(self, signal_type: SignalType, neuron_id: str):
        if neuron_id not in self._subscriptions[signal_type]:
            self._subscriptions[signal_type].append(neuron_id)

    def unsubscribe(self, signal_type: SignalType, neuron_id: str):
        if neuron_id in self._subscriptions[signal_type]:
            self._subscriptions[signal_type].remove(neuron_id)

    def reset(self):
        self.state = NeuronState.IDLE
        self._input_buffer.clear()
        self._output_buffer.clear()
        self._error_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "state": self.state.name,
            "metadata": {
                "version": self.metadata.version,
                "category": self.metadata.category,
                "tags": self.metadata.tags,
                "stability": self.metadata.stability
            }
        }


class NeuronFactory:
    _registry: Dict[str, Type[BaseNeuron]] = {}

    @classmethod
    def register(cls, type_name: str, neuron_class: Type[BaseNeuron]):
        cls._registry[type_name] = neuron_class

    @classmethod
    def create(cls, type_name: str, **kwargs) -> BaseNeuron:
        if type_name not in cls._registry:
            raise ValueError(f"Neuron type {type_name} not registered")
        return cls._registry[type_name](**kwargs)

    @classmethod
    def get_registered_types(cls) -> List[str]:
        return list(cls._registry.keys())
