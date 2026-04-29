"""
cortex.cognitive_autonomy.energy.scheduler
===========================================
M9 — ProcessScheduler: schedulazione bio-ispirata a basso consumo.

Principio biologico:
  Il cervello biologico usa attenzione selettiva e gating per decidere
  quali circuiti attivare in ogni momento. Non tutti i pensieri avvengono
  in parallelo: c'è un bottleneck attentivo (global workspace theory).

SPEACE implementa un scheduler che:
  1. Assegna priorità energetica a ogni task (essenziale > normale > esplorativa)
  2. Verifica il budget disponibile prima di ogni attivazione
  3. Differisce o scarta i task non essenziali in stati di bassa energia
  4. Rispetta il ciclo sonno-veglia (SleepWakeCycle)

Categorie di priorità (ispirate alla Maslow per i processi AI):
  CRITICAL  (P0): safety, homeostasis, self-repair → sempre eseguiti
  HIGH      (P1): planning, memory consolidation → eseguiti se awake/idle
  NORMAL    (P2): reasoning, communication → eseguiti se awake
  LOW       (P3): exploration, curiosity, learning → eseguiti solo se awake+energia alta

M9 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set

from .budget     import EnergyBudget, EnergyConfig
from .sleep_wake import SleepWakeCycle, WakeState

logger = logging.getLogger("speace.cognitive_autonomy.energy.scheduler")


# ─────────────────────────────────────────────────────────────────────────────
# TaskPriority — livelli di priorità energetica
# ─────────────────────────────────────────────────────────────────────────────

class TaskPriority(IntEnum):
    CRITICAL   = 0   # sempre eseguito (safety, repair)
    HIGH       = 1   # eseguito in AWAKE + IDLE
    NORMAL     = 2   # eseguito solo in AWAKE
    LOW        = 3   # eseguito solo in AWAKE con energia > 0.5
    EXPLORATORY = 4  # eseguito solo se SleepWakeCycle non blocca esplorazione


# ─────────────────────────────────────────────────────────────────────────────
# ScheduledTask — descrizione di un task da schedulare
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScheduledTask:
    """
    Descrizione di un task da passare al ProcessScheduler.

    Attributi:
        id:          identificatore univoco
        description: descrizione human-readable
        priority:    TaskPriority (default NORMAL)
        tags:        set di tag per filtri rapidi (es. "safety", "explore")
        estimated_cpu_pct:  carico CPU stimato (default: usa cpu_per_neuron)
        estimated_memory_mb: RAM stimata (default: usa memory_per_neuron)
    """
    id:                  str
    description:         str
    priority:            TaskPriority = TaskPriority.NORMAL
    tags:                Set[str]     = field(default_factory=set)
    estimated_cpu_pct:   float        = 0.0   # 0 = usa default config
    estimated_memory_mb: float        = 0.0   # 0 = usa default config

    @property
    def is_critical(self) -> bool:
        return self.priority == TaskPriority.CRITICAL

    @property
    def is_exploratory(self) -> bool:
        return self.priority == TaskPriority.EXPLORATORY or "explore" in self.tags


# ─────────────────────────────────────────────────────────────────────────────
# ScheduleResult — esito della decisione di scheduling
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScheduleResult:
    """Esito della valutazione di un task da parte del ProcessScheduler."""
    task_id:     str
    approved:    bool
    reason:      str   # spiegazione della decisione
    wake_state:  str   # stato SleepWakeCycle al momento della decisione
    energy_at:   float # energy_drive al momento della decisione
    deferred:    bool  # True se task differito (non scartato definitivamente)

    def to_dict(self) -> dict:
        return {
            "task_id":    self.task_id,
            "approved":   self.approved,
            "reason":     self.reason,
            "wake_state": self.wake_state,
            "energy_at":  round(self.energy_at, 3),
            "deferred":   self.deferred,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ProcessScheduler — cuore dello scheduling bio-ispirato
# ─────────────────────────────────────────────────────────────────────────────

class ProcessScheduler:
    """
    M9 — Scheduler bio-ispirato per i processi di SPEACE.

    Integra EnergyBudget + SleepWakeCycle per decidere se e quando
    eseguire ogni processo del Cortex.

    Schema decisionale (ispirato al gating talamo-corticale):

        task CRITICAL    → sempre APPROVED (bypass budget)
        task HIGH        → APPROVED in AWAKE/IDLE, DEFERRED in DEEP_SLEEP
        task NORMAL      → APPROVED solo in AWAKE, DEFERRED altrimenti
        task LOW         → APPROVED in AWAKE + energy > 0.5, altrimenti DEFERRED
        task EXPLORATORY → APPROVED solo se !should_skip_exploration()
                           + budget disponibile

    Uso:
        scheduler = ProcessScheduler(budget, sleep_cycle)
        result = scheduler.evaluate(task, energy_drive=0.4)
        if result.approved:
            run_task(task)
        else:
            deferred_queue.append(task)
    """

    def __init__(
        self,
        budget:      Optional[EnergyBudget]      = None,
        sleep_cycle: Optional[SleepWakeCycle]    = None,
        config:      Optional[EnergyConfig]      = None,
    ) -> None:
        self.config      = config or EnergyConfig()
        self.budget      = budget or EnergyBudget(self.config)
        self.sleep_cycle = sleep_cycle or SleepWakeCycle(self.config)
        self._deferred:  List[ScheduledTask] = []
        self._history:   List[ScheduleResult] = []

    # ── API pubblica ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        task:         ScheduledTask,
        energy_drive: float = 0.8,
        has_pending:  bool  = False,
    ) -> ScheduleResult:
        """
        Valuta se il task può essere eseguito ora.

        Aggiorna il ciclo sonno-veglia con l'energy_drive corrente,
        poi applica le regole di priorità.

        Args:
            task:         il task da valutare
            energy_drive: livello di energia [0,1] da DriveExecutive
            has_pending:  se True, considera task pendenti urgenti

        Returns:
            ScheduleResult con approved=True/False e motivazione.
        """
        # Aggiorna stato sonno-veglia
        wake = self.sleep_cycle.tick(energy_drive, has_pending)
        self.budget.apply_behavioral_limits(energy_drive, repair_mode=(energy_drive < 0.3))

        approved, reason, deferred = self._decide(task, wake, energy_drive)

        result = ScheduleResult(
            task_id    = task.id,
            approved   = approved,
            reason     = reason,
            wake_state = wake.value,
            energy_at  = energy_drive,
            deferred   = deferred,
        )
        self._history.append(result)

        if deferred:
            self._deferred.append(task)
            logger.debug("[Scheduler] DEFERRED %s: %s", task.id, reason)
        elif approved:
            self.budget.activate(task.id)
            logger.debug("[Scheduler] APPROVED %s (energy=%.2f wake=%s)",
                         task.id, energy_drive, wake.value)
        else:
            logger.debug("[Scheduler] REJECTED %s: %s", task.id, reason)

        return result

    def release(self, task_id: str) -> None:
        """Notifica al budget che il task ha terminato."""
        self.budget.deactivate(task_id)

    def flush_deferred(self, energy_drive: float) -> List[ScheduledTask]:
        """
        Tenta di rieseguire i task differiti con l'energia corrente.
        Ritorna i task che ora possono essere eseguiti.
        """
        runnable: List[ScheduledTask] = []
        still_deferred: List[ScheduledTask] = []

        for task in self._deferred:
            result = self.evaluate(task, energy_drive)
            if result.approved:
                runnable.append(task)
            else:
                still_deferred.append(task)

        self._deferred = still_deferred
        return runnable

    # ── Logica di decisione ───────────────────────────────────────────────────

    def _decide(
        self,
        task:         ScheduledTask,
        wake:         WakeState,
        energy_drive: float,
    ) -> tuple[bool, str, bool]:
        """
        Restituisce (approved, reason, deferred).
        deferred=True → task rimandato (non scartato)
        """

        # P0: CRITICAL — bypass totale
        if task.priority == TaskPriority.CRITICAL:
            return True, "CRITICAL: bypass budget garantito", False

        # Deep sleep: solo CRITICAL passano
        if wake == WakeState.DEEP_SLEEP:
            if self.sleep_cycle.should_skip_nonessential():
                return False, f"DEEP_SLEEP: task non essenziale differito", True

        # P4: EXPLORATORY — bloccato se esplorazione sospesa
        if task.is_exploratory and self.sleep_cycle.should_skip_exploration():
            return False, (
                f"IDLE/SLEEP: esplorazione sospesa (energy={energy_drive:.2f})"
            ), True

        # P1 HIGH: passa in AWAKE e IDLE, bloccato in DEEP_SLEEP
        if task.priority == TaskPriority.HIGH:
            if wake in (WakeState.AWAKE, WakeState.IDLE):
                ok = self.budget.can_activate(task.id)
                return (ok, "HIGH: budget disponibile" if ok else "HIGH: budget esaurito", not ok)
            return False, "HIGH: DEEP_SLEEP attivo", True

        # P2 NORMAL: solo in AWAKE
        if task.priority == TaskPriority.NORMAL:
            if wake != WakeState.AWAKE:
                return False, f"NORMAL: sistema in {wake.value}", True
            ok = self.budget.can_activate(task.id)
            return (ok, "NORMAL: budget ok" if ok else "NORMAL: budget esaurito", not ok)

        # P3 LOW: solo in AWAKE con energia sufficiente
        if task.priority == TaskPriority.LOW:
            if wake != WakeState.AWAKE:
                return False, f"LOW: sistema in {wake.value}", True
            if energy_drive < 0.5:
                return False, f"LOW: energia insufficiente ({energy_drive:.2f} < 0.5)", True
            ok = self.budget.can_activate(task.id)
            return (ok, "LOW: approvato" if ok else "LOW: budget esaurito", not ok)

        # Fallback (EXPLORATORY in stato AWAKE)
        ok = self.budget.can_activate(task.id)
        return (ok, "EXPLORATORY: approvato" if ok else "EXPLORATORY: budget esaurito", not ok)

    # ── Metriche ─────────────────────────────────────────────────────────────

    @property
    def deferred_count(self) -> int:
        return len(self._deferred)

    def get_status(self) -> dict:
        recent = self._history[-20:] if self._history else []
        approved = sum(1 for r in recent if r.approved)
        return {
            "sleep_wake":     self.sleep_cycle.get_status(),
            "budget":         self.budget.get_metrics(),
            "deferred_tasks": self.deferred_count,
            "recent_approved_rate": (
                approved / len(recent) if recent else 1.0
            ),
            "total_decisions": len(self._history),
        }


__all__ = ["TaskPriority", "ScheduledTask", "ScheduleResult", "ProcessScheduler"]
