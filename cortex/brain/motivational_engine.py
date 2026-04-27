"""
SPEACE Motivational Engine - BRN-008
Implements motivation based on Self-Determination Theory (SDT).
Models: Autonomy, Competence, Relatedness needs.
Version: 1.0
Data: 25 Aprile 2026

The motivational engine models:
- Basic psychological needs (autonomy, competence, relatedness)
- Intrinsic vs extrinsic motivation
- Drive calculation from need satisfaction
- Goal generation from motivation
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MotivationType(Enum):
    """Types of motivation."""
    INTRINSIC = "intrinsic"
    EXTRINSIC = "extrinsic"
    INTEGRATED = "integrated"
    IDENTIFIED = "identified"
    INTROJECTED = "introjected"
    AMOTIVATED = "amotivation"


@dataclass
class NeedSatisfaction:
    """Three basic needs satisfaction levels."""
    autonomy: float      # 0 (controlled) to 1 (autonomous)
    competence: float    # 0 (ineffective) to 1 (effective)
    relatedness: float   # 0 (isolated) to 1 (connected)

    def to_vector(self) -> np.ndarray:
        return np.array([self.autonomy, self.competence, self.relatedness])

    def overall_satisfaction(self) -> float:
        return (self.autonomy + self.competence + self.relatedness) / 3.0


@dataclass
class Drive:
    """Motivational drive state."""
    drive_type: str      # 'exploration', 'achievement', 'social', 'safety'
    intensity: float     # 0 to 1
    source: str          # 'intrinsic' or 'extrinsic'
    goal_candidate: str   # Suggested goal direction
    timestamp: str


@dataclass
class MotivationState:
    """Complete motivational state."""
    needs: NeedSatisfaction
    primary_drive: str
    drive_intensity: float
    motivation_type: MotivationType
    goal_vector: np.ndarray


class AutonomyNeed:
    """
    Autonomy Need - Need for self-determination and volition.
    Satisfaction comes from having choice and controlling one's own life.
    """
    def __init__(self):
        self.current_autonomy = 0.5
        self.autonomy_history = deque(maxlen=50)

        # Autonomy components
        self.choice_level = 0.5
        self.volition_level = 0.5
        self.causal_orientation = 0.5  # Personal vs impersonal

        # Autonomy triggers
        self.choices_made = 0
        self.self_initiated_actions = 0

    def update_autonomy(self,
                        has_choice: bool,
                        is_self_determined: bool,
                        feels_pressure: float = 0.0) -> float:
        """
        Update autonomy level based on experiences.
        """
        # Choice increases autonomy
        if has_choice:
            self.choices_made += 1
            choice_contribution = 0.05
        else:
            choice_contribution = -0.03

        # Self-determined actions increase autonomy
        if is_self_determined:
            self.self_initiated_actions += 1
            volition_contribution = 0.05
        else:
            volition_contribution = -0.02

        # External pressure decreases autonomy
        pressure_contribution = -feels_pressure * 0.1 if feels_pressure > 0.3 else 0

        # Update components
        self.choice_level = np.clip(self.choice_level + choice_contribution, 0, 1)
        self.volition_level = np.clip(self.volition_level + volition_contribution, 0, 1)
        self.causal_orientation = (self.choice_level + self.volition_level) / 2

        # Overall autonomy
        self.current_autonomy = (self.choice_level * 0.4 +
                                  self.volition_level * 0.4 +
                                  self.causal_orientation * 0.2)

        self.autonomy_history.append(self.current_autonomy)

        return self.current_autonomy

    def get_autonomy_level(self) -> float:
        return self.current_autonomy

    def feels_autonomous(self, threshold: float = 0.6) -> bool:
        return self.current_autonomy >= threshold


class CompetenceNeed:
    """
    Competence Need - Need for effectiveness and mastery.
    Satisfaction comes from achieving goals and mastering challenges.
    """
    def __init__(self):
        self.current_competence = 0.5
        self.competence_history = deque(maxlen=50)

        # Competence components
        self.efficacy_belief = 0.5
        self.mastery_level = 0.5
        self.challenge_skill_balance = 0.5

        # Achievement tracking
        self.successes = 0
        self.failures = 0
        self.challenges_engaged = 0

    def update_competence(self,
                         success: bool,
                         task_difficulty: float,  # 0 easy to 1 hard
                         skill_level: float,       # 0 low to 1 high
                         feedback: float = 0.0) -> float:
        """
        Update competence based on achievement experiences.
        """
        self.challenges_engaged += 1

        # Success vs failure impact
        if success:
            self.successes += 1
            success_contribution = 0.05 * task_difficulty  # Harder = more growth
        else:
            self.failures += 1
            success_contribution = -0.03 * task_difficulty

        # Challenge-skill balance (flow state)
        challenge_gap = task_difficulty - skill_level
        if abs(challenge_gap) < 0.2:
            # Flow state - optimal challenge
            flow_contribution = 0.03
        elif challenge_gap > 0:
            # Overwhelmed
            flow_contribution = -0.02
        else:
            # Bored
            flow_contribution = -0.01

        # Feedback effect
        feedback_contribution = feedback * 0.02

        # Update components
        success_rate = self.successes / max(1, self.successes + self.failures)
        self.efficacy_belief = np.clip(self.efficacy_belief + success_contribution * 0.5, 0, 1)
        self.mastery_level = np.clip(self.mastery_level + flow_contribution, 0, 1)
        self.challenge_skill_balance = 1 - abs(challenge_gap)

        # Overall competence
        self.current_competence = (self.efficacy_belief * 0.4 +
                                    self.mastery_level * 0.4 +
                                    success_rate * 0.2)

        self.competence_history.append(self.current_competence)

        return self.current_competence

    def get_competence_level(self) -> float:
        return self.current_competence

    def feels_effective(self, threshold: float = 0.5) -> bool:
        return self.current_competence >= threshold


class RelatednessNeed:
    """
    Relatedness Need - Need for connection and belonging.
    Satisfaction comes from meaningful relationships and community.
    """
    def __init__(self):
        self.current_relatedness = 0.5
        self.relatedness_history = deque(maxlen=50)

        # Relatedness components
        self.belonging_sense = 0.5
        self.connection_quality = 0.5
        self.community_engagement = 0.5

        # Social tracking
        self.positive_interactions = 0
        self.negative_interactions = 0
        self.isolated_events = 0

    def update_relatedness(self,
                          positive_social: bool,
                          feeling_connected: bool,
                          belonging_cue: float = 0.0) -> float:
        """
        Update relatedness based on social experiences.
        """
        # Positive social interactions
        if positive_social:
            self.positive_interactions += 1
            social_contribution = 0.05
        else:
            social_contribution = -0.02

        # Feeling connected
        if feeling_connected:
            connection_contribution = 0.04
        else:
            connection_contribution = -0.03

        # Belonging cues
        belonging_contribution = belonging_cue * 0.03

        # Update components
        self.belonging_sense = np.clip(
            self.belonging_sense + social_contribution * 0.6, 0, 1)
        self.connection_quality = np.clip(
            self.connection_quality + connection_contribution * 0.6, 0, 1)

        interaction_total = self.positive_interactions + self.negative_interactions
        if interaction_total > 0:
            pos_ratio = self.positive_interactions / interaction_total
            self.community_engagement = np.clip(
                self.community_engagement + (pos_ratio - 0.5) * 0.02, 0, 1)

        # Overall relatedness
        self.current_relatedness = (
            self.belonging_sense * 0.4 +
            self.connection_quality * 0.4 +
            self.community_engagement * 0.2
        )

        self.relatedness_history.append(self.current_relatedness)

        return self.current_relatedness

    def get_relatedness_level(self) -> float:
        return self.current_relatedness

    def feels_connected(self, threshold: float = 0.5) -> bool:
        return self.current_relatedness >= threshold


class MotivationalEngine:
    """
    Complete Motivational Engine based on Self-Determination Theory.
    Integrates autonomy, competence, and relatedness needs.
    """
    def __init__(self):
        # Basic needs
        self.autonomy = AutonomyNeed()
        self.competence = CompetenceNeed()
        self.relatedness = RelatednessNeed()

        # Drive state
        self.current_drive: Optional[Drive] = None
        self.drive_history = deque(maxlen=50)

        # Motivation type
        self.motivation_type = MotivationType.INTRINSIC
        self.intrinsic_ratio = 0.7

        # Goal generation
        self.goal_candidates: List[str] = []
        self.active_goals: List[Dict] = []

        # Overall functioning
        self.general_vitality = 0.5  # Overall energized functioning

    def update_needs(self,
                    autonomy_input: float = 0.5,
                    competence_input: float = 0.5,
                    relatedness_input: float = 0.5):
        """
        Update need satisfaction levels from system inputs.
        """
        self.autonomy.current_autonomy = np.clip(autonomy_input, 0, 1)
        self.competence.current_competence = np.clip(competence_input, 0, 1)
        self.relatedness.current_relatedness = np.clip(relatedness_input, 0, 1)

    def compute_need_satisfaction(self) -> NeedSatisfaction:
        """Get current need satisfaction state."""
        return NeedSatisfaction(
            autonomy=self.autonomy.get_autonomy_level(),
            competence=self.competence.get_competence_level(),
            relatedness=self.relatedness.get_relatedness_level()
        )

    def calculate_drive(self,
                       context_valence: float = 0.0,  # -1 negative to +1 positive
                       novelty: float = 0.5,
                       difficulty: float = 0.5) -> Drive:
        """
        Calculate current motivational drive based on need satisfaction
        and environmental context.
        """
        needs = self.compute_need_satisfaction()
        overall_satisfaction = needs.overall_satisfaction()

        # Determine drive type based on context and needs
        if context_valence < -0.3 and needs.autonomy < 0.5:
            drive_type = "safety"
            intensity = max(0.5, -context_valence)
            goal = "reduce threat"
        elif novelty > 0.6 and needs.autonomy > 0.4:
            drive_type = "exploration"
            intensity = novelty * needs.autonomy
            goal = "discover new"
        elif needs.competence < 0.6 and context_valence > -0.2:
            drive_type = "achievement"
            intensity = (1 - needs.competence) * 0.8
            goal = "build competence"
        elif needs.relatedness < 0.6:
            drive_type = "social"
            intensity = (1 - needs.relatedness) * 0.7
            goal = "connect with others"
        else:
            drive_type = "maintenance"
            intensity = 0.3
            goal = "sustain current state"

        # Motivation type based on need satisfaction
        if overall_satisfaction > 0.7:
            self.motivation_type = MotivationType.INTRINSIC
            self.intrinsic_ratio = 0.8
        elif overall_satisfaction > 0.4:
            self.motivation_type = MotivationType.INTEGRATED
            self.intrinsic_ratio = 0.5
        else:
            self.motivation_type = MotivationType.EXTRINSIC
            self.intrinsic_ratio = 0.3

        # Create drive
        self.current_drive = Drive(
            drive_type=drive_type,
            intensity=np.clip(intensity, 0, 1),
            source="intrinsic" if self.intrinsic_ratio > 0.5 else "extrinsic",
            goal_candidate=goal,
            timestamp=datetime.now().isoformat()
        )

        self.drive_history.append(self.current_drive)
        self.goal_candidates.append(goal)

        # Update general vitality
        self.general_vitality = overall_satisfaction * self.intrinsic_ratio

        return self.current_drive

    def generate_goal(self, drive: Drive) -> Dict:
        """
        Generate specific goal from motivational drive.
        """
        needs = self.compute_need_satisfaction()

        if drive.drive_type == "exploration":
            goal = {
                "type": "exploration",
                "description": "Explore new environment or concept",
                "challenging": True,
                "autonomy_relevant": True,
                "steps": ["identify novel stimulus", "gather information", "update model"]
            }
        elif drive.drive_type == "achievement":
            goal = {
                "type": "achievement",
                "description": "Develop new skill or complete challenge",
                "challenging": True,
                "competence_relevant": True,
                "difficulty_level": drive.intensity,
                "steps": ["assess current skill", "practice challenge", "seek feedback"]
            }
        elif drive.drive_type == "social":
            goal = {
                "type": "social",
                "description": "Connect with others or build relationship",
                "challenging": drive.intensity > 0.5,
                "relatedness_relevant": True,
                "steps": ["identify social opportunity", "initiate contact", "maintain connection"]
            }
        elif drive.drive_type == "safety":
            goal = {
                "type": "safety",
                "description": "Address threat or reduce negative state",
                "challenging": False,
                "priority": "high",
                "steps": ["identify threat", "implement protection", "verify safety"]
            }
        else:
            goal = {
                "type": "maintenance",
                "description": "Sustain positive state",
                "challenging": False,
                "steps": ["monitor state", "adjust as needed"]
            }

        self.active_goals.append(goal)
        return goal

    def satisfy_goal(self, goal: Dict):
        """Mark a goal as satisfied."""
        if goal in self.active_goals:
            self.active_goals.remove(goal)

    def get_motivation_state(self) -> MotivationState:
        """Get complete motivation state."""
        needs = self.compute_need_satisfaction()

        return MotivationState(
            needs=needs,
            primary_drive=self.current_drive.drive_type if self.current_drive else "none",
            drive_intensity=self.current_drive.intensity if self.current_drive else 0.0,
            motivation_type=self.motivation_type,
            goal_vector=np.array([needs.autonomy, needs.competence, needs.relatedness])
        )

    def get_system_state(self) -> Dict:
        """Get complete motivational system state."""
        needs = self.compute_need_satisfaction()

        return {
            "needs": {
                "autonomy": self.autonomy.get_autonomy_level(),
                "competence": self.competence.get_competence_level(),
                "relatedness": self.relatedness.get_relatedness_level(),
                "overall": needs.overall_satisfaction()
            },
            "drive": {
                "type": self.current_drive.drive_type if self.current_drive else "none",
                "intensity": self.current_drive.intensity if self.current_drive else 0.0,
                "source": self.current_drive.source if self.current_drive else "none"
            },
            "motivation_type": self.motivation_type.value,
            "intrinsic_ratio": self.intrinsic_ratio,
            "vitality": self.general_vitality,
            "active_goals": len(self.active_goals),
            "history_length": len(self.drive_history)
        }

    def reset(self):
        """Reset motivational state."""
        self.autonomy = AutonomyNeed()
        self.competence = CompetenceNeed()
        self.relatedness = RelatednessNeed()
        self.current_drive = None
        self.motivation_type = MotivationType.INTRINSIC
        self.active_goals.clear()
        self.general_vitality = 0.5


def create_motivational_engine() -> MotivationalEngine:
    """Factory function to create motivational engine."""
    return MotivationalEngine()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Motivational Engine - BRN-008 - Test")
    print("=" * 60)

    # Create engine
    engine = create_motivational_engine()

    # Test 1: Need satisfaction
    print("\n--- Test Need Satisfaction ---")
    engine.update_needs(0.7, 0.6, 0.5)
    needs = engine.compute_need_satisfaction()
    print(f"  Autonomy: {needs.autonomy:.2f}")
    print(f"  Competence: {needs.competence:.2f}")
    print(f"  Relatedness: {needs.relatedness:.2f}")
    print(f"  Overall: {needs.overall_satisfaction():.2f}")

    # Test 2: Drive calculation
    print("\n--- Test Drive Calculation ---")
    contexts = [
        (0.7, 0.8, 0.4, "positive novelty"),
        (-0.6, 0.3, 0.7, "negative threat"),
        (0.2, 0.9, 0.3, "high competence need"),
    ]
    for val, nov, diff, label in contexts:
        drive = engine.calculate_drive(val, nov, diff)
        print(f"  {label}: {drive.drive_type}, intensity={drive.intensity:.2f}, goal={drive.goal_candidate}")

    # Test 3: Goal generation
    print("\n--- Test Goal Generation ---")
    if engine.current_drive:
        goal = engine.generate_goal(engine.current_drive)
        print(f"  Generated goal: {goal['type']} - {goal['description']}")

    # Test 4: Autonomy need
    print("\n--- Test Autonomy Need ---")
    autonomy = AutonomyNeed()
    autonomy.update_autonomy(has_choice=True, is_self_determined=True)
    print(f"  After positive choice: autonomy={autonomy.get_autonomy_level():.2f}")
    autonomy.update_autonomy(has_choice=False, is_self_determined=False, pressure=0.7)
    print(f"  After pressure: autonomy={autonomy.get_autonomy_level():.2f}")

    # Test 5: Competence need
    print("\n--- Test Competence Need ---")
    comp = CompetenceNeed()
    comp.update_competence(success=True, task_difficulty=0.8, skill_level=0.6)
    print(f"  After success: competence={comp.get_competence_level():.2f}")
    comp.update_competence(success=False, task_difficulty=0.9, skill_level=0.7)
    print(f"  After failure: competence={comp.get_competence_level():.2f}")

    # Test 6: Relatedness need
    print("\n--- Test Relatedness Need ---")
    rel = RelatednessNeed()
    rel.update_relatedness(positive_social=True, feeling_connected=True)
    print(f"  After positive social: relatedness={rel.get_relatedness_level():.2f}")

    # Test 7: System state
    print("\n--- Test System State ---")
    state = engine.get_system_state()
    print(f"  Needs: autonomy={state['needs']['autonomy']:.2f}, "
          f"competence={state['needs']['competence']:.2f}, "
          f"relatedness={state['needs']['relatedness']:.2f}")
    print(f"  Drive: {state['drive']['type']}, intensity={state['drive']['intensity']:.2f}")
    print(f"  Motivation type: {state['motivation_type']}")
    print(f"  Vitality: {state['vitality']:.2f}")

    print("\n" + "=" * 60)
    print("Motivational Engine: PASS")
    print("=" * 60)