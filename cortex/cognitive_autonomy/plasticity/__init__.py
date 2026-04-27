"""cortex.cognitive_autonomy.plasticity — Plasticità strutturale (M5.14+)

M5.14: EdgePruner conservativo (decadimento peso + rimozione sotto soglia).
M5.15: EdgeGrower via SafeProactive HIGH (co-attivazione → proposta arco).
M5.16: PlasticityLogger su mesh_state.jsonl.
"""

from .edge_pruning import (
    PlasticityLogger,
    PrunerConfig, EdgePruner,
    GrowthConfig, EdgeGrower,
    create_plasticity_layer,
)

__all__ = [
    "PlasticityLogger",
    "PrunerConfig", "EdgePruner",
    "GrowthConfig", "EdgeGrower",
    "create_plasticity_layer",
]
