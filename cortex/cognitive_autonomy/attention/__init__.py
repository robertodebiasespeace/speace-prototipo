"""cortex.cognitive_autonomy.attention — Attention Gating (M5.11+)

M5.11: policy uniforme + salience-weighted (baseline).
M5.12: policy RL-driven con reward = ΔΦ(t) — TODO.
M5.13: diversity entropy check (≥ 1.0 bit) — integrated in AttentionGating.
"""

from .gating import (
    AttentionPolicy,
    AttentionStream,
    GatingResult,
    AttentionGating,
    create_uniform_gating,
    create_salience_gating,
)

__all__ = [
    "AttentionPolicy",
    "AttentionStream",
    "GatingResult",
    "AttentionGating",
    "create_uniform_gating",
    "create_salience_gating",
]
