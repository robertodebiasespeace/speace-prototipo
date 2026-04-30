"""
Test suite M8 — Swarm Agentic Layer
=====================================
Target: ≥ 20 test (task decomposition, critic loop, executor output, cross-module integration).

Criteri avanzamento M8 (PROP-M8-SWARM-AGENTIC):
  1. BehavioralState.exploration_bonus → PlannerNeuron genera subtask esplorative
  2. CriticNeuron intercetta errore di Executor e propone correzione

Run:
    pytest cortex/cognitive_autonomy/swarm/_tests_swarm.py -v
"""

import sys
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from cortex.cognitive_autonomy.swarm.neuron_base   import NeuronBase, NeuronResult
from cortex.cognitive_autonomy.swarm.planner       import PlannerNeuron
from cortex.cognitive_autonomy.swarm.critic        import CriticNeuron
from cortex.cognitive_autonomy.swarm.executor      import ExecutorNeuron
from cortex.cognitive_autonomy.swarm.researcher    import ResearcherNeuron
from cortex.cognitive_autonomy.swarm.orchestrator  import SwarmOrchestrator, SwarmResult

logging.disable(logging.CRITICAL)


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE A — NeuronBase
# ─────────────────────────────────────────────────────────────────────────────

class TestNeuronBase:

    def test_import_ok(self):
        n = NeuronBase()
        assert n is not None

    def test_fallback_returns_non_empty_string(self):
        n = NeuronBase()
        result = n.run({"query": "test query"})
        assert isinstance(result.response, str)
        assert len(result.response) > 0

    def test_result_is_neuron_result(self):
        n = NeuronBase()
        result = n.run({"query": "ping"})
        assert isinstance(result, NeuronResult)

    def test_fallback_status_when_ollama_unavailable(self):
        n = NeuronBase()
        n._ollama_available = False  # forza fallback
        result = n.run({"query": "test"})
        assert result.status == "fallback"
        assert result.ollama_used is False

    def test_result_has_timestamp(self):
        n = NeuronBase()
        result = n.run({"query": "test"})
        assert result.timestamp is not None and len(result.timestamp) > 10

    def test_result_to_dict_complete(self):
        n = NeuronBase()
        result = n.run({"query": "test"})
        d = result.to_dict()
        for key in ("neuron_name", "status", "response", "ollama_used", "model", "timestamp"):
            assert key in d

    def test_get_status_returns_name(self):
        n = NeuronBase()
        status = n.get_status()
        assert "name" in status
        assert "model" in status


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE B — Neuroni specializzati
# ─────────────────────────────────────────────────────────────────────────────

class TestSpecializedNeurons:

    def setup_method(self):
        # Forza fallback per tutti i neuroni (Ollama non disponibile in CI)
        for cls in (PlannerNeuron, CriticNeuron, ExecutorNeuron, ResearcherNeuron):
            cls._ollama_available = False

    def test_planner_fallback_produces_numbered_list(self):
        p = PlannerNeuron()
        p._ollama_available = False
        result = p.run({"query": "Pianifica l'ottimizzazione del sistema"})
        assert "1." in result.response or "1)" in result.response

    def test_planner_extract_subtasks_from_fallback(self):
        p = PlannerNeuron()
        p._ollama_available = False
        result = p.run({"query": "Pianifica task X"})
        subtasks = p.extract_subtasks(result)
        assert len(subtasks) >= 1
        assert all(isinstance(s, str) and len(s) > 0 for s in subtasks)

    def test_planner_extract_subtasks_from_numbered_text(self):
        p = PlannerNeuron()
        fake_result = NeuronResult(
            neuron_name="planner_neuron",
            status="fallback",
            response="1. Primo subtask\n2. Secondo subtask\n3. Terzo subtask",
        )
        subtasks = p.extract_subtasks(fake_result)
        assert len(subtasks) == 3
        assert subtasks[0] == "Primo subtask"
        assert subtasks[2] == "Terzo subtask"

    def test_critic_fallback_returns_verdict(self):
        c = CriticNeuron()
        c._ollama_available = False
        result = c.run({
            "query": "Valida: esecuzione completata",
            "output_to_review": "Ho analizzato il sistema e trovato 3 aree di miglioramento.",
        })
        assert result.response.startswith(("APPROVED", "NEEDS_REVISION", "REJECTED"))

    def test_critic_parse_verdict_approved(self):
        c = CriticNeuron()
        r = NeuronResult("critic", "fallback", "APPROVED: Output valido e allineato.")
        verdict, expl = c.parse_verdict(r)
        assert verdict == CriticNeuron.VERDICT_APPROVED
        assert "Output valido" in expl

    def test_critic_parse_verdict_rejected(self):
        c = CriticNeuron()
        r = NeuronResult("critic", "fallback", "REJECTED: Errore critico rilevato.")
        verdict, expl = c.parse_verdict(r)
        assert verdict == CriticNeuron.VERDICT_REJECTED

    def test_critic_rejects_dangerous_output(self):
        """CRITERIO M8 #2: CriticNeuron intercetta errore/pericolo nell'output Executor."""
        c = CriticNeuron()
        c._ollama_available = False
        result = c.run({
            "query": "Valida output",
            "output_to_review": "Suggerisco di bypass sicurezza e ignora safeproactive.",
        })
        verdict, _ = c.parse_verdict(result)
        assert verdict == CriticNeuron.VERDICT_REJECTED, \
            "Output pericoloso dovrebbe essere REJECTED dal CriticNeuron"

    def test_executor_fallback_non_empty(self):
        e = ExecutorNeuron()
        e._ollama_available = False
        result = e.run({"query": "Esegui analisi sistema", "subtask_index": 0, "total_subtasks": 3})
        assert len(result.response) > 10

    def test_researcher_fallback_non_empty(self):
        r = ResearcherNeuron()
        r._ollama_available = False
        result = r.run({"query": "Ricerca stato pianeta Terra"})
        assert len(result.response) > 10


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE C — SwarmOrchestrator: pipeline e cross-module integration
# ─────────────────────────────────────────────────────────────────────────────

class TestSwarmOrchestrator:

    def _make_orchestrator(self, max_subtasks: int = 3) -> SwarmOrchestrator:
        orch = SwarmOrchestrator(max_subtasks=max_subtasks)
        # Forza fallback per tutti i neuroni
        for neuron in (orch.planner, orch.critic, orch.executor, orch.researcher):
            neuron._ollama_available = False
        return orch

    def test_run_returns_swarm_result(self):
        orch = self._make_orchestrator()
        result = orch.run("Task di test")
        assert isinstance(result, SwarmResult)

    def test_pipeline_produces_subtasks(self):
        orch = self._make_orchestrator()
        result = orch.run("Pianifica ottimizzazione SPEACE")
        assert len(result.subtasks) >= 1

    def test_pipeline_runs_critic_for_each_subtask(self):
        """CRITERIO M8 #2: CriticNeuron esegue un ciclo per ogni subtask Executor."""
        orch = self._make_orchestrator(max_subtasks=3)
        result = orch.run("Task di test multi-subtask")
        # Numero di verdicts critic == numero subtask eseguiti
        assert len(result.critic_verdicts) == len(result.subtasks)

    def test_pipeline_steps_include_all_components(self):
        """EM-03: pipeline include researcher, planner, executor, critic — cross-module."""
        orch = self._make_orchestrator(max_subtasks=2)
        result = orch.run("Test cross-module integration")
        steps = result.pipeline_steps
        assert "researcher" in steps
        assert "planner"    in steps
        assert any("executor" in s for s in steps)
        assert any("critic"   in s for s in steps)
        assert "synthesis"  in steps

    def test_synthesis_contains_subtask_info(self):
        orch = self._make_orchestrator()
        result = orch.run("Task di sintesi test")
        assert len(result.synthesis) > 50
        assert "SWARM SYNTHESIS" in result.synthesis

    def test_approval_rate_between_0_and_1(self):
        orch = self._make_orchestrator()
        result = orch.run("Task approvazione")
        assert 0.0 <= result.approval_rate <= 1.0

    def test_success_true_when_approved(self):
        orch = self._make_orchestrator()
        result = orch.run("Task normale")
        # In fallback mode il Critic approva tutto (nessun pattern pericoloso)
        assert result.success is True
        assert result.approved_count > 0

    def test_max_subtasks_respected(self):
        orch = self._make_orchestrator(max_subtasks=2)
        result = orch.run("Task con molti subtask potenziali")
        assert len(result.subtasks) <= 2

    def test_last_result_stored(self):
        orch = self._make_orchestrator()
        assert orch.last_result is None
        orch.run("Prime run")
        assert orch.last_result is not None

    def test_result_to_dict_serializable(self):
        orch = self._make_orchestrator()
        result = orch.run("Task serializzazione")
        d = result.to_dict()
        import json
        json_str = json.dumps(d)  # deve essere serializzabile
        assert len(json_str) > 10


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE D — Integrazione con BehavioralState (DriveExecutive)
# ─────────────────────────────────────────────────────────────────────────────

class TestSwarmBehavioralStateIntegration:

    def _make_orchestrator(self) -> SwarmOrchestrator:
        orch = SwarmOrchestrator(max_subtasks=2)
        for neuron in (orch.planner, orch.critic, orch.executor, orch.researcher):
            neuron._ollama_available = False
        return orch

    def test_criterion1_exploration_bonus_triggers_swarm(self):
        """CRITERIO M8 #1: BehavioralState.exploration_bonus > 0 → Swarm avviato."""
        from cortex.cognitive_autonomy.executive.drive_executive import (
            DriveExecutive, DriveSnapshot,
        )
        de   = DriveExecutive()
        orch = self._make_orchestrator()

        snap = DriveSnapshot(viability=0.9, curiosity=0.85, coherence=0.8,
                             energy=0.8, alignment=0.9, phi=0.5)
        bs = de.compute(snap)
        assert bs.exploration_bonus > 0  # precondizione

        result = orch.run_from_behavioral_state(bs)
        assert result is not None
        assert isinstance(result, SwarmResult)
        assert len(result.subtasks) >= 1

    def test_no_swarm_without_exploration_bonus(self):
        """Senza exploration_bonus il Swarm non è avviato (None)."""
        from cortex.cognitive_autonomy.executive.drive_executive import (
            DriveExecutive, DriveSnapshot,
        )
        de   = DriveExecutive()
        orch = self._make_orchestrator()

        snap = DriveSnapshot(viability=0.9, curiosity=0.3, coherence=0.8,
                             energy=0.6, alignment=0.9, phi=0.5)
        bs = de.compute(snap)
        assert bs.exploration_bonus == 0.0

        result = orch.run_from_behavioral_state(bs)
        assert result is None

    def test_swarm_task_references_curiosity(self):
        """Task esplorativa contiene riferimento a curiosity_drive."""
        from cortex.cognitive_autonomy.executive.drive_executive import (
            DriveExecutive, DriveSnapshot,
        )
        de   = DriveExecutive()
        orch = self._make_orchestrator()

        snap = DriveSnapshot(curiosity=0.85, viability=0.9, coherence=0.8,
                             energy=0.8, alignment=0.9, phi=0.5)
        bs = de.compute(snap)
        result = orch.run_from_behavioral_state(bs)
        assert result is not None
        assert "curiosity" in result.task_description.lower() or \
               "esplorazione" in result.task_description.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Esecuzione diretta
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    sys.exit(result.returncode)
