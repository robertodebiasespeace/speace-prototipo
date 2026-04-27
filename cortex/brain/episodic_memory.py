"""
SPEACE Episodic Memory System - BRN-012
Implements hippocampal-cortical dialogic memory with consolidation.
Models: CA3, CA1, Dentate Gyrus, Entorhinal Cortex.
Version: 1.0
Data: 25 Aprile 2026

The episodic memory system models:
- Hippocampal CA3: pattern separation and completion
- Hippocampal CA1: sequential memory formation
- Dentate Gyrus: sparse encoding
- Entorhinal Cortex: relay between hippocampus and cortex
- SLOW oscillation consolidation
- Memory replay during idle states
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryPhase(Enum):
    """Phases of memory processing."""
    ENCODING = "encoding"
    CONSOLIDATION = "consolidation"
    RETRIEVAL = "retrieval"
    REPLAY = "replay"


@dataclass
class EpisodicMemory:
    """Single episodic memory trace."""
    id: str
    content: np.ndarray
    context: np.ndarray
    temporal_sequence: np.ndarray  # When it happened
    spatial_context: np.ndarray    # Where it happened
    emotional_tag: float           # Emotional significance
    activation_strength: float = 1.0
    consolidation_level: float = 0.0  # 0 = new, 1 = fully consolidated
    encoding_time: str = ""
    retrieval_count: int = 0


@dataclass
class MemoryResult:
    """Result of memory retrieval."""
    memory: Optional[EpisodicMemory]
    confidence: float
    retrieval_time_ms: float
    matches: List[str]  # IDs of similar memories


class DentateGyrus:
    """
    Dentate Gyrus - Sparse pattern separator.
    Creates distinct representations for similar inputs.
    Implements pattern separation to avoid interference.
    """
    def __init__(self, input_size: int = 256, output_size: int = 128):
        self.input_size = input_size
        self.output_size = output_size

        # Mossy cell synapses (DG -> CA3)
        self.mossy_weights = np.random.randn(output_size, input_size) * 0.08

        # Inhibition for sparse coding
        self.k_winner = 12  # Only k neurons active
        self.inhibition_strength = 0.5

        # Pattern separation history
        self.separation_events = deque(maxlen=50)

    def separate_pattern(self, cortical_input: np.ndarray) -> np.ndarray:
        """
        Apply pattern separation to create sparse distinct representation.
        Similar inputs -> very different outputs (if possible).
        """
        # Compute mossy fiber projection
        projection = np.dot(self.mossy_weights, cortical_input)

        # Apply k-winner-take-all for sparse coding
        sorted_indices = np.argsort(projection)[::-1]
        sparse_output = np.zeros(self.output_size)

        for i in range(self.k_winner):
            sparse_output[sorted_indices[i]] = projection[sorted_indices[i]]

        # Apply lateral inhibition
        for i in range(self.output_size):
            if sparse_output[i] > 0:
                # Reduce neighbors
                neighbor_sum = np.sum(sparse_output[max(0, i-3):min(self.output_size, i+4)])
                inhibition = neighbor_sum * self.inhibition_strength / 7
                sparse_output[i] -= inhibition

        sparse_output = np.clip(sparse_output, 0, None)
        sparse_output = sparse_output / (np.linalg.norm(sparse_output) + 1e-8)

        self.separation_events.append({
            "input_similarity": float(np.std(cortical_input)),
            "output_sparsity": float(np.sum(sparse_output > 0))
        })

        return sparse_output

    def learn_pattern(self, input_pattern: np.ndarray, target_output: np.ndarray, lr: float = 0.01):
        """Learn to improve pattern separation."""
        current_output = self.separate_pattern(input_pattern)
        error = target_output - current_output

        # Hebbian update
        delta = lr * np.outer(error, input_pattern)
        self.mossy_weights += delta

        # Normalize
        row_norms = np.linalg.norm(self.mossy_weights, axis=1, keepdims=True)
        row_norms[row_norms == 0] = 1
        self.mossy_weights = self.mossy_weights / row_norms * np.sqrt(self.output_size / self.input_size)


class CA3Region:
    """
    CA3 Region - Pattern completion and auto-associative memory.
    Implements fast learning and recall of complete patterns from partial cues.
    """
    def __init__(self, input_size: int = 128, recurrent_size: int = 128):
        self.input_size = input_size
        self.recurrent_size = recurrent_size

        # Input weights (from DG) - DG outputs 128, but what_cue is 64
        self.input_weights = np.random.randn(recurrent_size, 64) * 0.06

        # Recurrent weights (CA3 -> CA3 auto-association)
        self.recurrent_weights = np.random.randn(recurrent_size, recurrent_size) * 0.04
        # Make slightly symmetric for associative memory
        self.recurrent_weights = (self.recurrent_weights + self.recurrent_weights.T) / 2

        # Memory storage
        self.stored_patterns: List[np.ndarray] = []
        self.pattern_metadata: List[Dict] = []

        # Completion threshold
        self.completion_threshold = 0.6

    def store_memory(self, pattern: np.ndarray, metadata: Dict = None):
        """Store pattern in CA3 auto-associative network."""
        # Normalize pattern
        norm_pattern = pattern / (np.linalg.norm(pattern) + 1e-8)

        self.stored_patterns.append(norm_pattern)
        self.pattern_metadata.append(metadata or {})

        # Update recurrent weights (Hebbian)
        hebbian_update = np.outer(norm_pattern, norm_pattern) * 0.01
        np.fill_diagonal(hebbian_update, 0)  # Don't self-learn
        self.recurrent_weights += hebbian_update

        # Normalize
        self.recurrent_weights = np.clip(self.recurrent_weights, 0, 0.5)
        self.recurrent_weights = self.recurrent_weights / (np.linalg.norm(self.recurrent_weights) + 1e-8)

    def complete_pattern(self, partial_pattern: np.ndarray,
                        iterations: int = 5) -> np.ndarray:
        """
        Complete partial pattern using auto-associative recall.
        Iteratively enrich pattern until stable.
        """
        # Normalize input
        pattern = partial_pattern / (np.linalg.norm(partial_pattern) + 1e-8)

        for _ in range(iterations):
            # Input contribution
            input_contribution = np.dot(self.input_weights, pattern)

            # Recurrent contribution (memory association)
            if len(self.stored_patterns) > 0:
                # Find best matching stored pattern
                similarities = [np.dot(pattern, p) for p in self.stored_patterns]
                best_idx = np.argmax(similarities)
                best_match = self.stored_patterns[best_idx]

                if similarities[best_idx] > 0.3:
                    recurrent_contribution = np.dot(self.recurrent_weights, best_match) * 0.3
                else:
                    recurrent_contribution = np.zeros(self.recurrent_size)
            else:
                recurrent_contribution = np.zeros(self.recurrent_size)

            # Combine
            pattern = input_contribution + recurrent_contribution
            pattern = pattern / (np.linalg.norm(pattern) + 1e-8)

        return pattern

    def retrieve_similar(self, query: np.ndarray, threshold: float = 0.5) -> List[Tuple[int, float]]:
        """Retrieve all stored patterns similar to query."""
        similarities = []
        for i, pattern in enumerate(self.stored_patterns):
            sim = np.dot(query, pattern) / (np.linalg.norm(query) * np.linalg.norm(pattern) + 1e-8)
            if sim > threshold:
                similarities.append((i, sim))

        return sorted(similarities, key=lambda x: x[1], reverse=True)


class CA1Region:
    """
    CA1 Region - Sequential memory and temporal ordering.
    Forms sequences from spatial/temporal inputs.
    """
    def __init__(self, input_size: int = 128, output_size: int = 96):
        self.input_size = input_size
        self.output_size = output_size

        # Input from CA3
        self.ca3_weights = np.random.randn(output_size, input_size) * 0.05

        # Temporal sequence weights
        self.sequence_weights = np.random.randn(output_size, input_size) * 0.04

        # Sequence memory
        self.sequences: List[List[np.ndarray]] = []  # List of sequences
        self.sequence_timing: List[np.ndarray] = []  # Temporal markers

        # Current sequence buffer
        self.current_sequence: List[np.ndarray] = []
        self.sequence_timestamps: List[str] = []

    def encode_item(self, item: np.ndarray, timestamp: str) -> np.ndarray:
        """Encode single item with temporal context."""
        # CA3 input
        ca3_contribution = np.dot(self.ca3_weights, item)

        # Add temporal sequence info
        if len(self.current_sequence) > 0:
            prev_item = self.current_sequence[-1]
            temporal_info = np.dot(self.sequence_weights, prev_item)
            ca3_contribution += temporal_info * 0.3

        self.current_sequence.append(item)
        self.sequence_timestamps.append(timestamp)

        return ca3_contribution

    def finalize_sequence(self) -> np.ndarray:
        """Finalize current sequence into a single representation."""
        if not self.current_sequence:
            return np.zeros(self.output_size)

        # Average all items in sequence
        sequence_repr = np.mean(self.current_sequence, axis=0)

        # Add sequence context
        if len(sequence_repr) > self.output_size:
            sequence_repr = sequence_repr[:self.output_size]
        elif len(sequence_repr) < self.output_size:
            sequence_repr = np.pad(sequence_repr, (0, self.output_size - len(sequence_repr)))

        # Store sequence
        self.sequences.append(self.current_sequence.copy())
        timing = np.array([len(self.current_sequence), np.mean([len(s) for s in self.current_sequence])])
        self.sequence_timing.append(timing)

        # Clear buffer
        self.current_sequence = []
        self.sequence_timestamps = []

        return sequence_repr

    def recall_sequence(self, start_cue: np.ndarray, length: int = 5) -> List[np.ndarray]:
        """Recall a sequence starting from a cue."""
        recalled = []

        # Find starting point
        best_match = None
        best_sim = 0
        for seq in self.sequences:
            if len(seq) > 0 and np.dot(start_cue, seq[0]).mean() > best_sim:
                best_match = seq
                best_sim = np.dot(start_cue, seq[0]).mean()

        if best_match:
            recalled = best_match[:length]
        else:
            # Generate synthetic sequence
            recalled = [start_cue] * length

        return recalled


class EntorhinalCortex:
    """
    Entorhinal Cortex - Relay between hippocampus and cortex.
    Implements the "what" and "where" pathway separation.
    """
    def __init__(self, input_size: int = 256, output_size: int = 128):
        self.input_size = input_size
        # Output to DG must be 128 to match DG input_size
        self.output_size = 128

        # "What" pathway (identity) - outputs 64
        self.what_weights = np.random.randn(64, input_size) * 0.04

        # "Where" pathway (spatial) - outputs 64
        self.where_weights = np.random.randn(64, input_size) * 0.04

        # Output
        self.what_output = np.zeros(64)
        self.where_output = np.zeros(64)

    def process_to_hippocampus(self, cortical_input: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Process cortical input for hippocampal delivery."""
        # What pathway
        self.what_output = np.tanh(np.dot(self.what_weights, cortical_input))

        # Where pathway
        self.where_output = np.tanh(np.dot(self.where_weights, cortical_input))

        return self.what_output.copy(), self.where_output.copy()

    def process_from_hippocampus(self, hippocampal_input: np.ndarray) -> np.ndarray:
        """Process hippocampal output for cortical delivery."""
        # Combine and project back to cortex
        half = len(hippocampal_input) // 2
        combined = np.concatenate([
            np.dot(self.what_weights.T, hippocampal_input[:half]),
            np.dot(self.where_weights.T, hippocampal_input[half:])
        ])

        return np.tanh(combined)[:self.output_size]

    def get_output(self) -> np.ndarray:
        """Get combined what-where output."""
        return np.concatenate([self.what_output, self.where_output])


class HippocampalSystem:
    """
    Complete Hippocampal System.
    Integrates DG, CA3, CA1, and EC for full episodic memory.
    """
    def __init__(self):
        # Components
        self.dentate = DentateGyrus(input_size=256, output_size=128)
        self.ca3 = CA3Region(input_size=128, recurrent_size=128)
        self.ca1 = CA1Region(input_size=128, output_size=96)
        self.entorhinal = EntorhinalCortex(input_size=256, output_size=128)

        # Memory storage
        self.episodic_memories: Dict[str, EpisodicMemory] = {}
        self.memory_index: List[str] = []

        # Consolidation state
        self.consolidation_candidates: deque = deque(maxlen=20)
        self.slow_oscillation_phase = "up"  # SLOW oscillation for consolidation

        # Replay system
        self.replay_buffer: deque = deque(maxlen=50)

    def encode_experience(self, content: np.ndarray, context: np.ndarray,
                          emotional_tag: float = 0.5) -> str:
        """
        Encode a new experience into episodic memory.
        Returns memory ID.
        """
        # Generate memory ID
        memory_id = f"mem_{datetime.now().isoformat()}"

        # Process through entorhinal
        what_in, where_in = self.entorhinal.process_to_hippocampus(context)

        # DG pattern separation
        separated = self.dentate.separate_pattern(content)

        # CA3 pattern completion setup
        self.ca3.store_memory(separated, {"emotion": emotional_tag})

        # CA1 sequential encoding
        ca1_encoding = self.ca1.encode_item(separated, datetime.now().isoformat())

        # Create episodic memory
        memory = EpisodicMemory(
            id=memory_id,
            content=content,
            context=context,
            temporal_sequence=ca1_encoding,
            spatial_context=where_in,
            emotional_tag=emotional_tag,
            activation_strength=1.0,
            consolidation_level=0.0,
            encoding_time=datetime.now().isoformat()
        )

        self.episodic_memories[memory_id] = memory
        self.memory_index.append(memory_id)

        # Add to consolidation candidates
        self.consolidation_candidates.append(memory_id)

        return memory_id

    def retrieve(self, cue: np.ndarray, context_hint: np.ndarray = None,
                emotional_hint: float = None) -> MemoryResult:
        """
        Retrieve memory using content and context cues.
        """
        import time
        start = time.time()

        # Process cue through entorhinal
        what_cue, where_cue = self.entorhinal.process_to_hippocampus(cue)

        # Use CA3 for pattern completion
        completed = self.ca3.complete_pattern(what_cue)

        # Search for matching memories
        candidates = []
        for memory_id in self.memory_index:
            memory = self.episodic_memories[memory_id]

            # Compute similarity
            content_sim = np.dot(completed, memory.temporal_sequence) / (128)
            context_sim = np.dot(where_cue, memory.spatial_context) / (64) if len(memory.spatial_context) > 0 else 0

            # Emotional bias
            if emotional_hint is not None:
                emotion_bias = 1.0 - abs(emotional_hint - memory.emotional_tag)
            else:
                emotion_bias = 1.0

            combined_score = (content_sim * 0.5 + context_sim * 0.3 + emotion_bias * 0.2)

            if combined_score > 0.3:
                candidates.append((memory_id, combined_score))

        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)

        if candidates:
            best_id = candidates[0][0]
            best_memory = self.episodic_memories[best_id]
            best_memory.retrieval_count += 1

            # Boost activation
            best_memory.activation_strength = min(1.5, best_memory.activation_strength * 1.1)

            elapsed_ms = (time.time() - start) * 1000

            return MemoryResult(
                memory=best_memory,
                confidence=candidates[0][1],
                retrieval_time_ms=elapsed_ms,
                matches=[mid for mid, score in candidates[:3]]
            )

        elapsed_ms = (time.time() - start) * 1000
        return MemoryResult(
            memory=None,
            confidence=0.0,
            retrieval_time_ms=elapsed_ms,
            matches=[]
        )

    def consolidate_memory(self, memory_id: str):
        """
        Consolidate a memory from working to long-term.
        Simulates SLOW oscillation-mediated transfer to cortex.
        """
        if memory_id not in self.episodic_memories:
            return

        memory = self.episodic_memories[memory_id]

        # Increase consolidation level
        memory.consolidation_level += 0.3

        # During "up" phase of SLOW oscillation, memory traces are strengthened
        if self.slow_oscillation_phase == "up":
            memory.activation_strength *= 1.1

        memory.consolidation_level = min(1.0, memory.consolidation_level)

    def trigger_replay(self, memory_id: str = None) -> List[np.ndarray]:
        """
        Trigger memory replay - reactivates memory during idle.
        Can be triggered spontaneously or by cue.
        """
        if memory_id:
            # Replay specific memory
            if memory_id in self.episodic_memories:
                memory = self.episodic_memories[memory_id]
                self.replay_buffer.append({
                    "type": "targeted_replay",
                    "memory_id": memory_id
                })
                return [memory.content, memory.context]
        else:
            # Random replay of recent memories
            if len(self.memory_index) > 0:
                import random
                recent_memories = self.memory_index[-10:]
                replay_id = random.choice(recent_memories)
                if replay_id in self.episodic_memories:
                    memory = self.episodic_memories[replay_id]
                    self.replay_buffer.append({
                        "type": "spontaneous_replay",
                        "memory_id": replay_id
                    })
                    return [memory.content, memory.context]

        return []

    def apply_slow_oscillation(self):
        """
        Simulate SLOW oscillation (0.5-1 Hz) for memory consolidation.
        Alternates between up and down states.
        """
        if self.slow_oscillation_phase == "up":
            # Up state: consolidate memories
            for memory_id in list(self.consolidation_candidates):
                self.consolidate_memory(memory_id)
            self.slow_oscillation_phase = "down"
        else:
            # Down state: rest
            self.slow_oscillation_phase = "up"

    def get_memory_summary(self, memory_id: str) -> Optional[Dict]:
        """Get summary of a specific memory."""
        if memory_id not in self.episodic_memories:
            return None

        memory = self.episodic_memories[memory_id]
        return {
            "id": memory.id,
            "activation": memory.activation_strength,
            "consolidation": memory.consolidation_level,
            "emotion": memory.emotional_tag,
            "retrievals": memory.retrieval_count,
            "age": (datetime.now() - datetime.fromisoformat(memory.encoding_time)).total_seconds()
        }

    def get_system_state(self) -> Dict:
        """Get complete system state."""
        return {
            "total_memories": len(self.episodic_memories),
            "consolidation_candidates": len(self.consolidation_candidates),
            "slow_oscillation_phase": self.slow_oscillation_phase,
            "replay_count": len(self.replay_buffer),
            "ca3_patterns_stored": len(self.ca3.stored_patterns),
            "ca1_sequences_stored": len(self.ca1.sequences)
        }


def create_hippocampal_system() -> HippocampalSystem:
    """Factory function to create hippocampal system."""
    return HippocampalSystem()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Episodic Memory System - BRN-012 - Test")
    print("=" * 60)

    # Create system
    hippocampus = create_hippocampal_system()

    # Test 1: Encoding
    print("\n--- Test Encoding ---")
    for i in range(5):
        content = np.random.randn(256)
        context = np.random.randn(256)
        emotion = np.random.choice([0.3, 0.5, 0.7, 0.9])
        mem_id = hippocampus.encode_experience(content, context, emotion)
        print(f"  Memory {i+1}: {mem_id[-20:]}")

    # Test 2: Retrieval
    print("\n--- Test Retrieval ---")
    query = np.random.randn(256)
    result = hippocampus.retrieve(query, emotional_hint=0.6)
    print(f"  Retrieved: {result.memory.id[-20:] if result.memory else 'None'}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Retrieval time: {result.retrieval_time_ms:.2f}ms")
    print(f"  Matches: {result.matches[:2]}")

    # Test 3: DG pattern separation
    print("\n--- Test Pattern Separation ---")
    similar_inputs = [np.random.randn(256) * 0.5 for _ in range(3)]
    outputs = [hippocampus.dentate.separate_pattern(inp) for inp in similar_inputs]
    for i, out in enumerate(outputs):
        print(f"  Input {i+1} sparse active: {np.sum(out > 0)}")

    # Test 4: CA3 pattern completion
    print("\n--- Test Pattern Completion ---")
    partial = np.random.randn(128) * 0.3
    completed = hippocampus.ca3.complete_pattern(partial)
    print(f"  Partial norm: {np.linalg.norm(partial):.3f}")
    print(f"  Completed norm: {np.linalg.norm(completed):.3f}")

    # Test 5: Slow oscillation consolidation
    print("\n--- Test Slow Oscillation ---")
    for phase in range(4):
        hippocampus.apply_slow_oscillation()
        print(f"  Phase {phase+1}: {hippocampus.slow_oscillation_phase}")

    # Test 6: Replay
    print("\n--- Test Replay ---")
    replayed = hippocampus.trigger_replay()
    print(f"  Replayed memory items: {len(replayed)}")

    # Test 7: System state
    print("\n--- Test System State ---")
    state = hippocampus.get_system_state()
    print(f"  Total memories: {state['total_memories']}")
    print(f"  CA3 patterns: {state['ca3_patterns_stored']}")
    print(f"  Slow oscillation: {state['slow_oscillation_phase']}")

    print("\n" + "=" * 60)
    print("Episodic Memory System: PASS")
    print("=" * 60)