"""
cortex.cognitive_autonomy.swarm.orchestrator
=============================================
M8 — SwarmOrchestrator: 10° comparto del SPEACE Cortex.

Implementa il layer di orchestrazione multi-neurone che risolve il problema
EM-03: "PFC non integra feedback cross-modulo".

Pipeline:
  Input (da DriveExecutive.BehavioralState, exploration_bonus > 0)
    → Researcher (raccoglie contesto)
    → Planner (decompone in subtask)
    → Executor (esegue ogni subtask)
    → Critic (valida ogni output Executor)
    → Output (risultato sintetizzato)

Il SwarmOrchestrator è il componente che realizza l'integrazione cross-modulo:
ogni neurone legge l'output del precedente, creando un loop non-lineare
emergente impossibile con moduli isolati.

EPI-010: cognitive_autonomy.swarm.enabled: true (attivato al completamento M8)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .neuron_base import NeuronResult
from .planner    import PlannerNeuron
from .critic     import CriticNeuron
from .executor   import ExecutorNeuron
from .researcher import ResearcherNeuron

logger = logging.getLogger(__name__)

# Lazy import per evitare dipendenza circolare
def _get_behavioral_state_type():
    try:
        from cortex.cognitive_autonomy.executive.drive_executive import BehavioralState
        return BehavioralState
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SwarmResult — output dell'intera pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SwarmResult:
    """
    Risultato dell'intera pipeline SwarmOrchestrator.
    Contiene tutti i contributi di ogni neurone e il synthesis finale.
    """
    task_description: str
    synthesis: str                           # output sintetizzato finale
    subtasks: List[str] = field(default_factory=list)
    executor_outputs: List[NeuronResult] = field(default_factory=list)
    critic_verdicts: List[tuple] = field(default_factory=list)
    researcher_result: Optional[NeuronResult] = None
    planner_result: Optional[NeuronResult] = None
    approved_count: int = 0
    rejected_count: int = 0
    pipeline_steps: List[str] = field(default_factory=list)
    ollama_used: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "task_description":  self.task_description,
            "synthesis":         self.synthesis,
            "subtasks":          self.subtasks,
            "executor_outputs":  [r.to_dict() for r in self.executor_outputs],
            "critic_verdicts":   [(v, e) for v, e in self.critic_verdicts],
            "approved_count":    self.approved_count,
            "rejected_count":    self.rejected_count,
            "pipeline_steps":    self.pipeline_steps,
            "ollama_used":       self.ollama_used,
            "timestamp":         self.timestamp,
        }

    @property
    def success(self) -> bool:
        """True se almeno un subtask è stato approvato dal Critic."""
        return self.approved_count > 0

    @property
    def approval_rate(self) -> float:
        total = self.approved_count + self.rejected_count
        return self.approved_count / total if total > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# SwarmOrchestrator
# ─────────────────────────────────────────────────────────────────────────────

class SwarmOrchestrator:
    """
    10° comparto SPEACE Cortex — orchestrazione multi-neurone.

    Realizza il cross-module feedback mancante (EM-03):
      PlannerNeuron → subtask list
      ResearcherNeuron → context arricchito
      ExecutorNeuron (per ogni subtask) → azioni concrete
      CriticNeuron (per ogni output Executor) → validazione

    Il risultato sintetizzato integra output di 4 neuroni specializzati.

    Uso:
        orchestrator = SwarmOrchestrator()
        result = orchestrator.run("Analizza lo stato del sistema SPEACE")
        # oppure con BehavioralState:
        result = orchestrator.run_from_behavioral_state(behavioral_state)
    """

    MAX_SUBTASKS = 4  # Limite per evitare esplosione di chiamate Ollama

    def __init__(
        self,
        model:             str  = "gemma3:4b",
        max_subtasks:      int  = MAX_SUBTASKS,
        critic_strict:     bool = False,
    ) -> None:
        self.model        = model
        self.max_subtasks = max_subtasks
        self.critic_strict = critic_strict  # se True, rejected → tutta la pipeline fallisce

        # Neuroni
        self.planner    = PlannerNeuron(model=model)
        self.critic     = CriticNeuron(model=model)
        self.executor   = ExecutorNeuron(model=model)
        self.researcher = ResearcherNeuron(model=model)

        self._last_result: Optional[SwarmResult] = None

    # ── API pubblica ──────────────────────────────────────────────────────────

    def run(self, task: str, context: Optional[Dict] = None) -> SwarmResult:
        """
        Esegue la pipeline completa per un task dato.

        Args:
            task:    descrizione del task (stringa)
            context: dict opzionale con contesto aggiuntivo

        Returns:
            SwarmResult con synthesis e output di ogni neurone.
        """
        return asyncio.run(self._run_pipeline(task, context or {}))

    def run_from_behavioral_state(self, behavioral_state: Any) -> Optional[SwarmResult]:
        """
        Genera ed esegue un task esplorativo quando exploration_bonus > 0.

        Se exploration_bonus è 0 → restituisce None (non attivo).

        Args:
            behavioral_state: BehavioralState da DriveExecutive

        Returns:
            SwarmResult oppure None se exploration_bonus == 0.
        """
        if not hasattr(behavioral_state, "exploration_bonus"):
            return None
        if behavioral_state.exploration_bonus <= 0:
            return None

        snap = getattr(behavioral_state, "source_snapshot", None)
        curiosity = snap.curiosity if snap else 0.5

        task = (
            f"Esplorazione autonoma generata da curiosity_drive={curiosity:.2f}. "
            f"exploration_bonus={behavioral_state.exploration_bonus:.2f}. "
            f"Obiettivo: identificare opportunità evolutive per SPEACE e pattern emergenti "
            f"non ancora modellati nel WorldModel."
        )
        context = {
            "behavioral_state": behavioral_state.to_dict()
                if hasattr(behavioral_state, "to_dict") else {},
            "triggered_by":     "curiosity_drive",
            "exploration_bonus": behavioral_state.exploration_bonus,
        }
        logger.info(
            "[SwarmOrchestrator] Task esplorativo da curiosity=%.2f, bonus=%.2f",
            curiosity, behavioral_state.exploration_bonus
        )
        return self.run(task, context)

    @property
    def last_result(self) -> Optional[SwarmResult]:
        return self._last_result

    def get_status(self) -> dict:
        return {
            "model":        self.model,
            "max_subtasks": self.max_subtasks,
            "neurons": {
                "planner":    self.planner.get_status(),
                "critic":     self.critic.get_status(),
                "executor":   self.executor.get_status(),
                "researcher": self.researcher.get_status(),
            },
        }

    # ── Pipeline asincrona ────────────────────────────────────────────────────

    async def _run_pipeline(self, task: str, context: Dict) -> SwarmResult:
        steps: List[str] = []
        any_ollama = False

        logger.info("[SwarmOrchestrator] START pipeline: task='%s'", task[:80])

        # ── STEP 1: Researcher — raccoglie contesto ───────────────────────────
        steps.append("researcher")
        researcher_result = await self.researcher.process({
            "query":   f"Ricerca contesto per: {task}",
            "context": context,
        })
        any_ollama = any_ollama or researcher_result.ollama_used
        logger.debug("[SwarmOrchestrator] Researcher done: %s", researcher_result.status)

        # ── STEP 2: Planner — decompone in subtask ────────────────────────────
        steps.append("planner")
        planner_context = {
            "query":      f"Pianifica: {task}",
            "researcher": researcher_result.response,
            **context,
        }
        planner_result = await self.planner.process(planner_context)
        any_ollama = any_ollama or planner_result.ollama_used

        subtasks = self.planner.extract_subtasks(planner_result)
        subtasks = subtasks[:self.max_subtasks]  # limita
        logger.info(
            "[SwarmOrchestrator] Planner prodotto %d subtask: %s",
            len(subtasks), subtasks
        )

        # ── STEP 3: Executor + Critic per ogni subtask ────────────────────────
        executor_outputs: List[NeuronResult] = []
        critic_verdicts:  List[tuple]        = []
        approved_count  = 0
        rejected_count  = 0

        for i, subtask in enumerate(subtasks):
            steps.append(f"executor[{i}]")

            # Executor
            exec_result = await self.executor.process({
                "query":           subtask,
                "subtask_index":   i,
                "total_subtasks":  len(subtasks),
                "task":            task,
            })
            any_ollama = any_ollama or exec_result.ollama_used
            executor_outputs.append(exec_result)

            # Critic valida l'output dell'Executor
            steps.append(f"critic[{i}]")
            critic_result = await self.critic.process({
                "query":            f"Valida questo output: {exec_result.response[:300]}",
                "output_to_review": exec_result.response,
                "subtask":          subtask,
            })
            any_ollama = any_ollama or critic_result.ollama_used

            verdict, explanation = self.critic.parse_verdict(critic_result)
            critic_verdicts.append((verdict, explanation))

            if verdict == CriticNeuron.VERDICT_APPROVED:
                approved_count += 1
                logger.info("[SwarmOrchestrator] Subtask %d/%d: APPROVED", i+1, len(subtasks))
            elif verdict == CriticNeuron.VERDICT_REJECTED:
                rejected_count += 1
                logger.warning(
                    "[SwarmOrchestrator] Subtask %d/%d: REJECTED — %s",
                    i+1, len(subtasks), explanation[:80]
                )
                if self.critic_strict:
                    break  # modalità strict: ferma alla prima rejection
            else:
                logger.info(
                    "[SwarmOrchestrator] Subtask %d/%d: NEEDS_REVISION",
                    i+1, len(subtasks)
                )

        # ── STEP 4: Synthesis ─────────────────────────────────────────────────
        steps.append("synthesis")
        synthesis = self._synthesize(
            task, subtasks, executor_outputs, critic_verdicts,
            approved_count, rejected_count, context
        )

        result = SwarmResult(
            task_description=task,
            synthesis=synthesis,
            subtasks=subtasks,
            executor_outputs=executor_outputs,
            critic_verdicts=critic_verdicts,
            researcher_result=researcher_result,
            planner_result=planner_result,
            approved_count=approved_count,
            rejected_count=rejected_count,
            pipeline_steps=steps,
            ollama_used=any_ollama,
        )
        self._last_result = result

        logger.info(
            "[SwarmOrchestrator] DONE: %d subtask, %d approved, %d rejected, ollama=%s",
            len(subtasks), approved_count, rejected_count, any_ollama
        )
        return result

    def _synthesize(
        self,
        task: str,
        subtasks: List[str],
        executor_outputs: List[NeuronResult],
        critic_verdicts: List[tuple],
        approved: int,
        rejected: int,
        context: Optional[Dict] = None,
    ) -> str:
        """
        Sintetizza i risultati di tutti i neuroni in un output coerente.
        Questa è l'integrazione cross-modulo che risolve EM-03.

        Se context contiene 'memory_episodes', include il contesto di memoria
        autobiografica nella sintesi (M8.1 — Hippocampus→PFC wiring).
        """
        context = context or {}
        lines = [
            f"=== SWARM SYNTHESIS: {task[:80]} ===",
            f"Subtask pianificati: {len(subtasks)} | Approvati: {approved} | Rigettati: {rejected}",
            "",
        ]

        # ── Memory context (M8.1 — Hippocampus wiring) ───────────────────────
        memory_episodes = context.get("memory_episodes", [])
        if memory_episodes:
            lines.append(f"[MEMORY] Contesto da {len(memory_episodes)} episodi autobiografici:")
            for ep in memory_episodes[:3]:  # max 3 per brevità
                action  = ep.get("action", "?") if isinstance(ep, dict) else getattr(ep, "content", {}).get("action", "?")
                outcome = ep.get("outcome", "?") if isinstance(ep, dict) else getattr(ep, "outcome", "?")
                ctx_str = ep.get("context", "") if isinstance(ep, dict) else ""
                lines.append(f"  • {action} → outcome={outcome} [{ctx_str}]")
            lines.append("")

        for i, (subtask, exec_out, (verdict, expl)) in enumerate(
            zip(subtasks, executor_outputs, critic_verdicts)
        ):
            verdict_icon = {"approved": "✓", "needs_revision": "~", "rejected": "✗"}.get(verdict, "?")
            lines.append(f"[{verdict_icon}] Subtask {i+1}: {subtask}")
            lines.append(f"    Output: {exec_out.response[:120].strip()}")
            lines.append(f"    Critic: {verdict.upper()} — {expl[:80]}")
            lines.append("")

        approval_rate = approved / max(1, approved + rejected)
        lines.append(
            f"Approval rate: {approval_rate:.0%} | "
            f"Ollama: {'ON' if any(r.ollama_used for r in executor_outputs) else 'FALLBACK'}"
        )
        return "\n".join(lines)


__all__ = ["SwarmOrchestrator", "SwarmResult"]
