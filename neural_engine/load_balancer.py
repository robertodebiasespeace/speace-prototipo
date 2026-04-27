"""
SPEACE Neural Engine - Load Balancer
Sistema di bilanciamento carico per operazione equilibrata.
Evita sovraccarico mantenendo armonia con l'ambiente.
"""

from __future__ import annotations

import uuid
import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, List, Set, Callable
from collections import defaultdict
from collections import deque


class LoadLevel(Enum):
    IDLE = auto()
    LIGHT = auto()
    MODERATE = auto()
    HEAVY = auto()
    CRITICAL = auto()
    OVERLOADED = auto()


class ResourceType(Enum):
    CPU = auto()
    MEMORY = auto()
    NETWORK = auto()
    STORAGE = auto()
    ENERGY = auto()
    ATTENTION = auto()


@dataclass
class ResourceMetrics:
    resource_type: ResourceType
    current_usage: float = 0.0
    capacity: float = 1.0
    avg_usage: float = 0.0
    peak_usage: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemLoad:
    overall_level: LoadLevel = LoadLevel.IDLE
    cpu_load: float = 0.0
    memory_load: float = 0.0
    network_load: float = 0.0
    task_queue_depth: int = 0
    active_neurons: int = 0
    total_capacity: float = 1.0
    available_capacity: float = 1.0
    utilization_ratio: float = 0.0
    balance_score: float = 1.0
    sustainability_index: float = 0.8


@dataclass
class ThrottleConfig:
    max_concurrent_tasks: int = 10
    max_queue_depth: int = 100
    task_timeout: float = 300.0
    rest_interval: float = 1.0
    burst_allowance: float = 0.2
    recovery_rate: float = 0.1


class LoadBalancer:
    VERSION = "1.0.0"

    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()

        self._resource_metrics: Dict[ResourceType, ResourceMetrics] = {
            rt: ResourceMetrics(resource_type=rt, capacity=1.0)
            for rt in ResourceType
        }

        self._load_history: deque = deque(maxlen=1000)
        self._load_predictions: Dict[str, float] = {}
        self._throttle_state = {
            "throttled": False,
            "throttle_factor": 1.0,
            "suppressed_tasks": 0,
            "last_throttle": 0
        }

        self._lock = threading.RLock()
        self._callbacks: Dict[str, Callable] = {}

        self._load_weights = {
            ResourceType.CPU: 0.3,
            ResourceType.MEMORY: 0.25,
            ResourceType.NETWORK: 0.2,
            ResourceType.STORAGE: 0.1,
            ResourceType.ENERGY: 0.1,
            ResourceType.ATTENTION: 0.05
        }

        self._safety_margins = {
            LoadLevel.IDLE: 0.1,
            LoadLevel.LIGHT: 0.2,
            LoadLevel.MODERATE: 0.3,
            LoadLevel.HEAVY: 0.4,
            LoadLevel.CRITICAL: 0.5,
            LoadLevel.OVERLOADED: 0.7
        }

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self):
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        while self._running:
            self._update_resource_metrics()
            self._calculate_system_load()
            self._apply_throttle_if_needed()

            time.sleep(1.0)

    def _update_resource_metrics(self):
        try:
            import psutil

            cpu_load = psutil.cpu_percent() / 100.0
            memory_load = psutil.virtual_memory().percent / 100.0

            try:
                net_io = psutil.net_io_counters()
                network_load = min(1.0, (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024 * 100))
            except Exception:
                network_load = 0.0

            self.update_resource(ResourceType.CPU, cpu_load)
            self.update_resource(ResourceType.MEMORY, memory_load)
            self.update_resource(ResourceType.NETWORK, network_load)

        except ImportError:
            self.update_resource(ResourceType.CPU, 0.3)
            self.update_resource(ResourceType.MEMORY, 0.4)

    def update_resource(self, resource_type: ResourceType, value: float):
        with self._lock:
            metrics = self._resource_metrics[resource_type]
            metrics.current_usage = max(0.0, min(1.0, value))
            metrics.timestamp = time.time()

            if metrics.current_usage > metrics.peak_usage:
                metrics.peak_usage = metrics.current_usage

            history_weight = 0.7
            metrics.avg_usage = (
                history_weight * metrics.avg_usage +
                (1 - history_weight) * metrics.current_usage
            )

    def get_resource(self, resource_type: ResourceType) -> ResourceMetrics:
        return self._resource_metrics.get(resource_type)

    def _calculate_system_load(self) -> SystemLoad:
        weights = self._load_weights
        total_weight = sum(weights.values())

        weighted_load = 0.0
        for rt, weight in weights.items():
            metrics = self._resource_metrics[rt]
            weighted_load += (metrics.current_usage * weight) / total_weight

        cpu = self._resource_metrics[ResourceType.CPU].current_usage
        memory = self._resource_metrics[ResourceType.MEMORY].current_usage
        network = self._resource_metrics[ResourceType.NETWORK].current_usage

        variance = ((cpu - weighted_load) ** 2 +
                     (memory - weighted_load) ** 2 +
                     (network - weighted_load) ** 2) / 3
        balance_score = max(0.0, 1.0 - variance * 2)

        total_capacity = 1.0 - weighted_load
        available_capacity = max(0.0, total_capacity - self._get_safety_margin(weighted_load))

        if weighted_load < 0.2:
            level = LoadLevel.IDLE
        elif weighted_load < 0.4:
            level = LoadLevel.LIGHT
        elif weighted_load < 0.6:
            level = LoadLevel.MODERATE
        elif weighted_load < 0.8:
            level = LoadLevel.HEAVY
        elif weighted_load < 0.95:
            level = LoadLevel.CRITICAL
        else:
            level = LoadLevel.OVERLOADED

        load = SystemLoad(
            overall_level=level,
            cpu_load=cpu,
            memory_load=memory,
            network_load=network,
            utilization_ratio=weighted_load,
            balance_score=balance_score,
            available_capacity=available_capacity,
            sustainability_index=self._calculate_sustainability()
        )

        self._load_history.append({
            "timestamp": time.time(),
            "load": load,
            "metrics": {
                rt.name: m.current_usage
                for rt, m in self._resource_metrics.items()
            }
        })

        return load

    def _get_safety_margin(self, load_level: float) -> float:
        if load_level < 0.2:
            return 0.05
        elif load_level < 0.4:
            return 0.1
        elif load_level < 0.6:
            return 0.15
        elif load_level < 0.8:
            return 0.2
        else:
            return 0.3

    def _calculate_sustainability(self) -> float:
        energy = self._resource_metrics[ResourceType.ENERGY].current_usage
        attention = self._resource_metrics[ResourceType.ATTENTION].current_usage

        energy_factor = 1.0 - energy
        attention_factor = 1.0 - (attention * 0.5)

        return (energy_factor * 0.6 + attention_factor * 0.4)

    def _apply_throttle_if_needed(self):
        current_load = self._calculate_system_load()

        if current_load.overall_level == LoadLevel.OVERLOADED:
            self._throttle_state["throttled"] = True
            self._throttle_state["throttle_factor"] = 0.3
            self._throttle_state["last_throttle"] = time.time()
        elif current_load.overall_level == LoadLevel.CRITICAL:
            self._throttle_state["throttled"] = True
            self._throttle_state["throttle_factor"] = 0.6
            self._throttle_state["last_throttle"] = time.time()
        elif current_load.overall_level == LoadLevel.HEAVY:
            if self._throttle_state["throttled"]:
                self._throttle_state["throttle_factor"] = 0.8
        elif current_load.overall_level in (LoadLevel.IDLE, LoadLevel.LIGHT):
            self._throttle_state["throttled"] = False
            self._throttle_state["throttle_factor"] = 1.0

        if self._throttle_state["throttled"]:
            recovery_elapsed = time.time() - self._throttle_state["last_throttle"]
            if recovery_elapsed > 30:
                self._throttle_state["throttle_factor"] = min(
                    1.0,
                    self._throttle_state["throttle_factor"] + self.config.recovery_rate
                )
                if self._throttle_state["throttle_factor"] >= 1.0:
                    self._throttle_state["throttled"] = False

    def can_accept_task(
        self,
        priority: int = 2,
        estimated_load: float = 0.1
    ) -> tuple[bool, str]:
        current_load = self._calculate_system_load()

        if current_load.overall_level == LoadLevel.OVERLOADED:
            return False, "System overloaded"

        if current_load.overall_level == LoadLevel.CRITICAL:
            if priority < 1:
                return False, "Critical load - only high priority tasks"
            if estimated_load > current_load.available_capacity:
                return False, "Insufficient capacity"

        if current_load.task_queue_depth >= self.config.max_queue_depth:
            if priority < 0:
                return False, "Queue full"
            return False, "Queue at maximum capacity"

        effective_capacity = current_load.available_capacity * self._throttle_state["throttle_factor"]

        if estimated_load > effective_capacity:
            return False, f"Insufficient resources (need {estimated_load:.2f}, have {effective_capacity:.2f})"

        return True, "OK"

    def get_throttle_factor(self) -> float:
        return self._throttle_state["throttle_factor"]

    def is_throttled(self) -> bool:
        return self._throttle_state["throttled"]

    def get_admission_decision(
        self,
        task_id: str,
        priority: int,
        estimated_load: float
    ) -> Dict[str, Any]:
        can_accept, reason = self.can_accept_task(priority, estimated_load)

        return {
            "task_id": task_id,
            "accepted": can_accept,
            "reason": reason,
            "current_load": self._calculate_system_load().overall_level.name,
            "throttle_factor": self._throttle_state["throttle_factor"],
            "available_capacity": self._calculate_system_load().available_capacity,
            "timestamp": time.time()
        }

    def get_load_report(self) -> Dict[str, Any]:
        current_load = self._calculate_system_load()

        recent_history = list(self._load_history)[-60:]

        avg_cpu = sum(h["metrics"].get("CPU", 0) for h in recent_history) / len(recent_history) if recent_history else 0
        avg_memory = sum(h["metrics"].get("MEMORY", 0) for h in recent_history) / len(recent_history) if recent_history else 0

        return {
            "current_load": {
                "level": current_load.overall_level.name,
                "cpu": current_load.cpu_load,
                "memory": current_load.memory_load,
                "network": current_load.network_load,
                "utilization_ratio": current_load.utilization_ratio,
                "balance_score": current_load.balance_score,
                "available_capacity": current_load.available_capacity,
                "sustainability_index": current_load.sustainability_index
            },
            "averages": {
                "cpu_60s": avg_cpu,
                "memory_60s": avg_memory
            },
            "throttle": {
                "active": self._throttle_state["throttled"],
                "factor": self._throttle_state["throttle_factor"],
                "suppressed_count": self._throttle_state["suppressed_tasks"]
            },
            "history_size": len(self._load_history),
            "recommendations": self._generate_recommendations(current_load)
        }

    def _generate_recommendations(self, load: SystemLoad) -> List[str]:
        recommendations = []

        if load.cpu_load > 0.8:
            recommendations.append("High CPU usage - consider reducing computation intensity")

        if load.memory_load > 0.85:
            recommendations.append("High memory pressure - prioritize memory optimization")

        if load.balance_score < 0.5:
            recommendations.append("Imbalanced resource usage - redistribute tasks")

        if load.sustainability_index < 0.5:
            recommendations.append("Low sustainability - reduce energy consumption")

        if load.overall_level in (LoadLevel.HEAVY, LoadLevel.CRITICAL, LoadLevel.OVERLOADED):
            recommendations.append("High system load - prioritize essential tasks only")

        return recommendations

    def suggest_load_shedding(self, target_reduction: float) -> List[Dict[str, Any]]:
        current_load = self._calculate_system_load()
        suggestions = []

        if current_load.cpu_load > 0.5:
            suggestions.append({
                "type": "cpu",
                "action": "defer_non_critical",
                "potential_reduction": current_load.cpu_load * 0.3,
                "priority": "medium"
            })

        if current_load.network_load > 0.5:
            suggestions.append({
                "type": "network",
                "action": "batch_operations",
                "potential_reduction": current_load.network_load * 0.4,
                "priority": "low"
            })

        if current_load.memory_load > 0.6:
            suggestions.append({
                "type": "memory",
                "action": "clear_caches",
                "potential_reduction": current_load.memory_load * 0.2,
                "priority": "high"
            })

        return suggestions

    def register_callback(self, name: str, callback: Callable):
        self._callbacks[name] = callback

    def notify_load_change(self, old_level: LoadLevel, new_level: LoadLevel):
        for callback in self._callbacks.values():
            try:
                callback(old_level, new_level)
            except Exception:
                pass

    def get_predictions(self) -> Dict[str, float]:
        if len(self._load_history) < 10:
            return {}

        recent = list(self._load_history)[-30:]
        if not recent:
            return {}

        cpu_values = [h["metrics"].get("CPU", 0) for h in recent]
        trend = sum(cpu_values[-10:]) / 10 - sum(cpu_values[:10]) / 10

        return {
            "cpu_trend": trend,
            "predicted_load_1min": min(1.0, sum(cpu_values[-5:]) / 5 + trend)
        }

    def reset_metrics(self):
        with self._lock:
            for metrics in self._resource_metrics.values():
                metrics.current_usage = 0.0
                metrics.avg_usage = 0.0
                metrics.peak_usage = 0.0

            self._load_history.clear()
            self._throttle_state["throttled"] = False
            self._throttle_state["throttle_factor"] = 1.0
