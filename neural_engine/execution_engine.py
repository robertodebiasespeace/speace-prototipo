"""
SPEACE Neural Engine - Execution Engine
Motore di esecuzione con validazione e sistema di ticket.
Coordina l'esecuzione distribuita dei neuroni.
"""

from __future__ import annotations

import uuid
import time
import threading
import queue
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future

from .neuron_base import (
    BaseNeuron, NeuronType, NeuronState, ExecutionContext, Contract
)
from .graph_core import ComputationalGraph, EdgeType
from .synapse import SynapseManager, SignalType
from .protocol import InteropProtocol, ExecutionTicket, ContractSpec


class ExecutionState(Enum):
    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    VALIDATION_FAILED = auto()


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ExecutionJob:
    job_id: str
    neuron_id: str
    inputs: Dict[str, Any]
    priority: Priority
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    state: ExecutionState = ExecutionState.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    context_id: Optional[str] = None


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)


class ResourceMonitor:
    def __init__(self):
        self._limits = {
            "max_concurrent_jobs": 10,
            "max_queue_size": 100,
            "max_execution_time": 300,
            "max_memory_mb": 512
        }
        self._current_load = {
            "concurrent_jobs": 0,
            "queued_jobs": 0,
            "total_executions": 0
        }

    def can_execute(self, priority: Priority) -> bool:
        if self._current_load["concurrent_jobs"] >= self._limits["max_concurrent_jobs"]:
            return priority in (Priority.CRITICAL, Priority.HIGH)

        if self._current_load["queued_jobs"] >= self._limits["max_queue_size"]:
            return priority == Priority.CRITICAL

        return True

    def acquire_slot(self) -> bool:
        if self._current_load["concurrent_jobs"] >= self._limits["max_concurrent_jobs"]:
            return False
        self._current_load["concurrent_jobs"] += 1
        return True

    def release_slot(self):
        self._current_load["concurrent_jobs"] = max(0, self._current_load["concurrent_jobs"] - 1)

    def increment_queued(self):
        self._current_load["queued_jobs"] += 1

    def decrement_queued(self):
        self._current_load["queued_jobs"] = max(0, self._current_load["queued_jobs"] - 1)

    def record_execution(self):
        self._current_load["total_executions"] += 1

    def get_load_info(self) -> Dict[str, Any]:
        return {
            **self._current_load,
            "limits": self._limits,
            "utilization": {
                "concurrent": self._current_load["concurrent_jobs"] / self._limits["max_concurrent_jobs"],
                "queue": self._current_load["queued_jobs"] / self._limits["max_queue_size"]
            }
        )


class ExecutionEngine:
    VERSION = "1.0.0"

    def __init__(
        self,
        graph: ComputationalGraph,
        synapse_manager: SynapseManager,
        protocol: Optional[InteropProtocol] = None
    ):
        self.graph = graph
        self.synapse_manager = synapse_manager
        self.protocol = protocol or InteropProtocol()

        self._jobs: Dict[str, ExecutionJob] = {}
        self._job_queue: deque = deque()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._resource_monitor = ResourceMonitor()

        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        self._validation_callbacks: Dict[str, Callable] = {}
        self._execution_callbacks: Dict[str, Callable] = {}
        self._history: List[Dict[str, Any]] = []
        self._max_history = 1000

    def start(self):
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    def submit(
        self,
        neuron_id: str,
        inputs: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        validation_required: bool = True
    ) -> Optional[str]:
        neuron = self.graph.get_neuron(neuron_id)
        if not neuron:
            return None

        if validation_required and neuron.contract:
            validation = self._validate_against_contract(neuron, inputs)
            if not validation.valid:
                job_id = f"job_{uuid.uuid4().hex[:12]}"
                job = ExecutionJob(
                    job_id=job_id,
                    neuron_id=neuron_id,
                    inputs=inputs,
                    priority=priority,
                    state=ExecutionState.VALIDATION_FAILED,
                    validation_errors=validation.errors
                )
                self._jobs[job_id] = job
                return job_id

        if not self._resource_monitor.can_execute(priority):
            return None

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = ExecutionJob(
            job_id=job_id,
            neuron_id=neuron_id,
            inputs=inputs,
            priority=priority
        )

        self._jobs[job_id] = job
        self._enqueue_job(job)

        return job_id

    def _enqueue_job(self, job: ExecutionJob):
        job.state = ExecutionState.QUEUED
        self._resource_monitor.increment_queued()

        inserted = False
        for i, queued_job in enumerate(self._job_queue):
            if job.priority.value < queued_job.priority.value:
                self._job_queue.insert(i, job)
                inserted = True
                break

        if not inserted:
            self._job_queue.append(job)

    def _worker_loop(self):
        while self._running:
            job = None

            with self._lock:
                if self._job_queue and self._resource_monitor.can_execute(Priority.NORMAL):
                    job = self._job_queue.popleft()
                    self._resource_monitor.decrement_queued()

            if job:
                self._execute_job(job)
            else:
                time.sleep(0.01)

    def _execute_job(self, job: ExecutionJob):
        if not self._resource_monitor.acquire_slot():
            job.state = ExecutionState.FAILED
            job.error = "Resource allocation failed"
            return

        job.state = ExecutionState.RUNNING
        job.started_at = time.time()

        neuron = self.graph.get_neuron(job.neuron_id)
        if not neuron:
            job.state = ExecutionState.FAILED
            job.error = "Neuron not found"
            self._resource_monitor.release_slot()
            return

        context = ExecutionContext(
            execution_id=job.job_id,
            neuron_id=job.neuron_id,
            inputs=job.inputs,
            metadata={"priority": job.priority.name}
        )

        try:
            result = neuron.execute(context)
            job.result = result
            job.state = ExecutionState.COMPLETED
            job.completed_at = time.time()

            self._update_synapses_on_success(job)
            self._record_execution(job, success=True)

            for callback in self._execution_callbacks.values():
                try:
                    callback(job)
                except Exception:
                    pass

        except Exception as e:
            job.state = ExecutionState.FAILED
            job.error = str(e)
            job.completed_at = time.time()

            self._update_synapses_on_failure(job)
            self._record_execution(job, success=False)

        finally:
            self._resource_monitor.release_slot()
            self._resource_monitor.record_execution()

            if self.protocol:
                ticket = self.protocol.get_ticket(job.context_id) if job.context_id else None
                if ticket:
                    self.protocol.complete_ticket(job.job_id, job.result or {})

    def _validate_against_contract(
        self,
        neuron: BaseNeuron,
        inputs: Dict[str, Any]
    ) -> ValidationResult:
        errors = []
        warnings = []

        if not neuron.contract:
            return ValidationResult(valid=True)

        for port in neuron.contract.input_ports:
            if port.required and port.name not in inputs:
                errors.append(f"Missing required input: {port.name}")

            if port.name in inputs and port.data_type:
                actual_type = type(inputs[port.name]).__name__
                if port.data_type != "any" and actual_type != port.data_type:
                    warnings.append(
                        f"Type mismatch for {port.name}: expected {port.data_type}, got {actual_type}"
                    )

        for precond in neuron.contract.preconditions:
            if not self._evaluate_condition(precond, inputs):
                errors.append(f"Precondition failed: {precond}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        try:
            return eval(condition, {"data": data})
        except Exception:
            return False

    def _update_synapses_on_success(self, job: ExecutionJob):
        outcome = job.result.get("outcome", {}) if job.result else {}
        fitness = outcome.get("fitness_after", 0.5)

        synapses = self.synapse_manager.get_synapses_for_source(job.neuron_id)
        for synapse in synapses:
            self.synapse_manager.update_from_outcome(
                synapse.synapse_id,
                execution_success=True,
                outcome_metric=fitness
            )

    def _update_synapses_on_failure(self, job: ExecutionJob):
        synapses = self.synapse_manager.get_synapses_for_source(job.neuron_id)
        for synapse in synapses:
            self.synapse_manager.update_from_outcome(
                synapse.synapse_id,
                execution_success=False,
                outcome_metric=0.0
            )

    def _record_execution(self, job: ExecutionJob, success: bool):
        record = {
            "job_id": job.job_id,
            "neuron_id": job.neuron_id,
            "priority": job.priority.name,
            "success": success,
            "duration": job.completed_at - job.started_at if job.completed_at and job.started_at else 0,
            "timestamp": time.time()
        }

        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_job(self, job_id: str) -> Optional[ExecutionJob]:
        return self._jobs.get(job_id)

    def get_pending_jobs(self, neuron_id: Optional[str] = None) -> List[ExecutionJob]:
        jobs = [j for j in self._jobs.values() if j.state == ExecutionState.QUEUED]
        if neuron_id:
            jobs = [j for j in jobs if j.neuron_id == neuron_id]
        return sorted(jobs, key=lambda j: j.priority.value)

    def get_running_jobs(self) -> List[ExecutionJob]:
        return [j for j in self._jobs.values() if j.state == ExecutionState.RUNNING]

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.state in (ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED):
            return False

        job.state = ExecutionState.CANCELLED
        job.completed_at = time.time()

        for i, queued_job in enumerate(self._job_queue):
            if queued_job.job_id == job_id:
                del self._job_queue[i]
                self._resource_monitor.decrement_queued()
                break

        return True

    def get_execution_history(
        self,
        limit: int = 100,
        neuron_id: Optional[str] = None,
        success_only: bool = False
    ) -> List[Dict[str, Any]]:
        history = self._history
        if neuron_id:
            history = [h for h in history if h["neuron_id"] == neuron_id]
        if success_only:
            history = [h for h in history if h["success"]]

        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._jobs)
        by_state = defaultdict(int)
        for job in self._jobs.values():
            by_state[job.state.name] += 1

        completed = [j for j in self._jobs.values() if j.state == ExecutionState.COMPLETED]
        avg_duration = 0
        if completed:
            durations = [
                j.completed_at - j.started_at
                for j in completed
                if j.completed_at and j.started_at
            ]
            if durations:
                avg_duration = sum(durations) / len(durations)

        return {
            "total_jobs": total,
            "by_state": dict(by_state),
            "average_duration": avg_duration,
            "resource_load": self._resource_monitor.get_load_info()
        }

    def register_validation_callback(self, name: str, callback: Callable):
        self._validation_callbacks[name] = callback

    def register_execution_callback(self, name: str, callback: Callable):
        self._execution_callbacks[name] = callback

    def execute_batch(
        self,
        jobs: List[Tuple[str, Dict[str, Any], Priority]]
    ) -> List[Optional[str]]:
        results = []
        for neuron_id, inputs, priority in jobs:
            job_id = self.submit(neuron_id, inputs, priority)
            results.append(job_id)
        return results

    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> Optional[ExecutionJob]:
        start = time.time()
        while True:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if job.state in (ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED, ExecutionState.VALIDATION_FAILED):
                return job

            if timeout and (time.time() - start) > timeout:
                return job

            time.sleep(0.01)
