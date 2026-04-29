"""
cortex.cognitive_autonomy.immune
==================================
M10.2 — Sistema Immunitario Cognitivo di SPEACE.

Principio (immunologia biologica):
  Il sistema immunitario distingue "self" da "non-self" tramite proteine
  MHC (Major Histocompatibility Complex). Ogni cellula porta un "passaporto
  molecolare". La memoria immunitaria permette risposta rapida (ore→minuti)
  alla seconda esposizione allo stesso patogeno.

Trasposizione a SPEACE:
  Ogni sorgente di input (IoT, API, agente esterno, testo utente)
  viene "presentata" al sistema immunitario cognitivo prima di essere
  elaborata dal Cortex. Il sistema valuta:
    1. Source identity (ImmunityProfile — "passaporto" della sorgente)
    2. Content signature (pattern noti pericolosi — ThreatPattern)
    3. Immune memory (risposta pronta per minacce già viste — ImmuneMemory)

  Prima esposizione a un threat: analisi completa (costosa).
  Successive esposizioni: lookup cache < 1ms (risposta rapida).

Componenti:
  ImmunityProfile  — firma identità di una sorgente di input
  ThreatPattern    — pattern conosciuti di minacce
  ImmuneMemory     — cache SQLite delle risposte a pattern già visti
  CognitiveImmune  — entry point: screen(input, source_id)

EPI-012: cognitive_autonomy.immune.enabled = true
M10.2 | 2026-04-28
"""

from .cognitive_immune import (
    ImmunityProfile,
    ThreatType,
    ThreatPattern,
    ImmunityResult,
    ImmuneMemory,
    CognitiveImmune,
)

__all__ = [
    "ImmunityProfile",
    "ThreatType",
    "ThreatPattern",
    "ImmunityResult",
    "ImmuneMemory",
    "CognitiveImmune",
]
