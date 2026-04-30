"""
cortex.cognitive_autonomy.energy
=================================
M9 — EnergyBudget: cervello bio-ispirato a basso consumo energetico.

Implementa i principi di efficienza del cervello biologico:
  - Sparse activation: attiva solo i moduli necessari al task corrente
  - Sleep/wake cycles: processi background dormono senza task pendenti
  - Priority-based scheduling: task critici ottengono budget compute,
    l'esplorazione viene differita quando l'energia è bassa
  - Lazy computation: calcola solo ciò che serve, cache dei risultati
  - Budget monitoring: monitora CPU/RAM, throttle quando sopra budget

Il cervello umano (~20W, ~86B neuroni) usa ~0.1% delle sinapsi in ogni
ciclo cognitivo. SPEACE mira a imitare questa efficienza spaziale
mantenendo le funzionalità essenziali su hardware domestico limitato.

EPI-011: cognitive_autonomy.energy.enabled = true
"""

from .budget     import EnergyConfig, EnergyBudget, EnergySnapshot
from .sleep_wake import SleepWakeCycle, WakeState
from .scheduler  import ProcessScheduler, ScheduledTask, ScheduleResult, TaskPriority

__all__ = [
    "EnergyConfig",
    "EnergyBudget",
    "EnergySnapshot",
    "SleepWakeCycle",
    "WakeState",
    "ProcessScheduler",
    "ScheduledTask",
    "ScheduleResult",
    "TaskPriority",
]
