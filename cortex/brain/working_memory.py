"""
SPEACE Working Memory Module - BRN-006
Implements prefrontal working memory with rapid access and temporal maintenance.
Models: DLPFC, VLPFC, ACC (Anterior Cingulate Cortex).
Version: 1.0
Data: 25 Aprile 2026

Working memory is crucial for:
- Maintaining information temporarily for task execution
- Binding disparate items into coherent representations
- Executive attention and interference control
- Decision making with limited capacity
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WMRegion(Enum):
    """Working memory brain regions."""
    DLPFC = "dorsolateral_prefrontal"  # Spatial reasoning, manipulation
    VLPFC = "ventrolateral_prefrontal"  # Item maintenance, recognition
    ACC = "anterior_cingulate"  # Conflict monitoring, error detection


@dataclass
class WMItem:
    """Single item in working memory."""
    id: str
    content: np.ndarray
    activation: float
    timestamp: str
    decay_rate: float = 0.01

    def get_age(self) -> float:
        """Get age in seconds."""
        then = datetime.fromisoformat(self.timestamp)
        return (datetime.now() - then).total_seconds()


@dataclass
class WMState:
    """Complete working memory state."""
    active_items: int
    total_capacity: int
    mean_activation: float
    interference_level: float
    current_focus: Optional[str] = None


class DLPFC_Module:
    """
    Dorsolateral PFC - Spatial working memory and mental manipulation.
    Holds "what" and "where" information for spatial reasoning tasks.
    """
    def __init__(self, capacity: int = 4, item_size: int = 128):
        self.capacity = capacity
        self.item_size = item_size

        # Storage
        self.items: Dict[str, WMItem] = {}
        self.item_order = deque(maxlen=capacity)  # FIFO

        # Attention mechanism
        self.focused_item: Optional[str] = None
        self.attention_weight = 0.8

        # Manipulation buffer
        self.manipulation_buffer = np.zeros(item_size)
        self.manipulation_active = False

        # Executive functions
        self.binding_strength = np.ones(capacity) * 0.5
        self.interference_threshold = 0.6

        # Metrics
        self.access_count = 0
        self.interference_events = 0

    def store(self, item_id: str, content: np.ndarray, priority: float = 0.5) -> bool:
        """Store item in DLPFC working memory."""
        # Enforce capacity
        if len(self.items) >= self.capacity and item_id not in self.items:
            # Remove oldest item
            oldest_id = self.item_order[0] if len(self.item_order) > 0 else None
            if oldest_id and oldest_id in self.items:
                del self.items[oldest_id]
                self.item_order.popleft()

        # Store new item
        activation = priority * self.attention_weight
        self.items[item_id] = WMItem(
            id=item_id,
            content=content[:self.item_size],
            activation=activation,
            timestamp=datetime.now().isoformat(),
            decay_rate=0.02
        )
        self.item_order.append(item_id)

        logger.debug(f"DLPFC stored item {item_id}, capacity: {len(self.items)}/{self.capacity}")
        return True

    def retrieve(self, item_id: str) -> Optional[np.ndarray]:
        """Retrieve specific item by id."""
        self.access_count += 1

        if item_id not in self.items:
            return None

        item = self.items[item_id]
        # Boost activation on access
        item.activation = min(1.0, item.activation + 0.2)
        item.timestamp = datetime.now().isoformat()

        return item.content.copy()

    def focus_on(self, item_id: str):
        """Focus attention on specific item."""
        if item_id in self.items:
            self.focused_item = item_id
            self.items[item_id].activation = min(1.0, self.items[item_id].activation + 0.3)

    def manipulate(self, operation: str, item_ids: List[str]) -> Optional[np.ndarray]:
        """
        Perform mental manipulation on items.
        Operations: 'compare', 'transform', 'combine', 'sequence'
        """
        if not item_ids or operation not in ['compare', 'transform', 'combine', 'sequence']:
            return None

        # Retrieve items
        item_contents = []
        for item_id in item_ids:
            if item_id in self.items:
                item_contents.append(self.items[item_id].content)
            else:
                return None

        if not item_contents:
            return None

        self.manipulation_active = True

        if operation == 'combine':
            self.manipulation_buffer = np.mean(item_contents, axis=0)
        elif operation == 'compare':
            self.manipulation_buffer = item_contents[0] - np.mean(item_contents[1:], axis=0)
        elif operation == 'transform':
            self.manipulation_buffer = np.tanh(item_contents[0] * 1.5)
        elif operation == 'sequence':
            self.manipulation_buffer = np.concatenate(item_contents)[:self.item_size]

        return self.manipulation_buffer.copy()

    def decay_all(self):
        """Apply decay to all items."""
        for item in self.items.values():
            item.activation *= (1 - item.decay_rate)
            item.activation = max(0.0, item.activation)

    def check_interference(self) -> float:
        """Check interference level between items."""
        if len(self.items) < 2:
            return 0.0

        items_list = list(self.items.values())
        similarities = []

        for i in range(len(items_list)):
            for j in range(i + 1, len(items_list)):
                similarity = np.dot(items_list[i].content, items_list[j].content)
                similarity /= (np.linalg.norm(items_list[i].content) * np.linalg.norm(items_list[j].content) + 1e-8)
                similarities.append(abs(similarity))

        interference = np.mean(similarities) if similarities else 0.0
        return interference

    def get_state(self) -> Dict:
        return {
            "items_stored": len(self.items),
            "capacity": self.capacity,
            "focused_item": self.focused_item,
            "manipulation_active": self.manipulation_active,
            "interference": self.check_interference(),
            "access_count": self.access_count
        }


class VLPFC_Module:
    """
    Ventrolateral PFC - Item recognition and maintenance.
    Specialized for "what" information and item recognition.
    """
    def __init__(self, capacity: int = 5, item_size: int = 96):
        self.capacity = capacity
        self.item_size = item_size

        # Category-based organization
        self.items_by_category: Dict[str, List[str]] = {}
        self.category_weights = np.random.randn(32, item_size) * 0.03

        # Storage
        self.items: Dict[str, WMItem] = {}
        self.recency_order = deque(maxlen=capacity)

        # Recognition buffers
        self.recognition_threshold = 0.6
        self.template_match_scores = deque(maxlen=20)

        # Semantic associations
        self.associations = {}  # item_id -> [(associated_id, strength)]

    def store(self, item_id: str, content: np.ndarray,
             category: str = None, priority: float = 0.5) -> bool:
        """Store item with optional category."""
        # Enforce capacity
        if len(self.items) >= self.capacity and item_id not in self.items:
            oldest_id = self.recency_order[0] if len(self.recency_order) > 0 else None
            if oldest_id and oldest_id in self.items:
                del self.items[oldest_id]
                self.recency_order.popleft()

        # Categorize if provided
        if category and category not in self.items_by_category:
            self.items_by_category[category] = []
        if category and item_id not in self.items_by_category.get(category, []):
            self.items_by_category[category].append(item_id)

        # Store item
        activation = priority * 0.9
        self.items[item_id] = WMItem(
            id=item_id,
            content=content[:self.item_size],
            activation=activation,
            timestamp=datetime.now().isoformat(),
            decay_rate=0.015
        )
        self.recency_order.append(item_id)

        return True

    def recognize(self, probe: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        Recognize if probe matches any stored item.
        Returns (item_id, confidence) or None.
        """
        probe_norm = probe / (np.linalg.norm(probe) + 1e-8)

        best_match = None
        best_score = 0.0

        for item_id, item in self.items.items():
            item_norm = item.content / (np.linalg.norm(item.content) + 1e-8)
            score = np.dot(probe_norm, item_norm)

            if score > best_score:
                best_score = score
                best_match = item_id

        self.template_match_scores.append(best_score)

        if best_score >= self.recognition_threshold:
            return best_match, best_score

        return None

    def get_category_items(self, category: str) -> List[str]:
        """Get all items in a category."""
        return self.items_by_category.get(category, []).copy()

    def add_association(self, item1_id: str, item2_id: str, strength: float = 0.5):
        """Add semantic association between items."""
        if item1_id not in self.associations:
            self.associations[item1_id] = []
        if item2_id not in self.associations:
            self.associations[item2_id] = []

        self.associations[item1_id].append((item2_id, strength))
        self.associations[item2_id].append((item1_id, strength))

    def retrieve_by_association(self, item_id: str) -> List[Tuple[str, float]]:
        """Retrieve items associated with given item."""
        associations = self.associations.get(item_id, [])
        return [(assoc_id, strength) for assoc_id, strength in associations
                if assoc_id in self.items]

    def decay_all(self):
        """Apply decay to all items."""
        for item in self.items.values():
            item.activation *= (1 - item.decay_rate)
            item.activation = max(0.0, item.activation)

    def get_state(self) -> Dict:
        return {
            "items_stored": len(self.items),
            "capacity": self.capacity,
            "categories": len(self.items_by_category),
            "avg_recognition_score": np.mean(list(self.template_match_scores)) if self.template_match_scores else 0.0,
            "associations_count": len(self.associations)
        }


class ACC_Module:
    """
    Anterior Cingulate Cortex - Conflict monitoring and error detection.
    Monitors for conflict in decision making and initiates error signals.
    """
    def __init__(self, input_size: int = 128, output_size: int = 64):
        self.input_size = input_size
        self.output_size = output_size

        # Conflict monitoring
        self.conflict_weights = np.random.randn(output_size, input_size) * 0.03
        self.conflict_threshold = 0.5

        # Error detection
        self.error_weights = np.random.randn(output_size, input_size) * 0.04
        self.error_signal = 0.0

        # Output signals
        self.conflict_level = 0.0
        self.error_probability = 0.0
        self.confidence_level = 0.8

        # Monitoring history
        self.conflict_history = deque(maxlen=100)
        self.error_history = deque(maxlen=50)

    def monitor_conflict(self, response1: np.ndarray, response2: np.ndarray = None) -> float:
        """
        Monitor conflict between competing responses.
        High conflict = multiple competing options.
        """
        # Compare response patterns
        if response2 is not None:
            # Direct comparison
            conflict = np.sum(np.abs(response1 - response2)) / len(response1)
        else:
            # Self competition (response vs itself after delay)
            conflict = np.var(response1) * 0.5

        self.conflict_level = np.clip(conflict, 0, 1)
        self.conflict_history.append(self.conflict_level)

        # Compute confidence based on conflict
        self.confidence_level = 1.0 - self.conflict_level * 0.5

        return self.conflict_level

    def detect_error(self, expected: np.ndarray, actual: np.ndarray) -> float:
        """
        Detect error between expected and actual outcomes.
        Returns error magnitude.
        """
        error = np.mean(np.abs(expected - actual))
        self.error_signal = error

        # Error probability based on error magnitude
        self.error_probability = min(1.0, error * 2)

        self.error_history.append({
            "error_magnitude": error,
            "error_signal": self.error_signal,
            "timestamp": datetime.now().isoformat()
        })

        return error

    def process(self, cortical_input: np.ndarray) -> Dict[str, float]:
        """Process monitoring signals."""
        # Compute conflict
        conflict_input = np.dot(self.conflict_weights, cortical_input[:self.input_size])
        self.conflict_level = float(np.mean(np.abs(conflict_input)))

        # Compute error signal
        error_input = np.dot(self.error_weights, cortical_input[:self.input_size])
        self.error_signal = float(np.mean(np.abs(error_input)))

        # Update history
        self.conflict_history.append(self.conflict_level)

        return {
            "conflict_level": self.conflict_level,
            "error_signal": self.error_signal,
            "confidence": self.confidence_level,
            "error_probability": self.error_probability
        }

    def needs_reconfiguration(self, threshold: float = None) -> bool:
        """Check if system needs executive reconfiguration."""
        if threshold is None:
            threshold = self.conflict_threshold

        return self.conflict_level > threshold or self.error_probability > 0.5

    def get_state(self) -> Dict:
        return {
            "conflict_level": self.conflict_level,
            "error_signal": self.error_signal,
            "confidence": self.confidence_level,
            "error_probability": self.error_probability,
            "avg_conflict": np.mean(list(self.conflict_history)) if self.conflict_history else 0.0,
            "error_count": len(self.error_history)
        }


class WorkingMemory:
    """
    Complete Working Memory System.
    Integrates DLPFC, VLPFC, and ACC for full WM functionality.
    """
    def __init__(self, dlpfc_capacity: int = 4, vlpfc_capacity: int = 5):
        # Components
        self.dlpfc = DLPFC_Module(capacity=dlpfc_capacity, item_size=128)
        self.vlpfc = VLPFC_Module(capacity=vlpfc_capacity, item_size=96)
        self.acc = ACC_Module(input_size=128, output_size=64)

        # Capacity limits (Miller's 7 +/- 2)
        self.max_capacity = 7
        self.total_items = 0

        # State tracking
        self.is_attending = False
        self.current_focus: Optional[str] = None
        self.attention_binding_strength = 0.7

        # Central executive state
        self.executive_active = False
        self.interference_suppression = False

        # History
        self.access_history = deque(maxlen=100)
        self.manipulation_history = deque(maxlen=50)

    def store(self, item_id: str, content: np.ndarray,
             region: WMRegion = WMRegion.DLPFC,
             priority: float = 0.5,
             category: str = None) -> bool:
        """Store item in specified region."""
        self.total_items += 1

        if region == WMRegion.DLPFC:
            success = self.dlpfc.store(item_id, content, priority)
        elif region == WMRegion.VLPFC:
            success = self.vlpfc.store(item_id, content, category, priority)
        else:
            return False

        if success:
            self.access_history.append({
                "action": "store",
                "item_id": item_id,
                "region": region.value,
                "timestamp": datetime.now().isoformat()
            })

        return success

    def retrieve(self, item_id: str, region: WMRegion = WMRegion.DLPFC) -> Optional[np.ndarray]:
        """Retrieve item from specified region."""
        if region == WMRegion.DLPFC:
            result = self.dlpfc.retrieve(item_id)
        elif region == WMRegion.VLPFC:
            item = self.vlpfc.items.get(item_id)
            result = item.content.copy() if item else None
        else:
            return None

        if result is not None:
            self.access_history.append({
                "action": "retrieve",
                "item_id": item_id,
                "region": region.value,
                "timestamp": datetime.now().isoformat()
            })

        return result

    def focus_attention(self, item_id: str):
        """Focus attention on specific item."""
        self.is_attending = True
        self.current_focus = item_id
        self.dlpfc.focus_on(item_id)

    def release_attention(self):
        """Release attention focus."""
        self.is_attending = False
        self.current_focus = None

    def manipulate_items(self, operation: str, item_ids: List[str]) -> Optional[np.ndarray]:
        """Perform mental manipulation on items."""
        result = self.dlpfc.manipulate(operation, item_ids)

        if result is not None:
            self.manipulation_history.append({
                "operation": operation,
                "items": item_ids,
                "result_size": len(result),
                "timestamp": datetime.now().isoformat()
            })
            self.executive_active = True

        return result

    def recognize(self, probe: np.ndarray) -> Optional[Tuple[str, float]]:
        """Recognize probe against stored items (VLPFC)."""
        return self.vlpfc.recognize(probe)

    def monitor_conflict(self, response1: np.ndarray, response2: np.ndarray = None) -> float:
        """Monitor for decision conflict."""
        return self.acc.monitor_conflict(response1, response2)

    def detect_error(self, expected: np.ndarray, actual: np.ndarray) -> float:
        """Detect error between expected and actual."""
        return self.acc.detect_error(expected, actual)

    def decay_all(self):
        """Apply decay to all working memory items."""
        self.dlpfc.decay_all()
        self.vlpfc.decay_all()

    def cleanup_weaks(self, threshold: float = 0.1):
        """Remove items with activation below threshold."""
        # DLPFC cleanup
        to_remove_dlpfc = [k for k, v in self.dlpfc.items.items() if v.activation < threshold]
        for k in to_remove_dlpfc:
            del self.dlpfc.items[k]

        # VLPFC cleanup
        to_remove_vlpfc = [k for k, v in self.vlpfc.items.items() if v.activation < threshold]
        for k in to_remove_vlpfc:
            del self.vlpfc.items[k]

        self.total_items = len(self.dlpfc.items) + len(self.vlpfc.items)

    def get_free_capacity(self) -> int:
        """Get free storage capacity."""
        return self.max_capacity - self.total_items

    def get_state(self) -> WMState:
        """Get complete working memory state."""
        dlpfc_state = self.dlpfc.get_state()
        vlpfc_state = self.vlpfc.get_state()
        acc_state = self.acc.get_state()

        total_active = dlpfc_state['items_stored'] + vlpfc_state['items_stored']

        return WMState(
            active_items=total_active,
            total_capacity=self.max_capacity,
            mean_activation=np.mean([
                np.mean([v.activation for v in self.dlpfc.items.values()]) if self.dlpfc.items else 0,
                np.mean([v.activation for v in self.vlpfc.items.values()]) if self.vlpfc.items else 0
            ]),
            interference_level=(dlpfc_state.get('interference', 0) + acc_state['conflict_level']) / 2,
            current_focus=self.current_focus
        )

    def get_system_state(self) -> Dict:
        """Get complete system state for debugging."""
        return {
            "dlpfc": self.dlpfc.get_state(),
            "vlpfc": self.vlpfc.get_state(),
            "acc": self.acc.get_state(),
            "total_items": self.total_items,
            "max_capacity": self.max_capacity,
            "is_attending": self.is_attending,
            "current_focus": self.current_focus,
            "executive_active": self.executive_active,
            "access_history_len": len(self.access_history)
        }

    def reset(self):
        """Reset working memory to empty state."""
        self.dlpfc.items.clear()
        self.dlpfc.item_order.clear()
        self.vlpfc.items.clear()
        self.vlpfc.recency_order.clear()
        self.total_items = 0
        self.is_attending = False
        self.current_focus = None
        self.executive_active = False


def create_working_memory() -> WorkingMemory:
    """Factory function to create working memory system."""
    return WorkingMemory()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Working Memory Module - BRN-006 - Test")
    print("=" * 60)

    # Create WM
    wm = create_working_memory()

    # Test 1: Store items
    print("\n--- Test Storage ---")
    for i in range(4):
        item_id = f"item_{i}"
        content = np.random.randn(128)
        region = WMRegion.DLPFC if i % 2 == 0 else WMRegion.VLPFC
        wm.store(item_id, content, region, priority=0.7)
        print(f"  Stored {item_id} in {region.value}, free capacity: {wm.get_free_capacity()}")

    # Test 2: Retrieve
    print("\n--- Test Retrieval ---")
    retrieved = wm.retrieve("item_0", WMRegion.DLPFC)
    print(f"  Retrieved item_0: {retrieved.shape if retrieved is not None else None}")

    # Test 3: Attention focus
    print("\n--- Test Attention ---")
    wm.focus_attention("item_1")
    print(f"  Focus on item_1, is_attending: {wm.is_attending}")
    wm.release_attention()
    print(f"  Released attention, is_attending: {wm.is_attending}")

    # Test 4: Manipulation
    print("\n--- Test Manipulation ---")
    result = wm.manipulate_items('combine', ['item_0', 'item_1'])
    print(f"  Combined items: {result.shape if result is not None else None}")

    result = wm.manipulate_items('compare', ['item_0', 'item_2'])
    print(f"  Compared items: {result.shape if result is not None else None}")

    # Test 5: Recognition (VLPFC)
    print("\n--- Test Recognition ---")
    probe = np.random.randn(96)
    match = wm.recognize(probe)
    print(f"  Probe recognition: {match}")

    # Store exact item for matching test
    exact_content = np.ones(96) * 0.5
    wm.store("exact_template", exact_content, WMRegion.VLPFC, priority=0.9)

    # Create probe very similar to template
    similar_probe = np.ones(96) * 0.52
    match = wm.recognize(similar_probe)
    print(f"  Similar probe: {match}")

    # Test 6: Conflict monitoring
    print("\n--- Test Conflict Monitoring ---")
    response1 = np.random.randn(128)
    response2 = np.random.randn(128)
    conflict = wm.monitor_conflict(response1, response2)
    print(f"  Conflict level: {conflict:.3f}")

    # Test 7: Error detection
    print("\n--- Test Error Detection ---")
    expected = np.random.randn(64)
    actual = expected + np.random.randn(64) * 0.1
    error = wm.detect_error(expected, actual)
    print(f"  Error magnitude: {error:.3f}")

    # Test 8: Decay
    print("\n--- Test Decay ---")
    wm.decay_all()
    state = wm.get_state()
    print(f"  Items after decay: {state.active_items}")

    # Test 9: System state
    print("\n--- Test System State ---")
    full_state = wm.get_system_state()
    print(f"  DLPFC items: {full_state['dlpfc']['items_stored']}")
    print(f"  VLPFC items: {full_state['vlpfc']['items_stored']}")
    print(f"  ACC confidence: {full_state['acc']['confidence']:.3f}")
    print(f"  Executive active: {full_state['executive_active']}")

    print("\n" + "=" * 60)
    print("✅ Working Memory Module test completed - BRN-006")
    print("=" * 60)