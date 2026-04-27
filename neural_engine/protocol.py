"""
SPEACE Neural Engine - Interoperability Protocol
Linguaggio operativo condiviso + contratto di esecuzione + sistema validazione.
Coordina comunicazione tra componenti SPEACE, script, algoritmi, skills, plugins.
"""

from __future__ import annotations

import uuid
import time
import hashlib
import json
import jsonschema
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable
from abc import ABC, abstractmethod

from .neuron_base import NeuronType, SignalType


class MessageType(Enum):
    EXECUTE = auto()
    QUERY = auto()
    RESPONSE = auto()
    ERROR = auto()
    HEARTBEAT = auto()
    SYNC_REQUEST = auto()
    SYNC_RESPONSE = auto()
    EVENT = auto()
    BROADCAST = auto()


class ValidationLevel(Enum):
    NONE = auto()
    SYNTAX = auto()
    SEMANTIC = auto()
    CONTRACT = auto()
    FULL = auto()


@dataclass
class Schema:
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    additionalProperties: bool = True


@dataclass
class Message:
    id: str
    msg_type: MessageType
    sender: str
    receiver: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    schema_version: str = "1.0"
    validation_level: ValidationLevel = ValidationLevel.CONTRACT
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractSpec:
    name: str
    version: str
    input_schema: Schema
    output_schema: Schema
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    error_codes: Dict[int, str] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass
class ExecutionTicket:
    ticket_id: str
    neuron_id: str
    contract: ContractSpec
    inputs: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)


class InteropProtocol:
    VERSION = "1.0.0"
    SUPPORTED_TYPES = {mt.name for mt in MessageType}
    SUPPORTED_VALIDATION = {vl.name for vl in ValidationLevel}

    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:12]}"
        self._contracts: Dict[str, ContractSpec] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._pending_tickets: Dict[str, ExecutionTicket] = {}
        self._response_handlers: Dict[str, Callable] = {}
        self._schema_cache: Dict[str, Dict] = {}

    def register_contract(self, contract: ContractSpec) -> bool:
        key = f"{contract.name}:{contract.version}"
        if key in self._contracts:
            return False
        self._contracts[key] = contract
        self._schema_cache[key] = self._contract_to_json_schema(contract)
        return True

    def get_contract(self, name: str, version: str) -> Optional[ContractSpec]:
        key = f"{name}:{version}"
        return self._contracts.get(key)

    def validate_against_contract(
        self,
        name: str,
        version: str,
        data: Dict[str, Any],
        direction: str = "input"
    ) -> tuple[bool, List[str]]:
        key = f"{name}:{version}"
        if key not in self._contracts:
            return False, [f"Contract {key} not found"]

        contract = self._contracts[key]
        schema = contract.input_schema if direction == "input" else contract.output_schema

        errors = []
        try:
            jsonschema.validate(instance=data, schema=self._schema_cache[key][direction])
        except jsonschema.ValidationError as e:
            errors.append(str(e.message))
            return False, errors

        for precond in contract.preconditions if direction == "input" else contract.postconditions:
            if not self._evaluate_condition(precond, data):
                errors.append(f"Condition failed: {precond}")

        return len(errors) == 0, errors

    def _contract_to_json_schema(self, contract: ContractSpec) -> Dict[str, Any]:
        return {
            "input": {
                "type": "object",
                "properties": contract.input_schema.properties,
                "required": contract.input_schema.required,
                "additionalProperties": contract.input_schema.additionalProperties
            },
            "output": {
                "type": "object",
                "properties": contract.output_schema.properties,
                "required": contract.output_schema.required,
                "additionalProperties": contract.output_schema.additionalProperties
            }
        }

    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        try:
            return eval(condition, {"data": data})
        except Exception:
            return False

    def create_message(
        self,
        msg_type: MessageType,
        sender: str,
        receiver: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Message:
        return Message(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=msg_type,
            sender=sender,
            receiver=receiver,
            payload=payload,
            correlation_id=correlation_id
        )

    def send_message(self, message: Message) -> str:
        self._log_message(message)
        return message.id

    def _log_message(self, message: Message):
        pass

    def register_handler(self, msg_type: MessageType, handler: Callable):
        if msg_type not in self._message_handlers:
            self._message_handlers[msg_type] = []
        self._message_handlers[msg_type].append(handler)

    def handle_message(self, message: Message) -> Optional[Message]:
        handlers = self._message_handlers.get(message.msg_type, [])
        for handler in handlers:
            try:
                result = handler(message)
                if result:
                    return result
            except Exception:
                pass
        return None

    def create_ticket(
        self,
        neuron_id: str,
        contract_name: str,
        contract_version: str,
        inputs: Dict[str, Any]
    ) -> Optional[ExecutionTicket]:
        contract = self.get_contract(contract_name, contract_version)
        if not contract:
            return None

        valid, errors = self.validate_against_contract(
            contract_name, contract_version, inputs, "input"
        )

        ticket = ExecutionTicket(
            ticket_id=f"ticket_{uuid.uuid4().hex[:12]}",
            neuron_id=neuron_id,
            contract=contract,
            inputs=inputs,
            validation_errors=errors if not valid else []
        )

        self._pending_tickets[ticket.ticket_id] = ticket
        return ticket if valid else None

    def complete_ticket(
        self,
        ticket_id: str,
        result: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        if ticket_id not in self._pending_tickets:
            return False, ["Ticket not found"]

        ticket = self._pending_tickets[ticket_id]
        valid, errors = self.validate_against_contract(
            ticket.contract.name,
            ticket.contract.version,
            result,
            "output"
        )

        if valid:
            ticket.status = "completed"
            ticket.result = result
        else:
            ticket.status = "validation_failed"
            ticket.validation_errors = errors

        return valid, errors

    def fail_ticket(self, ticket_id: str, error: str):
        if ticket_id in self._pending_tickets:
            self._pending_tickets[ticket_id].status = "failed"
            self._pending_tickets[ticket_id].error = error

    def get_ticket(self, ticket_id: str) -> Optional[ExecutionTicket]:
        return self._pending_tickets.get(ticket_id)


class ComponentBridge:
    def __init__(self, protocol: InteropProtocol):
        self.protocol = protocol
        self._bridges: Dict[str, Any] = {}
        self._adapters: Dict[str, Callable] = {}

    def register_bridge(self, component_type: str, bridge: Any):
        self._bridges[component_type] = bridge

    def register_adapter(self, component_id: str, adapter: Callable):
        self._adapters[component_id] = adapter

    def translate_message(self, component_type: str, message: Message) -> Any:
        bridge = self._bridges.get(component_type)
        if bridge and hasattr(bridge, 'translate'):
            return bridge.translate(message)
        return message

    def adapt_output(self, component_id: str, output: Any) -> Dict[str, Any]:
        adapter = self._adapters.get(component_id)
        if adapter:
            return adapter(output)
        return {"data": output}


class StandardNeuronContracts:
    @staticmethod
    def script_contract() -> ContractSpec:
        return ContractSpec(
            name="standard_script",
            version="1.0",
            input_schema=Schema(
                type="object",
                properties={
                    "script_path": {"type": "string"},
                    "parameters": {"type": "object"},
                    "context": {"type": "object"}
                },
                required=["script_path"]
            ),
            output_schema=Schema(
                type="object",
                properties={
                    "exit_code": {"type": "integer"},
                    "output": {"type": "string"},
                    "errors": {"type": "array"}
                },
                required=["exit_code"]
            )
        )

    @staticmethod
    def algorithm_contract() -> ContractSpec:
        return ContractSpec(
            name="standard_algorithm",
            version="1.0",
            input_schema=Schema(
                type="object",
                properties={
                    "algorithm_id": {"type": "string"},
                    "input_data": {"type": "object"},
                    "config": {"type": "object"}
                },
                required=["algorithm_id", "input_data"]
            ),
            output_schema=Schema(
                type="object",
                properties={
                    "result": {"type": "object"},
                    "metrics": {"type": "object"},
                    "execution_time_ms": {"type": "number"}
                },
                required=["result"]
            )
        )

    @staticmethod
    def skill_contract() -> ContractSpec:
        return ContractSpec(
            name="standard_skill",
            version="1.0",
            input_schema=Schema(
                type="object",
                properties={
                    "skill_name": {"type": "string"},
                    "task": {"type": "string"},
                    "parameters": {"type": "object"}
                },
                required=["skill_name", "task"]
            ),
            output_schema=Schema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "result": {"type": "object"},
                    "confidence": {"type": "number"}
                },
                required=["success"]
            )
        )

    @staticmethod
    def plugin_contract() -> ContractSpec:
        return ContractSpec(
            name="standard_plugin",
            version="1.0",
            input_schema=Schema(
                type="object",
                properties={
                    "plugin_id": {"type": "string"},
                    "action": {"type": "string"},
                    "params": {"type": "object"}
                },
                required=["plugin_id", "action"]
            ),
            output_schema=Schema(
                type="object",
                properties={
                    "status": {"type": "string"},
                    "data": {"type": "object"}
                },
                required=["status"]
            )
        )

    @staticmethod
    def cortex_module_contract() -> ContractSpec:
        return ContractSpec(
            name="cortex_module",
            version="1.0",
            input_schema=Schema(
                type="object",
                properties={
                    "module_name": {"type": "string"},
                    "operation": {"type": "string"},
                    "data": {"type": "object"}
                },
                required=["module_name", "operation"]
            ),
            output_schema=Schema(
                type="object",
                properties={
                    "output": {"type": "object"},
                    "state_changes": {"type": "array"},
                    "metrics": {"type": "object"}
                }
            )
        )


def create_protocol() -> InteropProtocol:
    protocol = InteropProtocol()
    protocol.register_contract(StandardNeuronContracts.script_contract())
    protocol.register_contract(StandardNeuronContracts.algorithm_contract())
    protocol.register_contract(StandardNeuronContracts.skill_contract())
    protocol.register_contract(StandardNeuronContracts.plugin_contract())
    protocol.register_contract(StandardNeuronContracts.cortex_module_contract())
    return protocol
