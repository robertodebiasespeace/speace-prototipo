"""Test suite HTN Planner — 38 tests"""
from __future__ import annotations
import sys, time, uuid
sys.path.insert(0, '/sessions/beautiful-affectionate-franklin/mnt/SPEACE-prototipo')
import pytest

from cortex.cognitive_autonomy.planning.hierarchical_planner import (
    WorldState, Goal, GoalPriority, GoalStack,
    PrimitiveTask, CompoundTask, TaskStatus,
    Method, MethodLibrary,
    Plan, PlanStatus, PlanMonitor,
    HTNPlanner, HierarchicalPlanningSystem,
    create_htn_planner,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_goal(name="test_goal", conditions=None, priority=GoalPriority.MEDIUM):
    return Goal(
        goal_id=f"G-{uuid.uuid4().hex[:6]}",
        name=name,
        conditions=conditions or {"done": True},
        priority=priority,
    )

def make_primitive(name="do_thing", pre=None, effects=None):
    return PrimitiveTask(
        task_id=f"T-{uuid.uuid4().hex[:6]}",
        name=name,
        preconditions=pre or {},
        effects=effects or {"done": True},
    )


# ── TestWorldState ─────────────────────────────────────────────────────────────

class TestWorldState:
    def test_set_and_get(self):
        ws = WorldState()
        ws.set("x", 42)
        assert ws.get("x") == 42

    def test_holds_true(self):
        ws = WorldState({"active": True})
        assert ws.holds("active") is True

    def test_holds_false(self):
        ws = WorldState()
        assert ws.holds("missing") is False

    def test_all_hold(self):
        ws = WorldState({"a": True, "b": True})
        assert ws.all_hold(["a", "b"]) is True

    def test_all_hold_fails(self):
        ws = WorldState({"a": True})
        assert ws.all_hold(["a", "b"]) is False

    def test_satisfies(self):
        ws = WorldState({"x": 1, "y": 2})
        assert ws.satisfies({"x": 1}) is True
        assert ws.satisfies({"x": 9}) is False

    def test_apply_effects(self):
        ws = WorldState()
        ws.apply_effects({"done": True, "value": 5})
        assert ws.holds("done")
        assert ws.get("value") == 5

    def test_copy_independence(self):
        ws = WorldState({"a": 1})
        ws2 = ws.copy()
        ws2.set("a", 99)
        assert ws.get("a") == 1   # original unchanged

    def test_delta(self):
        ws1 = WorldState({"a": 1, "b": 2})
        ws2 = WorldState({"a": 1, "b": 99})
        d = ws1.delta(ws2)
        assert "b" in d
        assert "a" not in d


# ── TestGoal ───────────────────────────────────────────────────────────────────

class TestGoal:
    def test_is_satisfied(self):
        goal = make_goal(conditions={"done": True})
        ws = WorldState({"done": True})
        assert goal.is_satisfied(ws) is True

    def test_not_satisfied(self):
        goal = make_goal(conditions={"done": True})
        ws = WorldState({"done": False})
        assert goal.is_satisfied(ws) is False

    def test_not_expired_no_deadline(self):
        goal = make_goal()
        assert goal.is_expired is False

    def test_expired_past_deadline(self):
        goal = Goal(
            goal_id="G-X", name="g", conditions={},
            deadline=time.time() - 10
        )
        assert goal.is_expired is True


# ── TestGoalStack ──────────────────────────────────────────────────────────────

class TestGoalStack:
    def test_push_and_len(self):
        gs = GoalStack()
        gs.push(make_goal())
        assert len(gs) == 1

    def test_highest_priority_critical(self):
        gs = GoalStack()
        gs.push(make_goal("low", priority=GoalPriority.LOW))
        gs.push(make_goal("critical", priority=GoalPriority.CRITICAL))
        top = gs.get_highest_priority()
        assert top.name == "critical"

    def test_remove_satisfied(self):
        gs = GoalStack()
        gs.push(make_goal("g1", conditions={"a": True}))
        gs.push(make_goal("g2", conditions={"b": True}))
        ws = WorldState({"a": True})
        removed = gs.remove_satisfied(ws)
        assert any(g.name == "g1" for g in removed)
        assert len(gs) == 1

    def test_remove_expired(self):
        gs = GoalStack()
        gs.push(Goal("X", "expired", {}, deadline=time.time()-1))
        gs.push(make_goal("fresh"))
        gs.remove_expired()
        assert len(gs) == 1


# ── TestPrimitiveTask ──────────────────────────────────────────────────────────

class TestPrimitiveTask:
    def test_can_execute_no_preconditions(self):
        t = make_primitive()
        ws = WorldState()
        assert t.can_execute(ws) is True

    def test_can_execute_preconditions_met(self):
        t = make_primitive(pre={"ready": True})
        ws = WorldState({"ready": True})
        assert t.can_execute(ws) is True

    def test_cannot_execute_preconditions_unmet(self):
        t = make_primitive(pre={"ready": True})
        ws = WorldState()
        assert t.can_execute(ws) is False

    def test_execute_applies_effects(self):
        t = make_primitive(effects={"done": True, "count": 5})
        ws = WorldState()
        success = t.execute(ws)
        assert success is True
        assert ws.holds("done")
        assert ws.get("count") == 5

    def test_execute_sets_completed(self):
        t = make_primitive()
        ws = WorldState()
        t.execute(ws)
        assert t.status == TaskStatus.COMPLETED

    def test_execute_fails_when_blocked(self):
        t = make_primitive(pre={"needed": True})
        ws = WorldState()   # no "needed"
        success = t.execute(ws)
        assert success is False
        assert t.status == TaskStatus.BLOCKED


# ── TestMethodLibrary ──────────────────────────────────────────────────────────

class TestMethodLibrary:
    def test_register_and_count(self):
        ml = MethodLibrary()
        m = Method("M1", "Test", "do_thing", subtask_specs=[])
        ml.register(m)
        assert ml.method_count == 1

    def test_get_applicable_all_conditions_met(self):
        ml = MethodLibrary()
        m = Method("M1", "T", "do_thing", preconditions={"ok": True}, subtask_specs=[])
        ml.register(m)
        ws = WorldState({"ok": True})
        result = ml.get_applicable("do_thing", ws)
        assert len(result) == 1

    def test_get_applicable_conditions_not_met(self):
        ml = MethodLibrary()
        m = Method("M1", "T", "do_thing", preconditions={"ok": True}, subtask_specs=[])
        ml.register(m)
        ws = WorldState()
        result = ml.get_applicable("do_thing", ws)
        assert result == []

    def test_speace_defaults_loaded(self):
        ml = MethodLibrary()
        ml.register_speace_defaults()
        assert ml.method_count == 4
        assert ml.has_methods_for("analyze_situation")
        assert ml.has_methods_for("self_improve")


# ── TestHTNPlanner ─────────────────────────────────────────────────────────────

class TestHTNPlanner:
    def setup_method(self):
        self.ml = MethodLibrary()
        self.ml.register_speace_defaults()
        self.planner = HTNPlanner(self.ml)

    def test_plan_already_satisfied(self):
        goal = Goal("G1", "analyze_situation", {"causal_analysis_done": True})
        ws = WorldState({"causal_analysis_done": True})
        plan = self.planner.plan(goal, ws)
        assert plan is not None
        assert plan.status == PlanStatus.COMPLETED

    def test_plan_generates_steps(self):
        goal = Goal("G1", "analyze_situation", {"causal_analysis_done": True})
        ws = WorldState({"brn_017_active": True})
        plan = self.planner.plan(goal, ws)
        assert plan is not None
        assert len(plan.steps) == 3

    def test_plan_step_names(self):
        goal = Goal("G1", "analyze_situation", {"causal_analysis_done": True})
        ws = WorldState({"brn_017_active": True})
        plan = self.planner.plan(goal, ws)
        names = [s.name for s in plan.steps]
        assert "load_causal_graph" in names

    def test_plan_fails_no_method(self):
        goal = Goal("G1", "unknown_task_xyz", {"xyz_done": True})
        ws = WorldState()
        plan = self.planner.plan(goal, ws)
        assert plan.status == PlanStatus.FAILED

    def test_plan_self_improve(self):
        goal = Goal("G2", "self_improve", {"proposals_submitted": True})
        ws = WorldState({"brn_020_active": True})
        plan = self.planner.plan(goal, ws)
        assert plan is not None
        assert len(plan.steps) == 3

    def test_plan_world_model(self):
        goal = Goal("G3", "update_world_model", {"beliefs_propagated": True})
        ws = WorldState()
        plan = self.planner.plan(goal, ws)
        assert plan is not None
        assert len(plan.steps) == 3

    def test_plan_stats_increment(self):
        goal = Goal("G1", "analyze_situation", {"causal_analysis_done": True})
        ws = WorldState({"brn_017_active": True})
        self.planner.plan(goal, ws)
        stats = self.planner.get_stats()
        assert stats["plans_generated"] >= 1


# ── TestHierarchicalPlanningSystem ─────────────────────────────────────────────

class TestHierarchicalPlanningSystem:
    def test_init(self):
        hps = create_htn_planner()
        assert hps.method_library.method_count == 4

    def test_add_and_generate_plan(self):
        hps = create_htn_planner()
        ws = WorldState({"brn_017_active": True})
        goal = hps.create_goal("analyze_situation", {"causal_analysis_done": True})
        hps.add_goal(goal)
        plan = hps.generate_plan_for_top_goal(ws)
        assert plan is not None
        assert len(plan.steps) > 0

    def test_execute_next_step(self):
        hps = create_htn_planner()
        ws = WorldState({"brn_017_active": True})
        goal = hps.create_goal("analyze_situation", {"causal_analysis_done": True})
        hps.add_goal(goal)
        hps.generate_plan_for_top_goal(ws)
        result = hps.execute_next_step(ws)
        assert result["status"] == "executed"

    def test_execute_all_steps(self):
        hps = create_htn_planner()
        ws = WorldState({"brn_017_active": True})
        goal = hps.create_goal("analyze_situation", {"causal_analysis_done": True})
        hps.add_goal(goal)
        plan = hps.generate_plan_for_top_goal(ws)
        n_steps = len(plan.steps)
        for _ in range(n_steps):
            result = hps.execute_next_step(ws)
            assert result["status"] == "executed"
        assert plan.is_complete

    def test_no_plan_without_goals(self):
        hps = create_htn_planner()
        ws = WorldState()
        plan = hps.generate_plan_for_top_goal(ws)
        assert plan is None

    def test_get_status(self):
        hps = create_htn_planner()
        status = hps.get_status()
        assert "acti