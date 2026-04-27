"""
SPEACE Amygdala Module - BRN-003
Implements emotional processing: fear conditioning, reward processing, social signals.
Models: Basolateral Complex (BL), Centromedial Nucleus (CeM), Lateral Nucleus, Central Nucleus.
Version: 1.0
Data: 25 Aprile 2026

The amygdala is crucial for:
- Fear conditioning and threat detection
- Reward processing and appetitive learning
- Emotional valence computation
- Social signal processing
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionalValence(Enum):
    """Emotional valence categories."""
    FEAR = "fear"
    ANGER = "anger"
    SADNESS = "sadness"
    JOY = "joy"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


@dataclass
class EmotionalState:
    """Complete emotional state of the amygdala."""
    valence: str
    arousal: float  # 0-1 activation level
    dominance: float  # 0-1 control level
    fear_level: float = 0.0
    reward_signals: float = 0.0
    threat_detected: bool = False
    timestamp: str = ""


@dataclass
class FearConditioningResult:
    """Result of fear conditioning process."""
    conditioned_response: float
    fear_extinction_rate: float
    generalization_level: float
    timestamp: str


class LateralNucleus:
    """
    Lateral Nucleus (LA) - Primary input station for amygdala.
    Receives sensory inputs from thalamus and cortex.
    """
    def __init__(self, input_size: int = 256, neuron_count: int = 128):
        self.input_size = input_size
        self.neuron_count = neuron_count

        # Sensory input weights
        self.sensory_weights = np.random.randn(neuron_count, input_size) * 0.05

        # Auditory vs visual vs somatosensory specialization
        self.modality_specific_weights = {
            "auditory": np.random.randn(neuron_count // 3, input_size) * 0.03,
            "visual": np.random.randn(neuron_count // 3, input_size) * 0.03,
            "somatosensory": np.random.randn(neuron_count // 3, input_size) * 0.03,
        }

        # Intrinsic excitability
        self.excitability = np.ones(neuron_count) * 0.5
        self.resting_activity = np.zeros(neuron_count)

        # Memory traces for conditioning
        self.conditioned_traces = deque(maxlen=100)
        self.novelty_signals = deque(maxlen=50)

        self.output = np.zeros(neuron_count)

    def process_sensory(self, sensory_input: np.ndarray, modality: str = "somatosensory") -> np.ndarray:
        """Process sensory input with modality-specific processing."""
        # General sensory processing
        sensory_output = np.dot(self.sensory_weights, sensory_input[:self.input_size])

        # Modality-specific enhancement
        if modality in self.modality_specific_weights:
            mod_weights = self.modality_specific_weights[modality]
            mod_output = np.dot(mod_weights, sensory_input[:self.input_size])
            # Replace corresponding portion
            start_idx = {"auditory": 0, "visual": 43, "somatosensory": 86}[modality]
            end_idx = start_idx + len(mod_output)
            sensory_output[start_idx:end_idx] += mod_output

        # Apply excitability modulation
        self.output = np.tanh(sensory_output * self.excitability)

        # Novelty detection (high variance = novel)
        variance = float(np.var(sensory_input))
        novelty = min(1.0, variance * 2) if variance > 0.3 else 0.0
        self.novelty_signals.append(novelty)

        return self.output.copy()

    def store_conditioned_trace(self, pattern: np.ndarray, outcome: str):
        """Store pattern for later conditioning association."""
        self.conditioned_traces.append({
            "pattern": pattern.copy(),
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "novelty": float(np.var(pattern))
        })

    def get_activity(self) -> float:
        return float(np.mean(np.abs(self.output)))


class BasolateralComplex:
    """
    Basolateral Complex (BLA) - Contains basal and accessory basal nuclei.
    Site of emotional learning and memory consolidation.
    """
    def __init__(self, input_size: int = 256, neuron_count: int = 192):
        self.input_size = input_size
        self.neuron_count = neuron_count

        # Input from Lateral Nucleus - LA outputs 128 neurons
        self.la_input_weights = np.random.randn(neuron_count, 128) * 0.04

        # Input from prefrontal cortex (top-down)
        self.pfc_weights = np.random.randn(neuron_count, input_size) * 0.03

        # Hippocampal context input
        self.hippocampal_weights = np.random.randn(neuron_count, 128) * 0.02

        # Valence-specific neurons (positive vs negative)
        self.positive_neurons = np.zeros(neuron_count // 2)
        self.negative_neurons = np.zeros(neuron_count // 2)

        # Learning parameters
        self.learning_rate = 0.01
        self.consolidation_threshold = 0.7

        # Emotional memory storage
        self.emotional_memories = deque(maxlen=200)
        self.association_strengths = {}

        self.output = np.zeros(neuron_count)

    def process_emotional(self, la_input: np.ndarray, pfc_context: np.ndarray = None,
                          hippocampal_context: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Process emotional stimuli with valence computation."""
        # Lateral amygdala input - LA output is 128 neurons
        la_contribution = np.dot(self.la_input_weights, la_input)  # la_input is 128 elements

        # Prefrontal top-down modulation (extinction, regulation)
        pfc_contribution = np.zeros(self.neuron_count)
        if pfc_context is not None:
            # Pad or truncate to expected input size
            if len(pfc_context) > self.input_size:
                pfc_context = pfc_context[:self.input_size]
            elif len(pfc_context) < self.input_size:
                pfc_context = np.pad(pfc_context, (0, self.input_size - len(pfc_context)))
            pfc_contribution = np.dot(self.pfc_weights, pfc_context)

        # Hippocampal context (where did this happen?)
        hippo_contribution = np.zeros(self.neuron_count)
        if hippocampal_context is not None and len(hippocampal_context) == 128:
            hippo_contribution = np.dot(self.hippocampal_weights, hippocampal_context)

        # Combine inputs
        total_input = la_contribution + 0.4 * pfc_contribution + 0.2 * hippo_contribution

        # Split into positive and negative valence populations
        half = len(total_input) // 2
        self.positive_neurons = total_input[:half]
        self.negative_neurons = total_input[half:]

        # Apply valence-specific activation
        self.positive_neurons = np.tanh(self.positive_neurons) * 1.2  # Facilitate positive
        self.negative_neurons = np.tanh(self.negative_neurons) * 1.2  # Facilitate negative

        self.output = np.concatenate([self.positive_neurons, self.negative_neurons])

        return self.output.copy(), self.compute_valence_signal()

    def compute_valence_signal(self) -> Tuple[float, float]:
        """Compute positive and negative valence signals."""
        pos_signal = float(np.mean(np.abs(self.positive_neurons)))
        neg_signal = float(np.mean(np.abs(self.negative_neurons)))
        return pos_signal, neg_signal

    def learn_association(self, cs_signal: np.ndarray, us_signal: np.ndarray,
                         outcome_valence: str):
        """Learn CS-US association (classical conditioning)."""
        # Compute association strength
        association = np.dot(cs_signal, us_signal) / (len(cs_signal) * len(us_signal))

        # Store in memory
        memory_entry = {
            "cs_pattern": cs_signal[:64].copy(),  # Store compressed
            "outcome": outcome_valence,
            "association_strength": float(association),
            "timestamp": datetime.now().isoformat()
        }
        self.emotional_memories.append(memory_entry)

        # Update weights for future processing
        self.association_strengths[outcome_valence] = float(association)

        logger.info(f"Amygdala learned {outcome_valence} association: {association:.3f}")

    def recall_emotional(self, pattern: np.ndarray) -> Optional[Dict]:
        """Recall emotional memory matching pattern."""
        if not self.emotional_memories:
            return None

        # Find best matching memory
        best_match = None
        best_similarity = 0.0

        for memory in self.emotional_memories:
            similarity = np.dot(pattern[:64], memory["cs_pattern"]) / 64
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = memory

        if best_similarity > 0.5:
            return {"memory": best_match, "similarity": float(best_similarity)}

        return None

    def get_valence_bias(self) -> float:
        """Get current valence bias (-1 negative to +1 positive)."""
        pos = float(np.mean(np.abs(self.positive_neurons)))
        neg = float(np.mean(np.abs(self.negative_neurons)))
        if pos + neg > 0.01:
            return (pos - neg) / (pos + neg)
        return 0.0


class CentromedialNucleus:
    """
    Centromedial Nucleus (CeM) - Main output nucleus of amygdala.
    Projects to brainstem and hypothalamic sites for autonomic responses.
    """
    def __init__(self, input_size: int = 192, neuron_count: int = 96):
        self.input_size = input_size
        self.neuron_count = neuron_count

        # Input from Basolateral Complex
        self.bla_weights = np.random.randn(neuron_count, input_size) * 0.06

        # Output neurons for different response types
        self.fear_response_neurons = np.zeros(neuron_count // 3)
        self.appetitive_neurons = np.zeros(neuron_count // 3)
        self.autonomic_neurons = np.zeros(neuron_count // 3)

        # Gating mechanism (inhibitory control)
        self.gating_threshold = 0.5
        self.inhibition_strength = 0.8

        # Response history
        self.response_history = deque(maxlen=100)

        self.output = np.zeros(neuron_count)

    def process_output(self, bla_input: np.ndarray, fear_signal: float = 0.0,
                      reward_signal: float = 0.0) -> Dict[str, np.ndarray]:
        """Process outputs for different behavioral systems."""
        # Input processing
        bla_contribution = np.dot(self.bla_weights, bla_input[:self.input_size])

        # Fear signal modulation
        fear_mod = 1.0 + fear_signal * 0.5

        # Reward signal modulation
        reward_mod = 1.0 + reward_signal * 0.3

        # Compute different output channels
        third = self.neuron_count // 3
        self.fear_response_neurons = np.tanh(bla_contribution[:third] * fear_mod)
        self.appetitive_neurons = np.tanh(bla_contribution[third:2*third] * reward_mod)
        self.autonomic_neurons = np.tanh(bla_contribution[2*third:] * (fear_mod + reward_mod) / 2)

        # Gating: if too many outputs, inhibit
        total_activity = np.mean(np.abs(self.output))
        if total_activity > self.gating_threshold:
            inhibition = self.inhibition_strength * (total_activity - self.gating_threshold)
            self.fear_response_neurons *= (1 - inhibition)
            self.appetitive_neurons *= (1 - inhibition)

        self.output = np.concatenate([
            self.fear_response_neurons,
            self.appetitive_neurons,
            self.autonomic_neurons
        ])

        # Store response
        self.response_history.append({
            "fear": float(np.mean(self.fear_response_neurons)),
            "appetitive": float(np.mean(self.appetitive_neurons)),
            "autonomic": float(np.mean(self.autonomic_neurons)),
            "timestamp": datetime.now().isoformat()
        })

        return {
            "fear_response": self.fear_response_neurons.copy(),
            "appetitive": self.appetitive_neurons.copy(),
            "autonomic": self.autonomic_neurons.copy(),
            "combined_output": self.output.copy()
        }

    def get_fear_response_strength(self) -> float:
        return float(np.mean(np.abs(self.fear_response_neurons)))

    def get_appetitive_strength(self) -> float:
        return float(np.mean(np.abs(self.appetitive_neurons)))


class CentralNucleus:
    """
    Central Nucleus (CeA) - Coord outputs to brainstem effectors.
    Controls species-specific defensive responses and autonomic output.
    """
    def __init__(self, input_size: int = 96, output_size: int = 64):
        self.input_size = input_size
        self.output_size = output_size

        # Input from Centromedial nucleus
        self.cem_weights = np.random.randn(output_size, input_size) * 0.05

        # Output to different brainstem targets
        self.brainstem_outputs = {
            "periaqueductal_gray": np.zeros(output_size // 4),
            "hypothalamus": np.zeros(output_size // 4),
            "lateral_habenula": np.zeros(output_size // 4),
            "brainstem_autonomic": np.zeros(output_size // 4)
        }

        # Autonomic state
        self.heart_rate_modulation = 0.0
        self.respiration_modulation = 0.0
        self.pupil_dilation = 0.0

        self.output = np.zeros(output_size)

    def coordinate_responses(self, cem_output: np.ndarray) -> Dict[str, np.ndarray]:
        """Coordinate brainstem outputs for coordinated response."""
        # Process input
        self.output = np.dot(self.cem_weights, cem_output[:self.input_size])

        # Route to different targets
        quarter = self.output_size // 4
        self.brainstem_outputs["periaqueductal_gray"] = self.output[:quarter]
        self.brainstem_outputs["hypothalamus"] = self.output[quarter:2*quarter]
        self.brainstem_outputs["lateral_habenula"] = self.output[2*quarter:3*quarter]
        self.brainstem_outputs["brainstem_autonomic"] = self.output[3*quarter:]

        # Update autonomic parameters
        self.heart_rate_modulation = float(np.mean(np.abs(self.brainstem_outputs["brainstem_autonomic"])))
        self.pupil_dilation = float(np.mean(np.abs(self.brainstem_outputs["hypothalamus"])))

        return self.brainstem_outputs.copy()

    def get_autonomic_state(self) -> Dict[str, float]:
        return {
            "heart_rate_modulation": self.heart_rate_modulation,
            "respiration_modulation": self.respiration_modulation,
            "pupil_dilation": self.pupil_dilation
        }


class Amygdala:
    """
    Complete Amygdala System.
    Integrates all nuclei for emotional processing.
    """
    def __init__(self):
        # Initialize nuclei
        self.lateral = LateralNucleus(input_size=256, neuron_count=128)
        self.basolateral = BasolateralComplex(input_size=256, neuron_count=192)
        self.centromedial = CentromedialNucleus(input_size=192, neuron_count=96)
        self.central = CentralNucleus(input_size=96, output_size=64)

        # Emotional state tracking
        self.current_state: EmotionalState = EmotionalState(
            valence="neutral", arousal=0.5, dominance=0.5
        )
        self.emotional_history = deque(maxlen=200)

        # Fear conditioning state
        self.fear_conditioned = False
        self.conditioning_trials = 0
        self.extinction_trial = 0

        # Social signals
        self.social_signal_processing = False

        # Reward learning
        self.last_reward = 0.0
        self.reward_history = deque(maxlen=50)

    def process_emotional_stimulus(self, sensory_input: np.ndarray,
                                   modality: str = "somatosensory",
                                   pfc_context: np.ndarray = None,
                                   hippocampal_context: np.ndarray = None) -> EmotionalState:
        """
        Process emotional stimulus through complete amygdala circuit.
        """
        # Stage 1: Lateral nucleus (input)
        la_output = self.lateral.process_sensory(sensory_input, modality)

        # Stage 2: Basolateral complex (learning and valence)
        bla_output, (pos_valence, neg_valence) = self.basolateral.process_emotional(
            la_output, pfc_context, hippocampal_context
        )

        # Stage 3: Centromedial nucleus (output generation)
        cem_output = self.centromedial.process_output(
            bla_output,
            fear_signal=neg_valence,
            reward_signal=pos_valence
        )

        # Stage 4: Central nucleus (brainstem coordination)
        brainstem_outputs = self.central.coordinate_responses(cem_output["combined_output"])

        # Compute emotional state
        fear_level = self.centromedial.get_fear_response_strength()
        reward_level = self.centromedial.get_appetitive_strength()

        # Determine valence
        if fear_level > reward_level * 1.2:
            valence = "fear" if fear_level > 0.6 else "anger"
        elif reward_level > fear_level * 1.2:
            valence = "joy"
        else:
            valence = "neutral"

        arousal = min(1.0, (fear_level + reward_level) / 2 + 0.3)
        dominance = 0.5 + (reward_level - fear_level) * 0.3

        self.current_state = EmotionalState(
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            fear_level=fear_level,
            reward_signals=reward_level,
            threat_detected=fear_level > 0.5,
            timestamp=datetime.now().isoformat()
        )

        self.emotional_history.append(self.current_state)

        return self.current_state

    def condition_fear(self, conditioned_stimulus: np.ndarray,
                       unconditioned_stimulus: np.ndarray):
        """
        Classical fear conditioning.
        CS (conditioned stimulus) becomes associated with US (unconditioned stimulus).
        """
        # Store the trace for later recall
        self.lateral.store_conditioned_trace(conditioned_stimulus, "fear")

        # Learn the association in basolateral complex
        self.basolateral.learn_association(
            conditioned_stimulus, unconditioned_stimulus, "fear"
        )

        self.fear_conditioned = True
        self.conditioning_trials += 1

        logger.info(f"Fear conditioning trial {self.conditioning_trials} completed")

    def condition_reward(self, conditioned_stimulus: np.ndarray,
                        reward_stimulus: np.ndarray):
        """
        Appetitive conditioning (reward learning).
        """
        self.basolateral.learn_association(
            conditioned_stimulus, reward_stimulus, "reward"
        )
        self.last_reward = 1.0
        self.reward_history.append(1.0)

    def extinguish_fear(self, extinction_stimulus: np.ndarray, trials: int = 10):
        """
        Fear extinction training (PFC-mediated).
        """
        if self.fear_conditioned:
            for _ in range(trials):
                # Present CS without US - basolateral learns new safety association
                self.basolateral.learn_association(
                    extinction_stimulus, np.zeros(64), "safety"
                )
            self.extinction_trial += trials
            logger.info(f"Fear extinction: {trials} trials completed")

    def process_social_signal(self, social_input: np.ndarray) -> Dict[str, Any]:
        """
        Process social signals (faces, voices, gestures).
        """
        # Social signals go through lateral and basolateral
        la_output = self.lateral.process_sensory(social_input, "visual")
        bla_output, _ = self.basolateral.process_emotional(la_output)

        # Social recognition produces approach/avoid response
        approach_signal = float(np.mean(self.basolateral.positive_neurons))
        avoid_signal = float(np.mean(self.basolateral.negative_neurons))

        self.social_signal_processing = True

        return {
            "approach": approach_signal,
            "avoid": avoid_signal,
            "social_recognition": approach_signal + avoid_signal > 0.3
        }

    def get_valence_arousal(self) -> Tuple[float, float]:
        """Get current valence and arousal values."""
        if len(self.emotional_history) > 0:
            recent = self.emotional_history[-1]
            valence_map = {"fear": -0.8, "anger": -0.5, "sadness": -0.6,
                          "joy": 0.8, "surprise": 0.2, "disgust": -0.7, "neutral": 0.0}
            valence = valence_map.get(recent.valence, 0.0)
            return valence, recent.arousal
        return 0.0, 0.5

    def get_system_state(self) -> Dict:
        """Get complete amygdala system state."""
        return {
            "current_state": {
                "valence": self.current_state.valence,
                "arousal": self.current_state.arousal,
                "dominance": self.current_state.dominance,
                "fear_level": self.current_state.fear_level,
                "reward_signals": self.current_state.reward_signals,
                "threat_detected": self.current_state.threat_detected
            },
            "fear_conditioned": self.fear_conditioned,
            "conditioning_trials": self.conditioning_trials,
            "extinction_trials": self.extinction_trial,
            "valence_bias": self.basolateral.get_valence_bias(),
            "lateral_activity": self.lateral.get_activity(),
            "autonomic_state": self.central.get_autonomic_state(),
            "brainstem_outputs": {
                k: float(np.mean(np.abs(v))) for k, v in self.central.brainstem_outputs.items()
            }
        }

    def reset(self):
        """Reset amygdala to neutral state."""
        self.current_state = EmotionalState(valence="neutral", arousal=0.5, dominance=0.5)
        self.fear_conditioned = False
        self.social_signal_processing = False


def create_amygdala() -> Amygdala:
    """Factory function to create amygdala system."""
    return Amygdala()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Amygdala Module - BRN-003 - Test")
    print("=" * 60)

    # Create amygdala
    amygdala = create_amygdala()

    # Test 1: Basic emotional processing
    print("\n--- Test Emotional Processing ---")
    for modality in ["somatosensory", "visual", "auditory"]:
        sensory = np.random.randn(256)
        state = amygdala.process_emotional_stimulus(sensory, modality)
        print(f"  {modality}: valence={state.valence}, arousal={state.arousal:.2f}, fear={state.fear_level:.2f}")

    # Test 2: Fear conditioning
    print("\n--- Test Fear Conditioning ---")
    cs = np.random.randn(256)  # Conditioned stimulus
    us = np.random.randn(256)  # Unconditioned stimulus (threat)

    amygdala.condition_fear(cs, us)
    print(f"  Fear conditioned: {amygdala.fear_conditioned}")

    # Test conditioned response
    response = amygdala.process_emotional_stimulus(cs, "somatosensory")
    print(f"  Fear response to CS: {response.fear_level:.3f}")

    # Test 3: Reward conditioning
    print("\n--- Test Reward Conditioning ---")
    reward_cs = np.random.randn(256)
    reward_us = np.random.randn(256) * 0.5 + 2.0  # Positive signal
    amygdala.condition_reward(reward_cs, reward_us)

    reward_response = amygdala.process_emotional_stimulus(reward_cs, "visual")
    print(f"  Reward signal: {reward_response.reward_signals:.3f}")

    # Test 4: Valence/Arousal
    print("\n--- Test Valence/Arousal ---")
    valence, arousal = amygdala.get_valence_arousal()
    print(f"  Current: valence={valence:.2f}, arousal={arousal:.2f}")

    # Test 5: Social signal processing
    print("\n--- Test Social Signal Processing ---")
    social_input = np.random.randn(256)
    social_result = amygdala.process_social_signal(social_input)
    print(f"  Approach: {social_result['approach']:.3f}, Avoid: {social_result['avoid']:.3f}")
    print(f"  Recognized: {social_result['social_recognition']}")

    # Test 6: System state
    print("\n--- Test System State ---")
    state = amygdala.get_system_state()
    print(f"  Threat detected: {state['current_state']['threat_detected']}")
    print(f"  Autonomic - HR modulation: {state['autonomic_state']['heart_rate_modulation']:.3f}")
    print(f"  Brainstem outputs: {state['brainstem_outputs']}")

    print("\n" + "=" * 60)
    print("✅ Amygdala Module test completed - BRN-003")
    print("=" * 60)