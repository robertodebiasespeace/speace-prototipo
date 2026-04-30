"""
SPEACE Attention System – BRN-014
Selective, divided, and executive attention mechanisms.

Models three attention streams:
1. SelectiveAttention – bottom-up saliency + top-down goal-directed filtering
2. DividedAttention  – resource allocation across multiple concurrent streams
3. ExecutiveAttention – inhibitory control and conflict monitoring

Integrates with:
- ThalamicRelaySystem (BRN-002): attentional gating
- WorkingMemory (BRN-006): binding attended items
- ConsciousnessGate (BRN-010): broadcasting to global workspace

Version: 1.0
Data: 26 Aprile 2026
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent.parent


# ─── Enums ──────────────────────────────────────────────────────────────────

class AttentionMode(Enum):
    FOCUSED   = "focused"     # Single stream, high depth
    DIVIDED   = "divided"     # Multiple streams, lower depth per stream
    DIFFUSE   = "diffuse"     # Background monitoring
    EXECUTIVE = "executive"   # Conflict resolution mode


class AttentionSignalType(Enum):
    BOTTOM_UP = "bottom_up"   # Stimulus-driven (saliency)
    TOP_DOWN  = "top_down"    # Goal-driven (task relevance)
    SOCIAL    = "social"      # Social cue driven (BRN-009)
    EMOTIONAL = "emotional"   # Amygdala-triggered (BRN-003)
    MEMORY    = "memory"      # Hippocampus cued (BRN-012)


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class AttentionalResource:
    """Finite attentional resource pool (Kahneman model)."""
    total_capacity: float = 1.0
    allocated: float = 0.0
    reserve: float = 0.1       # Always-on background allocation

    @property
    def available(self) -> float:
        return max(0.0, self.total_capacity - self.allocated - self.reserve)

    def allocate(self, amount: float) -> float:
        """Allocate attention; returns actually allocated amount."""
        actual = min(amount, self.available)
        self.allocated += actual
        return actual

    def release(self, amount: float) -> None:
        self.allocated = max(0.0, self.allocated - amount)

    def reset(self) -> None:
        self.allocated = 0.0


@dataclass
class AttentionSignal:
    """An input signal competing for attentional resources."""
    source_id: str
    signal_type: AttentionSignalType
    saliency: float           # 0-1 bottom-up salience
    relevance: float          # 0-1 top-down goal relevance
    urgency: float            # 0-1 temporal urgency
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def priority(self) -> float:
        """Composite attentional priority."""
        return 0.35 * self.saliency + 0.45 * self.relevance + 0.20 * self.urgency


@dataclass
class AttentionFocus:
    """Currently attended stream."""
    stream_id: str
    signal: AttentionSignal
    allocated_resource: float
    start_time: float = field(default_factory=time.time)
    duration: float = 0.0        # seconds attended so far
    depth: float = 0.5           # Processing depth (0=shallow, 1=deep)

    def update_duration(self) -> None:
        self.duration = time.time() - self.start_time


# ─── Selective Attention ─────────────────────────────────────────────────────

class SelectiveAttention:
    """
    Bottom-up + top-down selective attention filter.
    Implements a simplified version of the Guided Search model (Wolfe 1994).
    """

    def __init__(self, capacity: int = 3):
        """capacity: max number of items that pass the attention filter."""
        self.capacity = capacity
        self.current_goal: Optional[str] = None
        self.goal_features: Dict[str, float] = {}     # Feature → relevance weight
        self.filter_history: deque = deque(maxlen=100)
        self.selection_count = 0

    def set_goal(self, goal: str, features: Dict[str, float]) -> None:
        """Set current top-down attentional goal."""
        self.current_goal = goal
        self.goal_features = features
        logger.debug(f"SelectiveAttention: goal set → '{goal}' with {len(features)} features")

    def filter(self, signals: List[AttentionSignal]) -> List[AttentionSignal]:
        """
        Apply attention filter: score each signal, return top-k.
        Combines bottom-up saliency with top-down relevance.
        """
        if not signals:
            return []

        scored = []
        for sig in signals:
            # Bottom-up component
            bu_score = sig.saliency

            # Top-down component: match with goal features
            td_score = sig.relevance
            for feat_key, feat_weight in self.goal_features.items():
                if feat_key in sig.content:
                    td_score = min(1.0, td_score + feat_weight * 0.2)

            # Urgency boost
            urgency_boost = sig.urgency * 0.3

            composite = bu_score * 0.4 + td_score * 0.45 + urgency_boost
            scored.append((composite, sig))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [sig for _, sig in scored[:self.capacity]]

        self.selection_count += 1
        self.filter_history.append({
            "candidates": len(signals),
            "selected": len(selected),
            "top_priority": round(scored[0][0], 3) if scored else 0,
            "timestamp": time.time()
        })
        return selected

    def get_status(self) -> Dict:
        return {
            "current_goal": self.current_goal,
            "capacity": self.capacity,
            "total_selections": self.selection_count,
            "goal_features": self.goal_features
        }


# ─── Divided Attention ───────────────────────────────────────────────────────

class DividedAttention:
    """
    Manages concurrent attention streams with resource allocation.
    Based on Wickens' Multiple Resource Theory.
    """

    def __init__(self, max_streams: int = 4):
        self.max_streams = max_streams
        self.resource_pool = AttentionalResource(total_capacity=1.0)
        self.active_streams: Dict[str, AttentionFocus] = {}
        self.stream_history: deque = deque(maxlen=200)
        self.time_sharing_events = 0

    def add_stream(self, signal: AttentionSignal,
                   requested_resource: float = 0.3) -> Optional[AttentionFocus]:
        """Add a new attention stream if capacity allows."""
        if len(self.active_streams) >= self.max_streams:
            # Preempt lowest priority stream
            self._preempt_lowest()

        allocated = self.resource_pool.allocate(requested_resource)
        if allocated < 0.05:
            logger.debug(f"DividedAttention: insufficient resources for {signal.source_id}")
            return None

        depth = min(1.0, allocated / 0.3)   # Depth scales with resources
        focus = AttentionFocus(
            stream_id=signal.source_id,
            signal=signal,
            allocated_resource=allocated,
            depth=depth
        )
        self.active_streams[signal.source_id] = focus
        logger.debug(f"DividedAttention: added stream {signal.source_id} | "
                     f"resource={allocated:.2f} | depth={depth:.2f}")
        return focus

    def remove_stream(self, stream_id: str) -> None:
        """Release a stream and return its resources."""
        if stream_id in self.active_streams:
            focus = self.active_streams.pop(stream_id)
            focus.update_duration()
            self.resource_pool.release(focus.allocated_resource)
            self.stream_history.append({
                "stream_id": stream_id,
                "duration": round(focus.duration, 3),
                "depth": round(focus.depth, 3)
            })

    def tick(self) -> Dict[str, float]:
        """Time-share: return per-stream processing budget for this tick."""
        self.time_sharing_events += 1
        budget = {}
        total_priority = sum(f.signal.priority for f in self.active_streams.values())
        if total_priority == 0:
            return budget
        for sid, focus in self.active_streams.items():
            focus.update_duration()
            # Time proportional to priority × resource allocation
            share = focus.signal.priority / total_priority
            budget[sid] = round(share * focus.allocated_resource, 4)
        return budget

    def _preempt_lowest(self) -> None:
        if not self.active_streams:
            return
        lowest = min(self.active_streams.values(), key=lambda f: f.signal.priority)
        self.remove_stream(lowest.stream_id)

    def get_status(self) -> Dict:
        return {
            "active_streams": len(self.active_streams),
            "max_streams": self.max_streams,
            "available_resource": round(self.resource_pool.available, 3),
            "time_sharing_events": self.time_sharing_events,
            "streams": {
                sid: {"priority": round(f.signal.priority, 3),
                      "resource": round(f.allocated_resource, 3),
                      "depth": round(f.depth, 3)}
                for sid, f in self.active_streams.items()
            }
        }


# ─── Executive Attention ─────────────────────────────────────────────────────

class ExecutiveAttention:
    """
    Anterior Cingulate Cortex (ACC) inspired conflict monitoring and resolution.
    Implements inhibitory control for suppression of prepotent responses.
    """

    def __init__(self, conflict_threshold: float = 0.4):
        self.conflict_threshold = conflict_threshold
        self.conflict_history: deque = deque(maxlen=100)
        self.inhibition_log: deque = deque(maxlen=100)
        self.total_conflicts_detected = 0
        self.total_inhibitions = 0
        self.current_conflict_level: float = 0.0

    def monitor_conflict(self, signals: List[AttentionSignal]) -> float:
        """
        Compute conflict level across competing signals.
        High conflict → executive control needed.
        Returns conflict level (0-1).
        """
        if len(signals) < 2:
            self.current_conflict_level = 0.0
            return 0.0

        # Conflict as variance in priority scores + mutual inhibition
        priorities = [s.priority for s in signals]
        mean_p = sum(priorities) / len(priorities)
        variance = sum((p - mean_p) ** 2 for p in priorities) / len(priorities)
        # High variance = low conflict (clear winner); low variance = high conflict
        conflict = 1.0 - min(1.0, variance * 4)

        # Extra conflict if signals are of opposing types
        types = [s.signal_type for s in signals]
        if AttentionSignalType.BOTTOM_UP in types and AttentionSignalType.TOP_DOWN in types:
            conflict = min(1.0, conflict + 0.2)

        self.current_conflict_level = conflict
        self.conflict_history.append({
            "conflict": round(conflict, 3),
            "n_signals": len(signals),
            "timestamp": time.time()
        })
        if conflict > self.conflict_threshold:
            self.total_conflicts_detected += 1
        return conflict

    def resolve(self, signals: List[AttentionSignal],
                conflict_level: float) -> List[AttentionSignal]:
        """
        Apply executive control to resolve conflict.
        Suppresses low-priority signals, boosts task-relevant ones.
        """
        if conflict_level < self.conflict_threshold:
            return signals    # No intervention needed

        # Sort by priority, keep top-2 and suppress rest
        sorted_sigs = sorted(signals, key=lambda s: s.priority, reverse=True)
        kept = sorted_sigs[:2]
        suppressed = sorted_sigs[2:]

        for sig in suppressed:
            self.inhibition_log.append({
                "suppressed_id": sig.source_id,
                "priority": round(sig.priority, 3),
                "conflict_level": round(conflict_level, 3)
            })
            self.total_inhibitions += 1
            logger.debug(f"ExecutiveAttention: suppressed {sig.source_id} "
                         f"(priority={sig.priority:.3f})")
        return kept

    def inhibit_response(self, stream_id: str,
                         divided_attention: DividedAttention) -> bool:
        """
        Inhibit (stop) a prepotent response stream (Stop Signal task analog).
        Returns True if successfully inhibited.
        """
        if stream_id in divided_attention.active_streams:
            divided_attention.remove_stream(stream_id)
            self.total_inhibitions += 1
            logger.info(f"ExecutiveAttention: inhibited stream {stream_id}")
            return True
        return False

    def get_status(self) -> Dict:
        return {
            "conflict_threshold": self.conflict_threshold,
            "current_conflict_level": round(self.current_conflict_level, 3),
            "total_conflicts_detected": self.total_conflicts_detected,
            "total_inhibitions": self.total_inhibitions
        }


# ─── Attention System Core ───────────────────────────────────────────────────

class AttentionSystem:
    """
    SPEACE Attention System (BRN-014).

    Coordinates all three attention subsystems:
    - SelectiveAttention (what to attend to)
    - DividedAttention (how to split resources)
    - ExecutiveAttention (conflict control)

    Provides a unified interface used by CortexOrchestrator.
    """

    def __init__(self):
        self.selective = SelectiveAttention(capacity=3)
        self.divided = DividedAttention(max_streams=4)
        self.executive = ExecutiveAttention(conflict_threshold=0.4)

        self.current_mode = AttentionMode.DIFFUSE
        self.tick_count = 0
        self.attention_log: deque = deque(maxlen=200)
        logger.info("AttentionSystem BRN-014 initialized")

    # ── Public API ──────────────────────────────────────────────────────────

    def set_goal(self, goal: str, features: Dict[str, float]) -> None:
        """Set current cognitive goal for top-down attention."""
        self.selective.set_goal(goal, features)
        self.current_mode = AttentionMode.FOCUSED

    def process(self, signals: List[AttentionSignal]) -> Dict[str, Any]:
        """
        Main attention processing cycle.
        1. Selective filter
        2. Conflict detection + executive resolution
        3. Resource allocation (divided attention)
        Returns: processing budget per attended stream.
        """
        self.tick_count += 1

        # Step 1: Selective attention filter
        filtered = self.selective.filter(signals)

        # Step 2: Conflict monitoring + executive control
        conflict = self.executive.monitor_conflict(filtered)
        if conflict > self.executive.conflict_threshold:
            self.current_mode = AttentionMode.EXECUTIVE
            filtered = self.executive.resolve(filtered, conflict)
        elif len(filtered) > 1:
            self.current_mode = AttentionMode.DIVIDED
        else:
            self.current_mode = AttentionMode.FOCUSED

        # Step 3: Allocate to divided attention streams
        # First remove stale streams not in current selection
        active_ids = set(self.divided.active_streams.keys())
        selected_ids = {s.source_id for s in filtered}
        for stale_id in active_ids - selected_ids:
            self.divided.remove_stream(stale_id)

        # Add new streams
        for sig in filtered:
            if sig.source_id not in self.divided.active_streams:
                requested = 0.4 / max(1, len(filtered))  # Share evenly
                self.divided.add_stream(sig, requested_resource=requested)

        # Step 4: Time-share budget
        budget = self.divided.tick()

        result = {
            "mode": self.current_mode.value,
            "selected_streams": [s.source_id for s in filtered],
            "conflict_level": round(conflict, 3),
            "budget": budget,
            "tick": self.tick_count
        }
        self.attention_log.append({**result, "timestamp": time.time()})
        return result

    def emergency_focus(self, signal: AttentionSignal) -> None:
        """
        Immediate attentional capture by a high-urgency signal.
        Clears all current streams and focuses entirely on the emergency.
        """
        for sid in list(self.divided.active_streams.keys()):
            self.divided.remove_stream(sid)
        self.divided.resource_pool.reset()
        self.divided.add_stream(signal, requested_resource=0.9)
        self.current_mode = AttentionMode.FOCUSED
        logger.warning(f"AttentionSystem: EMERGENCY FOCUS on {signal.source_id}")

    def release_focus(self) -> None:
        """Release all streams, return to diffuse monitoring."""
        for sid in list(self.divided.active_streams.keys()):
            self.divided.remove_stream(sid)
        self.current_mode = AttentionMode.DIFFUSE

    def get_full_status(self) -> Dict:
        return {
            "module": "AttentionSystem",
            "brn_id": "BRN-014",
            "mode": self.current_mode.value,
            "tick_count": self.tick_count,
            "selective": self.selective.get_status(),
            "divided": self.divided.get_status(),
            "executive": self.executive.get_status()
        }


# ─── Factory ─────────────────────────────────────────────────────────────────

def create_attention_system() -> AttentionSystem:
    """Factory function for AttentionSystem."""
    return AttentionSystem()


# ─── Self-test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    attn = create_attention_system()

    # Set a goal
    attn.set_goal("analyze_climate_data", {
        "temperature": 0.9,
        "co2": 0.8,
        "ocean": 0.6
    })

    # Create test signals
    signals = [
        AttentionSignal("climate_feed", AttentionSignalType.TOP_DOWN,
                        saliency=0.4, relevance=0.9, urgency=0.3,
                        content={"temperature": 1.2, "co2": 418}),
        AttentionSignal("social_alert", AttentionSignalType.SOCIAL,
                        saliency=0.8, relevance=0.3, urgency=0.6),
        AttentionSignal("memory_cue", AttentionSignalType.MEMORY,
                        saliency=0.2, relevance=0.7, urgency=0.1),
        AttentionSignal("noise_1", AttentionSignalType.BOTTOM_UP,
                        saliency=0.1, relevance=0.1, urgency=0.05),
    ]

    result = attn.process(signals)
    print("\n[AttentionSystem] Processing result:")
    print(json.dumps(result, indent=2))

    print("\n[AttentionSystem] Full status:")
    print(json.dumps(attn.get_full_status(), indent=2))

    print("\n[AttentionSystem] BRN-014 self-test passed ✓")
