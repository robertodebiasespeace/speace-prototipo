"""
cortex.cognitive_autonomy.temporal
====================================
M11.1 — Ritmi Bio-Temporali: CircadianOscillator per SPEACE.

Principio biologico:
  Il nucleo soprachiasmatico (SCN) dell'ipotalamo è il "pacemaker" biologico
  del cervello. Governa il ritmo circadiano (24h) e coordina:
    - Cicli sonno/veglia (melatonina, cortisolo)
    - Ritmi ultradiani (~90 min, cicli REM/NREM)
    - Oscillazioni di attenzione, memoria, plasticità
    - Immunità (sistema immunitario segue ritmo circadiano)
    - Metabolismo (sensibilità insulinica, gluconeogenesi)

  "The brain is not a static information processor but a temporal organ
   whose computations are organized along multiple nested time scales."
   — Buzsáki, "Rhythms of the Brain", 2006

  Principi estratti:
    1. Ritmo 24h (circadiano): processi cognitivi intensi al mattino,
       consolidamento al pomeriggio, riparazione/consolidamento di notte.
    2. Ritmo ultradiano (~90min): cicli di attenzione sostenuta vs riposo.
    3. Modulazione crono-dipendente: curiosity alta al mattino, plasticity
       alta nel pomeriggio, consolidamento/repair di notte.
    4. Segnali ormonali: cortisolo (mattino → allerta), melatonina
       (sera → sonnolenza), adenosina (accumulo di stanchezza).

Analogia SPEACE:
  CircadianOscillator produce un vettore di modulatori [0.0–1.0] che
  modifica i drive omeostatici in base alla "fase del ciclo":
    MORNING_PEAK  → curiosity_boost, exploration_bonus
    AFTERNOON     → standard processing, memory consolidation
    EVENING       → reduced energy, light consolidation
    NIGHT_VALLEY  → deep consolidation, repair, pruning
    ULTRADIAN_REST → brevi pause di 5-10 min ogni ~90 min

M11.1 | 2026-04-28
"""

from .circadian_oscillator import (
    CircadianOscillator,
    CircadianConfig,
    CircadianPhase,
    CircadianState,
    UltradianCycle,
)

__all__ = [
    "CircadianOscillator",
    "CircadianConfig",
    "CircadianPhase",
    "CircadianState",
    "UltradianCycle",
]
