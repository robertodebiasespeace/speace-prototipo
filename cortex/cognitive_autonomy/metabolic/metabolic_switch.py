"""
cortex.cognitive_autonomy.metabolic.metabolic_switch
=====================================================
M10.4 — MetabolicSwitch: regola quali moduli Cortex sono attivi
        in base all'energia disponibile.

Gerarchia di priorità moduli (ispirata a neurologia della sopravvivenza):
  SURVIVAL  (P0) — sempre attivi: homeostasis, safety, smfoi_kernel
  ESSENTIAL (P1) — attivi in REDUCED: energy_monitor, immune, predictive
  STANDARD  (P2) — attivi solo in NORMAL: memory, world_model, swarm
  EXPENSIVE (P3) — disabilitati per primi: curiosity, evolution, evolver

Transizioni:
  energy > HIGH_THRESHOLD  → NORMAL_METABOLISM
  energy > LOW_THRESHOLD   → REDUCED_METABOLISM  (se era NORMAL: hysteresis)
  energy ≤ LOW_THRESHOLD   → CONSERVATION

  Hysteresis (evita oscillazioni rapide):
    Per tornare a NORMAL da REDUCED serve energy > HIGH_THRESHOLD + 0.05
    Per tornare a REDUCED da CONSERVATION serve energy > LOW_THRESHOLD + 0.05

M10.4 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("speace.metabolic")


# ─────────────────────────────────────────────────────────────────────────────
# Costanti di priorità moduli
# ─────────────────────────────────────────────────────────────────────────────

# Mappa modulo → livello di priorità (0=sopravvivenza, 3=costoso)
MODULE_PRIORITY: Dict[str, int] = {
    # P0 — Survival: mai disabilitati
    "homeostatic_controller": 0,
    "safety_module":          0,
    "smfoi_kernel":           0,

    # P1 — Essential: disabilitati solo in CONSERVATION
    "energy_monitor":         1,
    "cognitive_immune":       1,
    "predictive_processor":   1,
    "event_bus":              1,

    # P2 — Standard: disabilitati in REDUCED e CONSERVATION
    "autobiographical_memory": 2,
    "world_model":             2,
    "swarm_orchestrator":      2,
    "consciousness_index":     2,

    # P3 — Expensive: disabilitati per primi (già in REDUCED)
    "curiosity_module":        3,
    "default_mode_network":    3,
    "evolver_heartbeat":       3,
    "mutation_engine":         3,
}


# ─────────────────────────────────────────────────────────────────────────────
# MetabolicMode — stati metabolici
# ─────────────────────────────────────────────────────────────────────────────

class MetabolicMode(str, Enum):
    NORMAL_METABOLISM  = "normal"      # energia > 50%: tutto attivo
    REDUCED_METABOLISM = "reduced"     # energia 25-50%: no P2, no P3
    CONSERVATION       = "conservation" # energia < 25%: solo P0 + P1


# ─────────────────────────────────────────────────────────────────────────────
# MetabolicProfile — snapshot del profilo metabolico corrente
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MetabolicProfile:
    """
    Snapshot del profilo metabolico corrente.

    Attributi:
        mode:            modalità metabolica corrente
        active_modules:  set di moduli attivi in questa modalità
        disabled_modules: set di moduli disabilitati
        energy_drive:    valore di energy al momento del calcolo
        estimated_load:  carico computazionale stimato (0.0→1.0)
        timestamp:       UNIX timestamp
    """
    mode:             MetabolicMode
    active_modules:   Set[str]
    disabled_modules: Set[str]
    energy_drive:     float
    estimated_load:   float
    timestamp:        float = field(default_factory=time.time)

    @property
    def active_count(self) -> int:
        return len(self.active_modules)

    @property
    def disabled_count(self) -> int:
        return len(self.disabled_modules)

    def is_active(self, module_id: str) -> bool:
        return module_id in self.active_modules

    def summary(self) -> str:
        return (
            f"[MetabolicProfile] mode={self.mode.value} "
            f"active={self.active_count} disabled={self.disabled_count} "
            f"energy={self.energy_drive:.2f} load≈{self.estimated_load:.2f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MetabolicSwitch — motore principale
# ─────────────────────────────────────────────────────────────────────────────

class MetabolicSwitch:
    """
    M10.4 — Regola i moduli attivi del Cortex in base all'energia disponibile.

    Implementa la flessibilità metabolica biologica:
    il cervello SPEACE riduce selettivamente l'attività dei moduli
    non essenziali quando l'energia è scarsa.

    Uso:
        switch = MetabolicSwitch()
        profile = switch.update(energy_drive=0.20)
        print(profile.summary())

        if not profile.is_active("curiosity_module"):
            # Non avviare esplorazione — modalità conservazione
            pass

    Uso con moduli personalizzati:
        custom_priorities = {**MODULE_PRIORITY, "my_module": 1}
        switch = MetabolicSwitch(module_priorities=custom_priorities)
    """

    # Soglie di transizione (con hysteresis)
    HIGH_THRESHOLD  = 0.50   # entra in NORMAL
    LOW_THRESHOLD   = 0.25   # entra in CONSERVATION
    HYSTERESIS      = 0.05   # banda morta per stabilità

    # Stima del carico computazionale per livello di priorità
    _LOAD_BY_PRIORITY = {0: 0.10, 1: 0.15, 2: 0.25, 3: 0.20}

    def __init__(
        self,
        module_priorities: Optional[Dict[str, int]] = None,
    ) -> None:
        self._priorities = module_priorities or dict(MODULE_PRIORITY)
        self._mode       = MetabolicMode.NORMAL_METABOLISM
        self._last_switch_time: float = 0.0
        self._switch_count: int = 0

    # ── API pubblica ──────────────────────────────────────────────────────────

    def update(self, energy_drive: float) -> MetabolicProfile:
        """
        Aggiorna la modalità metabolica in base all'energia.
        Applica hysteresis per evitare oscillazioni rapide.

        Args:
            energy_drive: valore energia in [0.0, 1.0]

        Returns:
            MetabolicProfile con la modalità e i moduli attivi
        """
        new_mode = self._compute_mode(energy_drive)
        if new_mode != self._mode:
            logger.info(
                "[MetabolicSwitch] %s → %s (energy=%.2f)",
                self._mode.value, new_mode.value, energy_drive
            )
            self._mode = new_mode
            self._last_switch_time = time.time()
            self._switch_count += 1

        return self._build_profile(energy_drive)

    @property
    def mode(self) -> MetabolicMode:
        return self._mode

    @property
    def switch_count(self) -> int:
        return self._switch_count

    def active_modules(self, energy_drive: Optional[float] = None) -> Set[str]:
        """
        Ritorna il set di moduli attivi per l'energia corrente.
        Se energy_drive è None, usa la modalità corrente senza aggiornare.
        """
        if energy_drive is not None:
            self.update(energy_drive)
        return self._compute_active_set(self._mode)

    def is_module_active(self, module_id: str, energy_drive: Optional[float] = None) -> bool:
        """Verifica se un modulo specifico è attivo."""
        active = self.active_modules(energy_drive)
        # Se il modulo non è nella mappa, default NORMAL_METABOLISM = attivo
        if module_id not in self._priorities:
            return True
        return module_id in active

    def add_module(self, module_id: str, priority: int) -> None:
        """Registra un nuovo modulo con la sua priorità."""
        if not 0 <= priority <= 3:
            raise ValueError(f"priority deve essere in [0,3], got {priority}")
        self._priorities[module_id] = priority

    # ── Metodi privati ────────────────────────────────────────────────────────

    def _compute_mode(self, energy_drive: float) -> MetabolicMode:
        """
        Calcola la nuova modalità con hysteresis.
        La banda morta evita oscillazioni rapide attorno alle soglie.
        """
        current = self._mode

        if current == MetabolicMode.NORMAL_METABOLISM:
            # Da NORMAL scende a REDUCED se energy < HIGH - hysteresis
            if energy_drive < self.HIGH_THRESHOLD - self.HYSTERESIS:
                if energy_drive <= self.LOW_THRESHOLD:
                    return MetabolicMode.CONSERVATION
                return MetabolicMode.REDUCED_METABOLISM
            return MetabolicMode.NORMAL_METABOLISM

        elif current == MetabolicMode.REDUCED_METABOLISM:
            # Da REDUCED sale a NORMAL se energy > HIGH + hysteresis
            if energy_drive > self.HIGH_THRESHOLD + self.HYSTERESIS:
                return MetabolicMode.NORMAL_METABOLISM
            # Da REDUCED scende a CONSERVATION se energy <= LOW - hysteresis
            if energy_drive <= self.LOW_THRESHOLD - self.HYSTERESIS:
                return MetabolicMode.CONSERVATION
            return MetabolicMode.REDUCED_METABOLISM

        else:  # CONSERVATION
            # Da CONSERVATION sale a REDUCED se energy > LOW + hysteresis
            if energy_drive > self.LOW_THRESHOLD + self.HYSTERESIS:
                if energy_drive > self.HIGH_THRESHOLD + self.HYSTERESIS:
                    return MetabolicMode.NORMAL_METABOLISM
                return MetabolicMode.REDUCED_METABOLISM
            return MetabolicMode.CONSERVATION

    def _compute_active_set(self, mode: MetabolicMode) -> Set[str]:
        """
        Calcola il set di moduli attivi per una data modalità.

        NORMAL       → P0 + P1 + P2 + P3 (tutti)
        REDUCED      → P0 + P1 (no P2, no P3)
        CONSERVATION → P0 solo
        """
        if mode == MetabolicMode.NORMAL_METABOLISM:
            max_priority = 3
        elif mode == MetabolicMode.REDUCED_METABOLISM:
            max_priority = 1
        else:  # CONSERVATION
            max_priority = 0

        return {
            mod for mod, pri in self._priorities.items()
            if pri <= max_priority
        }

    def _estimate_load(self, active: Set[str]) -> float:
        """Stima il carico computazionale normalizzato per i moduli attivi."""
        total = 0.0
        for mod in active:
            pri = self._priorities.get(mod, 2)
            total += self._LOAD_BY_PRIORITY.get(pri, 0.15)
        # Normalizza: carico massimo teorico (tutti i moduli P0-P3)
        max_load = sum(self._LOAD_BY_PRIORITY.get(pri, 0.15)
                       for pri in self._priorities.values())
        if max_load == 0:
            return 0.0
        return min(1.0, total / max_load)

    def _build_profile(self, energy_drive: float) -> MetabolicProfile:
        """Costruisce il MetabolicProfile corrente."""
        active   = self._compute_active_set(self._mode)
        disabled = set(self._priorities.keys()) - active
        load     = self._estimate_load(active)

        return MetabolicProfile(
            mode=self._mode,
            active_modules=active,
            disabled_modules=disabled,
            energy_drive=energy_drive,
            estimated_load=round(load, 3),
        )


__all__ = [
    "MetabolicSwitch",
    "MetabolicMode",
    "MetabolicProfile",
    "MODULE_PRIORITY",
]
