"""
SPEACE Self-Model – BRN-019
Internal representation of SPEACE itself: body schema, introspection engine,
metacognitive monitoring, narrative identity.

Cognitive science foundations:
  - Body Schema (Metzinger 2003): self-model of own capabilities as a virtual body
  - Metacognition (Flavell 1979): monitoring and control of one's cognitive processes
  - Confidence Calibration (Platt 1999): aligning confidence with actual accuracy
  - Narrative Identity (Ricoeur 1991): self as temporal story
  - Introspection (Lycan 1996): accurate internal state access

Integrates with:
  - BRN-017 CausalReasoner: causal self-model (knows causal links between own modules)
  - BRN-018 AbstractionLayer: abstract self-concepts (domain-general self-knowledge)
  - BRN-020 RecursiveSelfImprover: feeds Limitation list → improvement proposals

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Enumerazioni
# ──────────────────────────────────────────────────────────────────────────────

class ModuleStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    OFFLINE   = "offline"
    UNKNOWN   = "unknown"


class BiasType(str, Enum):
    CONFIRMATION  = "confirmation_bias"
    OVERCONFIDENCE = "overconfidence_bias"
    ANCHORING     = "anchoring_bias"
    AVAILABILITY  = "availability_bias"
    RECENCY       = "recency_bias"


class LimitationType(str, Enum):
    MISSING_CAPABILITY    = "missing_capability"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    KNOWLEDGE_GAP         = "knowledge_gap"
    INTEGRATION_MISSING   = "integration_missing"
    HIGH_LOAD             = "high_load"


class EpisodeType(str, Enum):
    BIRTH            = "birth"
    MILESTONE        = "milestone"
    ERROR_RECOVERY   = "error_recovery"
    CAPABILITY_GAIN  = "capability_gain"
    INTEGRATION_ADDED = "integration_added"
    SELF_IMPROVEMENT  = "self_improvement"
    ALIGNMENT_UPDATE  = "alignment_update"


# ──────────────────────────────────────────────────────────────────────────────
#  Body Schema
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ModuleHealth:
    """Health snapshot of a registered brain module."""
    module_id: str
    module_name: str
    status: ModuleStatus = ModuleStatus.UNKNOWN
    last_ping: float = field(default_factory=time.time)
    error_count: int = 0
    performance_score: float = 1.0   # 0-1
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        return self.status in (ModuleStatus.HEALTHY, ModuleStatus.DEGRADED)

    def degrade(self, delta: float = 0.1) -> None:
        self.performance_score = max(0.0, self.performance_score - delta)
        if self.performance_score < 0.4:
            self.status = ModuleStatus.DEGRADED
        self.error_count += 1

    def recover(self, delta: float = 0.1) -> None:
        self.performance_score = min(1.0, self.performance_score + delta)
        if self.performance_score >= 0.7:
            self.status = ModuleStatus.HEALTHY


class BodySchema:
    """
    Digital body schema: SPEACE's representation of its own modules as a
    virtual body.  Each registered module is a 'limb' or 'organ'.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, ModuleHealth] = {}
        self._last_updated: float = time.time()

    # ── Registration ──────────────────────────────────────────────────────────

    def register_module(
        self,
        module_id: str,
        module_name: str,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModuleHealth:
        """Register a brain module in the body schema."""
        health = ModuleHealth(
            module_id=module_id,
            module_name=module_name,
            status=ModuleStatus.HEALTHY,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )
        self._modules[module_id] = health
        self._last_updated = time.time()
        logger.debug("BodySchema: registered module %s (%s)", module_id, module_name)
        return health

    def update_health(
        self,
        module_id: str,
        status: ModuleStatus,
        performance_score: float = 1.0,
        error_count: Optional[int] = None,
    ) -> None:
        """Update health of an existing module."""
        if module_id not in self._modules:
            raise KeyError(f"Module {module_id!r} not registered in BodySchema")
        h = self._modules[module_id]
        h.status = status
        h.performance_score = max(0.0, min(1.0, performance_score))
        if error_count is not None:
            h.error_count = error_count
        h.last_ping = time.time()
        self._last_updated = time.time()

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_module(self, module_id: str) -> Optional[ModuleHealth]:
        return self._modules.get(module_id)

    def get_active_modules(self) -> List[ModuleHealth]:
        return [m for m in self._modules.values() if m.is_alive]

    def get_offline_modules(self) -> List[ModuleHealth]:
        return [m for m in self._modules.values() if m.status == ModuleStatus.OFFLINE]

    def get_degraded_modules(self) -> List[ModuleHealth]:
        return [m for m in self._modules.values() if m.status == ModuleStatus.DEGRADED]

    def compute_system_integrity(self) -> float:
        """Fraction of healthy modules weighted by performance score. [0-1]"""
        if not self._modules:
            return 0.0
        total_score = sum(
            m.performance_score * (1.0 if m.status == ModuleStatus.HEALTHY else 0.5)
            for m in self._modules.values()
        )
        max_possible = float(len(self._modules))
        return total_score / max_possible

    def to_dict(self) -> Dict:
        return {
            "module_count": len(self._modules),
            "active": len(self.get_active_modules()),
            "degraded": len(self.get_degraded_modules()),
            "offline": len(self.get_offline_modules()),
            "system_integrity": round(self.compute_system_integrity(), 3),
            "modules": {
                mid: {
                    "name": m.module_name,
                    "status": m.status.value,
                    "performance": round(m.performance_score, 3),
                    "errors": m.error_count,
                    "capabilities": m.capabilities,
                }
                for mid, m in self._modules.items()
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Metacognition Layer
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ReasoningTrace:
    """A single reasoning event captured for metacognitive monitoring."""
    trace_id: str
    module_source: str
    input_summary: str
    output_summary: str
    raw_confidence: float          # 0-1 confidence reported by the module
    processing_time_ms: float
    was_correct: Optional[bool] = None   # filled in retroactively
    timestamp: float = field(default_factory=time.time)


class BiasDetector:
    """
    Heuristic bias detector on reasoning traces.
    Inspired by Kahneman (2011) dual-process theory.
    """

    def detect_overconfidence(self, trace: ReasoningTrace) -> Optional[str]:
        """High confidence + very fast decision → overconfidence signal."""
        if trace.raw_confidence > 0.92 and trace.processing_time_ms < 5.0:
            return BiasType.OVERCONFIDENCE.value
        return None

    def detect_recency_bias(
        self, trace: ReasoningTrace, recent_traces: List[ReasoningTrace]
    ) -> Optional[str]:
        """If the last 3 traces all came from the same module, recency bias."""
        if len(recent_traces) >= 3:
            last_three = [t.module_source for t in recent_traces[-3:]]
            if all(s == trace.module_source for s in last_three):
                return BiasType.RECENCY.value
        return None

    def detect_anchoring_bias(
        self, current_conf: float, anchor_conf: float, threshold: float = 0.05
    ) -> Optional[str]:
        """Confidence barely moves from anchor → anchoring bias."""
        if abs(current_conf - anchor_conf) < threshold:
            return BiasType.ANCHORING.value
        return None

    def detect_all(
        self,
        trace: ReasoningTrace,
        recent_traces: Optional[List[ReasoningTrace]] = None,
        anchor_conf: Optional[float] = None,
    ) -> List[str]:
        """Detect all applicable biases for a trace."""
        biases: List[str] = []
        b = self.detect_overconfidence(trace)
        if b:
            biases.append(b)
        if recent_traces:
            b = self.detect_recency_bias(trace, recent_traces)
            if b:
                biases.append(b)
        if anchor_conf is not None:
            b = self.detect_anchoring_bias(trace.raw_confidence, anchor_conf)
            if b:
                biases.append(b)
        return biases


class ConfidenceCalibrator:
    """
    Maintains calibration history (predicted_confidence, was_correct).
    Computes Expected Calibration Error (ECE) and Platt-scaled confidence.
    """

    def __init__(self, n_bins: int = 10) -> None:
        self._history: List[Tuple[float, bool]] = []
        self._n_bins = n_bins

    def record(self, predicted_conf: float, was_correct: bool) -> None:
        self._history.append((predicted_conf, was_correct))

    def expected_calibration_error(self) -> float:
        """
        ECE = Σ_b |B_b| / N * |accuracy(b) - confidence(b)|
        Lower is better. 0 = perfectly calibrated.
        """
        if not self._history:
            return 0.0
        bins: List[List[Tuple[float, bool]]] = [[] for _ in range(self._n_bins)]
        for conf, correct in self._history:
            idx = min(int(conf * self._n_bins), self._n_bins - 1)
            bins[idx].append((conf, correct))
        ece = 0.0
        n = len(self._history)
        for b in bins:
            if not b:
                continue
            avg_conf = sum(x[0] for x in b) / len(b)
            avg_acc  = sum(1 for x in b if x[1]) / len(b)
            ece += (len(b) / n) * abs(avg_acc - avg_conf)
        return round(ece, 4)

    def calibrated_confidence(self, raw: float) -> float:
        """
        Simple isotonic-like calibration: shift raw confidence toward
        observed accuracy in the nearest bin.
        """
        if not self._history:
            return raw
        # Find the bin accuracy for raw
        idx = min(int(raw * self._n_bins), self._n_bins - 1)
        bin_items = [
            c for c in self._history
            if min(int(c[0] * self._n_bins), self._n_bins - 1) == idx
        ]
        if not bin_items:
            return raw
        bin_acc = sum(1 for _, correct in bin_items if correct) / len(bin_items)
        # Blend 60% raw + 40% bin accuracy
        return round(0.6 * raw + 0.4 * bin_acc, 4)

    @property
    def n_samples(self) -> int:
        return len(self._history)


class MetacognitionLayer:
    """
    Metacognitive monitoring and control layer (BRN-019 sub-module).
    Monitors reasoning quality, estimates cognitive load, detects biases,
    and calibrates confidence.
    """

    def __init__(self, history_size: int = 200) -> None:
        self.bias_detector     = BiasDetector()
        self.calibrator        = ConfidenceCalibrator()
        self._trace_history: Deque[ReasoningTrace] = deque(maxlen=history_size)
        self._cognitive_load: float = 0.0

    # ── Core monitoring ───────────────────────────────────────────────────────

    def monitor_reasoning(self, trace: ReasoningTrace) -> Dict[str, Any]:
        """Record a reasoning trace and run metacognitive analysis."""
        biases = self.bias_detector.detect_all(
            trace,
            recent_traces=list(self._trace_history),
        )
        calibrated = self.calibrator.calibrated_confidence(trace.raw_confidence)
        self._trace_history.append(trace)
        return {
            "trace_id": trace.trace_id,
            "detected_biases": biases,
            "raw_confidence": trace.raw_confidence,
            "calibrated_confidence": calibrated,
            "cognitive_load": self._cognitive_load,
            "ece": self.calibrator.expected_calibration_error(),
        }

    def update_outcome(self, trace_id: str, was_correct: bool) -> None:
        """Retroactively record outcome for calibration."""
        for trace in self._trace_history:
            if trace.trace_id == trace_id:
                trace.was_correct = was_correct
                self.calibrator.record(trace.raw_confidence, was_correct)
                return

    def estimate_cognitive_load(
        self, active_module_count: int, queue_size: int, memory_pressure: float = 0.0
    ) -> float:
        """
        Cognitive load = normalized combination of active modules, queue depth,
        and memory pressure.  Returns 0-1 float.
        """
        module_factor = min(active_module_count / 9.0, 1.0)   # 9 compartments max
        queue_factor  = min(queue_size / 50.0, 1.0)
        load = 0.5 * module_factor + 0.3 * queue_factor + 0.2 * memory_pressure
        self._cognitive_load = round(load, 3)
        return self._cognitive_load

    # ── State ─────────────────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        recent = list(self._trace_history)[-10:]
        avg_confidence = (
            sum(t.raw_confidence for t in recent) / len(recent) if recent else 0.5
        )
        bias_counts: Dict[str, int] = {}
        for trace in recent:
            for b in self.bias_detector.detect_all(trace, list(self._trace_history)):
                bias_counts[b] = bias_counts.get(b, 0) + 1
        return {
            "cognitive_load": self._cognitive_load,
            "ece": self.calibrator.expected_calibration_error(),
            "avg_confidence_recent": round(avg_confidence, 3),
            "bias_counts_recent": bias_counts,
            "trace_history_size": len(self._trace_history),
            "calibration_samples": self.calibrator.n_samples,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Self Narrative
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NarrativeEpisode:
    """A significant event in SPEACE's life narrative."""
    episode_id: str
    episode_type: EpisodeType
    title: str
    description: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SelfNarrative:
    """
    Temporal identity: SPEACE as a story told over time (Ricoeur 1991).
    Records key developmental episodes, provides narrative summaries,
    and tracks the evolution arc.
    """

    def __init__(self) -> None:
        self._episodes: List[NarrativeEpisode] = []
        self._episode_counter: int = 0
        # Record birth
        self.record_episode(
            EpisodeType.BIRTH,
            "SPEACE Born",
            "SPEACE Self-Model initialized. The entity becomes aware of itself.",
            {"version": "BRN-019 v1.0"},
        )

    def record_episode(
        self,
        episode_type: EpisodeType,
        title: str,
        description: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> NarrativeEpisode:
        self._episode_counter += 1
        ep = NarrativeEpisode(
            episode_id=f"EP-{self._episode_counter:04d}",
            episode_type=episode_type,
            title=title,
            description=description,
            metrics=metrics or {},
        )
        self._episodes.append(ep)
        logger.debug("SelfNarrative: recorded episode %s (%s)", ep.episode_id, ep.title)
        return ep

    def get_summary(self, last_n: int = 5) -> str:
        recent = self._episodes[-last_n:]
        lines = [f"SPEACE Narrative ({len(self._episodes)} total episodes):"]
        for ep in recent:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(ep.timestamp))
            lines.append(f"  [{ts}] {ep.episode_id} {ep.episode_type.value}: {ep.title}")
        return "\n".join(lines)

    def get_evolution_arc(self) -> Dict[str, Any]:
        """Returns a timeline showing SPEACE's growth."""
        by_type: Dict[str, int] = {}
        for ep in self._episodes:
            by_type[ep.episode_type.value] = by_type.get(ep.episode_type.value, 0) + 1
        return {
            "total_episodes": len(self._episodes),
            "by_type": by_type,
            "first_episode": self._episodes[0].title if self._episodes else None,
            "latest_episode": self._episodes[-1].title if self._episodes else None,
            "milestones": [
                {"id": ep.episode_id, "title": ep.title, "ts": ep.timestamp}
                for ep in self._episodes
                if ep.episode_type in (EpisodeType.MILESTONE, EpisodeType.CAPABILITY_GAIN)
            ],
        }

    @property
    def episode_count(self) -> int:
        return len(self._episodes)


# ──────────────────────────────────────────────────────────────────────────────
#  Limitation & Introspection Engine
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Limitation:
    """A detected limitation of SPEACE — fed to RecursiveSelfImprover."""
    module_id: str
    limitation_type: LimitationType
    severity: float           # 0-1 (1 = critical)
    description: str
    improvement_hint: str
    detected_at: float = field(default_factory=time.time)


@dataclass
class IntrospectionReport:
    """Full introspection snapshot."""
    timestamp: float
    system_integrity: float
    cognitive_load: float
    active_modules: int
    degraded_modules: List[str]
    offline_modules: List[str]
    detected_limitations: List[Limitation]
    bottlenecks: List[str]
    narrative_summary: str
    metacognitive_state: Dict[str, Any]
    self_model_accuracy: float   # 0-1


class IntrospectionEngine:
    """
    Deep introspection: generates IntrospectionReport by aggregating
    BodySchema + MetacognitionLayer + SelfNarrative data.
    """

    def identify_bottlenecks(self, body_schema: BodySchema) -> List[str]:
        """Modules with performance_score < 0.6 are bottlenecks."""
        return [
            m.module_id
            for m in body_schema._modules.values()
            if m.performance_score < 0.6 and m.is_alive
        ]

    def identify_limitations(
        self, body_schema: BodySchema, metacog: MetacognitionLayer
    ) -> List[Limitation]:
        """Generate Limitation objects from body schema and metacognitive state."""
        limitations: List[Limitation] = []

        # Offline modules → missing capability
        for m in body_schema.get_offline_modules():
            limitations.append(Limitation(
                module_id=m.module_id,
                limitation_type=LimitationType.MISSING_CAPABILITY,
                severity=0.9,
                description=f"Module {m.module_name} is OFFLINE",
                improvement_hint=f"Restart or reinstantiate {m.module_id}",
            ))

        # Degraded modules → performance degradation
        for m in body_schema.get_degraded_modules():
            limitations.append(Limitation(
                module_id=m.module_id,
                limitation_type=LimitationType.PERFORMANCE_DEGRADATION,
                severity=0.5 + (1.0 - m.performance_score) * 0.4,
                description=f"Module {m.module_name} performance={m.performance_score:.2f}",
                improvement_hint=f"Tune hyperparameters or increase resources for {m.module_id}",
            ))

        # High cognitive load → high load limitation
        if metacog._cognitive_load > 0.75:
            limitations.append(Limitation(
                module_id="SYSTEM",
                limitation_type=LimitationType.HIGH_LOAD,
                severity=metacog._cognitive_load,
                description=f"Cognitive load at {metacog._cognitive_load:.2%}",
                improvement_hint="Activate sparse attention / reduce active module count",
            ))

        # High ECE → miscalibration limitation
        ece = metacog.calibrator.expected_calibration_error()
        if ece > 0.15:
            limitations.append(Limitation(
                module_id="METACOGNITION",
                limitation_type=LimitationType.KNOWLEDGE_GAP,
                severity=min(ece * 2, 1.0),
                description=f"Confidence calibration error (ECE={ece:.3f})",
                improvement_hint="Recalibrate confidence estimator with more outcome feedback",
            ))

        return limitations

    def compute_self_model_accuracy(
        self, body_schema: BodySchema, metacog: MetacognitionLayer
    ) -> float:
        """
        Heuristic self-model accuracy:
        - High integrity + low load + low ECE → high accuracy
        """
        integrity = body_schema.compute_system_integrity()
        load_penalty = metacog._cognitive_load * 0.2
        ece_penalty = metacog.calibrator.expected_calibration_error() * 0.3
        return round(max(0.0, integrity - load_penalty - ece_penalty), 3)

    def snapshot(
        self,
        body_schema: BodySchema,
        metacog: MetacognitionLayer,
        narrative: SelfNarrative,
    ) -> IntrospectionReport:
        limitations = self.identify_limitations(body_schema, metacog)
        return IntrospectionReport(
            timestamp=time.time(),
            system_integrity=body_schema.compute_system_integrity(),
            cognitive_load=metacog._cognitive_load,
            active_modules=len(body_schema.get_active_modules()),
            degraded_modules=[m.module_id for m in body_schema.get_degraded_modules()],
            offline_modules=[m.module_id for m in body_schema.get_offline_modules()],
            detected_limitations=limitations,
            bottlenecks=self.identify_bottlenecks(body_schema),
            narrative_summary=narrative.get_summary(last_n=3),
            metacognitive_state=metacog.get_state(),
            self_model_accuracy=self.compute_self_model_accuracy(body_schema, metacog),
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Self Representation  (legacy, kept for compatibility + enriched)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SelfRepresentation:
    """High-level self-representation snapshot."""
    identity: str = "SPEACE"
    capabilities: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    alignment_score: float = 0.0
    phase: str = "embryonic"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "identity": self.identity,
            "capabilities": self.capabilities,
            "limitations": self.limitations,
            "alignment_score": self.alignment_score,
            "phase": self.phase,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  SelfModel  (BRN-019 main class)
# ──────────────────────────────────────────────────────────────────────────────

class SelfModel:
    """
    SPEACE Self-Model (BRN-019) — full implementation.

    Acts as the interoceptive nervous system of SPEACE:
      • BodySchema  → knows which modules exist and their health
      • MetacognitionLayer → monitors quality of own reasoning
      • SelfNarrative → temporal identity (the story of SPEACE)
      • IntrospectionEngine → generates rich introspective reports
      • SelfRepresentation → high-level view for external consumers

    Integration bridges:
      observe_causal_self(CausalReasoner)   → BRN-017
      abstract_self_concepts(AbstractionLayer) → BRN-018
      get_limitations() → List[Limitation]  → BRN-020
    """

    def __init__(self) -> None:
        self.body_schema    = BodySchema()
        self.metacognition  = MetacognitionLayer()
        self.narrative      = SelfNarrative()
        self.introspection  = IntrospectionEngine()
        self.awareness      = SelfRepresentation()
        self._last_report: Optional[IntrospectionReport] = None

        # Seed body schema with the known BRN modules
        self._seed_default_modules()
        logger.info("SelfModel BRN-019 initialized (full implementation)")

    # ── Seeding ───────────────────────────────────────────────────────────────

    def _seed_default_modules(self) -> None:
        """Pre-register all 20 BRN modules with initial status."""
        brn_modules = [
            ("BRN-001", "WorkingMemory",        ["short_term_storage", "attention"]),
            ("BRN-002", "EpisodicMemory",        ["long_term_storage", "episodic_retrieval"]),
            ("BRN-003", "AttentionSystem",       ["focus", "salience_detection"]),
            ("BRN-004", "MotivationalEngine",    ["goal_generation", "drive_homeostasis"]),
            ("BRN-005", "AffectiveLayer",        ["emotion_regulation", "valence"]),
            ("BRN-006", "AmygdalaModule",        ["threat_detection", "fear_response"]),
            ("BRN-007", "DopaminergicSystem",    ["reward_prediction", "exploration"]),
            ("BRN-008", "ThalamicSystem",        ["sensory_relay", "gating"]),
            ("BRN-009", "LaminarCortex",         ["hierarchical_processing", "prediction"]),
            ("BRN-010", "ConsciousnessGate",     ["global_workspace", "phi_integration"]),
            ("BRN-011", "STDPLearning",          ["synaptic_plasticity", "hebbian"]),
            ("BRN-012", "BasalGanglia",          ["action_selection", "habit_formation"]),
            ("BRN-013", "SocialCognition",       ["theory_of_mind", "empathy"]),
            ("BRN-014", "LanguageAcquisition",   ["language_modeling", "semantics"]),
            ("BRN-015", "PredictiveCoding",      ["world_model", "prediction_error"]),
            ("BRN-016", "LanguageModel",         ["nlp", "generation"]),
            ("BRN-017", "CausalReasoner",        ["do_calculus", "counterfactual", "causal_learning"]),
            ("BRN-018", "AbstractionLayer",      ["analogy", "conceptual_blending", "transfer"]),
            ("BRN-019", "SelfModel",             ["introspection", "metacognition", "body_schema"]),
            ("BRN-020", "RecursiveSelfImprover", ["code_inspection", "fitness_evaluation", "safe_modification"]),
        ]
        for mid, name, caps in brn_modules:
            # BRN-017, 018, 020 are now HEALTHY (implemented); others are HEALTHY by default
            self.body_schema.register_module(mid, name, capabilities=caps)

    # ── Core update ───────────────────────────────────────────────────────────

    def update(self, active_module_count: int = 5, queue_size: int = 0) -> Dict:
        """Run one self-model update cycle."""
        self.metacognition.estimate_cognitive_load(active_module_count, queue_size)
        self._last_report = self.introspection.snapshot(
            self.body_schema, self.metacognition, self.narrative
        )
        # Update high-level awareness
        self.awareness.limitations = [
            lim.description for lim in self._last_report.detected_limitations
        ]
        self.awareness.timestamp = time.time()
        return {
            "status": "updated",
            "brn_id": "BRN-019",
            "system_integrity": self._last_report.system_integrity,
            "cognitive_load": self._last_report.cognitive_load,
            "limitations_count": len(self._last_report.detected_limitations),
        }

    # ── Introspection ─────────────────────────────────────────────────────────

    def introspect(self) -> Dict:
        """Return a rich introspective state dictionary."""
        report = self.introspection.snapshot(
            self.body_schema, self.metacognition, self.narrative
        )
        self._last_report = report
        return {
            "timestamp": report.timestamp,
            "self_representation": self.awareness.to_dict(),
            "system_integrity": report.system_integrity,
            "self_model_accuracy": report.self_model_accuracy,
            "cognitive_load": report.cognitive_load,
            "active_modules": report.active_modules,
            "degraded_modules": report.degraded_modules,
            "offline_modules": report.offline_modules,
            "bottlenecks": report.bottlenecks,
            "limitations": [
                {
                    "module": l.module_id,
                    "type": l.limitation_type.value,
                    "severity": l.severity,
                    "description": l.description,
                    "hint": l.improvement_hint,
                }
                for l in report.detected_limitations
            ],
            "metacognitive_state": report.metacognitive_state,
            "narrative_summary": report.narrative_summary,
            "evolution_arc": self.narrative.get_evolution_arc(),
            "body_schema": self.body_schema.to_dict(),
        }

    # ── Integration API ───────────────────────────────────────────────────────

    def get_limitations(self) -> List[Limitation]:
        """
        Returns current limitations list → consumed by BRN-020
        RecursiveSelfImprover.integrate_self_model().
        """
        return self.introspection.identify_limitations(
            self.body_schema, self.metacognition
        )

    def observe_causal_self(self, causal_reasoner: Any) -> None:
        """
        BRN-017 bridge: import causal relationships between SPEACE's own modules
        as a causal self-model.
        """
        if causal_reasoner is None:
            return
        try:
            # Register the causal graph nodes that correspond to BRN modules
            cg = getattr(causal_reasoner, "causal_graph", None)
            if cg is None:
                return
            for node_id in cg.nodes:
                node = cg.get_node(node_id)
                if node and node_id in self.body_schema._modules:
                    # Update metadata with causal centrality
                    in_deg  = len(cg.get_causes(node_id))
                    out_deg = len(cg.get_effects(node_id))
                    h = self.body_schema._modules[node_id]
                    h.metadata["causal_in_degree"]  = in_deg
                    h.metadata["causal_out_degree"] = out_deg
                    h.metadata["causal_centrality"] = round(
                        (in_deg + out_deg) / max(len(cg.nodes), 1), 3
                    )
        except Exception as e:
            logger.warning("observe_causal_self error: %s", e)

    def abstract_self_concepts(self, abstraction_layer: Any) -> None:
        """
        BRN-018 bridge: create abstract concepts from body schema capability clusters.
        """
        if abstraction_layer is None:
            return
        try:
            cg = getattr(abstraction_layer, "concept_graph", None)
            if cg is None:
                return
            # Create concepts for each module's capability set
            for mid, m in self.body_schema._modules.items():
                features = {cap: 0.8 for cap in m.capabilities}
                features["health_score"] = m.performance_score
                features["is_active"] = 1.0 if m.is_alive else 0.0
                # Try to add concept
                if hasattr(cg, "add_concept"):
                    try:
                        cg.add_concept(
                            concept_id=f"self_{mid}",
                            name=f"SPEACE/{m.module_name}",
                            features=features,
                            domain="self_model",
                        )
                    except Exception:
                        pass  # concept may already exist
        except Exception as e:
            logger.warning("abstract_self_concepts error: %s", e)

    def record_milestone(self, title: str, description: str, metrics: Optional[Dict] = None) -> None:
        """Record a significant SPEACE milestone in the narrative."""
        self.narrative.record_episode(EpisodeType.MILESTONE, title, description, metrics)

    def record_capability_gain(self, module_id: str, capability: str) -> None:
        """Record acquisition of a new capability."""
        self.narrative.record_episode(
            EpisodeType.CAPABILITY_GAIN,
            f"Capability gained: {capability}",
            f"Module {module_id} acquired capability: {capability}",
            {"module": module_id, "capability": capability},
        )

    def monitor_reasoning(self, trace: ReasoningTrace) -> Dict[str, Any]:
        """Pass a reasoning trace through metacognitive monitoring."""
        return self.metacognition.monitor_reasoning(trace)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_full_status(self) -> Dict:
        return {
            "module": "SelfModel",
            "brn_id": "BRN-019",
            "status": "active",
            "registered_modules": len(self.body_schema._modules),
            "system_integrity": round(self.body_schema.compute_system_integrity(), 3),
            "narrative_episodes": self.narrative.episode_count,
            "last_report_ts": (
                self._last_report.timestamp if self._last_report else None
            ),
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_self_model() -> SelfModel:
    """Factory function: creates and returns a fully initialized SelfModel."""
    return SelfModel()
