"""
SPEACE HTN Planner — Hierarchical Task Network Planning
Implements long-term goal-oriented planning with task decomposition.

Theoretical foundations:
  - HTN Planning (Sacerdoti 1975, Erol et al. 1994): goals are decomposed into
    sub-tasks via methods until only primitive (executable) actions remain.
  - SHOP2 (Nau et al. 2003): forward-chaining HTN planner used in real-world AI
  - Goal Stack Planning (Newell & Simon 1972): LIFO goal resolution
  - Plan Monitoring & Re-planning (Wilkins 1988): detect plan failures, re-plan

Integration:
  - BRN-019 SelfModel: reads limitations → avoids planning with offline modules
  - BRN-020 RecursiveSelfImprover: proposes plan optimizations as code changes
  - BRN-017 CausalReasoner: uses causal structure for precondition inference
  - AGILoop: main consumer of plan steps (task 6)

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Enumerazioni
# ──────────────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING    = "pending"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    FAILED     = "failed"
    BLOCKED    = "blocked"


class PlanStatus(str, Enum):
    DRAFT      = "draft"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    FAILED     = "failed"
    REPLANNING = "replanning"


class GoalPriority(str, Enum):
    CRITICAL = "critical"   # survival / safety
    HIGH     = "high"       # main objectives
    MEDIUM   = "medium"     # evolution tasks
    LOW      = "low"        # nice-to-have


# ──────────────────────────────────────────────────────────────────────────────
#  World State
# ──────────────────────────────────────────────────────────────────────────────

class WorldState:
    """
    Partial representation of SPEACE's current world state.
    Uses a flat key-value store with typed predicates.
    Supports logical queries (holds, all_hold).
    """

    def __init__(self, facts: Optional[Dict[str, Any]] = None) -> None:
        self._facts: Dict[str, Any] = facts.copy() if facts else {}

    def set(self, key: str, value: Any) -> None:
        self._facts[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._facts.get(key, default)

    def holds(self, predicate: str) -> bool:
        """Check if a boolean predicate is True."""
        return bool(self._facts.get(predicate, False))

    def all_hold(self, predicates: List[str]) -> bool:
        """Check if all predicates hold."""
        return all(self.holds(p) for p in predicates)

    def any_holds(self, predicates: List[str]) -> bool:
        return any(self.holds(p) for p in predicates)

    def copy(self) -> "WorldState":
        return WorldState(self._facts.copy())

    def apply_effects(self, effects: Dict[str, Any]) -> None:
        """Apply an action's effects to the state."""
        for k, v in effects.items():
            self._facts[k] = v

    def satisfies(self, goal_conditions: Dict[str, Any]) -> bool:
        """Check if the world state satisfies all goal conditions."""
        for k, v in goal_conditions.items():
            if self._facts.get(k) != v:
                return False
        return True

    def delta(self, other: "WorldState") -> Dict[str, Any]:
        """Return facts that differ between self and other."""
        diffs = {}
        all_keys = set(self._facts) | set(other._facts)
        for k in all_keys:
            v1, v2 = self._facts.get(k), other._facts.get(k)
            if v1 != v2:
                diffs[k] = (v1, v2)
        return diffs

    def to_dict(self) -> Dict:
        return dict(self._facts)


# ──────────────────────────────────────────────────────────────────────────────
#  Task & Goal
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Goal:
    """A goal SPEACE wants to achieve."""
    goal_id: str
    name: str
    conditions: Dict[str, Any]          # world-state conditions to satisfy
    priority: GoalPriority = GoalPriority.MEDIUM
    deadline: Optional[float] = None    # unix timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        if self.deadline is None:
            return False
        return time.time() > self.deadline

    def is_satisfied(self, world_state: WorldState) -> bool:
        return world_state.satisfies(self.conditions)


@dataclass
class PrimitiveTask:
    """
    An atomic, executable action (HTN leaf node).
    Preconditions must hold; effects are applied to world state on execution.
    """
    task_id: str
    name: str
    preconditions: Dict[str, Any] = field(default_factory=dict)   # must hold before exec
    effects: Dict[str, Any] = field(default_factory=dict)          # applied after exec
    cost: float = 1.0
    required_modules: List[str] = field(default_factory=list)      # e.g. ["BRN-017"]
    executor: Optional[Callable] = field(default=None, repr=False)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def can_execute(self, world_state: WorldState) -> bool:
        return world_state.satisfies(self.preconditions)

    def execute(self, world_state: WorldState) -> bool:
        """Execute the task, apply effects, return success."""
        if not self.can_execute(world_state):
            self.status = TaskStatus.BLOCKED
            return False
        self.status = TaskStatus.ACTIVE
        self.started_at = time.time()
        try:
            if self.executor is not None:
                self.result = self.executor(world_state)
            world_state.apply_effects(self.effects)
            self.status = TaskStatus.COMPLETED
            self.completed_at = time.time()
            return True
        except Exception as e:
            logger.error("PrimitiveTask %s failed: %s", self.task_id, e)
            self.status = TaskStatus.FAILED
            return False


@dataclass
class CompoundTask:
    """
    A non-primitive task that must be decomposed via a Method.
    Analogous to an HTN compound task.
    """
    task_id: str
    name: str
    priority: GoalPriority = GoalPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING


# ──────────────────────────────────────────────────────────────────────────────
#  Method (HTN Decomposition)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Method:
    """
    An HTN method: decomposition rule for a CompoundTask.
    Preconditions specify when this method is applicable.
    Subtasks is an ordered list of task specs (compound or primitive).
    """
    method_id: str
    name: str
    compound_task_name: str       # which compound task this decomposes
    preconditions: Dict[str, Any] = field(default_factory=dict)
    subtask_specs: List[Dict[str, Any]] = field(default_factory=list)
    cost: float = 0.0
    priority: int = 0             # higher = preferred when multiple methods apply

    def is_applicable(self, world_state: WorldState) -> bool:
        return world_state.satisfies(self.preconditions)


# ──────────────────────────────────────────────────────────────────────────────
#  Plan
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Plan:
    """
    A totally-ordered plan: a sequence of PrimitiveTasks to execute.
    Generated by the HTN planner.
    """
    plan_id: str
    goal: Goal
    steps: List[PrimitiveTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    current_step_index: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    total_cost: float = 0.0
    execution_trace: List[Dict] = field(default_factory=list)

    def add_step(self, task: PrimitiveTask) -> None:
        self.steps.append(task)
        self.total_cost += task.cost

    @property
    def current_step(self) -> Optional[PrimitiveTask]:
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0
        return self.current_step_index / len(self.steps)

    def advance(self) -> None:
        self.current_step_index += 1
        if self.is_complete:
            self.status = PlanStatus.COMPLETED
            self.completed_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal.name,
            "status": self.status.value,
            "steps": len(self.steps),
            "progress": round(self.progress, 3),
            "total_cost": round(self.total_cost, 2),
            "current_step": (
                self.current_step.name if self.current_step else None
            ),
        }


# ──────────────────────────────────────────────────────────────────────────────
#  MethodLibrary
# ──────────────────────────────────────────────────────────────────────────────

class MethodLibrary:
    """Registry of decomposition methods for compound tasks."""

    def __init__(self) -> None:
        self._methods: Dict[str, List[Method]] = defaultdict(list)

    def register(self, method: Method) -> None:
        self._methods[method.compound_task_name].append(method)
        # Keep sorted by priority (descending)
        self._methods[method.compound_task_name].sort(
            key=lambda m: m.priority, reverse=True
        )
        logger.debug("MethodLibrary: registered method %s for %s",
                     method.method_id, method.compound_task_name)

    def get_applicable(
        self, compound_task_name: str, world_state: WorldState
    ) -> List[Method]:
        """Return all applicable methods for a compound task, by priority."""
        return [
            m for m in self._methods.get(compound_task_name, [])
            if m.is_applicable(world_state)
        ]

    def has_methods_for(self, task_name: str) -> bool:
        return task_name in self._methods and bool(self._methods[task_name])

    @property
    def method_count(self) -> int:
        return sum(len(v) for v in self._methods.values())

    def register_speace_defaults(self) -> None:
        """Register default SPEACE planning methods."""
        # ── Causal analysis method ─────────────────────────────────────────
        self.register(Method(
            method_id="M-CAUSAL-001",
            name="CausalAnalysisMethod",
            compound_task_name="analyze_situation",
            preconditions={"brn_017_active": True},
            subtask_specs=[
                {"name": "load_causal_graph",     "type": "primitive",
                 "effects": {"causal_graph_loaded": True}},
                {"name": "run_do_calculus",        "type": "primitive",
                 "preconditions": {"causal_graph_loaded": True},
                 "effects": {"causal_analysis_done": True}},
                {"name": "compute_counterfactuals","type": "primitive",
                 "preconditions": {"causal_analysis_done": True},
                 "effects": {"counterfactuals_ready": True}},
            ],
            priority=10,
        ))
        # ── Evolution cycle method ─────────────────────────────────────────
        self.register(Method(
            method_id="M-EVOL-001",
            name="EvolutionCycleMethod",
            compound_task_name="self_improve",
            preconditions={"brn_020_active": True},
            subtask_specs=[
                {"name": "inspect_modules",        "type": "primitive",
                 "effects": {"inspection_done": True}},
                {"name": "generate_proposals",     "type": "primitive",
                 "preconditions": {"inspection_done": True},
                 "effects": {"proposals_generated": True}},
                {"name": "submit_safe_proposals",  "type": "primitive",
                 "preconditions": {"proposals_generated": True},
                 "effects": {"proposals_submitted": True}},
            ],
            priority=8,
        ))
        # ── World model update method ──────────────────────────────────────
        self.register(Method(
            method_id="M-WORLD-001",
            name="WorldModelUpdateMethod",
            compound_task_name="update_world_model",
            preconditions={},
            subtask_specs=[
                {"name": "fetch_external_data",   "type": "primitive",
                 "effects": {"data_fetched": True}},
                {"name": "update_knowledge_graph", "type": "primitive",
                 "preconditions": {"data_fetched": True},
                 "effects": {"knowledge_graph_updated": True}},
                {"name": "propagate_beliefs",      "type": "primitive",
                 "preconditions": {"knowledge_graph_updated": True},
                 "effects": {"beliefs_propagated": True}},
            ],
            priority=5,
        ))
        # ── Abstract reasoning method ──────────────────────────────────────
        self.register(Method(
            method_id="M-ABSTRACT-001",
            name="AbstractReasoningMethod",
            compound_task_name="transfer_knowledge",
            preconditions={"brn_018_active": True},
            subtask_specs=[
                {"name": "find_analogies",         "type": "primitive",
                 "effects": {"analogies_found": True}},
                {"name": "blend_concepts",         "type": "primitive",
                 "preconditions": {"analogies_found": True},
                 "effects": {"concepts_blended": True}},
                {"name": "abstract_principles",    "type": "primitive",
                 "preconditions": {"concepts_blended": True},
                 "effects": {"principles_abstracted": True}},
            ],
            priority=7,
        ))


# ──────────────────────────────────────────────────────────────────────────────
#  Goal Stack Planner
# ──────────────────────────────────────────────────────────────────────────────

class GoalStack:
    """
    LIFO goal stack (Newell & Simon 1972).
    Goals are pushed and resolved top-down.
    """

    def __init__(self) -> None:
        self._stack: List[Goal] = []

    def push(self, goal: Goal) -> None:
        self._stack.append(goal)

    def pop(self) -> Optional[Goal]:
        return self._stack.pop() if self._stack else None

    def peek(self) -> Optional[Goal]:
        return self._stack[-1] if self._stack else None

    def remove_satisfied(self, world_state: WorldState) -> List[Goal]:
        """Remove and return goals that are now satisfied."""
        satisfied = [g for g in self._stack if g.is_satisfied(world_state)]
        self._stack = [g for g in self._stack if not g.is_satisfied(world_state)]
        return satisfied

    def remove_expired(self) -> List[Goal]:
        expired = [g for g in self._stack if g.is_expired]
        self._stack = [g for g in self._stack if not g.is_expired]
        return expired

    def get_highest_priority(self) -> Optional[Goal]:
        """Return the highest-priority non-expired goal."""
        active = [g for g in self._stack if not g.is_expired]
        if not active:
            return None
        priority_order = {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.MEDIUM: 2,
            GoalPriority.LOW: 3,
        }
        return min(active, key=lambda g: priority_order[g.priority])

    def __len__(self) -> int:
        return len(self._stack)


# ──────────────────────────────────────────────────────────────────────────────
#  HTN Planner (core)
# ──────────────────────────────────────────────────────────────────────────────

class HTNPlanner:
    """
    Hierarchical Task Network Planner.

    Algorithm (SHOP2-inspired, forward-chaining):
      1. Take the first task from the task network
      2. If primitive and preconditions hold: add to plan, apply effects, continue
      3. If compound: find applicable method, decompose, push subtasks
      4. If no method found: backtrack or fail
      5. Repeat until network empty (plan found) or exhausted (fail)

    Max recursion depth: configurable (default 10).
    """

    def __init__(
        self,
        method_library: Optional[MethodLibrary] = None,
        max_depth: int = 10,
        max_steps: int = 50,
    ) -> None:
        self.method_library = method_library or MethodLibrary()
        self.max_depth      = max_depth
        self.max_steps      = max_steps
        self._planning_stats: Dict[str, int] = defaultdict(int)

    def plan(self, goal: Goal, initial_state: WorldState) -> Optional[Plan]:
        """
        Generate a totally-ordered plan for `goal` starting from `initial_state`.
        Returns None if no plan found.
        """
        # Check if goal is already satisfied
        if goal.is_satisfied(initial_state):
            plan = Plan(
                plan_id=f"PLAN-{uuid.uuid4().hex[:8].upper()}",
                goal=goal,
                status=PlanStatus.COMPLETED,
            )
            plan.completed_at = time.time()
            return plan

        plan = Plan(
            plan_id=f"PLAN-{uuid.uuid4().hex[:8].upper()}",
            goal=goal,
        )

        state_copy = initial_state.copy()
        # Convert goal conditions into an initial compound task
        task_network: Deque[Dict] = deque()
        # Create one compound task per goal
        task_network.append({
            "type": "compound",
            "name": self._goal_to_task_name(goal),
            "goal": goal,
        })

        success = self._decompose(task_network, state_copy, plan, depth=0)
        if success:
            plan.status = PlanStatus.ACTIVE
            self._planning_stats["plans_generated"] += 1
            logger.info("HTNPlanner: plan %s generated (%d steps)",
                        plan.plan_id, len(plan.steps))
        else:
            plan.status = PlanStatus.FAILED
            self._planning_stats["plans_failed"] += 1
            logger.warning("HTNPlanner: no plan found for goal %s", goal.name)
        return plan

    def _goal_to_task_name(self, goal: Goal) -> str:
        """Map a goal name to a compound task name (convention: snake_case)."""
        return goal.name.lower().replace(" ", "_").replace("-", "_")

    def _decompose(
        self,
        task_network: Deque[Dict],
        state: WorldState,
        plan: Plan,
        depth: int,
    ) -> bool:
        """Recursive HTN decomposition. Returns True if plan found."""
        if depth > self.max_depth:
            logger.debug("HTNPlanner: max depth %d exceeded", self.max_depth)
            return False

        if not task_network:
            # Empty network — check if goal satisfied
            return plan.goal.is_satisfied(state)

        if len(plan.steps) >= self.max_steps:
            logger.debug("HTNPlanner: max steps exceeded")
            return False

        task_spec = task_network.popleft()

        if task_spec["type"] == "primitive":
            primitive = self._make_primitive(task_spec, plan.plan_id)
            if not primitive.can_execute(state):
                # Re-queue at front — try again after other tasks
                task_network.appendleft(task_spec)
                # Try proceeding anyway (optimistic execution)
                # For safety, just fail this branch
                return False
            plan.add_step(primitive)
            state.apply_effects(primitive.effects)
            return self._decompose(task_network, state, plan, depth)

        elif task_spec["type"] == "compound":
            task_name = task_spec["name"]
            methods = self.method_library.get_applicable(task_name, state)
            if not methods:
                # No method: if goal satisfied already, ok; else fail
                if plan.goal.is_satisfied(state):
                    return True
                logger.debug("HTNPlanner: no applicable method for %s", task_name)
                return False

            # Try methods in priority order
            for method in methods:
                saved_state  = state.copy()
                saved_steps  = len(plan.steps)
                saved_cost   = plan.total_cost

                # Build subtask network from method
                subtask_network: Deque[Dict] = deque(method.subtask_specs)
                subtask_network.extend(task_network)  # remaining tasks after

                success = self._decompose(subtask_network, state, plan, depth + 1)
                if success:
                    return True

                # Backtrack
                state._facts = saved_state._facts.copy()
                del plan.steps[saved_steps:]
                plan.total_cost = saved_cost

            return False

        else:
            logger.warning("HTNPlanner: unknown task type %s", task_spec.get("type"))
            return False

    def _make_primitive(self, spec: Dict, plan_id: str) -> PrimitiveTask:
        """Create a PrimitiveTask from a spec dict."""
        return PrimitiveTask(
            task_id=f"{plan_id}-T{uuid.uuid4().hex[:6].upper()}",
            name=spec.get("name", "unnamed"),
            preconditions=spec.get("preconditions", {}),
            effects=spec.get("effects", {}),
            cost=spec.get("cost", 1.0),
            required_modules=spec.get("required_modules", []),
        )

    def get_stats(self) -> Dict[str, int]:
        return dict(self._planning_stats)


# ──────────────────────────────────────────────────────────────────────────────
#  Plan Monitor & Re-planner
# ──────────────────────────────────────────────────────────────────────────────

class PlanMonitor:
    """
    Monitors plan execution and detects failures.
    Triggers re-planning when a step fails or world state deviates.
    """

    def __init__(self) -> None:
        self._failure_log: List[Dict] = []
        self._replanning_count: int = 0

    def check_preconditions(
        self, plan: Plan, world_state: WorldState
    ) -> bool:
        """Check if the current step's preconditions still hold."""
        step = plan.current_step
        if step is None:
            return True
        return step.can_execute(world_state)

    def record_failure(self, plan: Plan, reason: str) -> None:
        self._failure_log.append({
            "plan_id": plan.plan_id,
            "step_index": plan.current_step_index,
            "step_name": plan.current_step.name if plan.current_step else None,
            "reason": reason,
            "timestamp": time.time(),
        })
        logger.warning("PlanMonitor: plan %s failure at step %d: %s",
                       plan.plan_id, plan.current_step_index, reason)

    def needs_replanning(self, plan: Plan, world_state: WorldState) -> bool:
        """Heuristic: needs replanning if current step blocked or plan failed."""
        if plan.status == PlanStatus.FAILED:
            return True
        if plan.current_step and not plan.current_step.can_execute(world_state):
            return True
        return False

    def trigger_replan(
        self,
        planner: HTNPlanner,
        goal: Goal,
        world_state: WorldState,
    ) -> Optional[Plan]:
        """Re-plan from current state."""
        self._replanning_count += 1
        logger.info("PlanMonitor: triggering re-plan #%d for goal %s",
                    self._replanning_count, goal.name)
        return planner.plan(goal, world_state)

    @property
    def failure_count(self) -> int:
        return len(self._failure_log)

    @property
    def replanning_count(self) -> int:
        return self._replanning_count


# ──────────────────────────────────────────────────────────────────────────────
#  HierarchicalPlanningSystem (main facade)
# ──────────────────────────────────────────────────────────────────────────────

class HierarchicalPlanningSystem:
    """
    Main facade for SPEACE's long-term planning capability.

    Integrates:
      - GoalStack: manages multiple concurrent goals
      - MethodLibrary: knows how to decompose tasks
      - HTNPlanner: generates plans
      - PlanMonitor: monitors execution, triggers re-planning

    Usage:
      hps = HierarchicalPlanningSystem()
      hps.add_goal(goal)
      plan = hps.generate_plan_for_top_goal(world_state)
      step = plan.current_step
      step.execute(world_state)
      plan.advance()
    """

    def __init__(self) -> None:
        self.method_library = MethodLibrary()
        self.method_library.register_speace_defaults()
        self.planner     = HTNPlanner(self.method_library)
        self.goal_stack  = GoalStack()
        self.monitor     = PlanMonitor()
        self._active_plan: Optional[Plan] = None
        self._plan_history: List[Plan] = []
        logger.info("HierarchicalPlanningSystem initialized with %d default methods",
                    self.method_library.method_count)

    # ── Goal management ───────────────────────────────────────────────────────

    def add_goal(self, goal: Goal) -> None:
        """Push a goal onto the goal stack."""
        self.goal_stack.push(goal)
        logger.debug("HPS: added goal %s (priority=%s)", goal.name, goal.priority.value)

    def create_goal(
        self,
        name: str,
        conditions: Dict[str, Any],
        priority: GoalPriority = GoalPriority.MEDIUM,
        deadline_seconds: Optional[float] = None,
    ) -> Goal:
        """Factory for goals."""
        return Goal(
            goal_id=f"G-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            conditions=conditions,
            priority=priority,
            deadline=(time.time() + deadline_seconds) if deadline_seconds else None,
        )

    def remove_satisfied_goals(self, world_state: WorldState) -> List[Goal]:
        return self.goal_stack.remove_satisfied(world_state)

    # ── Planning ──────────────────────────────────────────────────────────────

    def generate_plan(
        self, goal: Goal, world_state: WorldState
    ) -> Optional[Plan]:
        """Generate a plan for a specific goal."""
        plan = self.planner.plan(goal, world_state)
        if plan:
            self._active_plan = plan
            self._plan_history.append(plan)
        return plan

    def generate_plan_for_top_goal(
        self, world_state: WorldState
    ) -> Optional[Plan]:
        """Generate a plan for the highest-priority pending goal."""
        # First, remove satisfied goals
        self.remove_satisfied_goals(world_state)
        self.goal_stack.remove_expired()

        goal = self.goal_stack.get_highest_priority()
        if goal is None:
            logger.debug("HPS: no active goals")
            return None
        return self.generate_plan(goal, world_state)

    # ── Execution step ────────────────────────────────────────────────────────

    def execute_next_step(self, world_state: WorldState) -> Dict[str, Any]:
        """
        Execute the next step of the active plan.
        Returns execution result dict.
        """
        if self._active_plan is None or self._active_plan.is_complete:
            return {"status": "no_active_plan", "step": None}

        if self.monitor.needs_replanning(self._active_plan, world_state):
            self.monitor.record_failure(self._active_plan, "preconditions_violated")
            new_plan = self.monitor.trigger_replan(
                self.planner, self._active_plan.goal, world_state
            )
            if new_plan and new_plan.status != PlanStatus.FAILED:
                self._active_plan = new_plan
                self._plan_history.append(new_plan)
            else:
                return {"status": "replan_failed", "step": None}

        step = self._active_plan.current_step
        if step is None:
            return {"status": "plan_complete", "step": None}

        success = step.execute(world_state)
        result = {
            "status": "executed" if success else "step_failed",
            "step": step.name,
            "plan_id": self._active_plan.plan_id,
            "progress": round(self._active_plan.progress, 3),
        }

        if success:
            self._active_plan.execution_trace.append({
                "step": step.name,
                "ts": time.time(),
                "success": True,
            })
            self._active_plan.advance()
        else:
            self.monitor.record_failure(self._active_plan, f"step {step.name} failed")
            self._active_plan.status = PlanStatus.FAILED

        return result

    # ── SelfModel integration ─────────────────────────────────────────────────

    def apply_self_model_constraints(self, self_model: Any) -> None:
        """
        BRN-019 bridge: apply limitations from SelfModel to planning.
        Offline modules → disable methods requiring them.
        """
        if self_model is None:
            return
        try:
            limitations = self_model.get_limitations()
            for lim in limitations:
                mod_id = lim.module_id.lower().replace("-", "_")
                # Set world state facts to disable methods for offline modules
                if hasattr(lim, "limitation_type"):
                    from cortex.brain.self_model import LimitationType
                    if lim.limitation_type == LimitationType.MISSING_CAPABILITY:
                        # Will be used in planning context
                        logger.info("HPS: constraint from SelfModel — %s offline", mod_id)
        except Exception as e:
            logger.warning("apply_self_model_constraints error: %s", e)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_goals": len(self.goal_stack),
            "method_count": self.method_library.method_count,
            "active_plan": (
                self._active_plan.to_dict() if self._active_plan else None
            ),
            "plans_generated": len(self._plan_history),
            "planner_stats": self.planner.get_stats(),
            "monitor": {
                "failures": self.monitor.failure_count,
                "replannings": self.monitor.replanning_count,
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_htn_planner() -> HierarchicalPlanningSystem:
    return HierarchicalPlanningSystem()
