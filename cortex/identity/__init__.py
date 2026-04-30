"""
cortex.identity
================
M14.3 — Identità narrativa persistente di SPEACE.

Espone:
  PersistentIdentity   — classe principale (storage JSON, tick, achievements)
  Achievement          — dataclass di una realizzazione
  EmergencePoint       — dataclass di uno snapshot history
"""

from .persistent_identity import (
    PersistentIdentity,
    Achievement,
    EmergencePoint,
    DEFAULT_CORE_VALUES,
    ACHIEVEMENT_EMERGENCE_THRESHOLD,
)

__all__ = [
    "PersistentIdentity",
    "Achievement",
    "EmergencePoint",
    "DEFAULT_CORE_VALUES",
    "ACHIEVEMENT_EMERGENCE_THRESHOLD",
]
