"""
SPEACE Cortex Mesh — OLC (Organism Language Contract)

Registry autoritativo dei tipi scambiabili fra neuroni della Continuous Neural Mesh.

Import dell'OLC → popolamento automatico del registry con i 12 tipi fondamentali
(SPEC_NEURON_CONTRACT.md §2.1).

API pubblica:
    from cortex.mesh.olc import (
        OLCBase, OLCValidationError, OLC_CONTRACT_VERSION, NEEDS_CATALOG,
        register, lookup, require, all_types, names, check_compatibility, snapshot,
        SensoryFrame, InterpretationFrame, WorldSnapshot, DecisionFrame,
        SafetyVerdict, ActionResult, MemoryDelta, ReflectionFrame,
        MutationProposal, NeedsSnapshot, FeedbackFrame, TaskProposal,
        ALL_TYPES,
    )

Milestone: M4.3 (PROP-CORTEX-NEURAL-MESH-M4)
"""

from .base import (
    OLCBase,
    OLCValidationError,
    OLC_CONTRACT_VERSION,
    NEEDS_CATALOG,
    register_olc_type,
    iso_now,
)
from .registry import (
    register,
    lookup,
    require,
    all_types,
    names,
    check_compatibility,
    snapshot,
)

# l'import di `types` popola il registry via decoratore @_reg
from .types import (
    SensoryFrame,
    InterpretationFrame,
    WorldSnapshot,
    DecisionFrame,
    SafetyVerdict,
    ActionResult,
    MemoryDelta,
    ReflectionFrame,
    MutationProposal,
    NeedsSnapshot,
    FeedbackFrame,
    TaskProposal,
    ALL_TYPES,
)

__all__ = [
    "OLCBase",
    "OLCValidationError",
    "OLC_CONTRACT_VERSION",
    "NEEDS_CATALOG",
    "register_olc_type",
    "iso_now",
    "register",
    "lookup",
    "require",
    "all_types",
    "names",
    "check_compatibility",
    "snapshot",
    "SensoryFrame",
    "InterpretationFrame",
    "WorldSnapshot",
    "DecisionFrame",
    "SafetyVerdict",
    "ActionResult",
    "MemoryDelta",
    "ReflectionFrame",
    "MutationProposal",
    "NeedsSnapshot",
    "FeedbackFrame",
    "TaskProposal",
    "ALL_TYPES",
]
