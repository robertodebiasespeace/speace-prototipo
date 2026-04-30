"""
cortex.events.resonance
========================
M10.3 — ResonanceScheduler: anti-risonanza degli heartbeat per SPEACE.

Principio fisico:
  Nella meccanica orbitale, la risonanza tra corpi celesti può causare
  instabilità. I sistemi stabili (es. Luna di Giove) evolvono verso
  rapporti di periodo NON interi (anti-risonanza) o vengono espulsi.
  Applicato a SPEACE: i processi con heartbeat sincronizzati causano
  spike di CPU/RAM simultanei → degradazione performance.

Soluzione:
  ResonanceScheduler calcola automaticamente:
  1. Offset iniziali distribuiti nel tempo (fase 0..T distribuita uniformemente)
  2. Rapporti di intervallo razionalmente indipendenti (evitare k*T₁ = m*T₂)
  3. Score di conflitto atteso: P(due processi si sovrappongono) in finestra Δt

  Algoritmo: greedy + Golden Ratio offset (φ ≈ 0.618) garantisce distribuzione
  ottimale per N processi con intervalli variabili. Ispirato a Phyllotaxis
  (la disposizione delle foglie segue la spirale aurea per massimizzare
  la luce solare — ogni foglia ottiene la sua "finestra temporale" ottimale).

Classi principali:
  ProcessSpec        — specifica di un processo schedulato
  ResonanceSchedule  — risultato dell'ottimizzazione (offset + adjusted intervals)
  ResonanceScheduler — calcola il piano anti-risonanza per N processi

M10.3 | 2026-04-28
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("speace.events.resonance")

# Golden ratio: φ ≈ 0.6180339887...
# Usato per distribuire gli offset in modo irrazionale (nessun ciclo)
_PHI = (math.sqrt(5) - 1) / 2


# ─────────────────────────────────────────────────────────────────────────────
# ProcessSpec — specifica di un processo
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProcessSpec:
    """
    Specifica di un processo con heartbeat periodico.

    Attributi:
        process_id:      identificatore univoco del processo
        base_interval_s: intervallo base desiderato in secondi
        priority:        0 (alta) → 9 (bassa) — i processi ad alta priorità
                         ottengono preferenza nell'assegnazione offset
        jitter_pct:      percentuale di jitter naturale accettabile (0.0 → 0.30)
                         Simula la variabilità biologica (heartbeat non è
                         perfettamente regolare). Default 0.05 (5%)
        fixed_interval:  se True, l'intervallo non può essere modificato;
                         solo l'offset è ottimizzabile
    """
    process_id:      str
    base_interval_s: float
    priority:        int   = 5
    jitter_pct:      float = 0.05
    fixed_interval:  bool  = False

    def __post_init__(self):
        if self.base_interval_s <= 0:
            raise ValueError(f"base_interval_s must be > 0 (got {self.base_interval_s})")
        if not 0.0 <= self.jitter_pct <= 0.30:
            raise ValueError(f"jitter_pct must be in [0, 0.30] (got {self.jitter_pct})")
        if not 0 <= self.priority <= 9:
            raise ValueError(f"priority must be in [0, 9] (got {self.priority})")


# ─────────────────────────────────────────────────────────────────────────────
# ResonanceSchedule — piano ottimizzato
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResonanceSchedule:
    """
    Risultato dell'ottimizzazione anti-risonanza.

    Attributi:
        offsets:           Dict[process_id → offset_seconds]
                           Quando avviare il primo heartbeat dopo t=0.
        adjusted_intervals: Dict[process_id → new_interval_seconds]
                           Intervalli (leggermente aggiustati) che minimizzano
                           sovrapposizioni future. Per processi fixed_interval
                           questi coincidono con base_interval_s.
        conflict_score:    Probabilità attesa di sovrapposizione in finestra
                           Δt=5s su un orizzonte di 3600s. 0.0 = nessun conflitto.
                           Target: < 0.15 (< 15% dei tick sono in conflitto).
        resonance_pairs:   Lista di coppie (pid_a, pid_b, score) con rischio
                           di risonanza elevato (score ≥ 0.30).
    """
    offsets:            Dict[str, float]
    adjusted_intervals: Dict[str, float]
    conflict_score:     float
    resonance_pairs:    List[Tuple[str, str, float]] = field(default_factory=list)

    def first_fire_at(self, process_id: str) -> float:
        """Ritorna l'orario (secondi da t=0) del primo heartbeat."""
        return self.offsets.get(process_id, 0.0)

    def next_fire_after(self, process_id: str, current_time: float) -> float:
        """Calcola il prossimo heartbeat dopo current_time."""
        offset   = self.offsets.get(process_id, 0.0)
        interval = self.adjusted_intervals.get(process_id, 60.0)
        if current_time <= offset:
            return offset
        elapsed   = current_time - offset
        n_cycles  = math.floor(elapsed / interval)
        return offset + (n_cycles + 1) * interval

    def summary(self) -> str:
        lines = ["[ResonanceSchedule]"]
        lines.append(f"  conflict_score: {self.conflict_score:.3f}")
        for pid in sorted(self.offsets):
            lines.append(
                f"  {pid}: offset={self.offsets[pid]:.1f}s  "
                f"interval={self.adjusted_intervals[pid]:.1f}s"
            )
        if self.resonance_pairs:
            lines.append("  ⚠ Risonanza rilevata:")
            for a, b, s in self.resonance_pairs:
                lines.append(f"    {a} ↔ {b}: score={s:.2f}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# ResonanceScheduler — ottimizzazione anti-risonanza
# ─────────────────────────────────────────────────────────────────────────────

class ResonanceScheduler:
    """
    M10.3 — Calcola un piano di scheduling anti-risonanza per N processi.

    Ispirato a:
      - Orbital resonance (meccanica celeste): i corpi stabili evolvono verso
        rapporti irrazionali per evitare accumulo di perturbazioni.
      - Phyllotaxis (spirale aurea): le foglie si dispongono a φ*360° l'una
        dall'altra per massimizzare la distribuzione della luce.
      - Heartbeat biologico: variabilità cardiaca (HRV) — il cuore sano non
        è un metronomo perfetto. Il jitter biologico è funzionale.

    Algoritmo:
      1. Ordina i processi per priorità (alta priorità = offset più piccolo).
      2. Assegna offset usando la sequenza di Golden Ratio:
         offset_i = (i * φ * T_max) mod T_max
         dove T_max = max(base_interval_s) tra tutti i processi.
      3. Per i processi non-fixed, aggiusta leggermente l'intervallo
         moltiplicando per un fattore irrazionale vicino a 1.0
         (es. 1 ± k*φ*0.01) per rompere le risonanze a lungo termine.
      4. Calcola il conflict_score stimando sovrapposizioni su 3600s.
      5. Identifica coppie ad alto rischio di risonanza.

    Uso:
        scheduler = ResonanceScheduler(window_s=5.0, horizon_s=3600.0)
        processes = [
            ProcessSpec("smfoi_kernel",     base_interval_s=60),
            ProcessSpec("evolver",          base_interval_s=3600, fixed_interval=True),
            ProcessSpec("memory_consolidate",base_interval_s=300),
            ProcessSpec("energy_monitor",   base_interval_s=60),
            ProcessSpec("predictive_update",base_interval_s=30),
        ]
        schedule = scheduler.compute(processes)
        print(schedule.summary())
    """

    def __init__(
        self,
        window_s:  float = 5.0,    # finestra di sovrapposizione (secondi)
        horizon_s: float = 3600.0, # orizzonte di simulazione (secondi)
    ) -> None:
        if window_s <= 0 or horizon_s <= 0:
            raise ValueError("window_s e horizon_s devono essere > 0")
        self._window   = window_s
        self._horizon  = horizon_s

    # ── API pubblica ──────────────────────────────────────────────────────────

    def compute(self, processes: List[ProcessSpec]) -> ResonanceSchedule:
        """
        Calcola il piano anti-risonanza per la lista di ProcessSpec.

        Ritorna un ResonanceSchedule con offsets, intervals e conflict_score.
        """
        if not processes:
            return ResonanceSchedule(
                offsets={}, adjusted_intervals={}, conflict_score=0.0
            )

        # Ordina: priorità più alta (numero basso) prima
        sorted_procs = sorted(processes, key=lambda p: (p.priority, p.process_id))

        # T_max per la distribuzione degli offset
        t_max = max(p.base_interval_s for p in sorted_procs)

        offsets:   Dict[str, float] = {}
        intervals: Dict[str, float] = {}

        for i, proc in enumerate(sorted_procs):
            # Offset: sequenza Golden Ratio distribuita in [0, t_max)
            raw_offset = (i * _PHI * t_max) % t_max
            # Clamp a un massimo pari all'intervallo del processo stesso
            # (non ha senso ritardare un processo più del suo proprio periodo)
            offset = raw_offset % proc.base_interval_s
            offsets[proc.process_id] = round(offset, 3)

            # Aggiustamento intervallo (solo se non fixed)
            if proc.fixed_interval:
                intervals[proc.process_id] = proc.base_interval_s
            else:
                # Fattore moltiplicativo irrazionale: alterna + e - per
                # distribuire uniformemente sopra e sotto il valore base
                sign    = 1 if i % 2 == 0 else -1
                factor  = 1.0 + sign * (i % 5) * _PHI * 0.005  # max ±1.5%
                new_interval = proc.base_interval_s * factor
                intervals[proc.process_id] = round(new_interval, 3)

        # Calcola conflict score e resonance pairs
        conflict_score, resonance_pairs = self._evaluate(
            sorted_procs, offsets, intervals
        )

        schedule = ResonanceSchedule(
            offsets=offsets,
            adjusted_intervals=intervals,
            conflict_score=round(conflict_score, 4),
            resonance_pairs=resonance_pairs,
        )
        logger.info(
            "[Resonance] %d processi → conflict_score=%.3f  pairs=%d",
            len(processes), conflict_score, len(resonance_pairs)
        )
        return schedule

    # ── Metodi privati ────────────────────────────────────────────────────────

    def _fire_times(
        self,
        proc_id:  str,
        offset:   float,
        interval: float,
    ) -> List[float]:
        """
        Genera tutti i tick di un processo nell'orizzonte di simulazione.
        """
        times = []
        t = offset
        while t <= self._horizon:
            times.append(t)
            t += interval
        return times

    def _evaluate(
        self,
        procs:     List[ProcessSpec],
        offsets:   Dict[str, float],
        intervals: Dict[str, float],
    ) -> Tuple[float, List[Tuple[str, str, float]]]:
        """
        Stima il conflict score e identifica coppie risonanti.

        conflict_score = N_conflitti / N_tick_totali
        dove un conflitto è: due processi con tick a distanza < window_s.

        resonance_pairs: coppie con pair_score ≥ 0.30.
        """
        # Genera tutti i tick
        tick_map: Dict[str, List[float]] = {}
        for proc in procs:
            pid = proc.process_id
            tick_map[pid] = self._fire_times(pid, offsets[pid], intervals[pid])

        total_ticks    = sum(len(v) for v in tick_map.values())
        total_conflicts = 0
        resonance_pairs: List[Tuple[str, str, float]] = []

        pids = [p.process_id for p in procs]
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                pid_a, pid_b = pids[i], pids[j]
                a_times = tick_map[pid_a]
                b_times = tick_map[pid_b]
                pair_conflicts = self._count_conflicts(a_times, b_times)
                total_conflicts += pair_conflicts

                # Pair score normalizzato rispetto ai tick minori
                denom = min(len(a_times), len(b_times))
                if denom > 0:
                    pair_score = pair_conflicts / denom
                    if pair_score >= 0.30:
                        resonance_pairs.append((pid_a, pid_b, round(pair_score, 3)))

        conflict_score = total_conflicts / max(total_ticks, 1)
        return conflict_score, resonance_pairs

    def _count_conflicts(
        self,
        times_a: List[float],
        times_b: List[float],
    ) -> int:
        """
        Conta quante coppie (t_a, t_b) hanno |t_a - t_b| < window_s.
        Algoritmo: merge + sliding window O(N log N).
        """
        if not times_a or not times_b:
            return 0

        # Merge entrambe le sequenze con etichetta
        merged = sorted(
            [(t, "a") for t in times_a] + [(t, "b") for t in times_b]
        )

        conflicts = 0
        n = len(merged)
        left = 0

        for right in range(n):
            t_r, tag_r = merged[right]
            # Avanza left finché merged[left] è fuori finestra
            while merged[left][0] < t_r - self._window:
                left += 1
            # Conta quanti nella finestra [left, right) hanno tag diverso
            for k in range(left, right):
                t_k, tag_k = merged[k]
                if tag_k != tag_r and abs(t_k - t_r) < self._window:
                    conflicts += 1

        return conflicts


# ─────────────────────────────────────────────────────────────────────────────
# Preset SPEACE: configurazione predefinita per i processi core
# ─────────────────────────────────────────────────────────────────────────────

def speace_default_processes() -> List[ProcessSpec]:
    """
    Ritorna la lista dei processi SPEACE con i loro heartbeat base.
    Usato da ResonanceScheduler.compute() per generare il piano default.
    """
    return [
        ProcessSpec("smfoi_kernel",          base_interval_s=60,   priority=0, fixed_interval=False),
        ProcessSpec("homeostatic_controller", base_interval_s=90,   priority=1, fixed_interval=False),
        ProcessSpec("energy_monitor",         base_interval_s=30,   priority=1, fixed_interval=False),
        ProcessSpec("predictive_update",      base_interval_s=45,   priority=2, fixed_interval=False),
        ProcessSpec("swarm_orchestrator",     base_interval_s=120,  priority=2, fixed_interval=False),
        ProcessSpec("memory_consolidate",     base_interval_s=300,  priority=3, fixed_interval=False),
        ProcessSpec("immune_scan",            base_interval_s=180,  priority=2, fixed_interval=False),
        ProcessSpec("evolver_heartbeat",      base_interval_s=3600, priority=4, fixed_interval=True),
        ProcessSpec("github_push",            base_interval_s=7200, priority=5, fixed_interval=True),
    ]


__all__ = [
    "ProcessSpec",
    "ResonanceSchedule",
    "ResonanceScheduler",
    "speace_default_processes",
]
