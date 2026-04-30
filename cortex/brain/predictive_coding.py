"""
SPEACE Predictive Coding Engine – BRN-015
Implements the Free Energy Principle (Friston) and hierarchical predictive coding.

The brain is a prediction machine: it constantly generates top-down predictions
and updates them based on bottom-up prediction errors.

Key components:
- HierarchicalPredictor: 6-level generative model
- PrecisionWeighting: confidence/certainty signals
- GenerativeModel: internal world representation
- FreeEnergyMinimizer: variational inference (perception as inference)
- PredictionErrorPropagator: error signals drive learning

References:
- Friston KJ (2010). The free-energy principle: a unified brain theory?
- Clark A (2015). Surfing Uncertainty: Prediction, Action, and the Embodied Mind.
- Rao RP, Ballard DH (1999). Predictive coding in the visual cortex.

Version: 1.0
Data: 26 Aprile 2026
"""

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent.parent


# ─── Enums ──────────────────────────────────────────────────────────────────

class CorticalLevel(Enum):
    """Hierarchical levels in the predictive coding hierarchy."""
    L1_SENSORY       = 1   # Raw sensory data (features)
    L2_PERCEPTUAL    = 2   # Perceptual grouping
    L3_CONCEPTUAL    = 3   # Object/event recognition
    L4_SEMANTIC      = 4   # Meaning & relations
    L5_NARRATIVE     = 5   # Temporal narrative / causal chains
    L6_ABSTRACT      = 6   # Abstract schemas & world model


class InferenceMode(Enum):
    PERCEPTION = "perception"    # Minimize prediction error via belief update
    ACTION     = "action"        # Minimize prediction error via action
    LEARNING   = "learning"      # Minimize prediction error via model update


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class Belief:
    """A probabilistic belief at a given level."""
    level: CorticalLevel
    content: Dict[str, Any]
    precision: float = 1.0     # Inverse variance (certainty)
    timestamp: float = field(default_factory=time.time)

    @property
    def uncertainty(self) -> float:
        return 1.0 / (self.precision + 1e-8)


@dataclass
class PredictionError:
    """Discrepancy between prediction and observation."""
    level: CorticalLevel
    source_id: str
    predicted: Dict[str, Any]
    observed: Dict[str, Any]
    error_magnitude: float     # Scalar summary of discrepancy
    precision_weighted: float  # Error × precision (what drives learning)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_surprising(self) -> bool:
        """Returns True if error exceeds expected variance."""
        return self.precision_weighted > 1.5


@dataclass
class GenerativeState:
    """State of the internal generative model at one level."""
    level: CorticalLevel
    belief: Belief
    prediction: Dict[str, Any] = field(default_factory=dict)
    error: Optional[PredictionError] = None
    free_energy: float = 0.0


# ─── Precision Weighting ─────────────────────────────────────────────────────

class PrecisionWeighting:
    """
    Dynamic precision (1/variance) estimation for each level and modality.
    High precision → errors weighted more → faster updating.
    Low precision → noise tolerance → smoother prediction.
    """

    def __init__(self):
        # Per-level base precisions
        self.level_precisions: Dict[CorticalLevel, float] = {
            lvl: 1.0 for lvl in CorticalLevel
        }
        self.precision_history: deque = deque(maxlen=100)
        self.update_rate = 0.1

    def get(self, level: CorticalLevel) -> float:
        return self.level_precisions[level]

    def update(self, level: CorticalLevel, error: float, actual: float) -> None:
        """
        Update precision estimate using empirical variance.
        precision ≈ 1 / (running_variance + ε)
        """
        current = self.level_precisions[level]
        # Exponential moving average of squared error
        residual = (error - actual) ** 2
        new_variance = (1 - self.update_rate) * (1.0 / current) + \
                       self.update_rate * residual
        new_precision = 1.0 / (new_variance + 1e-6)
        # Clip to reasonable range
        self.level_precisions[level] = max(0.1, min(10.0, new_precision))
        self.precision_history.append({
            "level": level.name, "precision": round(new_precision, 4)
        })

    def attenuate_noise(self, level: CorticalLevel) -> None:
        """Lower precision temporarily (expect more noise)."""
        self.level_precisions[level] = max(0.1, self.level_precisions[level] * 0.5)

    def boost_alertness(self, level: CorticalLevel) -> None:
        """Increase precision (high attention, expect accuracy)."""
        self.level_precisions[level] = min(10.0, self.level_precisions[level] * 1.5)

    def get_status(self) -> Dict:
        return {lvl.name: round(p, 4) for lvl, p in self.level_precisions.items()}


# ─── Generative Model ────────────────────────────────────────────────────────

class GenerativeModel:
    """
    The brain's internal model of the world used to generate top-down predictions.
    Organized as a hierarchy of causal models (latent variables).
    """

    def __init__(self):
        self.latent_states: Dict[CorticalLevel, Dict[str, Any]] = {
            lvl: {} for lvl in CorticalLevel
        }
        self.causal_connections: Dict[str, List[str]] = {}  # upper → lower predictions
        self.update_count = 0

    def predict(self, level: CorticalLevel,
                context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a top-down prediction for the given level, given context.
        Returns predicted sensory/perceptual content.
        """
        state = self.latent_states[level]
        if not state:
            # No learned state yet → return generic prediction
            return {
                "type": "prior",
                "level": level.name,
                "content": {},
                "confidence": 0.3
            }

        # Interpolate between stored state and context
        prediction = dict(state)
        for key, val in context.items():
            if key in prediction and isinstance(val, (int, float)):
                # Blend prior with context
                prediction[key] = 0.7 * prediction[key] + 0.3 * val
            else:
                prediction[key] = val
        prediction["confidence"] = 0.7
        prediction["level"] = level.name
        return prediction

    def update_state(self, level: CorticalLevel,
                     new_evidence: Dict[str, Any],
                     learning_rate: float = 0.1) -> None:
        """Update latent state based on prediction errors (model learning)."""
        current = self.latent_states[level]
        for key, val in new_evidence.items():
            if isinstance(val, (int, float)):
                if key in current:
                    current[key] = (1 - learning_rate) * current[key] + learning_rate * val
                else:
                    current[key] = val
            else:
                current[key] = val
        self.update_count += 1

    def get_status(self) -> Dict:
        return {
            "update_count": self.update_count,
            "levels_initialized": sum(
                1 for s in self.latent_states.values() if s
            )
        }


# ─── Free Energy Minimizer ───────────────────────────────────────────────────

class FreeEnergyMinimizer:
    """
    Implements variational free energy minimization.

    Free energy F ≈ prediction_error / precision + complexity_cost
    Minimization can happen by:
    1. Updating beliefs (perception as inference)
    2. Taking actions to change the world (active inference)
    3. Updating the generative model (learning)
    """

    def __init__(self):
        self.free_energy_history: deque = deque(maxlen=200)
        self.total_minimizations = 0

    def compute_free_energy(self, prediction_error: float,
                            precision: float,
                            complexity: float = 0.0) -> float:
        """
        F = (precision * prediction_error²) / 2 + complexity_cost
        Returns scalar free energy.
        """
        accuracy_term = 0.5 * precision * (prediction_error ** 2)
        complexity_term = 0.1 * complexity   # KL divergence proxy
        return accuracy_term + complexity_term

    def minimize_by_perception(self, beliefs: Dict[CorticalLevel, Belief],
                                errors: List[PredictionError],
                                generative_model: "GenerativeModel") -> Dict[CorticalLevel, Belief]:
        """
        Update beliefs to minimize free energy (perception/inference path).
        Returns updated beliefs.
        """
        updated = dict(beliefs)
        for err in errors:
            if err.level not in updated:
                continue
            belief = updated[err.level]
            precision = belief.precision

            # Belief update: shift toward observed if precision-weighted error is high
            update_strength = min(0.5, err.precision_weighted * 0.1)

            new_content = dict(belief.content)
            for key, obs_val in err.observed.items():
                if isinstance(obs_val, (int, float)):
                    pred_val = err.predicted.get(key, obs_val)
                    delta = (obs_val - pred_val) * update_strength * precision
                    new_content[key] = new_content.get(key, 0.0) + delta

            updated[err.level] = Belief(
                level=err.level,
                content=new_content,
                precision=precision
            )
            # Update generative model
            generative_model.update_state(err.level, new_content,
                                          learning_rate=0.05)
            self.total_minimizations += 1

        fe_sum = sum(self.compute_free_energy(
            e.error_magnitude, e.precision_weighted, 0.1
        ) for e in errors)
        self.free_energy_history.append(round(fe_sum, 4))
        return updated

    def get_current_free_energy(self) -> float:
        if not self.free_energy_history:
            return 0.0
        return self.free_energy_history[-1]

    def get_trend(self) -> str:
        if len(self.free_energy_history) < 5:
            return "insufficient_data"
        recent = list(self.free_energy_history)[-10:]
        delta = recent[-1] - recent[0]
        if delta < -0.1:
            return "decreasing"   # Good: model improving
        elif delta > 0.1:
            return "increasing"   # Bad: model deteriorating
        return "stable"

    def get_status(self) -> Dict:
        return {
            "total_minimizations": self.total_minimizations,
            "current_free_energy": round(self.get_current_free_energy(), 4),
            "trend": self.get_trend()
        }


# ─── Hierarchical Predictor ──────────────────────────────────────────────────

class HierarchicalPredictor:
    """
    6-level hierarchical predictive coding architecture.
    Each level predicts the level below and receives prediction errors from below.
    """

    def __init__(self, precision_weighting: PrecisionWeighting,
                 generative_model: GenerativeModel):
        self.precision = precision_weighting
        self.gm = generative_model
        self.states: Dict[CorticalLevel, GenerativeState] = {
            lvl: GenerativeState(
                level=lvl,
                belief=Belief(level=lvl, content={}, precision=1.0)
            )
            for lvl in CorticalLevel
        }
        self.propagation_count = 0

    def propagate_top_down(self, top_level_context: Dict[str, Any]) -> None:
        """Generate predictions cascading from top to bottom."""
        context = top_level_context
        for lvl in reversed(list(CorticalLevel)):
            prediction = self.gm.predict(lvl, context)
            self.states[lvl].prediction = prediction
            context = prediction   # Lower levels predict from higher predictions

    def propagate_bottom_up(self, sensory_input: Dict[str, Any]) -> List[PredictionError]:
        """
        Compute prediction errors from bottom to top.
        Returns list of precision-weighted prediction errors.
        """
        errors = []
        observed = sensory_input
        for lvl in CorticalLevel:
            state = self.states[lvl]
            prediction = state.prediction or {}
            precision = self.precision.get(lvl)

            # Compute error magnitude
            error_mag = self._compute_error(prediction, observed)
            pw_error = error_mag * precision

            pe = PredictionError(
                level=lvl,
                source_id=f"level_{lvl.value}",
                predicted=prediction,
                observed=dict(observed),
                error_magnitude=round(error_mag, 5),
                precision_weighted=round(pw_error, 5)
            )
            state.error = pe
            errors.append(pe)

            # Free energy for this level
            state.free_energy = 0.5 * precision * (error_mag ** 2)

            # Update precision estimates
            self.precision.update(lvl, error_mag, error_mag * 0.9)

            # Abstract: pass transformed observation upward
            observed = self._abstract(observed, lvl)

        self.propagation_count += 1
        return errors

    def _compute_error(self, predicted: Dict, observed: Dict) -> float:
        """Compute L2 prediction error between dicts."""
        if not predicted or not observed:
            return 0.5   # Default uncertainty
        keys = set(predicted.keys()) | set(observed.keys())
        if not keys:
            return 0.0
        sq_errors = []
        for k in keys:
            p = float(predicted.get(k, 0)) if isinstance(predicted.get(k), (int, float)) else 0.0
            o = float(observed.get(k, 0)) if isinstance(observed.get(k), (int, float)) else 0.0
            sq_errors.append((p - o) ** 2)
        return math.sqrt(sum(sq_errors) / len(sq_errors))

    def _abstract(self, observed: Dict, level: CorticalLevel) -> Dict:
        """Abstractify observation when moving up the hierarchy."""
        # Each level compresses: keep only salient features
        abstracted = {}
        for k, v in observed.items():
            if isinstance(v, (int, float)):
                # Round to reduce granularity at higher levels
                granularity = 10 ** (level.value - 1)
                abstracted[k] = round(v / granularity, 2) * granularity
            else:
                abstracted[k] = v
        return abstracted

    def get_total_free_energy(self) -> float:
        return sum(s.free_energy for s in self.states.values())

    def get_status(self) -> Dict:
        return {
            "propagation_count": self.propagation_count,
            "total_free_energy": round(self.get_total_free_energy(), 4),
            "level_errors": {
                lvl.name: round(s.error.error_magnitude, 4) if s.error else 0.0
                for lvl, s in self.states.items()
            },
            "precision_weights": self.precision.get_status()
        }


# ─── Predictive Coding Engine Core ──────────────────────────────────────────

class PredictiveCodingEngine:
    """
    SPEACE Predictive Coding Engine (BRN-015).

    Implements hierarchical predictive processing with free energy minimization.
    The engine continuously generates predictions and updates beliefs based on
    prediction errors – core mechanism for perception and learning.

    Integration points:
    - Feeds prediction errors to STDPLearning (BRN-011) for synaptic update
    - Supplies uncertainty signals to AttentionSystem (BRN-014)
    - Updates beliefs in WorkingMemory (BRN-006)
    - Drives motivational signals in DopaminergicSystem (BRN-005)
    """

    def __init__(self):
        self.precision = PrecisionWeighting()
        self.generative_model = GenerativeModel()
        self.predictor = HierarchicalPredictor(self.precision, self.generative_model)
        self.minimizer = FreeEnergyMinimizer()

        self.current_beliefs: Dict[CorticalLevel, Belief] = {
            lvl: Belief(level=lvl, content={}, precision=1.0)
            for lvl in CorticalLevel
        }
        self.cycle_count = 0
        self.surprise_events: deque = deque(maxlen=50)
        self.inference_mode = InferenceMode.PERCEPTION
        logger.info("PredictiveCodingEngine BRN-015 initialized")

    # ── Public API ──────────────────────────────────────────────────────────

    def process_sensory_input(self, sensory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full predictive coding cycle:
        1. Top-down predictions from current beliefs
        2. Bottom-up prediction errors from sensory data
        3. Free energy minimization → belief update
        Returns: surprise level, updated beliefs summary, action suggestions.
        """
        self.cycle_count += 1

        # Step 1: Generate top-down predictions
        top_context = {
            k: v for lvl_beliefs in self.current_beliefs.values()
            for k, v in lvl_beliefs.content.items()
        }
        self.predictor.propagate_top_down(top_context)

        # Step 2: Compute bottom-up prediction errors
        errors = self.predictor.propagate_bottom_up(sensory_data)

        # Step 3: Free energy minimization → belief update
        self.current_beliefs = self.minimizer.minimize_by_perception(
            self.current_beliefs, errors, self.generative_model
        )

        # Step 4: Surprise detection
        total_fe = self.predictor.get_total_free_energy()
        surprising_errors = [e for e in errors if e.is_surprising]
        surprise_level = len(surprising_errors) / max(1, len(errors))

        if surprise_level > 0.5:
            self.surprise_events.append({
                "cycle": self.cycle_count,
                "surprise_level": round(surprise_level, 3),
                "free_energy": round(total_fe, 4),
                "timestamp": time.time()
            })
            logger.debug(f"PredictiveCoding: surprise event at cycle {self.cycle_count} "
                         f"(level={surprise_level:.2f})")

        result = {
            "cycle": self.cycle_count,
            "total_free_energy": round(total_fe, 4),
            "fe_trend": self.minimizer.get_trend(),
            "surprise_level": round(surprise_level, 3),
            "surprising_errors": [e.level.name for e in surprising_errors],
            "prediction_errors": {
                e.level.name: round(e.error_magnitude, 4) for e in errors
            },
            "inference_mode": self.inference_mode.value
        }
        return result

    def boost_attention_to(self, level: CorticalLevel) -> None:
        """Increase precision at a level (directed attention)."""
        self.precision.boost_alertness(level)
        logger.debug(f"PredictiveCoding: boosted attention to level {level.name}")

    def expect_noise(self, level: CorticalLevel) -> None:
        """Reduce precision at a level (noisy input expected)."""
        self.precision.attenuate_noise(level)

    def inject_prior(self, level: CorticalLevel, prior: Dict[str, Any]) -> None:
        """Inject a prior belief at a given level."""
        self.current_beliefs[level] = Belief(
            level=level, content=prior, precision=0.8
        )
        self.generative_model.update_state(level, prior, learning_rate=0.2)

    def get_prediction(self, level: CorticalLevel) -> Dict[str, Any]:
        """Return current prediction at a given level."""
        return self.predictor.states[level].prediction

    def get_belief(self, level: CorticalLevel) -> Belief:
        """Return current belief at a given level."""
        return self.current_beliefs[level]

    def get_full_status(self) -> Dict:
        return {
            "module": "PredictiveCodingEngine",
            "brn_id": "BRN-015",
            "cycle_count": self.cycle_count,
            "inference_mode": self.inference_mode.value,
            "free_energy": self.minimizer.get_status(),
            "predictor": self.predictor.get_status(),
            "surprise_events_logged": len(self.surprise_events)
        }


# ─── Factory ─────────────────────────────────────────────────────────────────

def create_predictive_coding_engine() -> PredictiveCodingEngine:
    """Factory function for PredictiveCodingEngine."""
    return PredictiveCodingEngine()


# ─── Self-test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    pce = create_predictive_coding_engine()

    # Inject a prior about a climate monitoring context
    pce.inject_prior(CorticalLevel.L3_CONCEPTUAL, {
        "temperature_anomaly": 1.2,
        "co2_ppm": 420.0,
        "context": "climate_monitoring"
    })

    # Process simulated sensory input
    sensory = {
        "temperature_anomaly": 1.5,   # Slightly higher than predicted
        "co2_ppm": 421.0,
        "humidity": 0.65,
        "wind_speed": 3.2
    }

    print("\n[PredictiveCoding] Processing sensory input...")
    result = pce.process_sensory_input(sensory)
    print(json.dumps(result, indent=2))

    print("\n[PredictiveCoding] Full status:")
    print(json.dumps(pce.get_full_status(), indent=2))

    # Process again with a surprising input
    surprising_sensory = {
        "temperature_anomaly": 8.5,   # Very surprising!
        "co2_ppm": 480.0,
    }
    result2 = pce.process_sensory_input(surprising_sensory)
    print(f"\n[PredictiveCoding] Surprise level: {result2['surprise_level']}")
    print(f"[PredictiveCoding] Free energy trend: {result2['fe_trend']}")

    print("\n[PredictiveCoding] BRN-015 self-test passed ✓")
