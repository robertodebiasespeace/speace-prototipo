"""
cortex.cognitive_autonomy.energy.budget
========================================
M9 — EnergyBudget: gestione del budget energetico-computazionale di SPEACE.

Principio bio-ispirato:
  Il cervello biologico alloca risorse in modo dinamico e parsimonioso.
  Neuroni non attivi consumano pochissimo (potenziale di riposo ~-70mV).
  Solo i circuiti rilevanti per il task corrente vengono attivati
  (principio di sparse coding: ~1-5% dei neuroni attivi in ogni momento).

Implementazione:
  - EnergyConfig: soglie e limiti configurabili (epigenome-driven)
  - EnergyBudget: monitora consumi stimati e decide se attivare un modulo
  - EnergySnapshot: stato istantaneo del budget (immutabile, serializzabile)

Nota: i valori CPU/RAM sono STIME CONSERVATIVE. Non usiamo psutil per
non aggiungere dipendenze pesanti — usiamo un modello di contabilità
interna basato sui task schedulati (accounting-based budget).

M9 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("speace.cognitive_autonomy.energy.budget")


# ─────────────────────────────────────────────────────────────────────────────
# EnergyConfig — parametri configurabili (driven da epigenome.yaml)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnergyConfig:
    """
    Configurazione del budget energetico-computazionale di SPEACE.

    Tutti i valori sono calibrati per hardware domestico (16 GB RAM,
    CPU quad-core con carico misto). Modificabili via epigenome.yaml
    (EPI-011 block: cognitive_autonomy.energy).
    """

    # ── CPU budget ────────────────────────────────────────────────────────────
    cpu_budget_pct: float    = 35.0   # % CPU max per processi SPEACE background
    cpu_per_neuron: float    = 5.0    # % CPU stimata per ogni neurone attivo
    max_parallel_neurons: int = 2     # neuroni attivi contemporaneamente

    # ── Memory budget ─────────────────────────────────────────────────────────
    memory_budget_mb: float  = 512.0  # RAM max per SPEACE agent (MB)
    memory_per_neuron: float = 48.0   # RAM stimata per neurone (MB, include modello)

    # ── Sleep/wake thresholds ─────────────────────────────────────────────────
    sleep_threshold: float   = 0.30   # energy_drive sotto questa soglia → idle
    deep_sleep_threshold: float = 0.10  # energy_drive sotto questa → deep sleep
    wake_threshold: float    = 0.55   # energy_drive sopra questa → risveglio

    # ── Heartbeat intervals (secondi) ─────────────────────────────────────────
    active_heartbeat_s: float    = 60.0   # ciclo normale
    idle_heartbeat_s: float      = 300.0  # ciclo ridotto (idle)
    deep_sleep_heartbeat_s: float = 900.0  # ciclo minimo (deep sleep ~15 min)

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_ttl_s: float           = 300.0   # TTL cache risultati (5 min)
    enable_result_cache: bool    = True

    # ── Comportamenti adattativi ──────────────────────────────────────────────
    defer_exploration_in_idle: bool = True   # blocca task esplorative in idle
    skip_nonessential_in_sleep: bool = True  # salta tutto tranne safety in deep sleep
    log_energy_events: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# EnergySnapshot — stato istantaneo (immutabile)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EnergySnapshot:
    """Stato istantaneo del budget energetico. Immutabile e serializzabile."""
    timestamp:          float
    active_neurons:     int
    estimated_cpu_pct:  float
    estimated_memory_mb: float
    cpu_budget_pct:     float
    memory_budget_mb:   float
    cpu_available_pct:  float   # budget - consumed
    memory_available_mb: float
    over_cpu_budget:    bool
    over_memory_budget: bool

    @property
    def utilization_ratio(self) -> float:
        """Rapporto utilizzo/budget (0=idle, 1=saturo, >1=over budget)."""
        cpu_ratio = self.estimated_cpu_pct / max(self.cpu_budget_pct, 1.0)
        mem_ratio = self.estimated_memory_mb / max(self.memory_budget_mb, 1.0)
        return max(cpu_ratio, mem_ratio)

    def to_dict(self) -> dict:
        return {
            "timestamp":           self.timestamp,
            "active_neurons":      self.active_neurons,
            "estimated_cpu_pct":   round(self.estimated_cpu_pct, 2),
            "estimated_memory_mb": round(self.estimated_memory_mb, 1),
            "cpu_available_pct":   round(self.cpu_available_pct, 2),
            "memory_available_mb": round(self.memory_available_mb, 1),
            "over_cpu_budget":     self.over_cpu_budget,
            "over_memory_budget":  self.over_memory_budget,
            "utilization_ratio":   round(self.utilization_ratio, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# EnergyBudget — contabilità interna del budget computazionale
# ─────────────────────────────────────────────────────────────────────────────

class EnergyBudget:
    """
    M9 — Gestione budget computazionale bio-ispirata.

    Tiene traccia dei processi/neuroni attivi e stima il consumo
    totale (CPU + RAM). Non usa psutil: contabilità puramente interna,
    leggera e senza dipendenze aggiuntive.

    Integrazione con DriveExecutive:
      - energy_drive basso → EnergyBudget riduce max_parallel_neurons
      - self_repair_mode → EnergyBudget defer exploration, prioritize repair

    Uso:
        budget = EnergyBudget()
        if budget.can_activate("researcher_neuron"):
            budget.activate("researcher_neuron")
            ...
            budget.deactivate("researcher_neuron")

        snap = budget.snapshot()
    """

    def __init__(self, config: Optional[EnergyConfig] = None) -> None:
        self.config   = config or EnergyConfig()
        self._active: Dict[str, float] = {}   # process_id → activation_time
        self._result_cache: Dict[str, tuple] = {}  # key → (result, ts)
        self._total_activations = 0
        self._total_deferrals   = 0

    # ── Budget checking ───────────────────────────────────────────────────────

    def can_activate(self, process_id: str) -> bool:
        """
        Verifica se è possibile attivare un nuovo processo/neurone
        rispettando i budget CPU e RAM.

        Un processo già attivo non conta come nuovo.
        """
        if process_id in self._active:
            return True  # già attivo, nessun costo aggiuntivo

        new_count  = len(self._active) + 1
        new_cpu    = new_count * self.config.cpu_per_neuron
        new_mem    = new_count * self.config.memory_per_neuron

        cpu_ok = new_cpu <= self.config.cpu_budget_pct
        mem_ok = new_mem <= self.config.memory_budget_mb
        par_ok = new_count <= self.config.max_parallel_neurons

        if not (cpu_ok and mem_ok and par_ok):
            self._total_deferrals += 1
            if self.config.log_energy_events:
                logger.debug(
                    "[EnergyBudget] DEFERRAL %s: cpu=%.1f%% mem=%.0fMB neurons=%d "
                    "(limits: cpu=%.1f%% mem=%.0fMB neurons=%d)",
                    process_id, new_cpu, new_mem, new_count,
                    self.config.cpu_budget_pct,
                    self.config.memory_budget_mb,
                    self.config.max_parallel_neurons,
                )
            return False
        return True

    def activate(self, process_id: str) -> bool:
        """
        Registra l'attivazione di un processo. Ritorna False se già attivo.
        """
        if process_id in self._active:
            return False
        self._active[process_id] = time.monotonic()
        self._total_activations += 1
        if self.config.log_energy_events:
            logger.debug(
                "[EnergyBudget] ACTIVATE %s | active=%d cpu≈%.1f%% mem≈%.0fMB",
                process_id, len(self._active),
                len(self._active) * self.config.cpu_per_neuron,
                len(self._active) * self.config.memory_per_neuron,
            )
        return True

    def deactivate(self, process_id: str) -> float:
        """
        Deregistra un processo. Ritorna il tempo attivo in secondi.
        """
        if process_id not in self._active:
            return 0.0
        elapsed = time.monotonic() - self._active.pop(process_id)
        if self.config.log_energy_events:
            logger.debug(
                "[EnergyBudget] DEACTIVATE %s elapsed=%.2fs | active=%d",
                process_id, elapsed, len(self._active),
            )
        return elapsed

    # ── Adaptive limits (driven by DriveExecutive) ────────────────────────────

    def apply_behavioral_limits(self, energy_drive: float, repair_mode: bool) -> None:
        """
        Adatta i limiti in base allo stato comportamentale di DriveExecutive.

        Regole bio-ispirate:
          - energy_drive < 0.3  → max 1 neurone parallelo (sparse activation)
          - energy_drive < 0.5  → max 2 neuroni (ridotto)
          - repair_mode         → max 1 neurone (focus su survival)
          - energy_drive > 0.7  → max 3 neuroni (esplorazione attiva)
        """
        original = self.config.max_parallel_neurons

        if repair_mode or energy_drive < self.config.sleep_threshold:
            self.config.max_parallel_neurons = 1
        elif energy_drive < 0.5:
            self.config.max_parallel_neurons = 2
        elif energy_drive > 0.7:
            self.config.max_parallel_neurons = min(3, int(EnergyConfig().max_parallel_neurons) + 1)
        else:
            self.config.max_parallel_neurons = EnergyConfig().max_parallel_neurons

        if self.config.max_parallel_neurons != original:
            logger.info(
                "[EnergyBudget] max_parallel_neurons: %d→%d "
                "(energy=%.2f repair=%s)",
                original, self.config.max_parallel_neurons, energy_drive, repair_mode,
            )

    # ── Result cache (lazy computation) ──────────────────────────────────────

    def cache_get(self, key: str):
        """Recupera un risultato dalla cache se non scaduto. None se miss."""
        if not self.config.enable_result_cache:
            return None
        entry = self._result_cache.get(key)
        if entry is None:
            return None
        result, ts = entry
        if time.monotonic() - ts > self.config.cache_ttl_s:
            del self._result_cache[key]
            return None
        logger.debug("[EnergyBudget] CACHE HIT: %s", key)
        return result

    def cache_set(self, key: str, result) -> None:
        """Salva un risultato in cache."""
        if self.config.enable_result_cache:
            self._result_cache[key] = (result, time.monotonic())

    def cache_invalidate(self, prefix: str = "") -> int:
        """Invalida le voci di cache con il prefisso dato. Ritorna il numero rimosso."""
        keys = [k for k in self._result_cache if k.startswith(prefix)]
        for k in keys:
            del self._result_cache[k]
        return len(keys)

    # ── Snapshot e metriche ──────────────────────────────────────────────────

    def snapshot(self) -> EnergySnapshot:
        """Ritorna lo stato istantaneo del budget."""
        n_active = len(self._active)
        cpu_used = n_active * self.config.cpu_per_neuron
        mem_used = n_active * self.config.memory_per_neuron
        return EnergySnapshot(
            timestamp          = time.time(),
            active_neurons     = n_active,
            estimated_cpu_pct  = cpu_used,
            estimated_memory_mb = mem_used,
            cpu_budget_pct     = self.config.cpu_budget_pct,
            memory_budget_mb   = self.config.memory_budget_mb,
            cpu_available_pct  = max(0.0, self.config.cpu_budget_pct - cpu_used),
            memory_available_mb = max(0.0, self.config.memory_budget_mb - mem_used),
            over_cpu_budget    = cpu_used > self.config.cpu_budget_pct,
            over_memory_budget = mem_used > self.config.memory_budget_mb,
        )

    def get_metrics(self) -> dict:
        snap = self.snapshot()
        return {
            **snap.to_dict(),
            "total_activations": self._total_activations,
            "total_deferrals":   self._total_deferrals,
            "cache_size":        len(self._result_cache),
            "deferral_rate":     (
                self._total_deferrals /
                max(1, self._total_activations + self._total_deferrals)
            ),
        }


__all__ = ["EnergyConfig", "EnergyBudget", "EnergySnapshot"]
