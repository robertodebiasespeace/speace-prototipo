"""
Test suite AGI Loop — 33 tests
"""
from __future__ import annotations
import sys, time, uuid
sys.path.insert(0, '/sessions/beautiful-affectionate-franklin/mnt/SPEACE-prototipo')

import pytest
from cortex.cognitive_autonomy.integration.agi_loop import (
    CycleInput, CycleOutput, AGIMetrics,
    SurpriseDetector, SurpriseLevel,
    ModuleRegistry,
    SMFOIStepHandler,
    AGILoop, AGISystem, AGILoopStatus, CyclePhase,
    create_agi_loop, create_agi_system,
)
from cortex.cognitive_autonomy.planning.hierarchical_planner import (
    WorldState as PlannerWorldState, create_htn_planner, GoalPriority, Goal
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_world_state(**facts) -> PlannerWorldState:
    return PlannerWorldState(facts)

def make_loop_with_planner() -> AGILoop:
    loop = create_agi_loop()
    planner = create_htn_planner()
    loop.set_planner(planner)
    return loop

def make_full_loop() -> AGILoop:
    loop = make_loop_with_planner()
    from cortex.brain.self_model import create_self_model
    loop.register_module("BRN-019", create_self_model())
    return loop


# ── TestAGIMetrics ─────────────────────────────────────────────────────────────

class TestAGIMetrics:
    def test_initial_state(self):
        m = AGIMetrics()
        assert m.total_cycles == 0
        assert m.successful_cycles == 0

    def test_update_success(self):
        m = AGIMetrics()
        out = CycleOutput(cycle_id="C001", success=True,
                          surprise_level=SurpriseLevel.NONE, duration_ms=5.0)
        m.update(out)
        assert m.total_cycles == 1
        assert m.successful_cycles == 1
        assert m.failed_cycles == 0

    def test_update_failure(self):
        m = AGIMetrics()
        out = CycleOutput(cycle_id="C001", success=False,
                          surprise_level=SurpriseLevel.NONE, duration_ms=5.0)
        m.update(out)
        assert m.failed_cycles == 1

    def test_success_rate_in_to_dict(self):
        m = AGIMetrics()
        m.update(CycleOutput(cycle_id="C1", success=True,
                             surprise_level=SurpriseLevel.NONE, duration_ms=1.0))
        m.update(CycleOutput(cycle_id="C2", success=False,
                             surprise_level=SurpriseLevel.NONE, duration_ms=1.0))
        d = m.to_dict()
        assert d["success_rate"] == pytest.approx(0.5)

    def test_avg_cycle_ms(self):
        m = AGIMetrics()
        for ms in [10.0, 20.0, 30.0]:
            m.update(CycleOutput(cycle_id=f"C{ms}", success=True,
                                 surprise_level=SurpriseLevel.NONE, duration_ms=ms))
        assert m.avg_cycle_ms == pytest.approx(20.0)

    def test_surprise_counted(self):
        m = AGIMetrics()
        m.update(CycleOutput(cycle_id="C1", success=True,
                             surprise_level=SurpriseLevel.HIGH, duration_ms=1.0))
        assert m.total_surprises == 1


# ── TestSurpriseDetector ───────────────────────────────────────────────────────

class TestSurpriseDetector:
    def test_new_key_is_surprising(self):
        sd = SurpriseDetector()
        level, keys = sd.detect({"new_signal": 1.0})
        assert "new_signal" in keys
        assert level != SurpriseLevel.NONE

    def test_known_stable_key_not_surprising(self):
        sd = SurpriseDetector()
        for _ in range(10):
            sd.detect({"temp": 22.0})
        level, keys = sd.detect({"temp": 22.5})
        assert "temp" not in keys

    def test_large_deviation_is_surprising(self):
        sd = SurpriseDetector(novelty_threshold=0.1)
        for _ in range(10):
            sd.detect({"temp": 20.0})
        level, keys = sd.detect({"temp": 100.0})  # huge jump
        assert "temp" in keys

    def test_multiple_surprises_level_high(self):
        sd = SurpriseDetector()
        stimuli = {f"signal_{i}": float(i) for i in range(5)}
        level, keys = sd.detect(stimuli)
        assert level in (SurpriseLevel.HIGH, SurpriseLevel.CRITICAL)

    def test_empty_stimuli_no_surprise(self):
        sd = SurpriseDetector()
        level, keys = sd.detect({})
        assert level == SurpriseLevel.NONE
        assert keys == []


# ── TestModuleRegistry ─────────────────────────────────────────────────────────

class TestModuleRegistry:
    def test_register_and_get(self):
        mr = ModuleRegistry()
        mr.register("BRN-019", object())
        assert mr.get("BRN-019") is not None

    def test_disabled_returns_none(self):
        mr = ModuleRegistry()
        obj = object()
        mr.register("BRN-019", obj, enabled=False)
        assert mr.get("BRN-019") is None

    def test_enable_disable(self):
        mr = ModuleRegistry()
        mr.register("BRN-019", object())
        mr.disable("BRN-019")
        assert mr.get("BRN-019") is None
        mr.enable("BRN-019")
        assert mr.get("BRN-019") is not None

    def test_active_ids(self):
        mr = ModuleRegistry()
        mr.register("A", object())
        mr.register("B", object(), enabled=False)
        assert "A" in mr.active_ids()
        assert "B" not in mr.active_ids()

    def test_active_count(self):
        mr = ModuleRegistry()
        mr.register("A", object())
        mr.register("B", object())
        mr.register("C", object(), enabled=False)
        assert mr.active_count == 2


# ── TestSMFOIStepHandler ───────────────────────────────────────────────────────

class TestSMFOIStepHandler:
    def setup_method(self):
        self.handler = SMFOIStepHandler()
        self.registry = ModuleRegistry()
        self.ci = CycleInput(cycle_id="TEST", stimuli={}, world_state=None)

    def test_step1_no_self_model(self):
        r = self.handler.step1_self_location(self.ci, self.registry)
        assert r["phase"] == "located"
        assert "integrity" in r

    def test_step1_with_self_model(self):
        from cortex.brain.self_model import create_self_model
        sm = create_self_model()
        self.registry.register("BRN-019", sm)
        r = self.handler.step1_self_location(self.ci, self.registry)
        assert r["integrity"] == pytest.approx(1.0)

    def test_step2_returns_active_modules(self):
        self.registry.register("BRN-017", object())
        r = self.handler.step2_constraint_mapping(self.ci, self.registry)
        assert "BRN-017" in r["active_modules"]
        assert r["phase"] == "mapped"

    def test_step3_surprise_detection(self):
        sd = SurpriseDetector()
        ci = CycleInput(cycle_id="T", stimuli={"novel_key": 1.0})
        r = self.handler.step3_push_detection(ci, self.registry, sd)
        assert r["phase"] == "detected"
        assert r["surprise_level"] != SurpriseLevel.NONE.value

    def test_step5_no_planner_safe(self):
        r = self.handler.step5_output_action(self.ci, self.registry, None)
        assert r["phase"] == "acted"
        assert r["status"] == "no_planner"


# ── TestAGILoop ────────────────────────────────────────────────────────────────

class TestAGILoop:
    def test_init_status(self):
        loop = create_agi_loop()
        assert loop.status == AGILoopStatus.INIT

    def test_tick_returns_output(self):
        loop = create_agi_loop()
        out = loop.tick()
        assert isinstance(out, CycleOutput)
        assert out.cycle_id.startswith("C0001")

    def test_tick_increments_cycle(self):
        loop = create_agi_loop()
        loop.tick()
        loop.tick()
        assert loop._cycle_counter == 2

    def test_tick_with_planner_generates_action(self):
        loop = make_loop_with_planner()
        ws = make_world_state(brn_017_active=True)
        goal = loop.create_goal("analyze_situation", {"causal_analysis_done": True})
        loop.add_goal(goal)
        out = loop.tick(ws)
        assert out.action_taken is not None

    def test_tick_phases_in_output(self):
        loop = create_agi_loop()
        out = loop.tick()
        phases = out.phase_results
        assert "step1_self_location" in phases
        assert "step2_constraint_mapping" in phases
        assert "step3_push_detection" in phases
        assert "step4_evolution_stack" in phases
        assert "step5_output_action" in phases
        assert "step6_outcome_evaluation" in phases

    def test_surprise_detection_propagates(self):
        loop = create_agi_loop()
        out = loop.tick(stimuli={"brand_new_signal": 42.0})
        assert out.surprise_level != SurpriseLevel.NONE

    def test_run_n_cycles(self):
        loop = make_loop_with_planner()
        ws = make_world_state(brn_017_active=True)
        goal = loop.create_goal("analyze_situation", {"causal_analysis_done": True})
        loop.add_goal(goal)
        outputs = loop.run(ws, n_cycles=3)
        assert len(outputs) == 3
        assert all(isinstance(o, CycleOutput) for o in outputs)

    def test_metrics_updated_after_tick(self):
        loop = create_agi_loop()
        loop.tick()
        assert loop.metrics.total_cycles == 1

    def test_get_last_output(self):
        loop = create_agi_loop()
        loop.tick()
        last = loop.get_last_output()
        assert last is not None
        assert last.cycle_id == "C0001-" + loop.loop_id

    def test_hook_called(self):
        loop = create_agi_loop()
        hook_results = []
        loop.add_hook(lambda out: hook_results.append(out.cycle_id))
        loop.tick()
        assert len(hook_results) == 1

    def test_stopped_loop_returns_error(self):
        loop = create_agi_loop()
        loop.stop()
        out = loop.tick()
        assert not out.success
        assert "stopped" in out.cycle_id.lower()

    def test_get_status_structure(self):
        loop = create_agi_loop()
        loop.tick()
        status = loop.get_status()
        assert status["loop_id"] == loop.loop_id
        assert "metrics" in status
        assert status["cycle_count"] == 1


# ── TestAGISystem ──────────────────────────────────────────────────────────────

class TestAGISystem:
    def test_wire_all_registers_modules(self):
        sys = AGISystem().wire_all()
        assert len(sys.modules) >= 3   # at minimum BRN-019, BRN-020, HTN_PLANNER

    def test_tick_returns_output(self):
        sys = AGISystem().wire_all()
        ws = make_world_state(brn_017_active=True, brn_020_active=True)
        out = sys.tick(ws)
        assert isinstance(out, CycleOutput)

    def test_get_status_wired(self):
        sys = AGISystem().wire_all()
        status = sys.get_status()
        assert status["wired"] is True
        assert "loop" in status

    def test_full_3_cycle_run(self):
        sys = AGISystem().wire_all()
        ws = make_world_state(brn_017_active=True, brn_020_active=True)
        goal = sys.loop.create_goal("analyze_situation", {"causal_analysis_done": True})
        sys.loop.add_goal(goa