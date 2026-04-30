"""
cortex.cognitive_autonomy.energy.sleep_wake
============================================
M9 — SleepWakeCycle: ciclo sonno-veglia bio-ispirato per SPEACE.

Principio biologico:
  Il cervello non è mai completamente "off", ma cicla attraverso stati
  metabolicamente distinti:
    - AWAKE (veglia):     elaborazione attiva, alta frequenza neurale
    - IDLE (riposo):      ridotta attività, consolidamento memoria
    - DEEP_SLEEP (sonno): minimo consumo, manutenzione strutturale

SPEACE implementa questi stati per adattare il ritmo dei propri cicli
cognitivi (heartbeat SMFOI) in base all'energia disponibile e alla
presenza di task.

Transizioni di stato (isteresi per evitare oscillazioni):
  AWAKE      → IDLE       se energy_drive < sleep_threshold    (default 0.30)
  IDLE       → DEEP_SLEEP se energy_drive < deep_sleep_threshold (default 0.10)
  DEEP_SLEEP → IDLE       se energy_drive > wake_threshold * 0.5
  IDLE       → AWAKE      se energy_drive > wake_threshold     (default 0.55)
              O se has_pending_tasks=True (risveglio per urgenza)

M9 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .budget import EnergyConfig

logger = logging.getLogger("speace.cognitive_autonomy.energy.sleep_wake")


# ─────────────────────────────────────────────────────────────────────────────
# WakeState — stati del ciclo sonno-veglia
# ─────────────────────────────────────────────────────────────────────────────

class WakeState(str, Enum):
    AWAKE      = "awake"       # elaborazione attiva
    IDLE       = "idle"        # riposo leggero, heartbeat ridotto
    DEEP_SLEEP = "deep_sleep"  # manutenzione minima, solo safety attiva


# ─────────────────────────────────────────────────────────────────────────────
# SleepWakeCycle
# ─────────────────────────────────────────────────────────────────────────────

class SleepWakeCycle:
    """
    M9 — Gestisce il ciclo sonno-veglia di SPEACE.

    Decide in base all'energy_drive (da DriveExecutive/HomeostaticController)
    se il sistema deve essere attivo, in riposo, o in sleep profondo.

    Effetti pratici:
      AWAKE:      heartbeat normale (60s), tutte le feature attive
      IDLE:       heartbeat ridotto (300s), esplorazione sospesa
      DEEP_SLEEP: heartbeat minimo (900s), solo safety + homeostasis attivi

    Uso:
        cycle = SleepWakeCycle(config)
        state = cycle.tick(energy_drive=0.25, has_pending_tasks=False)
        interval = cycle.heartbeat_interval()
        if cycle.should_skip_exploration():
            ...
    """

    def __init__(self, config: Optional[EnergyConfig] = None) -> None:
        self.config = config or EnergyConfig()
        self._state:         WakeState = WakeState.AWAKE
        self._state_since:   float     = time.monotonic()
        self._transitions:   int       = 0
        self._last_energy:   float     = 1.0

    # ── Stato corrente ────────────────────────────────────────────────────────

    @property
    def state(self) -> WakeState:
        return self._state

    @property
    def state_duration_s(self) -> float:
        """Secondi trascorsi nello stato corrente."""
        return time.monotonic() - self._state_since

    # ── Tick — transizione di stato ───────────────────────────────────────────

    def tick(self, energy_drive: float, has_pending_tasks: bool = False) -> WakeState:
        """
        Valuta se cambiare stato in base all'energy_drive e alla presenza
        di task pendenti. Applica isteresi per evitare oscillazioni rapide.

        Args:
            energy_drive:      valore [0,1] da HomeostaticController/DriveExecutive
            has_pending_tasks: se True, forza risveglio anche in idle

        Returns:
            WakeState corrente dopo la transizione (se avvenuta)
        """
        self._last_energy = energy_drive
        old_state = self._state

        # ── Transizioni ───────────────────────────────────────────────────────
        if self._state == WakeState.AWAKE:
            if energy_drive < self.config.sleep_threshold:
                self._transition(WakeState.IDLE)

        elif self._state == WakeState.IDLE:
            if energy_drive < self.config.deep_sleep_threshold:
                self._transition(WakeState.DEEP_SLEEP)
            elif energy_drive > self.config.wake_threshold or has_pending_tasks:
                self._transition(WakeState.AWAKE)

        elif self._state == WakeState.DEEP_SLEEP:
            # Risveglio parziale solo se energia torna sopra metà soglia
            partial_wake = self.config.wake_threshold * 0.5
            if energy_drive > partial_wake or has_pending_tasks:
                self._transition(WakeState.IDLE)

        if self._state != old_state:
            logger.info(
                "[SleepWakeCycle] %s → %s (energy=%.2f pending=%s)",
                old_state.value, self._state.value,
                energy_drive, has_pending_tasks,
            )

        return self._state

    def _transition(self, new_state: WakeState) -> None:
        self._state      = new_state
        self._state_since = time.monotonic()
        self._transitions += 1

    # ── Effetti comportamentali ───────────────────────────────────────────────

    def heartbeat_interval(self) -> float:
        """
        Ritorna l'intervallo di heartbeat SMFOI in secondi
        basato sullo stato corrente.
        """
        return {
            WakeState.AWAKE:      self.config.active_heartbeat_s,
            WakeState.IDLE:       self.config.idle_heartbeat_s,
            WakeState.DEEP_SLEEP: self.config.deep_sleep_heartbeat_s,
        }[self._state]

    def should_skip_exploration(self) -> bool:
        """
        True se l'esplorazione autonoma deve essere sospesa.
        In IDLE e DEEP_SLEEP, le task esplorative vengono differite
        per conservare energia.
        """
        if not self.config.defer_exploration_in_idle:
            return False
        return self._state in (WakeState.IDLE, WakeState.DEEP_SLEEP)

    def should_skip_nonessential(self) -> bool:
        """
        True se solo i processi essenziali (safety, homeostasis) devono girare.
        Attivo solo in DEEP_SLEEP.
        """
        if not self.config.skip_nonessential_in_sleep:
            return False
        return self._state == WakeState.DEEP_SLEEP

    def is_awake(self) -> bool:
        return self._state == WakeState.AWAKE

    # ── Metriche ─────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "state":           self._state.value,
            "state_duration_s": round(self.state_duration_s, 1),
            "last_energy":     round(self._last_energy, 3),
            "transitions":     self._transitions,
            "heartbeat_s":     self.heartbeat_interval(),
            "skip_exploration": self.should_skip_exploration(),
            "skip_nonessential": self.should_skip_nonessential(),
        }


__all__ = ["WakeState", "SleepWakeCycle"]
