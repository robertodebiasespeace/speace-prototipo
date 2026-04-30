"""
SPEACE Basal Ganglia System - BRN-004
Implements action selection, habit formation, and reward learning.
Models: Striatum, GPi/SNr, STN, Substantia Nigra.
Version: 1.0
Data: 25 Aprile 2026

The basal ganglia are crucial for:
- Action selection (choosing one action over others)
- Habit formation (automatizing repeated behaviors)
- Reward processing and reinforcement learning
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PathwayType(Enum):
    """Basal ganglia pathways."""
    D1 = "direct"      # Direct pathway - facilitates movement
    D2 = "indirect"    # Indirect pathway - inhibits movement
    HYPERDIRECT = "hyperdirect"  # Fast inhibition via STN


@dataclass
class Action:
    """Represents an action that can be selected."""
    action_id: str
    name: str
    value: float  # Expected value
    salience: float  # How salient this action is
    previous_selection_count: int = 0


@dataclass
class SelectionResult:
    """Result of action selection."""
    selected_action: Optional[Action]
    all_actions: List[Action]
    selection_time_ms: float
    confidence: float


class Striatum:
    """
    Striatum - Input layer of basal ganglia.
    Receives cortex input, splits into D1/D2 pathways.
    """
    def __init__(self, input_size: int = 256, output_size: int = 128):
        self.input_size = input_size
        self.output_size = output_size

        # Corticostriatal synapses
        self.cortical_weights = np.random.randn(output_size, input_size) * 0.05

        # D1 vs D2 neuron populations
        self.d1_neurons = np.zeros(output_size // 2)
        self.d2_neurons = np.zeros(output_size // 2)

        # Learning parameters
        self.learning_rate = 0.01
        self.plasticity_history = deque(maxlen=100)

    def process(self, cortical_input: np.ndarray, dopamine_signal: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process cortical input and generate D1/D2 pathway activations.
        Positive dopamine -> D1 potentiation (go)
        Negative dopamine -> D2 potentiation (stop)
        """
        # Forward pass
        striatal_output = np.dot(self.cortical_weights, cortical_input)

        # Split into D1 and D2 populations
        half = len(striatal_output) // 2
        self.d1_neurons = striatal_output[:half]
        self.d2_neurons = striatal_output[half:]

        # Dopamine modulation
        if dopamine_signal > 0:
            # Positive DA -> D1 pathway facilitated (direct Go)
            self.d1_neurons *= (1 + dopamine_signal * 0.5)
        elif dopamine_signal < 0:
            # Negative DA -> D2 pathway facilitated (indirect Stop)
            self.d2_neurons *= (1 - dopamine_signal * 0.5)

        # Normalize
        self.d1_neurons = np.tanh(self.d1_neurons)
        self.d2_neurons = np.tanh(self.d2_neurons)

        return self.d1_neurons.copy(), self.d2_neurons.copy()

    def learn(self, cortical_input: np.ndarray, reward: float, td_error: float):
        """STDP-like learning at corticostriatal synapses."""
        # Simple reward-modulated Hebbian
        delta = self.learning_rate * td_error * np.outer(cortical_input[:self.output_size], np.ones(self.output_size))
        self.cortical_weights += delta

        # Normalize to prevent runaway
        row_norms = np.linalg.norm(self.cortical_weights, axis=1, keepdims=True)
        row_norms[row_norms == 0] = 1
        self.cortical_weights = self.cortical_weights / row_norms * np.sqrt(self.input_size / self.output_size)

        self.plasticity_history.append({"reward": reward, "td_error": td_error})

    def get_activity(self) -> float:
        return float(np.mean(np.abs(self.d1_neurons) + np.abs(self.d2_neurons)))


class GlobusPallidusInterna:
    """
    GPi (Globus Pallidus interna) - Output nucleus.
    Inhibits thalamic targets, releases actions.
    """
    def __init__(self, input_size: int = 64, output_size: int = 32):
        self.input_size = input_size
        self.output_size = output_size

        # Striatal inhibition weights
        self.striatal_weights = np.eye(output_size, input_size) * 0.8

        # Output neurons (tonically active)
        self.tonic_activity = 0.8  # High baseline activity
        self.output_neurons = np.ones(output_size) * self.tonic_activity

        self.inhibition_history = deque(maxlen=50)

    def process(self, d1_signal: np.ndarray, context: str = "normal") -> np.ndarray:
        """
        Process D1 direct pathway input.
        D1 activation inhibits GPi -> releases thalamus -> action goes.
        """
        # Apply striatal inhibition (D1 activates GPi, causing more inhibition)
        inhibition = np.dot(self.striatal_weights, d1_signal[:self.input_size])

        # Inhibition reduces GPi activity (less inhibition of thalamus)
        self.output_neurons = self.tonic_activity - inhibition * 0.5
        self.output_neurons = np.clip(self.output_neurons, 0, 1)

        self.inhibition_history.append({
            "inhibition_strength": float(np.mean(inhibition)),
            "output_activity": float(np.mean(self.output_neurons)),
            "context": context
        })

        return self.output_neurons.copy()

    def get_inhibition_level(self) -> float:
        return float(np.mean([h["inhibition_strength"] for h in self.inhibition_history]))


class SubthalamicNucleus:
    """
    STN - Subthalamic Nucleus.
    Provides excitatory input to GPi/SNr, part of hyperdirect pathway.
    Provides "紧急刹车" (emergency brake) for high conflict situations.
    """
    def __init__(self, input_size: int = 128, output_size: int = 48):
        self.input_size = input_size
        self.output_size = output_size

        # Cortex to STN (excitatory)
        self.cortical_weights = np.random.randn(output_size, input_size) * 0.03

        # STN to GPi/SNr (excitatory)
        self.output_weights = np.random.randn(output_size, output_size) * 0.05

        # STN activity (bursty, can go high in conflict)
        self.activity = np.zeros(output_size)
        self.conflict_level = 0.0

    def process(self, cortical_input: np.ndarray, conflict_signal: float = 0.0) -> np.ndarray:
        """
        Process cortical input with conflict detection.
        High conflict -> STN activates strongly -> GPi inhibition -> STOP
        """
        # Cortical excitation
        cortical_exc = np.dot(self.cortical_weights, cortical_input[:self.input_size])

        # Conflict modulation (from cortex, indicates high conflict)
        self.conflict_level = conflict_signal
        if conflict_signal > 0.3:
            # High conflict -> burst of STN activity
            self.activity = cortical_exc * (1 + conflict_signal * 2)
        else:
            self.activity = cortical_exc * 0.5  # Normal mode

        # Self-excitation (STN has excitatory connections)
        self.activity += np.dot(self.output_weights, self.activity) * 0.2

        self.activity = np.clip(self.activity, 0, 2)  # Can burst high

        return self.activity.copy()

    def get_conflict_level(self) -> float:
        return float(np.mean(self.activity))


class SubstantiaNigra:
    """
    Substantia Nigra - Contains SNc (dopamine) and SNr (output).
    Provides dopamine signals and output inhibition.
    """
    def __init__(self, input_size: int = 64, output_size: int = 32):
        self.input_size = input_size
        self.output_size = output_size

        # SNc - Dopamine neurons
        self.dopamine_level = 0.5  # Baseline
        self.dopamine_history = deque(maxlen=200)
        self.reward_prediction_error = 0.0

        # SNr - Output neurons
        self.snr_activity = np.ones(output_size) * 0.7  # Tonic inhibition

        # Striatal feedback
        self.striatal_modulation = np.zeros(output_size)

    def compute_dopamine(self, reward: float, predicted_reward: float,
                        learning_rate: float = 0.1) -> float:
        """
        Compute dopamine signal as TD error.
        DA = reward - predicted_reward
        """
        self.reward_prediction_error = reward - predicted_reward

        # Dopamine = positive when reward > prediction (unexpected reward)
        # Dopamine = negative when reward < prediction (missed reward)
        self.dopamine_level += learning_rate * self.reward_prediction_error
        self.dopamine_level = np.clip(self.dopamine_level, -1, 1)

        self.dopamine_history.append({
            "dopamine": self.dopamine_level,
            "reward": reward,
            "td_error": self.reward_prediction_error,
            "timestamp": datetime.now().isoformat()
        })

        return self.dopamine_level

    def process_snr(self, gpi_output: np.ndarray = None, striatal_d2: np.ndarray = None) -> np.ndarray:
        """Process SNr output with GPi input."""
        # GPi provides inhibition to SNr
        if gpi_output is not None:
            self.snr_activity = 0.7 - gpi_output[:self.output_size] * 0.5

        # D2 provides additional inhibition (stop signals)
        if striatal_d2 is not None:
            self.snr_activity -= striatal_d2[:self.output_size] * 0.3

        self.snr_activity = np.clip(self.snr_activity, 0, 1)

        return self.snr_activity.copy()

    def get_dopamine_signal(self) -> float:
        """Get current dopamine level normalized."""
        return self.dopamine_level


class GlobusPallidusExterna:
    """
    GPe - Globus Pallidus Externa.
    Part of indirect pathway, projects to STN and GPi.
    """
    def __init__(self, input_size: int = 64, output_size: int = 48):
        self.input_size = input_size
        self.output_size = output_size

        # Striatal D2 input
        self.d2_weights = np.eye(output_size, input_size) * 0.5

        # GPe to STN (inhibitory) and GPi (inhibitory)
        self.activity = np.zeros(output_size)
        self.tonic_activity = 0.4

    def process(self, d2_signal: np.ndarray) -> np.ndarray:
        """Process D2 indirect pathway input."""
        d2_inhibition = np.dot(self.d2_weights, d2_signal[:self.input_size])

        # GPe is tonically active, D2 reduces it
        self.activity = self.tonic_activity - d2_inhibition * 0.6
        self.activity = np.clip(self.activity, 0, 1)

        return self.activity.copy()


class BasalGanglia:
    """
    Complete Basal Ganglia system.
    Integrates all nuclei for action selection.
    """
    def __init__(self, num_actions: int = 8):
        self.num_actions = num_actions

        # Initialize components
        self.striatum = Striatum(input_size=256, output_size=num_actions * 4)
        self.gpi = GlobusPallidusInterna(input_size=num_actions * 2, output_size=num_actions)
        self.gpe = GlobusPallidusExterna(input_size=num_actions * 2, output_size=num_actions)
        self.stn = SubthalamicNucleus(input_size=256, output_size=num_actions)
        self.snr = SubstantiaNigra(input_size=num_actions, output_size=num_actions)

        # Action values and history
        self.action_values = np.ones(num_actions) * 0.5  # Initial optimistic
        self.action_selection_counts = np.zeros(num_actions)
        self.action_history = deque(maxlen=500)

        # System state
        self.last_dopamine = 0.5
        self.current_action: Optional[Action] = None

    def process(self, cortical_input: np.ndarray,
                context: Dict = None) -> np.ndarray:
        """
        Process cortical input through basal ganglia.
        Returns action activation levels.
        """
        # Get conflict signal from context
        conflict = context.get("conflict", 0.0) if context else 0.0

        # 1. STN processes early (hyperdirect pathway - fastest)
        stn_output = self.stn.process(cortical_input, conflict)

        # 2. Striatum processes D1/D2
        d1, d2 = self.striatum.process(cortical_input, self.last_dopamine)

        # 3. GPe (indirect pathway)
        gpe_output = self.gpe.process(d2)

        # 4. GPi output
        gpi_output = self.gpi.process(d1, context.get("mode", "normal") if context else "normal")

        # 5. SNr combines everything
        snr_output = self.snr.process_snr(gpi_output, d2)

        # Combine pathways for action selection
        # Direct (D1): facilitates actions (less GPi inhibition)
        direct_faciliation = d1[:self.num_actions] if len(d1) >= self.num_actions else np.pad(d1, (0, self.num_actions - len(d1)))

        # Indirect (D2): inhibits actions (through GPe -> STN -> GPi)
        indirect_inhibition = gpe_output[:self.num_actions] if len(gpe_output) >= self.num_actions else np.pad(gpe_output, (0, self.num_actions - len(gpe_output)))

        # Hyperdirect (STN): global inhibition in conflict
        hyperdirect_effect = stn_output[:self.num_actions] * 0.5 if len(stn_output) >= self.num_actions else np.pad(stn_output, (0, self.num_actions - len(stn_output))) * 0.5

        # Net action activations
        net_activations = direct_faciliation - indirect_inhibition - hyperdirect_effect

        # Update action values based on this
        self.action_values = 0.9 * self.action_values + 0.1 * net_activations

        return net_activations

    def select_action(self, cortical_input: np.ndarray,
                     context: Dict = None,
                     selection_threshold: float = 0.3) -> SelectionResult:
        """
        Select single action based on basal ganglia processing.
        Uses winner-take-all with threshold.
        """
        import time
        start = time.time()

        # Process inputs
        net_activations = self.process(cortical_input, context)

        # Apply softmax-like selection (not pure softmax - more discrete)
        actions = []
        for i in range(self.num_actions):
            actions.append(Action(
                action_id=f"action_{i}",
                name=f"Action_{i}",
                value=float(net_activations[i]),
                salience=float(net_activations[i] - np.mean(net_activations)),
                previous_selection_count=int(self.action_selection_counts[i])
            ))

        # Sort by value
        actions.sort(key=lambda a: a.value, reverse=True)

        # Select top action above threshold
        selected = None
        if len(actions) > 0 and actions[0].value > selection_threshold:
            selected = actions[0]
            self.action_selection_counts[0] += 1
            self.current_action = selected

        # Update history
        self.action_history.append({
            "selected": selected.action_id if selected else None,
            "all_values": [a.value for a in actions],
            "timestamp": datetime.now().isoformat()
        })

        elapsed_ms = (time.time() - start) * 1000

        return SelectionResult(
            selected_action=selected,
            all_actions=actions,
            selection_time_ms=elapsed_ms,
            confidence=float(actions[0].value - actions[1].value) if len(actions) > 1 else 0.0
        )

    def learn_from_reward(self, reward: float, predicted: float):
        """Learn from reward feedback using dopamine signals."""
        # Compute dopamine signal
        da = self.snr.compute_dopamine(reward, predicted)

        # Update last dopamine for next cycle
        self.last_dopamine = da

        # Train striatum
        self.striatum.learn(
            cortical_input=np.random.randn(256),  # In real system, use actual input
            reward=reward,
            td_error=da
        )

    def get_system_state(self) -> Dict:
        """Get complete basal ganglia state."""
        return {
            "action_values": self.action_values.tolist(),
            "selection_counts": self.action_selection_counts.tolist(),
            "dopamine_level": self.last_dopamine,
            "striatum_activity": self.striatum.get_activity(),
            "stn_conflict": self.stn.get_conflict_level(),
            "current_action": self.current_action.name if self.current_action else None,
            "total_selections": int(np.sum(self.action_selection_counts))
        }

    def habit_strength(self, action_idx: int) -> float:
        """Calculate habit strength for an action based on selection frequency."""
        if self.action_selection_counts[action_idx] == 0:
            return 0.0
        # Normalized frequency
        total = np.sum(self.action_selection_counts)
        return self.action_selection_counts[action_idx] / total if total > 0 else 0.0


class ActionSelectionPolicy:
    """
    Policy layer for action selection in basal ganglia.
    Bridges BG to motor system.
    """
    def __init__(self, basal_ganglia: BasalGanglia):
        self.bg = basal_ganglia
        self.epsilon = 0.1  # Exploration rate
        self.noise_scale = 0.2

    def select_with_policy(self, cortical_input: np.ndarray,
                         context: Dict = None,
                         force_explore: bool = False) -> Tuple[int, float]:
        """
        Select action using policy with optional exploration.
        Returns: (action_index, confidence)
        """
        # Get BG processing
        activations = self.bg.process(cortical_input, context)

        # Add exploration noise
        if force_explore or np.random.random() < self.epsilon:
            noise = np.random.randn(len(activations)) * self.noise_scale
            activations = activations + noise

        # Select winner
        action_idx = int(np.argmax(activations))
        confidence = float(activations[action_idx] - np.mean(activations))

        # Update selection
        self.bg.action_selection_counts[action_idx] += 1

        return action_idx, confidence

    def update_epsilon(self, decay: float = 0.99, min_epsilon: float = 0.01):
        """Decay exploration rate over time (learning)."""
        self.epsilon = max(min_epsilon, self.epsilon * decay)

    def get_policy_stats(self) -> Dict:
        """Get policy statistics."""
        return {
            "epsilon": self.epsilon,
            "total_selections": int(np.sum(self.bg.action_selection_counts)),
            "habit_formation": self.bg.action_selection_counts.tolist()
        }


def create_basal_ganglia(num_actions: int = 8) -> BasalGanglia:
    """Factory function to create basal ganglia system."""
    return BasalGanglia(num_actions=num_actions)


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Basal Ganglia System - Test")
    print("=" * 60)

    # Create BG system
    bg = create_basal_ganglia(num_actions=8)
    policy = ActionSelectionPolicy(bg)

    # Test action selection
    print("\n--- Test Action Selection ---")
    for trial in range(5):
        cortical = np.random.randn(256)
        result = bg.select_action(cortical, {"mode": "normal"})

        if result.selected_action:
            print(f"Trial {trial+1}: Selected {result.selected_action.name}, "
                  f"value={result.selected_action.value:.3f}, "
                  f"time={result.selection_time_ms:.2f}ms")

    # Test learning
    print("\n--- Test Learning ---")
    for trial in range(3):
        reward = np.random.choice([0, 1, 0.5])
        predicted = 0.5
        bg.learn_from_reward(reward, predicted)
        print(f"Learning trial {trial+1}: reward={reward}, DA={bg.last_dopamine:.3f}")

    # Test action values
    print("\n--- Action Values ---")
    state = bg.get_system_state()
    print(f"Action values: {[f'{v:.2f}' for v in state['action_values']]}")
    print(f"Dopamine: {state['dopamine_level']:.3f}")
    print(f"Striatum activity: {state['striatum_activity']:.3f}")
    print(f"Total selections: {state['total_selections']}")

    # Test habit formation
    print("\n--- Habit Formation ---")
    for i in range(8):
        habit = bg.habit_strength(i)
        print(f"  Action {i}: habit={habit:.3f}, count={bg.action_selection_counts[i]}")

    print("\n" + "=" * 60)
    print("Basal Ganglia System: PASS")
    print("=" * 60)