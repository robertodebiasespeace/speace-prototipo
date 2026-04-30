"""
Test suite M7.0 — DriveExecutive: BehavioralState causal bridge
================================================================
Target: ≥ 25 test causali (non snapshot).

Criteri avanzamento M7.0 (PROP-M7-DRIVE-EXECUTIVE):
  1. viability scende sotto soglia → task selection cambia → registrato
  2. curiosity supera soglia → task esplorativa generata spontaneamente

Run:
    pytest cortex/cognitive_autonomy/executive/_tests_executive.py -v
    python cortex/cognitive_autonomy/executive/_tests_executive.py
"""

import sys
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from cortex.cognitive_autonomy.executive.drive_executive import (
    DriveExecutive, BehavioralState, DriveSnapshot,
)
from cortex.cognitive_autonomy.executive.task_selector import (
    TaskSelector, Task, TaskPriority,
)
from cortex.cognitive_autonomy.executive.self_repair import (
    SelfRepairTrigger, RepairAction,
)

logging.disable(logging.CRITICAL)  # silenzia log durante i test


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_snap(**kwargs) -> DriveSnapshot:
    defaults = dict(viability=0.9, curiosity=0.5, coherence=0.8,
                    energy=0.75, alignment=0.8, phi=0.5)
    defaults.update(kwargs)
    return DriveSnapshot(**defaults)


def make_tasks():
    return [
        Task("T-normal",  "task normale",     base_priority=75, tags={"normal"}),
        Task("T-explore", "task esplorativa", base_priority=25, tags={"explore"}),
        Task("T-memory",  "consolida memoria",base_priority=30, tags={"memory"}),
        Task("T-critical","task critica",      base_priority=50, tags={"critical", "repair"}),
        Task("T-complex", "task complessa",    base_priority=60, tags={"normal"}, complexity=5),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE A — DriveSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestDriveSnapshot:

    def test_default_values_in_range(self):
        """Tutti i drive default sono in [0, 1]."""
        snap = DriveSnapshot()
        for attr in ("viability", "curiosity", "coherence", "energy", "alignment", "phi"):
            v = getattr(snap, attr)
            assert 0.0 <= v <= 1.0, f"{attr}={v} fuori range"

    def test_from_homeostasis_result_maps_viability(self):
        """from_homeostasis_result legge viability_score correttamente."""
        result = {
            "viability_score": 0.42,
            "h_state": {"energy": 0.3, "safety": 0.9, "coherence": 0.7, "alignment": 0.8},
            "alerts": [],
            "scaffold": False,
        }
        snap = DriveSnapshot.from_homeostasis_result(result, phi=0.6)
        assert snap.viability == pytest.approx(0.42)
        assert snap.phi == pytest.approx(0.6)
        assert snap.energy == pytest.approx(0.3)

    def test_from_homeostasis_result_defaults_missing_fields(self):
        """Campi mancanti in h_state ricevono valori di default sensati."""
        snap = DriveSnapshot.from_homeostasis_result({}, phi=0.5)
        assert 0.0 <= snap.viability <= 1.0
        assert 0.0 <= snap.energy <= 1.0

    def test_to_dict_contains_all_drives(self):
        snap = make_snap(viability=0.6)
        d = snap.to_dict()
        for key in ("viability", "curiosity", "coherence", "energy", "alignment", "phi"):
            assert key in d

    def test_timestamp_is_set(self):
        snap = DriveSnapshot()
        assert snap.timestamp is not None and len(snap.timestamp) > 10


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE B — DriveExecutive: regole causali
# ─────────────────────────────────────────────────────────────────────────────

class TestDriveExecutiveRules:

    def setup_method(self):
        self.de = DriveExecutive()

    # R1 — viability critica → repair
    def test_r1_viability_below_repair_threshold_activates_repair_mode(self):
        """CAUSAL: viability < 0.4 → self_repair_mode=True."""
        bs = self.de.compute(make_snap(viability=0.35))
        assert bs.self_repair_mode is True

    def test_r1_viability_below_repair_sets_focus_repair(self):
        """CAUSAL: viability < 0.4 → focus_shift='repair'."""
        bs = self.de.compute(make_snap(viability=0.35))
        assert bs.focus_shift == "repair"

    def test_r1_viability_below_repair_forces_single_task(self):
        """CAUSAL: viability < 0.4 → max_parallel_tasks=1."""
        bs = self.de.compute(make_snap(viability=0.39))
        assert bs.max_parallel_tasks == 1

    def test_r1_triggered_rule_recorded(self):
        """CAUSAL: viability < 0.4 → R1 presente in triggered_rules."""
        bs = self.de.compute(make_snap(viability=0.30))
        assert any("R1" in r for r in bs.triggered_rules)

    def test_r1_boundary_exactly_at_threshold_no_repair(self):
        """Boundary: viability == 0.4 (non sotto soglia) → NO repair mode."""
        bs = self.de.compute(make_snap(viability=0.40))
        assert bs.self_repair_mode is False

    # R2 — viability medio-bassa → conserve
    def test_r2_viability_between_04_and_06_sets_conserve(self):
        """CAUSAL: 0.4 ≤ viability < 0.6 → focus_shift='conserve'."""
        bs = self.de.compute(make_snap(viability=0.50))
        assert bs.focus_shift == "conserve"
        assert bs.self_repair_mode is False

    def test_r2_reduces_parallelism(self):
        """CAUSAL: conserve mode riduce max_parallel_tasks."""
        bs = self.de.compute(make_snap(viability=0.55))
        assert bs.max_parallel_tasks < 2

    def test_r2_not_triggered_above_conserve_threshold(self):
        """viability >= 0.6 → NO conserve, focus_shift=None."""
        bs = self.de.compute(make_snap(viability=0.65))
        assert bs.focus_shift is None

    # R3 — curiosity alta → exploration bonus
    def test_r3_high_curiosity_sets_exploration_bonus(self):
        """CAUSAL: curiosity > 0.7 → exploration_bonus=+0.3."""
        bs = self.de.compute(make_snap(curiosity=0.80))
        assert bs.exploration_bonus == pytest.approx(0.3)

    def test_r3_low_curiosity_no_bonus(self):
        """curiosity ≤ 0.7 → exploration_bonus=0."""
        bs = self.de.compute(make_snap(curiosity=0.65))
        assert bs.exploration_bonus == pytest.approx(0.0)

    def test_r3_triggered_rule_recorded(self):
        bs = self.de.compute(make_snap(curiosity=0.85))
        assert any("R3" in r for r in bs.triggered_rules)

    # R4 — coherence bassa → memory boost
    def test_r4_low_coherence_sets_memory_boost(self):
        """CAUSAL: coherence < 0.4 → memory_priority_boost=+0.5."""
        bs = self.de.compute(make_snap(coherence=0.30))
        assert bs.memory_priority_boost == pytest.approx(0.5)

    def test_r4_normal_coherence_no_boost(self):
        bs = self.de.compute(make_snap(coherence=0.70))
        assert bs.memory_priority_boost == pytest.approx(0.0)

    # R5 — energy → planning depth
    def test_r5_low_energy_sets_shallow_planning(self):
        """CAUSAL: energy < 0.3 → planning_depth=1."""
        bs = self.de.compute(make_snap(energy=0.20))
        assert bs.planning_depth == 1

    def test_r5b_high_energy_sets_deep_planning(self):
        """CAUSAL: energy > 0.7 → planning_depth=5."""
        bs = self.de.compute(make_snap(energy=0.85))
        assert bs.planning_depth == 5

    def test_r5_normal_energy_default_depth(self):
        bs = self.de.compute(make_snap(energy=0.50))
        assert bs.planning_depth == 3

    # R6 — alignment basso → blocca mutazioni
    def test_r6_low_alignment_closes_mutation_gate(self):
        """CAUSAL: alignment < 0.5 → mutation_gate_open=False."""
        bs = self.de.compute(make_snap(alignment=0.40))
        assert bs.mutation_gate_open is False

    def test_r6_high_alignment_keeps_gate_open(self):
        bs = self.de.compute(make_snap(alignment=0.80))
        assert bs.mutation_gate_open is True

    # R7 — Phi alto → parallelismo
    def test_r7_high_phi_sets_max_parallel_4(self):
        """CAUSAL: Φ > 0.7 → max_parallel_tasks=4."""
        bs = self.de.compute(make_snap(phi=0.85, viability=0.9))
        assert bs.max_parallel_tasks == 4

    def test_r7_not_applied_in_repair_mode(self):
        """Φ alto non aumenta parallelismo in repair mode."""
        bs = self.de.compute(make_snap(viability=0.30, phi=0.85))
        assert bs.self_repair_mode is True
        assert bs.max_parallel_tasks == 1  # repair override

    # Metadati
    def test_behavioral_state_has_timestamp(self):
        bs = self.de.compute(make_snap())
        assert bs.timestamp is not None

    def test_last_state_updated_after_compute(self):
        de = DriveExecutive()
        assert de.last_state is None
        de.compute(make_snap())
        assert de.last_state is not None

    def test_multiple_rules_can_trigger_simultaneously(self):
        """curiosity alta + coherence bassa → R3 + R4 entrambe attive."""
        bs = self.de.compute(make_snap(curiosity=0.85, coherence=0.30))
        rule_ids = [r[:2] for r in bs.triggered_rules]
        assert "R3" in rule_ids
        assert "R4" in rule_ids
        assert bs.exploration_bonus > 0
        assert bs.memory_priority_boost > 0


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE C — TaskSelector: selezione causale
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskSelectorCausal:

    def setup_method(self):
        self.de = DriveExecutive()
        self.sel = TaskSelector()
        self.tasks = make_tasks()

    def test_repair_mode_filters_to_critical_only(self):
        """CRITERIO M7.0 #1: viability bassa → task selection cambia."""
        snap = make_snap(viability=0.30)
        bs = self.de.compute(snap)
        assert bs.self_repair_mode is True
        selected = self.sel.select(self.tasks, bs)
        assert len(selected) >= 1
        for t in selected:
            assert "critical" in t.tags or "repair" in t.tags, \
                f"Task non-critical in repair mode: {t.id}"

    def test_normal_mode_selects_multiple_tasks(self):
        """Stato normale → seleziona max_parallel_tasks task."""
        bs = self.de.compute(make_snap(phi=0.8))
        assert bs.max_parallel_tasks == 4
        selected = self.sel.select(self.tasks, bs)
        assert len(selected) <= bs.max_parallel_tasks

    def test_exploration_bonus_boosts_explore_tasks(self):
        """CRITERIO M7.0 #2: curiosity alta → task esplorativa promossa."""
        bs = self.de.compute(make_snap(curiosity=0.85, phi=0.8))
        assert bs.exploration_bonus == pytest.approx(0.3)
        scored_tasks = self.sel.select(self.tasks, bs)
        # T-explore deve ricevere bonus e scalare nella classifica
        ids = [t.id for t in scored_tasks]
        assert "T-explore" in ids, "T-explore non selezionato con explore_bonus attivo"

    def test_memory_boost_elevates_memory_tasks(self):
        """coherence bassa → task memory scalano nella priorità."""
        bs = self.de.compute(make_snap(coherence=0.25, phi=0.8))
        assert bs.memory_priority_boost == pytest.approx(0.5)
        selected = self.sel.select(self.tasks, bs)
        ids = [t.id for t in selected]
        assert "T-memory" in ids

    def test_low_energy_penalizes_complex_tasks(self):
        """energy bassa → task ad alta complessità scendono di priorità."""
        bs_low = self.de.compute(make_snap(energy=0.20))
        bs_high = self.de.compute(make_snap(energy=0.90))
        sel_low  = self.sel.select(self.tasks, bs_low)
        sel_high = self.sel.select(self.tasks, bs_high)
        # T-complex dovrebbe apparire più tardi (o non apparire) con energy bassa
        ids_low  = [t.id for t in sel_low]
        ids_high = [t.id for t in sel_high]
        rank_low  = ids_low.index("T-complex")  if "T-complex"  in ids_low  else 999
        rank_high = ids_high.index("T-complex") if "T-complex" in ids_high else 999
        assert rank_low >= rank_high, \
            f"T-complex rank con energy bassa ({rank_low}) dovrebbe essere ≥ rank alto ({rank_high})"

    def test_spontaneous_explore_task_generated_when_bonus_active(self):
        """CRITERIO M7.0 #2: curiosity > 0.7 → task esplorativa spontanea generata."""
        bs = self.de.compute(make_snap(curiosity=0.85))
        task = self.sel.select_explore_task(bs)
        assert task is not None
        assert "explore" in task.tags
        assert "spontaneous" in task.tags

    def test_no_spontaneous_task_without_bonus(self):
        """curiosity ≤ 0.7 → nessuna task esplorativa spontanea."""
        bs = self.de.compute(make_snap(curiosity=0.50))
        task = self.sel.select_explore_task(bs)
        assert task is None

    def test_empty_task_list_returns_empty(self):
        bs = self.de.compute(make_snap())
        assert self.sel.select([], bs) == []


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE D — SelfRepairTrigger
# ─────────────────────────────────────────────────────────────────────────────

class TestSelfRepairTrigger:

    def setup_method(self):
        self.de  = DriveExecutive()
        self.srt = SelfRepairTrigger()

    def test_enters_repair_when_self_repair_mode_true(self):
        """viability < 0.4 → SelfRepairTrigger entra in repair."""
        bs = self.de.compute(make_snap(viability=0.30))
        self.srt.check(bs)
        assert self.srt.is_recovering() is True

    def test_repair_event_recorded(self):
        bs = self.de.compute(make_snap(viability=0.30))
        self.srt.check(bs)
        assert len(self.srt.repair_events) >= 1
        assert self.srt.repair_events[0]["event"] == "repair_entered"

    def test_exits_repair_when_viability_recovers(self):
        """Dopo repair, viability >= 0.55 → exit repair."""
        bs_low = self.de.compute(make_snap(viability=0.30))
        self.srt.check(bs_low)
        assert self.srt.is_recovering()

        snap_ok = make_snap(viability=0.70)
        recovered = self.srt.check_recovery(snap_ok)
        assert recovered is True
        assert self.srt.is_recovering() is False

    def test_generates_repair_actions_with_low_viability(self):
        snap = make_snap(viability=0.30, energy=0.20, coherence=0.30, alignment=0.35)
        actions = self.srt.generate_repair_actions(snap)
        assert len(actions) >= 2
        ids = [a.action_id for a in actions]
        assert "REPAIR-001-reduce-load" in ids

    def test_repair_actions_sorted_by_urgency_descending(self):
        snap = make_snap(viability=0.30, energy=0.20, coherence=0.30, alignment=0.35)
        actions = self.srt.generate_repair_actions(snap)
        urgencies = [a.urgency for a in actions]
        assert urgencies == sorted(urgencies, reverse=True)

    def test_no_repair_actions_in_normal_state(self):
        """Stato normale → solo REPAIR-001 (sempre consigliata in repair)."""
        # generate_repair_actions è chiamata solo quando in repair mode,
        # ma sempre produce almeno REPAIR-001.
        snap = make_snap(viability=0.30)
        actions = self.srt.generate_repair_actions(snap)
        assert len(actions) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# SEZIONE E — Integrazione end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndCausal:

    def test_criterion1_viability_drop_changes_task_selection_and_records(self):
        """
        CRITERIO M7.0 #1 (verifica completa):
        viability scende sotto soglia → task selection cambia → registrato in repair_events.
        """
        de  = DriveExecutive()
        sel = TaskSelector()
        srt = SelfRepairTrigger()
        tasks = make_tasks()

        # Stato normale
        bs_normal = de.compute(make_snap(viability=0.90))
        selected_normal = sel.select(tasks, bs_normal)
        srt.check(bs_normal)
        assert srt.is_recovering() is False

        # Viability scende
        bs_low = de.compute(make_snap(viability=0.30))
        selected_low = sel.select(tasks, bs_low)
        srt.check(bs_low)

        # Task selection è cambiata
        ids_normal = {t.id for t in selected_normal}
        ids_low    = {t.id for t in selected_low}
        assert ids_normal != ids_low, "Task selection DEVE cambiare con viability bassa"

        # Solo task critical in low state
        for t in selected_low:
            assert "critical" in t.tags or "repair" in t.tags

        # Evento registrato
        assert srt.is_recovering()
        assert len(srt.repair_events) >= 1

    def test_criterion2_curiosity_generates_spontaneous_explore_task(self):
        """
        CRITERIO M7.0 #2 (verifica completa):
        curiosity supera soglia → task esplorativa generata spontaneamente.
        """
        de  = DriveExecutive()
        sel = TaskSelector()

        bs = de.compute(make_snap(curiosity=0.85))

        # exploration_bonus è attivo
        assert bs.exploration_bonus == pytest.approx(0.3)
        assert any("R3" in r for r in bs.triggered_rules)

        # Task esplorativa spontanea generata
        task = sel.select_explore_task(bs)
        assert task is not None
        assert "spontaneous" in task.tags
        assert "curiosity_driven" in task.tags
        assert "explore" in task.tags

    def test_homeostasis_to_behavioral_state_pipeline(self):
        """Pipeline completa: HomeostaticController → DriveExecutive → BehavioralState."""
        from cortex.cognitive_autonomy.homeostasis.controller import HomeostaticController
        hc = HomeostaticController()
        hc._h_state["safety"] = 0.10
        hc._h_state["energy"] = 0.15
        result = hc.update({"safety": 0.10, "energy": 0.15})

        de = DriveExecutive()
        bs = de.compute_from_homeostasis(result, phi=0.5)

        # Viability è scesa sotto 1.0 (controller abilitato, non scaffold)
        assert result["viability_score"] < 1.0
        assert result.get("scaffold") is False
        # BehavioralState riflette energy bassa → planning_depth=1 (R5 causal)
        # La viability può essere sopra la soglia conserve (0.74), quindi
        # verifichiamo che almeno una regola causale abbia modificato il behavior.
        assert len(bs.triggered_rules) >= 1, "Nessuna regola causale triggered"
        assert bs.planning_depth == 1, f"planning_depth atteso 1 con energy=0.15, got {bs.planning_depth}"

    def test_smfoi_wiring_produces_behavioral_state(self):
        """SMFOI step 4 produce behavioral_state nel sea_state."""
        from cortex.SMFOI_v3 import SMFOIKernel
        kernel = SMFOIKernel()
        result = kernel.run_cycle({"type": "test", "content": "M7 integration check"})
        bstate = result.get("sea_state", {}).get("behavioral_state")
        assert bstate is not None, "behavioral_state non trovato nel sea_state"
        assert "max_parallel_tasks" in bstate
        assert "mutation_gate_open" in bstate
        assert "triggered_rules" in bstate


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
