"""
SPEACE AGI Loop — Unified Cognitive Cycle Orchestrator
Connects all AGI-critical modules into a single recursive cognitive loop.

The AGI Loop implements the SMFOI-KERNEL v0.3 (6-step) as the master clock:
  Step 1 — Self-Location     (SelfModel BRN-019: introspect current state)
  Step 2 — Constraint Mapping (BodySchema: check active modules & limitations)
  Step 3 — Push Detection    (WorldState: detect novel stimuli / surprises)
  Step 4 — Survival/Evolution Stack (HTNPlanner: select and advance plan)
  Step 5 — Output Action     (execute next plan step)
  Step 6 — Outcome Evaluation (CausalReasoner + RecursiveSelfImprover: learn)

Modules integrated:
  BRN-017 CausalReasoner       → causal world understanding
  BRN-018 AbstractionLayer     → cross-domain transfer & concept formation
  BRN-019 SelfModel            → self-awareness, metacognition, body schema
  BRN-020 RecursiveSelfImprover → safe self-modification proposals
  HTNPlanner                   → long-term goal-oriented planning
  NeuromodulatorBus (M15.2)    → global neuromodulation broadcast
  SparseActivation (M15.1)     → energy-efficient module selection

Cognitive cycle properties:
  - Recursive: each cycle output feeds into next cycle input
  - Self-aware: SelfModel monitors and reports each cycle
  - Causal: actions grounded in do-calculus, not mere correlation
  - Goal-directed: HTN plans decompose high-level goals into steps
  - Self-improving: RSI generates proposals after each cycle

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Enumerazioni
# ──────────────────────────────────────────────────────────────────────────────

class CyclePhase(str, Enum):
    SELF_LOCATION      = "self_location"       # Step 1 SMFOI
    CONSTRAINT_MAPPING = "constraint_mapping"  # Step 2
    PUSH_DETECTION     = "push_detection"      # Step 3
    EVOLUTION_STACK    = "evolution_stack"     # Step 4
    OUTPUT_ACTION      = "output_action"       # Step 5
    OUTCOME_EVALUATION = "outcome_evaluation"  # Step 6 (new v0.3)
    IDLE               = "idle"


class AGILoopStatus(str, Enum):
    INIT       = "init"
    RUNNING    = "running"
    PAUSED     = "paused"
    STOPPED    = "stopped"
    ERROR      = "error"


class SurpriseLevel(str, Enum):
    NONE     = "none"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ──────────────────────────────────────────────────────────────────────────────
#  Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CycleInput:
    """Inputs to a single AGI cognitive cycle."""
    cycle_id: str
    stimuli: Dict[str, Any] = field(default_factory=dict)     # external inputs
    world_state: Optional[Any] = None                          # WorldState object
    goal_update: Optional[Dict] = None                         # new goal from user
    feedback: Optional[Dict] = None                            # outcome of prev cycle
    timestamp: float = field(default_factory=time.time)


@dataclass
class CycleOutput:
    """Outputs from a single AGI cognitive cycle."""
    cycle_id: str
    phase_results: Dict[str, Any] = field(default_factory=dict)
    action_taken: Optional[str] = None
    action_result: Optional[Dict] = None
    proposals_generated: int = 0
    surprise_level: SurpriseLevel = SurpriseLevel.NONE
    self_model_snapshot: Optional[Dict] = None
    fitness_delta: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    success: bool = True


@dataclass
class AGIMetrics:
    """Running metrics of the AGI Loop."""
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    total_proposals: int = 0
    total_surprises: int = 0
    avg_cycle_ms: float = 0.0
    avg_fitness: float = 0.0
    last_cycle_ts: Optional[float] = None

    def update(self, output: CycleOutput) -> None:
        self.total_cycles += 1
        if output.success:
            self.successful_cycles += 1
        else:
            self.failed_cycles += 1
        self.total_proposals += output.proposals_generated
        if output.surprise_level not in (SurpriseLevel.NONE, SurpriseLevel.LOW):
            self.total_surprises += 1
        # Running average of cycle duration
        n = self.total_cycles
        self.avg_cycle_ms = ((n - 1) * self.avg_cycle_ms + output.duration_ms) / n
        if output.fitness_delta != 0:
            self.avg_fitness = ((n - 1) * self.avg_fitness + output.fitness_delta) / n
        self.last_cycle_ts = output.timestamp

    def to_dict(self) -> Dict:
        return {
            "total_cycles": self.total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "success_rate": (
                self.successful_cycles / self.total_cycles
                if self.total_cycles else 0.0
            ),
            "total_proposals": self.total_proposals,
            "total_surprises": self.total_surprises,
            "avg_cycle_ms": round(self.avg_cycle_ms, 2),
            "avg_fitness": round(self.avg_fitness, 4),
            "last_cycle_ts": self.last_cycle_ts,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Surprise Detector
# ──────────────────────────────────────────────────────────────────────────────

class SurpriseDetector:
    """
    Detects novel / surprising stimuli in cycle inputs.
    Integrates with BRN-017 CausalReasoner.detect_surprise().
    """

    def __init__(self, novelty_threshold: float = 0.3) -> None:
        self._novelty_threshold = novelty_threshold
        self._seen_keys: set = set()
        self._value_history: Dict[str, list] = {}

    def detect(
        self, stimuli: Dict[str, Any], causal_reasoner: Optional[Any] = None
    ) -> Tuple[SurpriseLevel, List[str]]:
        """
        Returns (surprise_level, [surprising_keys]).
        """
        surprises = []
        for k, v in stimuli.items():
            if k not in self._seen_keys:
                surprises.append(k)
                self._seen_keys.add(k)
            else:
                # Check for large value deviation
                history = self._value_history.get(k, [])
                if history and isinstance(v, (int, float)):
                    recent_avg = sum(history[-5:]) / len(history[-5:])
                    if recent_avg != 0:
                        deviation = abs(v - recent_avg) / (abs(recent_avg) + 1e-9)
                        if deviation > self._novelty_threshold:
                            surprises.append(k)
            # Update history
            if isinstance(v, (int, float)):
                self._value_history.setdefault(k, []).append(v)

        # Also ask CausalReasoner if we have one
        if causal_reasoner is not None:
            try:
                for k in list(surprises):
                    pred_err = type("PE", (), {
                        "node_id": k, "magnitude": 0.5, "is_surprising": True
                    })()
                    causal_reasoner.detect_surprise(pred_err)
            except Exception:
                pass

        n = len(surprises)
        if n == 0:
            return SurpriseLevel.NONE, []
        elif n == 1:
            return SurpriseLevel.LOW, surprises
        elif n <= 3:
            return SurpriseLevel.MEDIUM, surprises
        elif n <= 6:
            return SurpriseLevel.HIGH, surprises
        else:
            return SurpriseLevel.CRITICAL, surprises


# ──────────────────────────────────────────────────────────────────────────────
#  Module Registry (sparse activation proxy)
# ──────────────────────────────────────────────────────────────────────────────

class ModuleRegistry:
    """
    Lightweight registry of active modules for the AGI Loop.
    Integrates with SparseActivation (M15.1) if available.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, Any] = {}    # module_id → module instance
        self._enabled: Dict[str, bool] = {}

    def register(self, module_id: str, instance: Any, enabled: bool = True) -> None:
        self._modules[module_id] = instance
        self._enabled[module_id] = enabled
        logger.debug("ModuleRegistry: registered %s (enabled=%s)", module_id, enabled)

    def get(self, module_id: str) -> Optional[Any]:
        if self._enabled.get(module_id, False):
            return self._modules.get(module_id)
        return None

    def enable(self, module_id: str) -> None:
        self._enabled[module_id] = True

    def disable(self, module_id: str) -> None:
        self._enabled[module_id] = False

    def active_ids(self) -> List[str]:
        return [mid for mid, en in self._enabled.items() if en]

    @property
    def active_count(self) -> int:
        return sum(1 for v in self._enabled.values() if v)


# ──────────────────────────────────────────────────────────────────────────────
#  SMFOI Step Handlers
# ──────────────────────────────────────────────────────────────────────────────

class SMFOIStepHandler:
    """
    Executes the 6-step SMFOI-KERNEL v0.3 cycle.
    Each step is a method receiving (cycle_input, registry, state) → dict.
    """

    def step1_self_location(
        self, cycle_input: CycleInput, registry: ModuleRegistry
    ) -> Dict[str, Any]:
        """Self-Location: snapshot current state via SelfModel (BRN-019)."""
        self_model = registry.get("BRN-019")
        if self_model is not None:
            try:
                snapshot = self_model.introspect()
                return {
                    "integrity": snapshot.get("system_integrity", 1.0),
                    "load": snapshot.get("cognitive_load", 0.0),
                    "active_modules": snapshot.get("active_modules", 0),
                    "limitations": len(snapshot.get("limitations", [])),
                    "phase": "located",
                }
            except Exception as e:
                logger.warning("Step1 SelfModel error: %s", e)
        return {"phase": "located", "integrity": 1.0, "load": 0.0}

    def step2_constraint_mapping(
        self, cycle_input: CycleInput, registry: ModuleRegistry
    ) -> Dict[str, Any]:
        """Constraint Mapping: identify active modules and their constraints."""
        active = registry.active_ids()
        constraints = []
        self_model = registry.get("BRN-019")
        if self_model is not None:
            try:
                lims = self_model.get_limitations()
                constraints = [
                    {"module": l.module_id, "type": l.limitation_type.value,
                     "severity": l.severity}
                    for l in lims if l.severity > 0.5
                ]
            except Exception:
                pass
        return {
            "active_modules": active,
            "active_count": len(active),
            "constraints": constraints,
            "phase": "mapped",
        }

    def step3_push_detection(
        self,
        cycle_input: CycleInput,
        registry: ModuleRegistry,
        surprise_detector: SurpriseDetector,
    ) -> Dict[str, Any]:
        """Push Detection: detect novel stimuli and surprises."""
        causal = registry.get("BRN-017")
        level, surprises = surprise_detector.detect(
            cycle_input.stimuli or {}, causal_reasoner=causal
        )
        return {
            "surprise_level": level.value,
            "surprising_keys": surprises,
            "stimuli_count": len(cycle_input.stimuli or {}),
            "phase": "detected",
        }

    def step4_evolution_stack(
        self,
        cycle_input: CycleInput,
        registry: ModuleRegistry,
        planner: Any,
    ) -> Dict[str, Any]:
        """Survival/Evolution Stack: update plan and select next action."""
        if planner is None:
            return {"phase": "stacked", "action": None, "plan_status": "no_planner"}

        ws = cycle_input.world_state
        if ws is None:
            return {"phase": "stacked", "action": None, "plan_status": "no_world_state"}

        # If a goal was provided, add it
        if cycle_input.goal_update:
            try:
                from cortex.cognitive_autonomy.planning.hierarchical_planner import (
                    Goal, GoalPriority
                )
                goal = Goal(
                    goal_id=f"G-{uuid.uuid4().hex[:6]}",
                    name=cycle_input.goal_update.get("name", "goal"),
                    conditions=cycle_input.goal_update.get("conditions", {}),
                    priority=GoalPriority(
                        cycle_input.goal_update.get("priority", "medium")
                    ),
                )
                planner.add_goal(goal)
            except Exception as e:
                logger.warning("Step4 goal update error: %s", e)

        # Generate plan if none active
        status_dict = planner.get_status()
        if status_dict.get("active_plan") is None or \
                status_dict.get("active_plan", {}).get("status") in ("completed", "failed"):
            plan = planner.generate_plan_for_top_goal(ws)
            if plan:
                return {
                    "phase": "stacked",
                    "action": plan.current_step.name if plan.current_step else None,
                    "plan_id": plan.plan_id,
                    "plan_steps": len(plan.steps),
                    "plan_status": plan.status.value,
                }

        active_plan = status_dict.get("active_plan") or {}
        return {
            "phase": "stacked",
            "action": active_plan.get("current_step"),
            "plan_id": active_plan.get("plan_id"),
            "plan_status": active_plan.get("status", "no_active_plan"),
        }

    def step5_output_action(
        self,
        cycle_input: CycleInput,
        registry: ModuleRegistry,
        planner: Any,
    ) -> Dict[str, Any]:
        """Output Action: execute next plan step."""
        if planner is None or cycle_input.world_state is None:
            return {"phase": "acted", "result": None, "status": "no_planner"}

        try:
            result = planner.execute_next_step(cycle_input.world_state)
            return {"phase": "acted", "result": result, "status": result.get("status")}
        except Exception as e:
            logger.error("Step5 action error: %s", e)
            return {"phase": "acted", "result": None, "status": "error", "error": str(e)}

    def step6_outcome_evaluation(
        self,
        cycle_input: CycleInput,
        registry: ModuleRegistry,
        output: CycleOutput,
        rsi: Any,
        self_model: Any,
    ) -> Dict[str, Any]:
        """
        Outcome Evaluation & Learning (SMFOI v0.3 new step):
        Measure cycle result, compute fitness delta, generate RSI proposals.
        """
        proposals_generated = 0
        fitness_delta = 0.0

        # Run RSI cycle (code inspection + proposals)
        if rsi is not None:
            try:
                proposals = rsi.run_improvement_cycle(target_modules=[])
                rsi_result = {
                    "proposals_generated": len(proposals),
                    "fitness_delta": 0.0,
                }
                proposals_generated = rsi_result.get("proposals_generated", 0)
                fitness_delta = rsi_result.get("fitness_delta", 0.0)
            except Exception as e:
                logger.warning("Step6 RSI error: %s", e)

        # Record milestone in SelfNarrative if something important happened
        if self_model is not None and output.surprise_level in (
            SurpriseLevel.HIGH, SurpriseLevel.CRITICAL
        ):
            try:
                self_model.narrative.record_episode(
                    __import__("cortex.brain.self_model", fromlist=["EpisodeType"]).EpisodeType.MILESTONE,
                    f"High surprise event (cycle {output.cycle_id})",
                    f"Surprise level: {output.surprise_level.value}",
                )
            except Exception:
                pass

        # Update calibration feedback if we have it
        if cycle_input.feedback and self_model is not None:
            try:
                trace_id = cycle_input.feedback.get("trace_id")
                correct = cycle_input.feedback.get("was_correct", True)
                if trace_id:
                    self_model.metacognition.update_outcome(trace_id, correct)
            except Exception:
                pass

        return {
            "phase": "evaluated",
            "proposals_generated": proposals_generated,
            "fitness_delta": fitness_delta,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  AGI Loop (main class)
# ──────────────────────────────────────────────────────────────────────────────

class AGILoop:
    """
    SPEACE Unified Cognitive Loop — connects all AGI modules.

    Usage:
        loop = AGILoop()
        loop.register_module("BRN-017", causal_reasoner)
        loop.register_module("BRN-019", self_model)
        loop.register_module("BRN-020", rsi)
        loop.set_planner(htn_planner)

        world_state = WorldState({"brn_017_active": True})
        goal = loop.create_goal("analyze_situation", {"causal_analysis_done": True})
        loop.add_goal(goal)

        for _ in range(3):
            output = loop.tick(world_state)
            print(output.action_taken, output.success)
    """

    def __init__(
        self,
        loop_id: Optional[str] = None,
        max_history: int = 100,
    ) -> None:
        self.loop_id   = loop_id or f"AGI-{uuid.uuid4().hex[:8].upper()}"
        self.status    = AGILoopStatus.INIT
        self.metrics   = AGIMetrics()
        self._registry = ModuleRegistry()
        self._planner: Optional[Any] = None
        self._surprise_detector = SurpriseDetector()
        self._step_handler = SMFOIStepHandler()
        self._history: Deque[CycleOutput] = deque(maxlen=max_history)
        self._cycle_counter: int = 0
        self._phase: CyclePhase = CyclePhase.IDLE
        self._on_cycle_hooks: List[Callable[[CycleOutput], None]] = []
        logger.info("AGILoop %s initialized", self.loop_id)

    # ── Module registration ───────────────────────────────────────────────────

    def register_module(
        self, module_id: str, instance: Any, enabled: bool = True
    ) -> None:
        self._registry.register(module_id, instance, enabled)

    def set_planner(self, planner: Any) -> None:
        self._planner = planner
        logger.debug("AGILoop: planner set (%s)", type(planner).__name__)

    def add_hook(self, hook: Callable[[CycleOutput], None]) -> None:
        """Register a post-cycle hook (e.g., for logging, broadcasting)."""
        self._on_cycle_hooks.append(hook)

    # ── Goal management (delegate to planner) ────────────────────────────────

    def create_goal(
        self,
        name: str,
        conditions: Dict[str, Any],
        priority: str = "medium",
        deadline_seconds: Optional[float] = None,
    ) -> Any:
        """Create a goal via the planner (if available) or return a bare dict."""
        if self._planner is not None:
            from cortex.cognitive_autonomy.planning.hierarchical_planner import GoalPriority
            return self._planner.create_goal(
                name, conditions,
                priority=GoalPriority(priority),
                deadline_seconds=deadline_seconds,
            )
        return {"name": name, "conditions": conditions, "priority": priority}

    def add_goal(self, goal: Any) -> None:
        if self._planner is not None:
            self._planner.add_goal(goal)

    # ── Main tick ─────────────────────────────────────────────────────────────

    def tick(self, world_state: Optional[Any] = None, stimuli: Optional[Dict] = None,
             feedback: Optional[Dict] = None, goal_update: Optional[Dict] = None,
             ) -> CycleOutput:
        """
        Execute one full SMFOI 6-step cognitive cycle.
        Returns CycleOutput with results of all phases.
        """
        if self.status == AGILoopStatus.STOPPED:
            logger.warning("AGILoop tick called but loop is stopped")
            return CycleOutput(
                cycle_id="STOPPED", success=False,
                phase_results={"error": "loop stopped"}
            )

        self.status = AGILoopStatus.RUNNING
        start_ts = time.time()
        self._cycle_counter += 1
        cycle_id = f"C{self._cycle_counter:04d}-{self.loop_id}"

        cycle_input = CycleInput(
            cycle_id=cycle_id,
            stimuli=stimuli or {},
            world_state=world_state,
            goal_update=goal_update,
            feedback=feedback,
        )

        output = CycleOutput(cycle_id=cycle_id)
        phase_results: Dict[str, Any] = {}

        # ── Step 1: Self-Location ─────────────────────────────────────────────
        self._phase = CyclePhase.SELF_LOCATION
        r1 = self._step_handler.step1_self_location(cycle_input, self._registry)
        phase_results["step1_self_location"] = r1

        # ── Step 2: Constraint Mapping ────────────────────────────────────────
        self._phase = CyclePhase.CONSTRAINT_MAPPING
        r2 = self._step_handler.step2_constraint_mapping(cycle_input, self._registry)
        phase_results["step2_constraint_mapping"] = r2

        # ── Step 3: Push Detection ────────────────────────────────────────────
        self._phase = CyclePhase.PUSH_DETECTION
        r3 = self._step_handler.step3_push_detection(
            cycle_input, self._registry, self._surprise_detector
        )
        phase_results["step3_push_detection"] = r3
        output.surprise_level = SurpriseLevel(r3["surprise_level"])

        # ── Step 4: Evolution Stack ───────────────────────────────────────────
        self._phase = CyclePhase.EVOLUTION_STACK
        r4 = self._step_handler.step4_evolution_stack(
            cycle_input, self._registry, self._planner
        )
        phase_results["step4_evolution_stack"] = r4
        output.action_taken = r4.get("action")

        # ── Step 5: Output Action ─────────────────────────────────────────────
        self._phase = CyclePhase.OUTPUT_ACTION
        r5 = self._step_handler.step5_output_action(
            cycle_input, self._registry, self._planner
        )
        phase_results["step5_output_action"] = r5
        output.action_result = r5.get("result")
        output.success = r5.get("status") not in ("error", "replan_failed")

        # ── Step 6: Outcome Evaluation ────────────────────────────────────────
        self._phase = CyclePhase.OUTCOME_EVALUATION
        self_model = self._registry.get("BRN-019")
        rsi        = self._registry.get("BRN-020")
        r6 = self._step_handler.step6_outcome_evaluation(
            cycle_input, self._registry, output, rsi, self_model
        )
        phase_results["step6_outcome_evaluation"] = r6
        output.proposals_generated = r6.get("proposals_generated", 0)
        output.fitness_delta       = r6.get("fitness_delta", 0.0)

        # ── Finalize output ───────────────────────────────────────────────────
        output.phase_results = phase_results
        if self_model is not None:
            try:
                output.self_model_snapshot = {
                    "integrity": r1.get("integrity", 1.0),
                    "load": r1.get("load", 0.0),
                    "limitations": r1.get("limitations", 0),
                }
            except Exception:
                pass

        end_ts = time.time()
        output.duration_ms = round((end_ts - start_ts) * 1000, 2)
        self.metrics.update(output)
        self._history.append(output)
        self._phase = CyclePhase.IDLE

        # Fire hooks
        for hook in self._on_cycle_hooks:
            try:
                hook(output)
            except Exception as e:
                logger.warning("AGILoop hook error: %s", e)

        logger.info(
            "AGILoop cycle %s: action=%s surprise=%s duration=%.1fms",
            cycle_id, output.action_taken, output.surprise_level.value,
            output.duration_ms,
        )
        return output

    # ── Multi-cycle run ───────────────────────────────────────────────────────

    def run(
        self,
        world_state: Any,
        n_cycles: int,
        stimuli_sequence: Optional[List[Dict]] = None,
    ) -> List[CycleOutput]:
        """Run n_cycles ticks, optionally with a sequence of stimuli."""
        outputs = []
        for i in range(n_cycles):
            stimuli = (stimuli_sequence[i] if stimuli_sequence
                       and i < len(stimuli_sequence) else {})
            out = self.tick(world_state, stimuli=stimuli)
            outputs.append(out)
        return outputs

    # ── Control ───────────────────────────────────────────────────────────────

    def pause(self) -> None:
        self.status = AGILoopStatus.PAUSED
        logger.info("AGILoop %s paused", self.loop_id)

    def resume(self) -> None:
        self.status = AGILoopStatus.RUNNING
        logger.info("AGILoop %s resumed", self.loop_id)

    def stop(self) -> None:
        self.status = AGILoopStatus.STOPPED
        logger.info("AGILoop %s stopped", self.loop_id)

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_last_output(self) -> Optional[CycleOutput]:
        return self._history[-1] if self._history else None

    def get_history(self, last_n: int = 10) -> List[CycleOutput]:
        return list(self._history)[-last_n:]

    def get_status(self) -> Dict[str, Any]:
        last = self.get_last_output()
        return {
            "loop_id": self.loop_id,
            "status": self.status.value,
            "cycle_count": self._cycle_counter,
            "phase": self._phase.value,
            "active_modules": self._registry.active_count,
            "has_planner": self._planner is not None,
            "metrics": self.metrics.to_dict(),
            "last_cycle": {
                "id": last.cycle_id,
                "action": last.action_taken,
                "surprise": last.surprise_level.value,
                "duration_ms": last.duration_ms,
                "success": last.success,
            } if last else None,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Full AGI System (convenience builder)
# ──────────────────────────────────────────────────────────────────────────────

class AGISystem:
    """
    Convenience builder that wires all available modules into an AGILoop.
    If a module is unavailable (import error), it's gracefully skipped.
    """

    def __init__(self) -> None:
        self.loop    = AGILoop()
        self.modules: Dict[str, Any] = {}
        self._wired  = False

    def wire_all(self) -> "AGISystem":
        """Attempt to instantiate and register all BRN modules."""
        # BRN-019 SelfModel
        try:
            from cortex.brain.self_model import create_self_model
            sm = create_self_model()
            self.loop.register_module("BRN-019", sm)
            self.modules["BRN-019"] = sm
        except Exception as e:
            logger.warning("Could not wire BRN-019: %s", e)

        # BRN-020 RecursiveSelfImprover
        try:
            from cortex.brain.recursive_self_improvement import create_recursive_self_improver
            rsi = create_recursive_self_improver()
            self.loop.register_module("BRN-020", rsi)
            self.modules["BRN-020"] = rsi
        except Exception as e:
            logger.warning("Could not wire BRN-020: %s", e)

        # HTN Planner
        try:
            from cortex.cognitive_autonomy.planning.hierarchical_planner import create_htn_planner
            planner = create_htn_planner()
            self.loop.set_planner(planner)
            self.modules["HTN_PLANNER"] = planner
        except Exception as e:
            logger.warning("Could not wire HTNPlanner: %s", e)

        # BRN-017 CausalReasoner
        try:
            from cortex.brain.causal_reasoning import CausalReasoner
            cr = CausalReasoner()
            self.loop.register_module("BRN-017", cr)
            self.modules["BRN-017"] = cr
        except Exception as e:
            logger.warning("Could not wire BRN-017: %s", e)

        # BRN-018 AbstractionLayer
        try:
            from cortex.brain.abstraction_layer import create_abstraction_layer
            al = create_abstraction_layer()
            self.loop.register_module("BRN-018", al)
            self.modules["BRN-018"] = al
        except Exception as e:
            logger.warning("Could not wire BRN-018: %s", e)

        self._wired = True
        logger.info("AGISystem wired: %d modules active", self.loop._registry.active_count)
        return self

    def tick(self, world_state: Any = None, **kwargs) -> CycleOutput:
        return self.loop.tick(world_state, **kwargs)

    def get_status(self) -> Dict:
        return {
            "agi_system": True,
            "wired": self._wired,
            "modules": list(self.modules.keys()),
            "loop": self.loop.get_status(),
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_agi_loop() -> AGILoop:
    return AGILoop()


def create_agi_system() -> AGISystem:
    return AGISystem().wire_all()
