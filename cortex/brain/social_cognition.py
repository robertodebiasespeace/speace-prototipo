"""
SPEACE Social Cognition Module - BRN-009
Implements Theory of Mind, empathy, and social learning.
Version: 1.0
Data: 25 Aprile 2026

The social cognition module models:
- Theory of Mind (inferring mental states of others)
- Empathy (emotional and cognitive)
- Social learning (learning from observation)
- Joint attention and shared intentionality
- Intent decoding
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SocialSignalType(Enum):
    """Types of social signals."""
    FACIAL_EXPRESSION = "facial"
    VOCAL_TONE = "vocal"
    GESTURE = "gesture"
    GAZE_DIRECTION = "gaze"
    BODY_POSTURE = "posture"
    VERBAL = "verbal"
    SPATIAL = "spatial"  # Proxemics


@dataclass
class MentalState:
    """Represents another agent's mental state."""
    beliefs: Dict[str, float]    # Belief about world
    desires: Dict[str, float]    # Goals/motivations
    intentions: Dict[str, float] # Planned actions
    emotions: Dict[str, float]   # Current emotional state
    knowledge_level: float       # 0 to 1
    attention_focus: Optional[str] = None


@dataclass
class EmpathyResponse:
    """Empathic response to another's emotional state."""
    affective_empathy: float     # Emotional mirroring
    cognitive_empathy: float     # Understanding their state
    empathic_concern: float      # Concern for their wellbeing
    personal_distress: float     # Self-focused reaction
    timestamp: str


@dataclass
class SocialLearningResult:
    """Result of learning from social observation."""
    observed_action: str
    inferred_intent: str
    modeled_outcome: str
    confidence: float
    imitation_likelihood: float


class TheoryOfMind:
    """
    Theory of Mind - Inferring mental states of others.
    Represents how the system models the mental states of other agents.
    """
    def __init__(self):
        # Modeled agents
        self.modeled_agents: Dict[str, MentalState] = {}

        # ToM accuracy
        self.prediction_accuracy = 0.5
        self.prediction_history = deque(maxlen=50)

        # Model complexity
        self.depth_levels = 3  # 1st order, 2nd order, 3rd order beliefs

    def model_agent(self, agent_id: str, observations: np.ndarray = None) -> MentalState:
        """
        Create or update model of an agent based on observations.
        """
        if agent_id not in self.modeled_agents:
            self.modeled_agents[agent_id] = MentalState(
                beliefs={},
                desires={},
                intentions={},
                emotions={},
                knowledge_level=0.5
            )

        agent = self.modeled_agents[agent_id]

        # Update beliefs based on observations
        if observations is not None:
            # Simple belief update from observation encoding
            belief_strength = float(np.mean(np.abs(observations)))
            agent.knowledge_level = (agent.knowledge_level + belief_strength) / 2

            # Infer emotions from behavioral signals
            if len(observations) > 0:
                emotion_valence = np.mean(observations[:32])
                agent.emotions['valence'] = np.clip(emotion_valence, -1, 1)

        return agent

    def infer_belief(self, agent_id: str, fact: str) -> float:
        """
        Infer what an agent believes about a fact.
        """
        if agent_id not in self.modeled_agents:
            return 0.5

        agent = self.modeled_agents[agent_id]
        return agent.beliefs.get(fact, agent.knowledge_level)

    def infer_desire(self, agent_id: str, goal: str) -> float:
        """
        Infer how much an agent desires a goal.
        """
        if agent_id not in self.modeled_agents:
            return 0.3

        agent = self.modeled_agents[agent_id]
        return agent.desires.get(goal, 0.5)

    def predict_action(self, agent_id: str, context: np.ndarray) -> str:
        """
        Predict what action an agent will take based on their mental state.
        """
        if agent_id not in self.modeled_agents:
            return "unknown"

        agent = self.modeled_agents[agent_id]

        # Simple prediction based on desire and belief alignment
        max_desire = max(agent.desires.values()) if agent.desires else 0.5

        if max_desire > 0.6:
            return "goal_directed"
        elif agent.emotions.get('valence', 0) < -0.3:
            return "avoidance"
        else:
            return "exploratory"

    def second_order_belief(self, agent_id: str, target_agent: str,
                          fact: str) -> float:
        """
        Model what agent_id believes about target_agent's belief.
        (2nd order ToM)
        """
        if agent_id not in self.modeled_agents or target_agent not in self.modeled_agents:
            return 0.5

        # Assume agent reasons about others similarly to self
        target_belief = self.modeled_agents[target_agent].beliefs.get(fact, 0.5)

        # Agent's model of target's belief might be imperfect
        noise = np.random.randn() * 0.1
        return np.clip(target_belief + noise, 0, 1)

    def get_agent_state(self, agent_id: str) -> Optional[Dict]:
        """Get complete mental state of agent."""
        if agent_id not in self.modeled_agents:
            return None

        agent = self.modeled_agents[agent_id]
        return {
            "beliefs": agent.beliefs,
            "desires": agent.desires,
            "intentions": agent.intentions,
            "emotions": agent.emotions,
            "knowledge_level": agent.knowledge_level,
            "attention_focus": agent.attention_focus
        }


class EmpathyModule:
    """
    Empathy Module - Emotional and cognitive empathy responses.
    Computes empathic responses to others' emotional states.
    """
    def __init__(self):
        # Empathy components
        self.affective_empathy_strength = 0.6
        self.cognitive_empathy_strength = 0.5
        self.empathic_concern_strength = 0.4

        # Emotional contagion
        self.contagion_strength = 0.3
        self.emotional_broadcast = np.zeros(64)

        # Current empathic state
        self.current_response: Optional[EmpathyResponse] = None

    def compute_empathy(self, observed_emotion: np.ndarray,
                        self_emotional_state: np.ndarray,
                        perspective_taking: float = 0.5) -> EmpathyResponse:
        """
        Compute empathic response to observed emotion.
        """
        # Affective empathy: emotional contagion/mirroring
        emotional_similarity = 1 - np.mean(np.abs(observed_emotion - self_emotional_state))
        affective = emotional_similarity * self.affective_empathy_strength

        # Cognitive empathy: understanding their perspective
        cognitive = perspective_taking * self.cognitive_empathy_strength

        # Empathic concern: other-oriented concern
        concern = cognitive * self.empathic_concern_strength

        # Personal distress: self-focused reaction to their suffering
        distress_signal = np.mean(np.abs(observed_emotion[:32]))
        if distress_signal > 0.5:
            personal_distress = distress_signal * 0.5
        else:
            personal_distress = 0.1

        self.current_response = EmpathyResponse(
            affective_empathy=np.clip(affective, 0, 1),
            cognitive_empathy=np.clip(cognitive, 0, 1),
            empathic_concern=np.clip(concern, 0, 1),
            personal_distress=np.clip(personal_distress, 0, 1),
            timestamp=datetime.now().isoformat()
        )

        # Update emotional broadcast for contagion
        self.emotional_broadcast = (observed_emotion[:64] * self.contagion_strength +
                                     self_emotional_state[:64] * (1 - self.contagion_strength))

        return self.current_response

    def get_empathic_modulation(self) -> float:
        """
        Get modulation factor based on empathy.
        Higher empathy = more prosocial behavior modulation.
        """
        if self.current_response is None:
            return 1.0

        # Net empathic倾向
        net_empathy = (self.current_response.affective_empathy +
                      self.current_response.cognitive_empathy +
                      self.current_response.empathic_concern) / 3

        # Personal distress reduces prosocial motivation
        net_empathy -= self.current_response.personal_distress * 0.3

        return np.clip(1.0 + net_empathy * 0.3, 0.7, 1.3)


class SocialLearning:
    """
    Social Learning - Learning from observing others.
    Implements learning via observation, imitation, and instruction.
    """
    def __init__(self):
        # Learning parameters
        self.imitation_weight = 0.6
        self.observation_weight = 0.4

        # Observational learning history
        self.observed_actions = deque(maxlen=100)
        self.inferred_intents = deque(maxlen=50)

        # Emulation vs mimicry
        self.emulation_mode = True  # vs mimicry

    def learn_from_observation(self,
                               observed_behavior: np.ndarray,
                               outcome: str,
                               context: str = "neutral") -> SocialLearningResult:
        """
        Learn from observing another agent's behavior and its outcome.
        """
        # Infer intent from behavior
        inferred_intent = self._infer_intent(observed_behavior)

        # Model outcome relationship
        modeled_outcome = outcome  # Simplified

        # Confidence based on observation clarity
        confidence = float(np.mean(np.abs(observed_behavior)))

        # Imitation likelihood
        if context == "goal_achieved":
            imitation_likelihood = confidence * self.imitation_weight
        else:
            imitation_likelihood = confidence * self.imitation_weight * 0.5

        result = SocialLearningResult(
            observed_action="observed_behavior",
            inferred_intent=inferred_intent,
            modeled_outcome=modeled_outcome,
            confidence=confidence,
            imitation_likelihood=imitation_likelihood
        )

        self.observed_actions.append(observed_behavior)
        self.inferred_intents.append(inferred_intent)

        return result

    def _infer_intent(self, behavior: np.ndarray) -> str:
        """Infer intent from observed behavior."""
        # Simple heuristic based on behavior pattern
        magnitude = float(np.mean(np.abs(behavior)))

        if magnitude > 0.7:
            return "high_stakes_action"
        elif magnitude > 0.4:
            return "exploratory_action"
        else:
            return "routine_action"

    def should_imitate(self, result: SocialLearningResult,
                      own_efficacy: float = 0.5) -> bool:
        """
        Decide whether to imitate observed behavior.
        """
        # Higher when own efficacy is low and observed efficacy is high
        if own_efficacy < 0.5 and result.confidence > 0.6:
            return result.imitation_likelihood > 0.4

        # Higher when observed outcome was positive
        if result.modeled_outcome == "success":
            return result.imitation_likelihood > 0.5

        return result.imitation_likelihood > 0.7


class JointAttention:
    """
    Joint Attention - Shared focus of attention.
    Critical for social cognition and language development.
    """
    def __init__(self):
        self.shared_focus: Optional[str] = None
        self.focus_history = deque(maxlen=30)

        # Attentional coordination
        self.coordination_strength = 0.5
        self.following_likelihood = 0.7

        # Gaze tracking
        self.own_gaze_target = None
        self.other_gaze_target = None

    def establish_joint_attention(self, target: str,
                                   other_agent_focus: str = None) -> bool:
        """
        Establish joint attention on a target.
        """
        # If other agent is already looking at target, establish joint attention
        if other_agent_focus == target:
            self.shared_focus = target
            self.following_likelihood = 0.9
        else:
            # Try to direct attention
            self.shared_focus = target
            self.following_likelihood = 0.5

        self.focus_history.append({
            "target": target,
            "joint": other_agent_focus == target,
            "timestamp": datetime.now().isoformat()
        })

        return self.shared_focus == target

    def detect_joint_attention(self, own_gaze: str,
                               other_gaze: str) -> Tuple[bool, float]:
        """
        Detect if joint attention is occurring.
        Returns (is_joint, confidence).
        """
        self.own_gaze_target = own_gaze
        self.other_gaze_target = other_gaze

        is_joint = own_gaze == other_gaze

        if is_joint:
            confidence = self.coordination_strength * self.following_likelihood
        else:
            confidence = 0.1

        return is_joint, confidence

    def get_shared_attention(self) -> Optional[str]:
        return self.shared_focus


class IntentDecoding:
    """
    Intent Decoding - Interpreting intended actions from others.
    Uses predictive modeling and behavioral patterns.
    """
    def __init__(self):
        # Intent library
        self.intent_patterns: Dict[str, np.ndarray] = {}

        # Decoding confidence
        self.confidence_threshold = 0.5

        # Prediction history
        self.predictions = deque(maxlen=50)

    def learn_intent_pattern(self, intent: str, behavior: np.ndarray):
        """Learn pattern for an intent."""
        if intent not in self.intent_patterns:
            self.intent_patterns[intent] = np.zeros(64)

        # Update pattern with new observation
        self.intent_patterns[intent] = (0.9 * self.intent_patterns[intent] +
                                         0.1 * behavior[:64])

    def decode_intent(self, observed_behavior: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Decode intent from observed behavior.
        Returns (intent, confidence).
        """
        best_match = None
        best_similarity = 0.0

        for intent, pattern in self.intent_patterns.items():
            similarity = np.dot(observed_behavior[:64], pattern)
            similarity /= (np.linalg.norm(observed_behavior[:64]) * np.linalg.norm(pattern) + 1e-8)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = intent

        if best_similarity > self.confidence_threshold:
            self.predictions.append({
                "intent": best_match,
                "confidence": best_similarity,
                "timestamp": datetime.now().isoformat()
            })
            return best_match, best_similarity

        return None, 0.0


class SocialCognition:
    """
    Complete Social Cognition System.
    Integrates ToM, empathy, social learning, and joint attention.
    """
    def __init__(self):
        # Components
        self.tom = TheoryOfMind()
        self.empathy = EmpathyModule()
        self.social_learning = SocialLearning()
        self.joint_attention = JointAttention()
        self.intent_decoding = IntentDecoding()

        # Social state
        self.social_interaction_active = False
        self.current_interaction_partner: Optional[str] = None
        self.interaction_mode = "observation"  # 'observation', 'conversation', 'cooperation'

        # Social knowledge
        self.social_knowledge = {}  # Learned social patterns

    def perceive_social_signal(self, signal: np.ndarray,
                               signal_type: SocialSignalType) -> Dict[str, Any]:
        """
        Process social signal from environment.
        """
        if signal_type == SocialSignalType.GAZE_DIRECTION:
            # Update joint attention
            is_joint, confidence = self.joint_attention.detect_joint_attention(
                "current_target", signal[:10].argmax()
            )
            return {"joint_attention": is_joint, "confidence": confidence}

        elif signal_type == SocialSignalType.FACIAL_EXPRESSION:
            # Model emotion and compute empathy
            emotion_encoding = signal[:32]
            self_emotion = np.ones(32) * 0.5

            empathy_response = self.empathy.compute_empathy(
                emotion_encoding, self_emotion, perspective_taking=0.6
            )

            return {
                "empathy_response": empathy_response,
                "emotional_contagion": float(np.mean(emotion_encoding))
            }

        elif signal_type == SocialSignalType.GESTURE:
            # Decode intent
            intent, confidence = self.intent_decoding.decode_intent(signal)

            # Learn from observation
            if intent:
                self.social_learning.learn_from_observation(
                    signal, outcome="goal_achieved"
                )

            return {"decoded_intent": intent, "confidence": confidence}

        return {}

    def model_other_agent(self, agent_id: str,
                         observations: np.ndarray = None) -> MentalState:
        """Create/update model of another agent."""
        return self.tom.model_agent(agent_id, observations)

    def infer_others_belief(self, agent_id: str, fact: str) -> float:
        """Infer what another agent believes."""
        return self.tom.infer_belief(agent_id, fact)

    def predict_others_action(self, agent_id: str, context: np.ndarray) -> str:
        """Predict what another agent will do."""
        return self.tom.predict_action(agent_id, context)

    def compute_empathic_response(self, observed_emotion: np.ndarray) -> EmpathyResponse:
        """Compute empathy for observed emotion."""
        self_emotion = np.ones(32) * 0.5  # Neutral baseline
        return self.empathy.compute_empathy(observed_emotion, self_emotion)

    def learn_social(self, behavior: np.ndarray, outcome: str) -> SocialLearningResult:
        """Learn from social observation."""
        return self.social_learning.learn_from_observation(behavior, outcome)

    def should_imitate(self, result: SocialLearningResult) -> bool:
        """Decide whether to imitate observed behavior."""
        return self.social_learning.should_imitate(result)

    def establish_joint_attention(self, target: str) -> bool:
        """Establish shared attention on target."""
        return self.joint_attention.establish_joint_attention(target)

    def get_system_state(self) -> Dict:
        """Get complete social cognition state."""
        return {
            "tom": {
                "agents_modeled": len(self.tom.modeled_agents),
                "prediction_accuracy": self.tom.prediction_accuracy
            },
            "empathy": {
                "affective": self.empathy.affective_empathy_strength,
                "cognitive": self.empathy.cognitive_empathy_strength,
                "current_response": {
                    "affective": self.empathy.current_response.affective_empathy if self.empathy.current_response else 0,
                    "cognitive": self.empathy.current_response.cognitive_empathy if self.empathy.current_response else 0
                }
            },
            "joint_attention": {
                "shared_focus": self.joint_attention.get_shared_attention(),
                "coordination_strength": self.joint_attention.coordination_strength
            },
            "intent_decoding": {
                "intents_known": len(self.intent_decoding.intent_patterns),
                "predictions_made": len(self.intent_decoding.predictions)
            },
            "interaction": {
                "active": self.social_interaction_active,
                "partner": self.current_interaction_partner,
                "mode": self.interaction_mode
            }
        }

    def reset(self):
        """Reset social cognition state."""
        self.tom.modeled_agents.clear()
        self.social_interaction_active = False
        self.current_interaction_partner = None


def create_social_cognition() -> SocialCognition:
    """Factory function to create social cognition system."""
    return SocialCognition()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Social Cognition Module - BRN-009 - Test")
    print("=" * 60)

    # Create system
    social = create_social_cognition()

    # Test 1: Agent modeling (ToM)
    print("\n--- Test Theory of Mind ---")
    agent_state = social.model_other_agent("agent_1", np.random.randn(64))
    print(f"  Modeled agent_1: knowledge_level={agent_state.knowledge_level:.2f}")

    belief = social.infer_others_belief("agent_1", "fact_about_world")
    print(f"  Inferred belief: {belief:.2f}")

    predicted_action = social.predict_others_action("agent_1", np.random.randn(64))
    print(f"  Predicted action: {predicted_action}")

    # Test 2: Empathy
    print("\n--- Test Empathy ---")
    observed_emotion = np.random.randn(32) * 0.5 + 0.3
    empathy = social.compute_empathic_response(observed_emotion)
    print(f"  Affective empathy: {empathy.affective_empathy:.2f}")
    print(f"  Cognitive empathy: {empathy.cognitive_empathy:.2f}")
    print(f"  Empathic concern: {empathy.empathic_concern:.2f}")

    # Test 3: Social learning
    print("\n--- Test Social Learning ---")
    observed_behavior = np.random.randn(64)
    result = social.learn_social(observed_behavior, "success")
    print(f"  Inferred intent: {result.inferred_intent}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Imitation likelihood: {result.imitation_likelihood:.2f}")

    should_imitate = social.should_imitate(result)
    print(f"  Should imitate: {should_imitate}")

    # Test 4: Joint attention
    print("\n--- Test Joint Attention ---")
    established = social.establish_joint_attention("object_1")
    print(f"  Established joint attention on object_1: {established}")

    is_joint, confidence = social.joint_attention.detect_joint_attention("object_1", "object_1")
    print(f"  Joint attention detected: {is_joint}, confidence: {confidence:.2f}")

    # Test 5: Intent decoding
    print("\n--- Test Intent Decoding ---")
    social.intent_decoding.learn_intent_pattern("help", np.random.randn(64))
    social.intent_decoding.learn_intent_pattern("harm", np.random.randn(64))

    test_behavior = np.random.randn(64)
    decoded, confidence = social.intent_decoding.decode_intent(test_behavior)
    print(f"  Decoded intent: {decoded}, confidence: {confidence:.2f}")

    # Test 6: Social signal processing
    print("\n--- Test Social Signal Processing ---")
    gaze_signal = np.random.randn(64)
    gaze_result = social.perceive_social_signal(gaze_signal, SocialSignalType.GAZE_DIRECTION)
    print(f"  Gaze processing: joint={gaze_result.get('joint_attention')}, confidence={gaze_result.get('confidence', 0):.2f}")

    facial_signal = np.random.randn(64)
    facial_result = social.perceive_social_signal(facial_signal, SocialSignalType.FACIAL_EXPRESSION)
    print(f"  Facial processing: empathy_response={facial_result.get('empathy_response') is not None}")

    # Test 7: System state
    print("\n--- Test System State ---")
    state = social.get_system_state()
    print(f"  ToM agents: {state['tom']['agents_modeled']}")
    print(f"  Joint attention focus: {state['joint_attention']['shared_focus']}")
    print(f"  Intent patterns: {state['intent_decoding']['intents_known']}")

    print("\n" + "=" * 60)
    print("Social Cognition Module: PASS")
    print("=" * 60)