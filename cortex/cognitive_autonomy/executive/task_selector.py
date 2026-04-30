"""
cortex.cognitive_autonomy.executive.task_selector
==================================================
M7.0 — TaskSelector: selezione dei task guidata da BehavioralState.

Il TaskSelector riceve un BehavioralState dal DriveExecutive e lo usa
per filtrare, ordinare e limitare il numero di task che SPEACE esegue
in un dato ciclo SMFOI.

Comportamenti causali dimostrabili:
  1. BehavioralState.self_repair_mode → solo task con tag "critical"/"repair"
  2. BehavioralState.exploration_bonus → task con tag "explore" ricevono +bonus
  3. BehavioralState.max_parallel_tasks → limita il numero di task restituiti
  4. BehavioralState.planning_depth → task con alta complessità vengono
     abbassati di priorità quando energy è bassa
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Set

from .drive_executive import BehavioralState

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    """Priorità numerica dei task (più alto = più urgente)."""
    CRITICAL  = 100
    HIGH      = 75
    MEDIUM    = 50
    LOW       = 25
    EXPLORE   = 10


@dataclass
class Task:
    """
    Rappresentazione minima di un task per il TaskSelector.

    In produzione questa struttura viene popolata da SMFOI_v3.py o da
    qualsiasi componente che generi task (DriveExecutive, evolver, team
    scientifico, ecc.).
    """
    id: str
    description: str
    base_priority: float = TaskPriority.MEDIUM
    tags: Set[str] = field(default_factory=set)
    complexity: int = 1
    """Complessità stimata del task: 1 (semplice) → 5 (molto complesso)."""

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "description":    self.description,
            "base_priority":  self.base_priority,
            "tags":           list(self.tags),
            "complexity":     self.complexity,
        }


@dataclass
class ScoredTask:
    """Task con punteggio finale dopo applicazione del BehavioralState."""
    task: Task
    final_score: float
    score_breakdown: dict = field(default_factory=dict)


class TaskSelector:
    """
    Seleziona e ordina i task in base al BehavioralState corrente.

    Algoritmo:
      1. Se self_repair_mode → filtra solo task critical/repair
      2. Applica exploration_bonus ai task con tag "explore"
      3. Applica memory_priority_boost ai task con tag "memory"
      4. Penalizza task ad alta complessità se energy bassa (planning_depth=1)
      5. Ordina per final_score decrescente
      6. Tronca a max_parallel_tasks

    Uso:
        selector = TaskSelector()
        selected = selector.select(tasks, behavioral_state)
    """

    def select(
        self,
        tasks: List[Task],
        state: BehavioralState,
    ) -> List[Task]:
        """
        Seleziona i task da eseguire nel ciclo corrente.

        Args:
            tasks: lista di Task candidati
            state: BehavioralState prodotto da DriveExecutive

        Returns:
            Lista ordinata di Task (max state.max_parallel_tasks elementi).
        """
        if not tasks:
            return []

        # ── Step 1: filtraggio in repair mode ────────────────────────────────
        if state.self_repair_mode:
            critical = [t for t in tasks if t.has_tag("critical") or t.has_tag("repair")]
            if critical:
                logger.warning(
                    "[TaskSelector] REPAIR MODE: selezionati %d task critical/repair su %d totali",
                    len(critical), len(tasks)
                )
                tasks = critical
            else:
                # Nessun task critical disponibile: prendi il più prioritario
                logger.warning(
                    "[TaskSelector] REPAIR MODE: nessun task critical, uso il top-priority"
                )
                tasks = [max(tasks, key=lambda t: t.base_priority)]

        # ── Step 2: scoring ──────────────────────────────────────────────────
        scored: List[ScoredTask] = []
        for task in tasks:
            score = float(task.base_priority)
            breakdown: dict = {"base": score}

            # Exploration bonus
            if task.has_tag("explore") and state.exploration_bonus > 0:
                bonus = state.exploration_bonus * 100.0
                score += bonus
                breakdown["exploration_bonus"] = bonus

            # Memory priority boost
            if task.has_tag("memory") and state.memory_priority_boost > 0:
                boost = state.memory_priority_boost * 100.0
                score += boost
                breakdown["memory_boost"] = boost

            # Penalità complessità quando energy bassa
            if state.planning_depth == 1 and task.complexity > 2:
                penalty = (task.complexity - 2) * 15.0
                score -= penalty
                breakdown["complexity_penalty"] = -penalty

            breakdown["final"] = score
            scored.append(ScoredTask(task=task, final_score=score, score_breakdown=breakdown))

        # ── Step 3: ordinamento ──────────────────────────────────────────────
        scored.sort(key=lambda s: s.final_score, reverse=True)

        # ── Step 4: limite parallelismo ──────────────────────────────────────
        limit = state.max_parallel_tasks
        selected_scored = scored[:limit]
        selected = [s.task for s in selected_scored]

        logger.info(
            "[TaskSelector] Selezionati %d/%d task (max_parallel=%d, repair=%s, "
            "explore_bonus=%.2f, memory_boost=%.2f)",
            len(selected), len(tasks),
            state.max_parallel_tasks,
            state.self_repair_mode,
            state.exploration_bonus,
            state.memory_priority_boost,
        )
        for s in selected_scored:
            logger.debug("  → %s score=%.1f breakdown=%s", s.task.id, s.final_score, s.score_breakdown)

        return selected

    def select_explore_task(self, state: BehavioralState) -> Optional[Task]:
        """
        Genera spontaneamente un task esplorativo quando curiosity è alta.

        Questo implementa la regola causale:
          curiosity > 0.7 → genera task esplorativa spontanea

        Returns:
            Task esplorativo generato, oppure None se exploration_bonus == 0.
        """
        if state.exploration_bonus <= 0:
            return None

        snap = state.source_snapshot
        curiosity_val = snap.curiosity if snap else 0.5

        task = Task(
            id=f"explore_spontaneous_{id(state):x}",
            description=(
                f"Esplorazione spontanea generata da curiosity_drive="
                f"{curiosity_val:.2f} (bonus={state.exploration_bonus:.2f}). "
                f"Obiettivo: ricerca di pattern inaspettati nello stato corrente del sistema."
            ),
            base_priority=TaskPriority.EXPLORE,
            tags={"explore", "spontaneous", "curiosity_driven"},
            complexity=2,
        )
        logger.info(
            "[TaskSelector] Task esplorativo spontaneo generato: curiosity=%.2f bonus=%.2f",
            curiosity_val, state.exploration_bonus
        )
        return task


__all__ = ["TaskSelector", "Task", "TaskPriority", "ScoredTask"]
