"""
SPEACE Dopaminergic System - BRN-005
Implements reward prediction, motivation, and curiosity signals.
Models: VTA (Ventral Tegmental Area), SNc (Substantia Nigra pars compacta).
Version: 1.0
Data: 25 Aprile 2026

The dopaminergic system is crucial for:
- Reward prediction error computation (TD error)
- Motivation and drive computation
- Curiosity and exploration signals
- Reinforcement learning
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DopamineRegion(Enum):
    """Dopaminergic nuclei regions."""
    VTA = "ventral_tegmental_area"  # Reward, motivation
    SNc = "substantia_nigra_pars_compacta"  # Movement, habit


@dataclass
class RewardOutcome:
    """Outcome of a reward event."""
    expected_reward: float
    actual_reward: float
    td_error: float
    timestamp: str


@dataclass
class MotivationSignal:
    """Complete motivation signal from dopamine system."""
    drive_level: float  # Overall motivation
    curiosity_bonus: float  # Exploration bonus
    expected_reward: float  # Predicted reward
    novelty_signal: float  # Novelty detection
    timestamp: str


class VTA_Dopamine:
    """
    Ventral Tegmental Area (VTA) - Reward and motivation center.
    Projects to prefrontal cortex and nucleus accumbens.
    """
    def __init__(self, input_size: int = 128, output_size: int = 64):
        self.input_size = input_size
        self.output_size = output_size

        # Input from limbic structures, PFC, hippocampus
        self.limbic_weights = np.random.randn(output_size, input_size) * 0.04
        self.pfc_weights = np.random.randn(output_size, input_size) * 0.03
        self.hippocampal_weights = np.random.randn(output_size, 128) * 0.02

        # Dopamine neuron populations
        self.reward_neurons = np.zeros(output_size // 2)
        self.motivation_neurons = np.zeros(output_size // 2)

        # Reward prediction parameters
        self.expected_reward = 0.5
        self.reward_history = deque(maxlen=100)

        # Burst firing parameters
        self.burst_threshold = 0.6
        self.burst_magnitude = 1.5

        self.output = np.zeros(output_size)
        self.current_dopamine = 0.5

    def compute_td_error(self, actual_reward: float,
                         predicted_reward: float = None) -> float:
        """
        Compute Temporal Difference error.
        TD_error = actual_reward - predicted_reward
        Positive = unexpected reward (burst)
        Negative = missed reward (dip)
        """
        if predicted_reward is None:
            predicted_reward = self.expected_reward

        # TD error calculation
        td_error = actual_reward - predicted_reward

        # Update expected reward with learning rate
        self.expected_reward += 0.1 * td_error
        self.expected_reward = np.clip(self.expected_reward, 0, 1)

        # Store history
        self.reward_history.append({
            "actual": actual_reward,
            "predicted": predicted_reward,
            "td_error": td_error,
            "expected_reward": self.expected_reward,
            "timestamp": datetime.now().isoformat()
        })

        return td_error

    def process_reward_signal(self, reward_input: np.ndarray,
                              pfc_context: np.ndarray = None,
                              hippocampal_context: np.ndarray = None) -> Tuple[np.ndarray, float]:
        """Process reward signals through VTA."""
        # Compute inputs
        limbic_out = np.dot(self.limbic_weights, reward_input[:self.input_size])

        pfc_mod = np.zeros(self.output_size)
        if pfc_context is not None and len(pfc_context) == self.input_size:
            pfc_mod = np.dot(self.pfc_weights, pfc_context)

        hippo_mod = np.zeros(self.output_size)
        if hippocampal_context is not None and len(hippocampal_context) == 128:
            hippo_mod = np.dot(self.hippocampal_weights, hippocampal_context)

        # Combine inputs
        total_input = limbic_out + 0.3 * pfc_mod + 0.2 * hippo_mod

        # Split into reward and motivation populations
        half = len(total_input) // 2
        self.reward_neurons = np.tanh(total_input[:half])
        self.motivation_neurons = np.tanh(total_input[half:])

        # Compute dopamine signal based on TD error
        # If reward > expectation -> burst (positive DA)
        # If reward < expectation -> dip (negative DA)
        if len(self.reward_history) > 0:
            last_outcome = self.reward_history[-1]
            td = last_outcome["td_error"]
        else:
            td = 0.0

        # Map TD error to dopamine level
        if td > 0.1:
            # Unexpected reward - burst
            self.current_dopamine = 0.5 + td * 0.5
            self.current_dopamine = min(1.0, self.current_dopamine)
        elif td < -0.1:
            # Missed reward - dip
            self.current_dopamine = 0.5 + td * 0.3
            self.current_dopamine = max(0.0, self.current_dopamine)
        else:
            # Expected reward - baseline
            self.current_dopamine = 0.5 + np.mean(self.motivation_neurons) * 0.2

        # Modulate outputs by dopamine
        self.output = np.concatenate([
            self.reward_neurons * self.current_dopamine,
            self.motivation_neurons * self.current_dopamine
        ])

        return self.output.copy(), self.current_dopamine

    def compute_reward_prediction(self, context: np.ndarray) -> float:
        """Predict reward based on current context."""
        if len(context) < self.input_size:
            context = np.pad(context, (0, self.input_size - len(context)))

        prediction = np.dot(self.limbic_weights, context)[:32]
        return float(np.mean(prediction))

    def get_expected_reward(self) -> float:
        return self.expected_reward

    def get_burst_state(self) -> bool:
        """Check if dopamine neurons are in burst firing."""
        return self.current_dopamine > self.burst_threshold


class SNc_Dopamine:
    """
    Substantia Nigra pars compacta (SNc) - Movement and habit center.
    Projects to dorsal striatum for movement control.
    """
    def __init__(self, input_size: int = 128, output_size: int = 64):
        self.input_size = input_size
        self.output_size = output_size

        # Input from basal ganglia (indirect pathway)
        self.bg_input_weights = np.random.randn(output_size, input_size) * 0.04

        # Input from motor cortex
        self.motor_weights = np.random.randn(output_size, input_size) * 0.03

        # Dopamine neurons (smaller population than VTA)
        self.dopamine_neurons = np.zeros(output_size)

        # Movement parameters
        self.movement_threshold = 0.4
        self.habit_threshold = 0.7

        # Habit strength
        self.habit_signals = np.zeros(output_size)
        self.habit_history = deque(maxlen=100)

        self.output = np.zeros(output_size)
        self.current_dopamine = 0.5

    def process_movement_signal(self, bg_signal: np.ndarray,
                                motor_context: np.ndarray = None) -> Tuple[np.ndarray, float]:
        """Process movement signals through SNc."""
        # Basal ganglia input
        bg_out = np.dot(self.bg_input_weights, bg_signal[:self.input_size])

        # Motor context modulation
        motor_mod = np.zeros(self.output_size)
        if motor_context is not None and len(motor_context) == self.input_size:
            motor_mod = np.dot(self.motor_weights, motor_context)

        # Compute dopamine for movement
        total_input = bg_out + 0.4 * motor_mod

        # Apply movement threshold - SNc more phasic than VTA
        self.dopamine_neurons = np.tanh(total_input)

        # Determine dopamine level based on movement needs
        movement_related = float(np.mean(np.abs(self.dopamine_neurons)))

        if movement_related > self.movement_threshold:
            # Active movement - release dopamine for learning
            self.current_dopamine = 0.6 + movement_related * 0.3
        else:
            # Resting - baseline
            self.current_dopamine = 0.5

        self.output = self.dopamine_neurons * self.current_dopamine

        return self.output.copy(), self.current_dopamine

    def compute_habit_signal(self, action_frequency: np.ndarray) -> float:
        """Compute habit formation signal based on action frequency."""
        # High frequency actions get habit dopamine boost
        habit_strength = np.mean(action_frequency)

        if habit_strength > self.habit_threshold:
            # Strong habit - sustained dopamine
            habit_signal = min(1.0, 0.5 + habit_strength * 0.5)
        else:
            habit_signal = habit_strength

        self.habit_signals.fill(habit_signal)

        self.habit_history.append({
            "habit_strength": habit_strength,
            "habit_signal": habit_signal,
            "timestamp": datetime.now().isoformat()
        })

        return habit_signal

    def get_movement_dopamine(self) -> float:
        return self.current_dopamine


class MotivationCalculator:
    """
    Computes motivation signals from dopamine levels.
    Based on approach-avoidance drive calculation.
    """
    def __init__(self):
        self.current_drive = 0.5
        self.novelty_bonus = 0.0
        self.exploration_threshold = 0.3

        # Drive components
        self.approach_drive = 0.0
        self.avoid_drive = 0.0

        # History
        self.drive_history = deque(maxlen=100)

    def compute_drive(self, vta_dopamine: float, vta_expected_reward: float,
                     novelty_signal: float = 0.0) -> MotivationSignal:
        """Compute overall motivation drive."""
        # Approach drive based on expected reward
        self.approach_drive = vta_expected_reward * vta_dopamine

        # Avoid drive inversely related to dopamine
        self.avoid_drive = (1.0 - vta_dopamine) * 0.3

        # Net drive
        self.current_drive = self.approach_drive - self.avoid_drive
        self.current_drive = np.clip(self.current_drive, 0, 1)

        # Novelty bonus for curiosity
        if novelty_signal > self.exploration_threshold:
            self.novelty_bonus = novelty_signal * 0.2 * vta_dopamine
        else:
            self.novelty_bonus = 0.0

        motivation = MotivationSignal(
            drive_level=self.current_drive,
            curiosity_bonus=self.novelty_bonus,
            expected_reward=vta_expected_reward,
            novelty_signal=novelty_signal,
            timestamp=datetime.now().isoformat()
        )

        self.drive_history.append(motivation)

        return motivation

    def get_curiosity_signal(self) -> float:
        """Get curiosity bonus based on novelty."""
        return self.novelty_bonus


class CuriositySignal:
    """
    Computes curiosity and exploration signals.
    Drives information-seeking behavior.
    """
    def __init__(self):
        self.curiosity_threshold = 0.4
        self.information_gain_weight = 0.3

        # Curiosity state
        self.current_curiosity = 0.0
        self.exploration_count = 0
        self.surprise_signals = deque(maxlen=50)

    def compute_curiosity(self, expected_error: float, actual_error: float) -> float:
        """
        Compute curiosity signal based on prediction error.
        High prediction error -> high curiosity.
        """
        # Surprise = actual error - expected error
        surprise = abs(actual_error) - abs(expected_error)
        surprise = max(0.0, surprise)

        self.surprise_signals.append(surprise)

        # Curiosity proportional to recent surprise
        if len(self.surprise_signals) > 0:
            avg_surprise = np.mean(list(self.surprise_signals))
            self.current_curiosity = min(1.0, avg_surprise * 0.5 + surprise * 0.5)
        else:
            self.current_curiosity = surprise

        return self.current_curiosity

    def compute_information_gain(self, prior_knowledge: np.ndarray,
                                 posterior_knowledge: np.ndarray) -> float:
        """Compute information gain from learning."""
        # KL divergence proxy
        difference = np.sum(posterior_knowledge - prior_knowledge)
        return min(1.0, abs(difference) * self.information_gain_weight)

    def should_explore(self, curiosity_threshold: float = 0.5) -> bool:
        """Decide if system should explore vs exploit."""
        return self.current_curiosity > curiosity_threshold

    def record_exploration(self):
        """Record exploration action."""
        self.exploration_count += 1


class DopaminergicSystem:
    """
    Complete Dopaminergic System.
    Integrates VTA, SNc, motivation, and curiosity for reinforcement learning.
    """
    def __init__(self):
        # VTA - Reward and motivation
        self.vta = VTA_Dopamine(input_size=128, output_size=64)

        # SNc - Movement and habit
        self.snc = SNc_Dopamine(input_size=128, output_size=64)

        # Motivation calculator
        self.motivation = MotivationCalculator()

        # Curiosity calculator
        self.curiosity = CuriositySignal()

        # State tracking
        self.current_dopamine_level = 0.5
        self.td_error_history = deque(maxlen=200)
        self.reward_outcomes = deque(maxlen=100)

        # System flags
        self.burst_firing = False
        self.dip_firing = False

    def compute_td_error(self, actual_reward: float, predicted_reward: float = None) -> float:
        """Compute TD error from reward."""
        td_error = self.vta.compute_td_error(actual_reward, predicted_reward)

        self.td_error_history.append({
            "td_error": td_error,
            "actual_reward": actual_reward,
            "predicted_reward": predicted_reward or self.vta.expected_reward,
            "timestamp": datetime.now().isoformat()
        })

        # Update system state
        if td_error > 0.1:
            self.burst_firing = True
            self.dip_firing = False
            self.current_dopamine_level = 0.5 + td_error * 0.3
        elif td_error < -0.1:
            self.dip_firing = True
            self.burst_firing = False
            self.current_dopamine_level = 0.5 + td_error * 0.3
        else:
            self.burst_firing = False
            self.dip_firing = False
            self.current_dopamine_level = 0.5

        return td_error

    def process_reward_input(self, limbic_signal: np.ndarray,
                             pfc_context: np.ndarray = None,
                             hippocampal_context: np.ndarray = None,
                             motor_signal: np.ndarray = None) -> Dict[str, Any]:
        """
        Process reward and movement inputs through dopaminergic system.
        """
        # VTA processing (reward and motivation)
        vta_output, vta_da = self.vta.process_reward_signal(
            limbic_signal, pfc_context, hippocampal_context
        )

        # SNc processing (movement and habit)
        snc_output, snc_da = self.snc.process_movement_signal(
            limbic_signal[:128], motor_signal
        )

        # Compute motivation signal
        novelty = float(np.var(limbic_signal)) if len(limbic_signal) > 0 else 0.0
        motivation_signal = self.motivation.compute_drive(
            vta_da, self.vta.expected_reward, novelty
        )

        # Compute curiosity
        expected_error = 0.1
        actual_error = abs(vta_da - 0.5)
        curiosity_signal = self.curiosity.compute_curiosity(expected_error, actual_error)

        # Update current dopamine
        self.current_dopamine_level = (vta_da + snc_da) / 2

        return {
            "vta_output": vta_output,
            "snc_output": snc_output,
            "vta_dopamine": vta_da,
            "snc_dopamine": snc_da,
            "motivation": motivation_signal,
            "curiosity": curiosity_signal,
            "current_dopamine": self.current_dopamine_level,
            "burst_firing": self.burst_firing,
            "dip_firing": self.dip_firing,
            "should_explore": self.curiosity.should_explore()
        }

    def get_motivation_signal(self) -> MotivationSignal:
        """Get current motivation signal."""
        return MotivationSignal(
            drive_level=self.motivation.current_drive,
            curiosity_bonus=self.motivation.novelty_bonus,
            expected_reward=self.vta.expected_reward,
            novelty_signal=0.0,
            timestamp=datetime.now().isoformat()
        )

    def get_curiosity_signal(self) -> float:
        """Get current curiosity signal."""
        return self.curiosity.current_curiosity

    def get_dopamine_for_learning(self, target_area: str) -> float:
        """
        Get dopamine signal calibrated for specific target area.
        VTA projects to PFC, SNc projects to Striatum.
        """
        if target_area == "prefrontal":
            return self.vta.current_dopamine
        elif target_area == "striatum":
            return self.snc.current_dopamine
        elif target_area == "hippocampus":
            return self.vta.current_dopamine * 0.8  # Slightly lower
        else:
            return self.current_dopamine_level

    def learn_from_reward(self, actual: float, predicted: float = None) -> Dict:
        """Learn from reward outcome."""
        td = self.compute_td_error(actual, predicted)

        # Update motivation
        novelty = 0.5  # Placeholder
        motivation = self.motivation.compute_drive(
            self.current_dopamine_level,
            self.vta.expected_reward,
            novelty
        )

        return {
            "td_error": td,
            "dopamine_level": self.current_dopamine_level,
            "expected_reward": self.vta.expected_reward,
            "burst": self.burst_firing,
            "dip": self.dip_firing
        }

    def get_system_state(self) -> Dict:
        """Get complete dopaminergic system state."""
        return {
            "current_dopamine": self.current_dopamine_level,
            "vta_expected_reward": self.vta.expected_reward,
            "vta_burst": self.vta.get_burst_state(),
            "snc_movement_da": self.snc.get_movement_dopamine(),
            "motivation_drive": self.motivation.current_drive,
            "curiosity_level": self.curiosity.current_curiosity,
            "should_explore": self.curiosity.should_explore(),
            "burst_firing": self.burst_firing,
            "dip_firing": self.dip_firing,
            "td_error_history_len": len(self.td_error_history),
            "total_explorations": self.curiosity.exploration_count
        }

    def reset(self):
        """Reset dopaminergic system to baseline."""
        self.current_dopamine_level = 0.5
        self.burst_firing = False
        self.dip_firing = False
        self.vta.expected_reward = 0.5
        self.curiosity.current_curiosity = 0.0


def create_dopaminergic_system() -> DopaminergicSystem:
    """Factory function to create dopaminergic system."""
    return DopaminergicSystem()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Dopaminergic System - BRN-005 - Test")
    print("=" * 60)

    # Create system
    dopamine = create_dopaminergic_system()

    # Test 1: TD Error computation
    print("\n--- Test TD Error ---")
    for trial in range(5):
        actual_reward = np.random.choice([0.0, 0.5, 1.0, 0.2])
        predicted = 0.5
        td = dopamine.compute_td_error(actual_reward, predicted)
        print(f"  Trial {trial+1}: reward={actual_reward:.1f}, TD={td:+.3f}, DA={dopamine.current_dopamine_level:.3f}")

    # Test 2: Reward processing
    print("\n--- Test Reward Processing ---")
    limbic_signal = np.random.randn(128)
    result = dopamine.process_reward_input(limbic_signal)
    print(f"  VTA dopamine: {result['vta_dopamine']:.3f}")
    print(f"  SNc dopamine: {result['snc_dopamine']:.3f}")
    print(f"  Current dopamine: {result['current_dopamine']:.3f}")
    print(f"  Burst: {result['burst_firing']}, Dip: {result['dip_firing']}")

    # Test 3: Motivation
    print("\n--- Test Motivation ---")
    motivation = result['motivation']
    print(f"  Drive: {motivation.drive_level:.3f}")
    print(f"  Curiosity bonus: {motivation.curiosity_bonus:.3f}")
    print(f"  Expected reward: {motivation.expected_reward:.3f}")

    # Test 4: Curiosity exploration decision
    print("\n--- Test Curiosity ---")
    print(f"  Curiosity signal: {dopamine.get_curiosity_signal():.3f}")
    print(f"  Should explore: {dopamine.curiosity.should_explore()}")

    # Test 5: Learning from reward
    print("\n--- Test Learning ---")
    learn_result = dopamine.learn_from_reward(0.8, 0.5)
    print(f"  TD error: {learn_result['td_error']:+.3f}")
    print(f"  Dopamine level: {learn_result['dopamine_level']:.3f}")

    # Test 6: Get dopamine for different targets
    print("\n--- Test Dopamine Calibration ---")
    for target in ["prefrontal", "striatum", "hippocampus"]:
        da = dopamine.get_dopamine_for_learning(target)
        print(f"  {target}: DA={da:.3f}")

    # Test 7: System state
    print("\n--- Test System State ---")
    state = dopamine.get_system_state()
    print(f"  VTA expected reward: {state['vta_expected_reward']:.3f}")
    print(f"  Motivation drive: {state['motivation_drive']:.3f}")
    print(f"  Curiosity: {state['curiosity_level']:.3f}")
    print(f"  Total explorations: {state['total_explorations']}")

    print("\n" + "=" * 60)
    print("✅ Dopaminergic System test completed - BRN-005")
    print("=" * 60)