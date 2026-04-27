"""
SPEACE Affective Computing Layer - BRN-007
Implements emotional valence computation that influences all decisions.
Version: 1.0
Data: 25 Aprile 2026

The affective layer models:
- Dimensional emotional space (valence, arousal, dominance)
- Emotional influences on cognition and action selection
- Mood state tracking and regulation
- Affective priming of decisions
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionCategory(Enum):
    """Basic emotional categories per PAD model."""
    JOY = "joy"
    ELATION = "elation"
    RELIEF = "relief"
    SADNESS = "sadness"
    GRIEF = "grief"
    FEAR = "fear"
    ANGER = "anger"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    INTEREST = "interest"
    NEUTRAL = "neutral"


@dataclass
class EmotionalDimension:
    """Three-dimensional emotional space (PAD - Pleasure, Arousal, Dominance)."""
    valence: float      # -1 (negative) to +1 (positive)
    arousal: float      # 0 (calm) to 1 (excited)
    dominance: float    # 0 (submissive) to 1 (dominant)

    def to_vector(self) -> np.ndarray:
        return np.array([self.valence, self.arousal, self.dominance])

    def compute_intensity(self) -> float:
        """Overall emotional intensity."""
        return np.sqrt(self.valence**2 + self.arousal**2 + self.dominance**2) / np.sqrt(3)


@dataclass
class MoodState:
    """Affective state with history tracking."""
    current_mood: EmotionalDimension
    mood_trajectory: List[EmotionalDimension]
    duration_cycles: int
    dominant_emotion: EmotionCategory
    timestamp: str


class AffectiveComputing:
    """
    Affective Computing Layer.
    Computes emotional influences on all cognitive processes.
    """
    def __init__(self):
        # Emotional state space
        self.current_emotion = EmotionalDimension(valence=0.0, arousal=0.5, dominance=0.5)
        self.mood_history = deque(maxlen=100)
        self.emotional_episodes = deque(maxlen=50)

        # Affective modulation parameters
        self.valence_threshold = 0.3
        self.arousal_floor = 0.2
        self.dominance_baseline = 0.5

        # Emotional inertia (mood persists)
        self.valence_inertia = 0.85
        self.arousal_inertia = 0.90
        self.dominance_inertia = 0.80

        # Regulation mechanisms
        self.reappraisal_strength = 0.3
        self.suppression_threshold = 0.8

        # Influence weights on different systems
        self.cognitive_influence = 0.4
        self.action_influence = 0.6
        self.memory_influence = 0.3

        # Current mood state
        self.mood_state: MoodState = None
        self._update_mood_state()

    def compute_emotional_response(self,
                                   stimulus_valence: float,
                                   stimulus_arousal: float,
                                   stimulus_novelty: float = 0.5,
                                   context_modulation: float = 0.5) -> EmotionalDimension:
        """
        Compute emotional response to stimulus.
        Combines stimulus properties with current mood and context.
        """
        # New emotional response
        new_valence = stimulus_valence * (1 - self.reappraisal_strength * context_modulation)
        new_arousal = stimulus_arousal * (1 + stimulus_novelty * 0.3)
        new_dominance = self.dominance_baseline + (stimulus_valence - new_valence) * 0.2

        # Apply inertia (blend with current mood)
        new_valence = (self.valence_inertia * self.current_emotion.valence +
                      (1 - self.valence_inertia) * new_valence)
        new_arousal = (self.arousal_inertia * self.current_emotion.arousal +
                      (1 - self.arousal_inertia) * new_arousal)
        new_dominance = (self.dominance_inertia * self.current_emotion.dominance +
                        (1 - self.dominance_inertia) * new_dominance)

        # Clamp to valid ranges
        new_valence = np.clip(new_valence, -1, 1)
        new_arousal = np.clip(new_arousal, 0, 1)
        new_dominance = np.clip(new_dominance, 0, 1)

        self.current_emotion = EmotionalDimension(
            valence=new_valence,
            arousal=new_arousal,
            dominance=new_dominance
        )

        # Track episode if significant
        if self.current_emotion.compute_intensity() > 0.6:
            self.emotional_episodes.append({
                "emotion": self.current_emotion,
                "stimulus_valence": stimulus_valence,
                "stimulus_arousal": stimulus_arousal,
                "timestamp": datetime.now().isoformat()
            })

        self._update_mood_state()
        return self.current_emotion

    def get_affective_modulation(self, target_system: str) -> float:
        """
        Get affective modulation factor for different systems.
        Returns multiplier in range [0.5, 1.5].
        """
        base_modulation = 1.0

        # Valence-based modulation
        if self.current_emotion.valence > self.valence_threshold:
            if target_system in ["action", "motor", "basal_ganglia"]:
                base_modulation *= 1.2  # Positive mood facilitates action
            elif target_system in ["cognitive", "reasoning"]:
                base_modulation *= 1.1  # Slight facilitation

        elif self.current_emotion.valence < -self.valence_threshold:
            if target_system in ["action", "motor"]:
                base_modulation *= 0.8  # Negative mood may inhibit action
            elif target_system == "memory":
                base_modulation *= 1.15  # Negative events remembered more

        # Arousal-based modulation
        if self.current_emotion.arousal > 0.7:
            if target_system in ["attention", "perception"]:
                base_modulation *= 1.15  # High arousal sharpens attention
            elif target_system == "cognitive":
                base_modulation *= 0.9  # But impairs complex reasoning

        elif self.current_emotion.arousal < self.arousal_floor:
            if target_system in ["attention", "perception"]:
                base_modulation *= 0.85  # Low arousal reduces attention

        # Dominance-based modulation
        if self.current_emotion.dominance > 0.7:
            if target_system == "action":
                base_modulation *= 1.1  # High dominance facilitates action initiation
        elif self.current_emotion.dominance < 0.3:
            if target_system == "action":
                base_modulation *= 0.85  # Low dominance inhibits action

        return np.clip(base_modulation, 0.5, 1.5)

    def regulate_emotion(self, regulation_type: str = "reappraisal", intensity: float = 0.5):
        """
        Apply emotional regulation strategies.
        Types: 'reappraisal', 'suppression', 'expressive', 'avoidance'
        """
        if regulation_type == "reappraisal":
            # Cognitive reappraisal: reinterpret stimulus
            self.reappraisal_strength = np.clip(intensity, 0.1, 0.8)
            # Reappraisal reduces negative valence impact
            if self.current_emotion.valence < 0:
                self.current_emotion.valence *= (1 - intensity * 0.5)

        elif regulation_type == "suppression":
            # Emotion suppression: inhibit expression
            self.suppression_threshold = np.clip(intensity, 0.5, 1.0)
            # Suppression reduces arousal
            self.current_emotion.arousal *= (1 - intensity * 0.3)

        elif regulation_type == "expressive":
            # Expressive suppression/enhancement
            if intensity > 0.5:
                # Enhancement mode
                self.current_emotion.arousal = min(1.0, self.current_emotion.arousal * 1.2)
            else:
                # Dampening mode
                self.current_emotion.arousal *= 0.9

        self._update_mood_state()

    def compute_affective_priming(self, stimulus: np.ndarray) -> np.ndarray:
        """
        Apply affective priming to stimuli.
        Positive stimuli facilitated, negative suppressed.
        """
        valence_mod = self.current_emotion.valence  # -1 to +1

        # Create modulation vector
        if valence_mod > 0:
            # Positive mood: enhance positive features, slightly suppress negative
            priming = 1.0 + valence_mod * 0.3
        else:
            # Negative mood: enhance negative features, slightly suppress positive
            priming = 1.0 + valence_mod * 0.2

        return stimulus * priming

    def _update_mood_state(self):
        """Update current mood state tracking."""
        self.mood_history.append(self.current_emotion)

        # Compute dominant emotion category
        dominant = self._classify_emotion(self.current_emotion)

        self.mood_state = MoodState(
            current_mood=self.current_emotion,
            mood_trajectory=list(self.mood_history)[-10:],
            duration_cycles=len(self.mood_history) % 100,
            dominant_emotion=dominant,
            timestamp=datetime.now().isoformat()
        )

    def _classify_emotion(self, dims: EmotionalDimension) -> EmotionCategory:
        """Classify PAD dimensions to emotion category."""
        v, a, d = dims.valence, dims.arousal, dims.dominance

        # Simple rule-based classification
        if v > 0.5 and a > 0.5 and d > 0.5:
            return EmotionCategory.JOY
        elif v > 0.5 and a > 0.5 and d < 0.5:
            return EmotionCategory.ELATION
        elif v > 0.5 and a < 0.5:
            return EmotionCategory.RELIEF
        elif v < -0.5 and a > 0.5 and d > 0.5:
            return EmotionCategory.ANGER
        elif v < -0.5 and a > 0.5 and d < 0.5:
            return EmotionCategory.FEAR
        elif v < -0.5 and a < 0.5:
            return EmotionCategory.SADNESS
        elif v < -0.3 and a > 0.3:
            return EmotionCategory.DISGUST
        elif abs(v) < 0.2 and a > 0.7:
            return EmotionCategory.SURPRISE
        elif v > 0 and a > 0.4:
            return EmotionCategory.INTEREST
        else:
            return EmotionCategory.NEUTRAL

    def get_valence_arousal(self) -> Tuple[float, float]:
        """Get current valence and arousal for other systems."""
        return self.current_emotion.valence, self.current_emotion.arousal

    def get_mood_summary(self) -> Dict:
        """Get mood summary for reporting."""
        return {
            "current": {
                "valence": self.current_emotion.valence,
                "arousal": self.current_emotion.arousal,
                "dominance": self.current_emotion.dominance,
                "intensity": self.current_emotion.compute_intensity()
            },
            "mood_category": self.mood_state.dominant_emotion.value if self.mood_state else "neutral",
            "history_length": len(self.mood_history),
            "episodes_count": len(self.emotional_episodes)
        }

    def reset(self):
        """Reset affective state to baseline."""
        self.current_emotion = EmotionalDimension(valence=0.0, arousal=0.5, dominance=0.5)
        self.mood_history.clear()
        self.emotional_episodes.clear()
        self._update_mood_state()


class AffectiveLayer:
    """
    Top-level affective computing layer.
    Integrates with amygdala, dopamine, and other emotional systems.
    """
    def __init__(self):
        self.affective = AffectiveComputing()

        # Integration with other systems
        self.amygdala_valence = 0.0
        self.dopamine_level = 0.5
        self.social_context = 0.5  # 0 (isolated) to 1 (social)

        # Emotional memory
        self.emotional_memory_strength = 1.0

    def integrate_affect(self,
                        amygdala_signal: float,  # -1 fear to +1 reward
                        dopamine_signal: float,   # 0 to 1
                        social_modulation: float = 0.5) -> EmotionalDimension:
        """
        Integrate signals from various brain systems.
        Combines amygdala valence, dopamine arousal, and social context.
        """
        # Normalize inputs to 0-1 or -1 to 1 ranges
        self.amygdala_valence = np.clip(amygdala_signal, -1, 1)
        self.dopamine_level = np.clip(dopamine_signal, 0, 1)
        self.social_context = np.clip(social_modulation, 0, 1)

        # Compute integrated emotional response
        stimulus_valence = self.amygdala_valence * 0.6 + (dopamine_signal - 0.5) * 0.4
        stimulus_arousal = 0.3 + dopamine_signal * 0.5 + (1 - social_modulation) * 0.2

        # Social context modulates dominance
        context_mod = social_modulation

        return self.affective.compute_emotional_response(
            stimulus_valence=stimulus_valence,
            stimulus_arousal=stimulus_arousal,
            stimulus_novelty=dopamine_signal * 0.3,
            context_modulation=context_mod
        )

    def apply_to_cognition(self, cognitive_signal: np.ndarray) -> np.ndarray:
        """Apply affective modulation to cognitive processing."""
        modulation = self.affective.get_affective_modulation("cognitive")
        primed = self.affective.compute_affective_priming(cognitive_signal)
        return primed * modulation

    def apply_to_action_selection(self, action_values: np.ndarray) -> np.ndarray:
        """Apply affective modulation to action selection in basal ganglia."""
        modulation = self.affective.get_affective_modulation("action")

        # Positive affect widens selection (more exploration)
        # Negative affect narrows selection (more exploitation/fear)
        if self.current_emotion.valence > 0.3:
            # Add noise for exploration
            noise = np.random.randn(len(action_values)) * 0.1 * modulation
            action_values = action_values + noise
        elif self.current_emotion.valence < -0.3:
            # Focus on safest option
            action_values = action_values * 0.9

        return action_values * modulation

    def get_system_state(self) -> Dict:
        """Get complete affective system state."""
        return {
            "emotion": self.affective.get_mood_summary(),
            "modulation_factors": {
                "cognitive": self.affective.get_affective_modulation("cognitive"),
                "action": self.affective.get_affective_modulation("action"),
                "memory": self.affective.get_affective_modulation("memory")
            },
            "integration": {
                "amygdala_valence": self.amygdala_valence,
                "dopamine_level": self.dopamine_level,
                "social_context": self.social_context
            }
        }

    @property
    def current_emotion(self) -> EmotionalDimension:
        return self.affective.current_emotion


def create_affective_layer() -> AffectiveLayer:
    """Factory function to create affective computing layer."""
    return AffectiveLayer()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Affective Computing Layer - BRN-007 - Test")
    print("=" * 60)

    # Create layer
    affective = create_affective_layer()

    # Test 1: Basic emotional response
    print("\n--- Test Emotional Response ---")
    emotions = [
        (0.8, 0.7, "positive high arousal"),
        (-0.7, 0.8, "fear"),
        (0.3, 0.3, "calm positive"),
        (-0.4, 0.5, "sad"),
    ]

    for val, arous, label in emotions:
        emotion = affective.affective.compute_emotional_response(val, arous, novelty=0.5)
        print(f"  {label}: V={emotion.valence:.2f}, A={emotion.arousal:.2f}, D={emotion.dominance:.2f}")

    # Test 2: Integration
    print("\n--- Test System Integration ---")
    result = affective.integrate_affect(
        amygdala_signal=0.6,  # positive
        dopamine_signal=0.7,  # high
        social_modulation=0.8
    )
    print(f"  Integrated: V={result.valence:.2f}, A={result.arousal:.2f}, D={result.dominance:.2f}")

    # Test 3: Modulation factors
    print("\n--- Test Affective Modulation ---")
    for system in ["cognitive", "action", "memory"]:
        mod = affective.affective.get_affective_modulation(system)
        print(f"  {system}: {mod:.2f}")

    # Test 4: Affective priming
    print("\n--- Test Affective Priming ---")
    stimulus = np.random.randn(64)
    primed = affective.apply_to_cognition(stimulus)
    print(f"  Original mean: {np.mean(np.abs(stimulus)):.3f}")
    print(f"  Primed mean: {np.mean(np.abs(primed)):.3f}")

    # Test 5: Action selection modulation
    print("\n--- Test Action Selection Modulation ---")
    actions = np.array([0.5, 0.8, 0.3, 0.6, 0.4])
    modulated = affective.apply_to_action_selection(actions)
    print(f"  Original actions: {actions}")
    print(f"  Modulated actions: {modulated}")

    # Test 6: Regulation
    print("\n--- Test Emotional Regulation ---")
    affective.affective.regulate_emotion("reappraisal", intensity=0.7)
    state = affective.affective.get_mood_summary()
    print(f"  After reappraisal: valence={state['current']['valence']:.2f}")

    # Test 7: System state
    print("\n--- Test System State ---")
    full_state = affective.get_system_state()
    print(f"  Current emotion: {full_state['emotion']['mood_category']}")
    print(f"  Modulation factors: {full_state['modulation_factors']}")

    print("\n" + "=" * 60)
    print("Affective Computing Layer: PASS")
    print("=" * 60)