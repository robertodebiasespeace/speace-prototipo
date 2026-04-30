"""
cortex.cognitive_autonomy.sparse
==================================
M15.1 — Sparse Activation Engine: sparse coding bio-ispirato.

Principio biologico: solo 1-5% dei neuroni attivi per ciclo.
Riduzione energetica stimata: ~80-95% rispetto a full activation.
"""

from .sparse_activation import (
    SparseActivationEngine,
    SparseConfig,
    SparseResult,
    ModuleUnit,
)

__all__ = [
    "SparseActivationEngine",
    "SparseConfig",
    "SparseResult",
    "ModuleUnit",
]
