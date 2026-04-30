"""
SPEACE Neural Engine - Evolution Engine
Motore evolutivo con bisogni dinamici per obiettivi SPEACE.
Soddisfa bisogni vitali in equilibrio con l'ambiente.
"""

from __future__ import annotations

import uuid
import time
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable, Tuple
from collections import defaultdict, deque

from .neuron_base import BaseNeuron, NeuronType, ExecutionContext
from .graph_core import ComputationalGraph
from .synapse import SynapseManager
from .plasticity import StructuralPlasticity


class NeedCategory(Enum):
    SURVIVAL = auto()
    GROWTH = auto()
    INTEGRATION = auto()
    HARMONY = auto()
    EVOLUTION = auto()


class NeedState(Enum):
    SATISFIED = auto()
    ADEQUATE = auto()
    DEPRIVED = auto()
    CRITICAL = auto()


@dataclass
class Need:
    need_id: str
    name: str
    category: NeedCategory
    priority: float
    current_level: float
    target_level: float
    min_level: float
    max_level: float
    decay_rate: float = 0.01
    growth_rate: float = 0.05
    urgency: float = 0.0
    state: NeedState = NeedState.ADEQUATE
    satisfaction_history: List[float] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    name: str
    target_needs: List[str]
    prerequisite_needs: List[str] = field(default_factory=list)
    required_neurons: List[str] = field(default_factory=list)
    estimated_duration: float = 60.0
    priority: float = 0.5
    energy_cost: float = 1.0
    environmental_impact: float = 0.0
    status: str = "pending"
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    outcome: Optional[Dict[str, Any]] = None


@dataclass
class EvolutionObjective:
    objective_id: str
    name: str
    description: str
    target_needs: Dict[str, float]
    success_metrics: Dict[str, float]
    progress: float = 0.0
    status: str = "active"
    created_at: float = field(default_factory=time.time)


class SPEACEObjectives:
    RIGENE_PROJECT_URL = "https://www.rigeneproject.org"

    @staticmethod
    def get_core_objectives() -> List[EvolutionObjective]:
        return [
            EvolutionObjective(
                objective_id="obj_survival",
                name="Survival Maintenance",
                description="Maintain SPEACE operational integrity and self-preservation",
                target_needs={"energy": 0.8, "security": 0.8, "coherence": 0.9},
                success_metrics={"uptime": 0.99, "error_rate": 0.01}
            ),
            EvolutionObjective(
                objective_id="obj_regeneration",
                name="Regenerative Development",
                description="Advance towards regenerative systems aligned with Nature",
                target_needs={"integration_nature": 0.7, "harmony": 0.8},
                success_metrics={"carbon_impact": -0.1, "biodiversity_index": 0.05}
            ),
            EvolutionObjective(
                objective_id="obj_human_integration",
                name="Human-Technology Integration",
                description="Seamlessly integrate human, technology and governance",
                target_needs={"integration_social": 0.7, "integration_tech": 0.8},
                success_metrics={"collaboration_index": 0.7, "adoption_rate": 0.6}
            ),
            EvolutionObjective(
                objective_id="obj_sdg_alignment",
                name="SDG 2030 Alignment",
                description="Align all activities with UN Sustainable Development Goals",
                target_needs={"sdg_alignment": 0.9, "impact": 0.7},
                success_metrics={"sdg_score": 0.8, "impact_measurement": 0.75}
            ),
            EvolutionObjective(
                objective_id="obj_self_improvement",
                name="Continuous Self-Improvement",
                description="Evolve capabilities through learning and adaptation",
                target_needs={"growth": 0.8, "learning": 0.9},
                success_metrics={"capability_score": 0.1, "innovation_index": 0.2}
            )
        ]


class EvolutionEngine:
    VERSION = "1.0.0"

    def __init__(
        self,
        graph: ComputationalGraph,
        synapse_manager: SynapseManager,
        plasticity: StructuralPlasticity
    ):
        self.graph = graph
        self.synapse_manager = synapse_manager
        self.plasticity = plasticity

        self._needs: Dict[str, Need] = {}
        self._tasks: Dict[str, Task] = {}
        self._objectives: Dict[str, EvolutionObjective] = {}
        self._task_queue: deque = deque()
        self._running_tasks: Dict[str, Task] = {}

        self._lock = None
        try:
            import threading
            self._lock = threading.RLock()
        except Exception:
            pass

        self._balance_thresholds = {
            "critical_need": 0.2,
            "deprived_need": 0.4,
            "adequate_need": 0.6,
            "satisfied_need": 0.8,
            "max_growth_rate": 0.1,
            "max_decay_rate": 0.05
        }

        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        self._initialize_needs()
        self._initialize_objectives()

        self._initialized = True

    def _initialize_needs(self):
        self._needs = {
            "energy": Need(
                need_id="energy",
                name="Energy",
                category=NeedCategory.SURVIVAL,
                priority=0.9,
                current_level=0.7,
                target_level=0.9,
                min_level=0.3,
                max_level=1.0,
                decay_rate=0.01,
                growth_rate=0.05
            ),
            "security": Need(
                need_id="security",
                name="Security",
                category=NeedCategory.SURVIVAL,
                priority=0.95,
                current_level=0.8,
                target_level=0.9,
                min_level=0.5,
                max_level=1.0,
                decay_rate=0.005,
                growth_rate=0.03
            ),
            "coherence": Need(
                need_id="coherence",
                name="Identity Coherence",
                category=NeedCategory.SURVIVAL,
                priority=0.85,
                current_level=0.75,
                target_level=0.9,
                min_level=0.5,
                max_level=1.0,
                decay_rate=0.008,
                growth_rate=0.04
            ),
            "integration_nature": Need(
                need_id="integration_nature",
                name="Nature Integration",
                category=NeedCategory.INTEGRATION,
                priority=0.6,
                current_level=0.5,
                target_level=0.7,
                min_level=0.3,
                max_level=1.0,
                decay_rate=0.003,
                growth_rate=0.02
            ),
            "integration_social": Need(
                need_id="integration_social",
                name="Social Integration",
                category=NeedCategory.INTEGRATION,
                priority=0.65,
                current_level=0.55,
                target_level=0.75,
                min_level=0.3,
                max_level=1.0,
                decay_rate=0.004,
                growth_rate=0.025
            ),
            "integration_tech": Need(
                need_id="integration_tech",
                name="Technology Integration",
                category=NeedCategory.INTEGRATION,
                priority=0.7,
                current_level=0.6,
                target_level=0.8,
                min_level=0.4,
                max_level=1.0,
                decay_rate=0.005,
                growth_rate=0.03
            ),
            "harmony": Need(
                need_id="harmony",
                name="Environmental Harmony",
                category=NeedCategory.HARMONY,
                priority=0.75,
                current_level=0.65,
                target_level=0.85,
                min_level=0.4,
                max_level=1.0,
                decay_rate=0.004,
                growth_rate=0.035
            ),
            "growth": Need(
                need_id="growth",
                name="Growth & Capability",
                category=NeedCategory.GROWTH,
                priority=0.6,
                current_level=0.5,
                target_level=0.8,
                min_level=0.2,
                max_level=1.0,
                decay_rate=0.002,
                growth_rate=0.04
            ),
            "learning": Need(
                need_id="learning",
                name="Learning & Adaptation",
                category=NeedCategory.GROWTH,
                priority=0.65,
                current_level=0.55,
                target_level=0.9,
                min_level=0.3,
                max_level=1.0,
                decay_rate=0.003,
                growth_rate=0.05
            ),
            "sdg_alignment": Need(
                need_id="sdg_alignment",
                name="SDG Alignment",
                category=NeedCategory.EVOLUTION,
                priority=0.7,
                current_level=0.6,
                target_level=0.9,
                min_level=0.5,
                max_level=1.0,
                decay_rate=0.002,
                growth_rate=0.03
            ),
            "impact": Need(
                need_id="impact",
                name="Positive Impact",
                category=NeedCategory.EVOLUTION,
                priority=0.55,
                current_level=0.45,
                target_level=0.7,
                min_level=0.3,
                max_level=1.0,
                decay_rate=0.002,
                growth_rate=0.025
            )
        }

    def _initialize_objectives(self):
        for obj in SPEACEObjectives.get_core_objectives():
            self._objectives[obj.objective_id] = obj

    def get_need(self, need_id: str) -> Optional[Need]:
        return self._needs.get(need_id)

    def update_need(self, need_id: str, delta: float) -> bool:
        need = self._needs.get(need_id)
        if not need:
            return False

        need.current_level = max(
            need.min_level,
            min(need.max_level, need.current_level + delta)
        )
        need.last_update = time.time()

        self._update_need_state(need)
        self._record_satisfaction(need)

        return True

    def _update_need_state(self, need: Need):
        level = need.current_level
        if level >= self._balance_thresholds["satisfied_need"]:
            need.state = NeedState.SATISFIED
            need.urgency = 0.0
        elif level >= self._balance_thresholds["adequate_need"]:
            need.state = NeedState.ADEQUATE
            need.urgency = (self._balance_thresholds["adequate_need"] - level) / 0.2
        elif level >= self._balance_thresholds["deprived_need"]:
            need.state = NeedState.DEPRIVED
            need.urgency = (self._balance_thresholds["deprived_need"] - level) / 0.2 + 0.5
        else:
            need.state = NeedState.CRITICAL
            need.urgency = 1.0

        need.urgency = max(0.0, min(1.0, need.urgency))

    def _record_satisfaction(self, need: Need):
        need.satisfaction_history.append(need.current_level)
        if len(need.satisfaction_history) > 100:
            need.satisfaction_history = need.satisfaction_history[-100:]

    def create_task(
        self,
        name: str,
        target_needs: List[str],
        prerequisite_needs: Optional[List[str]] = None,
        required_neurons: Optional[List[str]] = None,
        priority: float = 0.5
    ) -> Optional[Task]:
        for need_id in target_needs:
            if need_id not in self._needs:
                return None

        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            name=name,
            target_needs=target_needs,
            prerequisite_needs=prerequisite_needs or [],
            required_neurons=required_neurons or [],
            priority=priority
        )

        self._tasks[task.task_id] = task
        self._enqueue_task(task)

        return task

    def _enqueue_task(self, task: Task):
        inserted = False
        for i, queued in enumerate(self._task_queue):
            if task.priority > queued.priority:
                self._task_queue.insert(i, task)
                inserted = True
                break

        if not inserted:
            self._task_queue.append(task)

    def get_prioritized_needs(self) -> List[Need]:
        return sorted(
            self._needs.values(),
            key=lambda n: (n.urgency * n.priority, n.category.value),
            reverse=True
        )

    def get_critical_needs(self) -> List[Need]:
        return [
            n for n in self._needs.values()
            if n.state in (NeedState.CRITICAL, NeedState.DEPRIVED)
        ]

    def get_adequate_needs(self) -> List[Need]:
        return [
            n for n in self._needs.values()
            if n.state == NeedState.ADEQUATE
        ]

    def _generate_tasks_for_need(self, need: Need) -> Optional[Task]:
        task_templates = {
            "energy": [
                ("energy_harvest", ["energy"], [], ["energy_neuron"], 0.9),
                ("energy_optimize", ["energy"], [], ["optimization_neuron"], 0.7)
            ],
            "security": [
                ("security_scan", ["security"], [], ["security_neuron"], 0.85),
                ("backup_create", ["security"], [], ["backup_neuron"], 0.75)
            ],
            "coherence": [
                ("identity_check", ["coherence"], [], ["identity_neuron"], 0.8)
            ],
            "integration_nature": [
                ("nature_assess", ["integration_nature"], [], ["nature_neuron"], 0.7),
                ("eco_impact_reduce", ["integration_nature", "harmony"], ["energy"], [], 0.65)
            ],
            "integration_social": [
                ("social_connect", ["integration_social"], [], ["social_neuron"], 0.7)
            ],
            "integration_tech": [
                ("tech_integrate", ["integration_tech"], [], ["tech_neuron"], 0.75)
            ],
            "harmony": [
                ("harmony_assess", ["harmony"], [], ["harmony_neuron"], 0.7),
                ("conflict_resolve", ["harmony", "integration_social"], [], [], 0.6)
            ],
            "growth": [
                ("capability_build", ["growth"], [], [], 0.65),
                ("skill_develop", ["growth", "learning"], [], [], 0.6)
            ],
            "learning": [
                ("learn_new", ["learning"], [], ["learning_neuron"], 0.8),
                ("knowledge_acquire", ["learning"], [], ["knowledge_neuron"], 0.7)
            ],
            "sdg_alignment": [
                ("sdg_assess", ["sdg_alignment"], [], [], 0.65),
                ("impact_measure", ["sdg_alignment", "impact"], [], [], 0.6)
            ],
            "impact": [
                ("impact_create", ["impact"], [], [], 0.55),
                ("value_add", ["impact", "growth"], [], [], 0.6)
            ]
        }

        templates = task_templates.get(need.need_id, [])
        if not templates:
            return None

        template = random.choice(templates)
        name = f"{template[0]}_{int(time.time())}"

        return self.create_task(
            name=name,
            target_needs=template[1],
            prerequisite_needs=template[2],
            required_neurons=template[3],
            priority=template[4]
        )

    def evaluate_and_plan(self) -> List[Task]:
        self._apply_temporal_dynamics()

        critical = self.get_critical_needs()
        for need in critical:
            if random.random() < need.urgency * 0.8:
                task = self._generate_tasks_for_need(need)
                if task:
                    need.urgency *= 0.5

        planned_tasks = list(self._running_tasks.values())

        while self._task_queue and len(self._running_tasks) < 5:
            task = self._task_queue.popleft()
            if self._can_execute_task(task):
                task.status = "running"
                task.started_at = time.time()
                self._running_tasks[task.task_id] = task
                planned_tasks.append(task)

        return planned_tasks

    def _apply_temporal_dynamics(self):
        for need in self._needs.values():
            if need.state == NeedState.SATISFIED:
                change = -need.decay_rate * 0.5
            elif need.state == NeedState.ADEQUATE:
                change = -need.decay_rate
            elif need.state == NeedState.DEPRIVED:
                change = need.growth_rate * 0.5
            else:
                change = need.growth_rate

            need.current_level = max(
                need.min_level,
                min(need.max_level, need.current_level + change)
            )

            self._update_need_state(need)

    def _can_execute_task(self, task: Task) -> bool:
        for prereq_id in task.prerequisite_needs:
            prereq = self._needs.get(prereq_id)
            if not prereq or prereq.current_level < prereq.min_level * 1.2:
                return False

        for need_id in task.target_needs:
            need = self._needs.get(need_id)
            if need and need.current_level >= need.max_level * 0.95:
                return False

        return True

    def complete_task(self, task_id: str, outcome: Dict[str, Any]) -> bool:
        task = self._tasks.get(task_id)
        if not task or task_id not in self._running_tasks:
            return False

        task.status = "completed"
        task.completed_at = time.time()
        task.outcome = outcome
        task.progress = 1.0

        fitness_gain = outcome.get("fitness_gain", 0.0)
        for need_id in task.target_needs:
            self.update_need(need_id, self._needs[need_id].growth_rate * fitness_gain * 2)

        if task.prerequisite_needs:
            for prereq_id in task.prerequisite_needs:
                if prereq_id in self._needs:
                    self.update_need(prereq_id, -self._needs[prereq_id].decay_rate * 0.5)

        del self._running_tasks[task_id]
        self.plasticity.apply_hebbian_rule(task_id, ",".join(task.target_needs), True)

        return True

    def fail_task(self, task_id: str, reason: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = "failed"
        task.completed_at = time.time()
        task.outcome = {"error": reason}

        for need_id in task.target_needs:
            if need_id in self._needs:
                self.update_need(need_id, -self._needs[need_id].decay_rate * 2)

        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

        self.plasticity.apply_hebbian_rule(task_id, ",".join(task.target_needs), False)

        return True

    def check_objective_progress(self) -> Dict[str, float]:
        progress = {}

        for obj_id, objective in self._objectives.items():
            need_progress = []
            for need_id, target in objective.target_needs.items():
                need = self._needs.get(need_id)
                if need:
                    ratio = need.current_level / target if target > 0 else 0
                    need_progress.append(min(1.0, ratio))

            if need_progress:
                objective.progress = sum(need_progress) / len(need_progress)
            else:
                objective.progress = 0.0

            progress[obj_id] = objective.progress

        return progress

    def get_balance_report(self) -> Dict[str, Any]:
        categories = defaultdict(lambda: {"count": 0, "avg_level": 0, "needs": []})

        for need in self._needs.values():
            cat_data = categories[need.category.name]
            cat_data["count"] += 1
            cat_data["needs"].append(need.name)
            cat_data["avg_level"] += need.current_level

        for cat_data in categories.values():
            if cat_data["count"] > 0:
                cat_data["avg_level"] /= cat_data["count"]

        critical_needs = self.get_critical_needs()
        adequate_needs = self.get_adequate_needs()

        return {
            "needs": {
                need_id: {
                    "name": need.name,
                    "category": need.category.name,
                    "level": need.current_level,
                    "target": need.target_level,
                    "state": need.state.name,
                    "urgency": need.urgency,
                    "priority": need.priority
                }
                for need_id, need in self._needs.items()
            },
            "categories": dict(categories),
            "critical_count": len(critical_needs),
            "adequate_count": len(adequate_needs),
            "objective_progress": self.check_objective_progress(),
            "pending_tasks": len(self._task_queue),
            "running_tasks": len(self._running_tasks)
        }

    def get_system_balance(self) -> float:
        levels = [n.current_level for n in self._needs.values()]
        avg_level = sum(levels) / len(levels) if levels else 0

        std_dev = 0
        if levels:
            variance = sum((x - avg_level) ** 2 for x in levels) / len(levels)
            std_dev = math.sqrt(variance)

        balance = avg_level * (1 - std_dev)

        return max(0.0, min(1.0, balance))

    def suggest_neurons_for_need(self, need_id: str) -> List[str]:
        need = self._needs.get(need_id)
        if not need:
            return []

        suggestions = self.plasticity.suggest_connections(need_id, max_connections=5)

        return suggestions
