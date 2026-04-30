"""
cortex.cognitive_autonomy.criticality
======================================
M13.0 — CriticalityController: Self-Organized Criticality (SOC).

Mantiene SPEACE nella zona critica ottimale tra ordine e caos,
massimizzando la capacità cognitiva (Beggs & Plenz 2003).
"""

from .criticality_controller import (
    CriticalityController,
    CriticalityConfig,
    CriticalityState,
    CriticalityZone,
    ModulationSuggestion,
)

__all__ = [
    "CriticalityController",
    "CriticalityConfig",
    "CriticalityState",
    "CriticalityZone",
    "ModulationSuggestion",
]
