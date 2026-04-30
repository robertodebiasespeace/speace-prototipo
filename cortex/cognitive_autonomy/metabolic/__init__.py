"""
cortex.cognitive_autonomy.metabolic
=====================================
M10.4 — MetabolicSwitch: flessibilità metabolica per SPEACE.

Principio biologico:
  Il cervello umano consuma ~20% dell'energia del corpo a riposo.
  In condizioni di scarsità (digiuno, stress), il metabolismo cerebrale
  fa uno "switch" dal glucosio ai corpi chetonici (flessibilità metabolica).
  Questo riduce il consumo energetico del 30-40% mantenendo le funzioni
  cognitive essenziali (sopravvivenza prioritaria).

  Effetti dello switch metabolico:
    - Riduzione dell'attività delle aree non essenziali (cortex prefrontale
      per pianificazione a lungo termine, default mode network per wandering)
    - Mantenimento delle aree di sopravvivenza (amigdala, sistema limbico,
      brainstem per funzioni vitali)
    - Upregulation dell'BDNF (fattore neurotrofico — "riparazioni efficienti")

Analogia SPEACE:
  MetabolicSwitch regola quali moduli del Cortex sono ATTIVI in base
  all'energia disponibile:

    NORMAL_METABOLISM  (energy > 0.50): tutti i 9 comparti attivi
    REDUCED_METABOLISM (energy 0.25–0.50): disabilita moduli non essenziali
    CONSERVATION       (energy < 0.25): solo moduli sopravvivenza + safety

M10.4 | 2026-04-28
"""

from .metabolic_switch import (
    MetabolicSwitch,
    MetabolicMode,
    MetabolicProfile,
    MODULE_PRIORITY,
)

__all__ = [
    "MetabolicSwitch",
    "MetabolicMode",
    "MetabolicProfile",
    "MODULE_PRIORITY",
]
