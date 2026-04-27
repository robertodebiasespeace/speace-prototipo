"""
SPEACE Neural Engine - Package Init
Neural Engine per SPEACE: grafo computazionale tipizzato e adattivo.
"""

from .neuron_base import (
    BaseNeuron,
    NeuronType,
    NeuronState,
    NeuronMetadata,
    Contract,
    Port,
    ExecutionContext,
    SignalType,
    NeuronFactory
)

from .graph_core import (
    ComputationalGraph,
    Edge,
    EdgeType,
    GraphMetadata,
    GraphState
)

from .protocol import (
    InteropProtocol,
    Message,
    MessageType,
    ContractSpec,
    Schema,
    ExecutionTicket,
    ValidationLevel,
    ComponentBridge,
    StandardNeuronContracts,
    create_protocol
)

from .synapse import (
    Synapse,
    SynapseManager,
    SynapticPlasticity,
    Signal,
    SynapseState,
    SynapseStrength
)

from .plasticity import (
    StructuralPlasticity,
    PlasticityRule,
    PlasticityEvent,
    FitnessScore
)

from .execution_engine import (
    ExecutionEngine,
    ExecutionJob,
    ExecutionState,
    Priority,
    ResourceMonitor,
    ValidationResult
)

from .evolution_engine import (
    EvolutionEngine,
    Need,
    NeedCategory,
    NeedState,
    Task,
    EvolutionObjective,
    SPEACEObjectives
)

from .environment_sensor import (
    EnvironmentSensor,
    EnvironmentalFactor,
    EnvironmentalReport,
    Constraint,
    Opportunity,
    EnvironmentDomain,
    NatureSensor,
    HumanSocietySensor,
    TechnologySensor,
    GovernanceSensor,
    LawSensor
)

from .load_balancer import (
    LoadBalancer,
    LoadLevel,
    ResourceType,
    ResourceMetrics,
    SystemLoad,
    ThrottleConfig
)

__version__ = "1.0.0"
__all__ = [
    "BaseNeuron",
    "NeuronType",
    "NeuronState",
    "Contract",
    "Port",
    "ExecutionContext",
    "ComputationalGraph",
    "Edge",
    "EdgeType",
    "InteropProtocol",
    "Message",
    "ContractSpec",
    "ExecutionTicket",
    "SynapseManager",
    "SynapticPlasticity",
    "StructuralPlasticity",
    "ExecutionEngine",
    "EvolutionEngine",
    "Need",
    "Task",
    "EnvironmentSensor",
    "LoadBalancer",
    "create_protocol",
    "SPEACEObjectives"
]
