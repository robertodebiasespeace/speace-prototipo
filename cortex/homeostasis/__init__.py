"""
cortex.homeostasis
===================
M14.5 — Moduli omeostatici di SPEACE.

Espone:
  KineticFlow        — flusso energetico inter-lobo (Homeodyna + Kinetica)
  KineticFlowConfig  — parametri del modello
  KineticFlowResult  — output di un tick
  LobeState          — stato energetico di un lobo
  DEFAULT_LOBES      — topologia lobi default (5 lobi cerebrali)
  DEFAULT_CONNECTIONS — connessioni inter-lobo default
"""

from .kinetic_flow import (
    KineticFlow,
    KineticFlowConfig,
    KineticFlowResult,
    LobeState,
    DEFAULT_LOBES,
    DEFAULT_CONNECTIONS,
)

__all__ = [
    "KineticFlow",
    "KineticFlowConfig",
    "KineticFlowResult",
    "LobeState",
    "DEFAULT_LOBES",
    "DEFAULT_CONNECTIONS",
]
