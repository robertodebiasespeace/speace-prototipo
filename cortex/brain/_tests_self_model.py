"""
Test suite BRN-019 SelfModel — 42 tests
"""
from __future__ import annotations
import sys, time, uuid
sys.path.insert(0, '/sessions/beautiful-affectionate-franklin/mnt/SPEACE-prototipo')

import pytest
from cortex.brain.self_model import (
    BodySchema, ModuleHealth, ModuleStatus,
    BiasDetector, ConfidenceCalibrator, MetacognitionLayer, ReasoningTrace,
    SelfNarrative, NarrativeEpisode, EpisodeType,
    Limitation, LimitationType, IntrospectionEngine,
    SelfRepresentation, SelfModel, create_self_model,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_trace(conf=0.7, ms=20.0, src="BRN-017") -> ReasoningTrace:
    return ReasoningTrace(
        trace_id=str(uuid.uuid4())[:8],
        module_source=src,
        input_summary="test input",
        output_summary="test output",
        raw_confidence=conf,
        processing_time_ms=ms,
    )


# ── TestBodySchema ─────────────────────────────────────────────────────────────

class TestBodySchema:
    def test_register_returns_health(self):
        bs = BodySchema()
        h = bs.register_module("M1", "TestModule", ["cap1", "cap2"])
        assert isinstance(h, ModuleHealth)
        assert h.module_id == "M1"
        assert h.status == ModuleStatus.HEALTHY

    def test_register_multiple(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.register_module("M2", "B", [])
        assert len(bs._modules) == 2

    def test_update_health_healthy_to_degraded(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.update_health("M1", ModuleStatus.DEGRADED, performance_score=0.4)
        assert bs.get_module("M1").status == ModuleStatus.DEGRADED
        assert bs.get_module("M1").performance_score == pytest.approx(0.4)

    def test_update_health_unknown_module_raises(self):
        bs = BodySchema()
        with pytest.raises(KeyError):
            bs.update_health("GHOST", ModuleStatus.OFFLINE)

    def test_get_active_modules(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.register_module("M2", "B", [])
        bs.update_health("M2", ModuleStatus.OFFLINE)
        active = bs.get_active_modules()
        assert len(active) == 1
        assert active[0].module_id == "M1"

    def test_get_offline_modules(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.update_health("M1", ModuleStatus.OFFLINE)
        assert len(bs.get_offline_modules()) == 1

    def test_get_degraded_modules(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.update_health("M1", ModuleStatus.DEGRADED, 0.35)
        assert len(bs.get_degraded_modules()) == 1

    def test_system_integrity_all_healthy(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.register_module("M2", "B", [])
        assert bs.compute_system_integrity() == pytest.approx(1.0)

    def test_system_integrity_one_offline(self):
        bs = BodySchema()
        bs.register_module("M1", "A", [])
        bs.register_module("M2", "B", [])
        bs.update_health("M2", ModuleStatus.OFFLINE, 0.0)
        integrity = bs.compute_system_integrity()
        assert integrity < 1.0

    def test_system_integrity_empty(self):
        bs = BodySchema()
        assert bs.compute_system_integrity() == 0.0

    def test_to_dict_structure(self):
        bs = BodySchema()
        bs.register_module("M1", "A", ["cap"])
        d = bs.to_dict()
        assert "module_count" in d
        assert "system_integrity" in d
        assert "M1" in d["modules"]

    def test_module_degrade_and_recover(self):
        bs = BodySchema()
        h = bs.register_module("M1", "A", [])
        h.degrade(0.5)
        assert h.error_count == 1
        assert h.performance_score == pytest.approx(0.5)
        h.recover(0.4)
        assert h.status == ModuleStatus.HEALTHY


# ── TestBiasDetector ───────────────────────────────────────────────────────────

class TestBiasDetector:
    def test_overconfidence_fast(self):
        bd = BiasDetector()
        trace = make_trace(conf=0.95, ms=2.0)
        assert bd.detect_overconfidence(trace) == "overconfidence_bias"

    def test_no_overconfidence_slow(self):
        bd = BiasDetector()
        trace = make_trace(conf=0.95, ms=50.0)
        assert bd.detect_overconfidence(trace) is None

    def test_no_overconfidence_low_conf(self):
        bd = BiasDetector()
        trace = make_trace(conf=0.7, ms=2.0)
        assert bd.detect_overconfidence(trace) is None

    def test_recency_bias_same_source(self):
        bd = BiasDetector()
        recent = [make_trace(src="BRN-017")] * 3
        trace  = make_trace(src="BRN-017")
        assert bd.detect_recency_bias(trace, recent) == "recency_bias"

    def test_no_recency_bias_different_sources(self):
        bd = BiasDetector()
        recent = [make_trace(src="BRN-017"), make_trace(src="BRN-018"), make_trace(src="BRN-020")]
        trace  = make_trace(src="BRN-017")
        assert bd.detect_recency_bias(trace, recent) is None

    def test_anchoring_bias(self):
        bd = BiasDetector()
        assert bd.detect_anchoring_bias(0.7, 0.702, threshold=0.05) == "anchoring_bias"

    def test_no_anchoring_bias(self):
        bd = BiasDetector()
        assert bd.detect_anchoring_bias(0.7, 0.9, threshold=0.05) is None

    def test_detect_all_returns_list(self):
        bd = BiasDetector()
        trace = make_trace(conf=0.96, ms=2.0)
        result = bd.detect_all(trace)
        assert isinstance(result, list)
        assert "overconfidence_bias" in result


# ── TestConfidenceCalibrator ───────────────────────────────────────────────────

class TestConfidenceCalibrator:
    def test_record_and_count(self):
        cc = ConfidenceCalibrator()
        cc.record(0.8, True)
        cc.record(0.6, False)
        assert cc.n_samples == 2

    def test_ece_empty(self):
        cc = ConfidenceCalibrator()
        assert cc.expected_calibration_error() == 0.0

    def test_ece_perfect(self):
        cc = ConfidenceCalibrator()
        # confidence=1.0 always correct → ECE ≈ 0
        for _ in range(20):
            cc.record(1.0, True)
        assert cc.expected_calibration_error() < 0.05

    def test_ece_imperfect(self):
        cc = ConfidenceCalibrator()
        for _ in range(10):
            cc.record(0.9, False)   # overconfident → high ECE
        assert cc.expected_calibration_error() > 0.5

    def test_calibrated_confidence_no_history(self):
        cc = ConfidenceCalibrator()
        assert cc.calibrated_confidence(0.7) == pytest.approx(0.7)

    def test_calibrated_confidence_with_history(self):
        cc = ConfidenceCalibrator()
        for _ in range(10):
            cc.record(0.8, True)
        c = cc.calibrated_confidence(0.8)
        assert 0.0 <= c <= 1.0


# ── TestMetacognitionLayer ─────────────────────────────────────────────────────

class TestMetacognitionLayer:
    def test_monitor_reasoning_returns_dict(self):
        ml = MetacognitionLayer()
        trace = make_trace(conf=0.7, ms=20.0)
        result = ml.monitor_reasoning(trace)
        assert "detected_biases" in result
        assert "calibrated_confidence" in result
        assert "ece" in result

    def test_overconfidence_detected_in_monitor(self):
        ml = MetacognitionLayer()
        trace = make_trace(conf=0.97, ms=1.0)
        result = ml.monitor_reasoning(trace)
        assert "overconfidence_bias" in result["detected_biases"]

    def test_cognitive_load_zero(self):
        ml = MetacognitionLayer()
        load = ml.estimate_cognitive_load(0, 0, 0.0)
        assert load == pytest.approx(0.0)

    def test_cognitive_load_high(self):
        ml = MetacognitionLayer()
        load = ml.estimate_cognitive_load(9, 50, 1.0)
        assert load == pytest.approx(1.0)

    def test_cognitive_load_mid(self):
        ml = MetacognitionLayer()
        load = ml.estimate_cognitive_load(5, 10, 0.0)
        assert 0.2 < load < 0.6

    def test_update_outcome(self):
        ml = MetacognitionLayer()
        trace = make_trace(conf=0.8, ms=10.0)
        ml.monitor_reasoning(trace)
        ml.update_outcome(trace.trace_id, was_correct=True)
        assert ml.calibrator.n_samples == 1

    def test_get_state_structure(self):
        ml = MetacognitionLayer()
        ml.monitor_reasoning(make_trace())
        state = ml.get_state()
        assert "cognitive_load" in state
        assert "ece" in state
        assert "avg_confidence_recent" in state


# ── TestSelfNarrative ──────────────────────────────────────────────────────────

class TestSelfNarrative:
    def test_birth_recorded_on_init(self):
        sn = SelfNarrative()
        assert sn.episode_count == 1

    def test_record_episode(self):
        sn = SelfNarrative()
        sn.record_episode(EpisodeType.MILESTONE, "First test", "desc")
        assert sn.episode_count == 2

    def test_get_summary_contains_title(self):
        sn = SelfNarrative()
        sn.record_episode(EpisodeType.MILESTONE, "Big Achievement", "desc")
        summary = sn.get_summary(last_n=5)
        assert "Big Achievement" in summary

    def test_evolution_arc_by_type(self):
        sn = SelfNarrative()
        sn.record_episode(EpisodeType.MILESTONE, "M1", "d")
        sn.record_episode(EpisodeType.CAPABILITY_GAIN, "CG1", "d")
        arc = sn.get_evolution_arc()
        assert arc["by_type"].get("milestone", 0) >= 1
        assert arc["by_type"].get("capability_gain", 0) >= 1

    def test_evolution_arc_milestones_list(self):
        sn = SelfNarrative()
        sn.record_episode(EpisodeType.MILESTONE, "M", "d")
        arc = sn.get_evolution_arc()
        assert len(arc["milestones"]) >= 1


# ── TestIntrospectionEngine ────────────────────────────────────────────────────

class TestIntrospectionEngine:
    def setup_method(self):
        self.bs = BodySchema()
        self.bs.register_module("M1", "A", [])
        self.bs.register_module("M2", "B", [])
        self.ml = MetacognitionLayer()
        self.sn = SelfNarrative()
        self.ie = IntrospectionEngine()

    def test_identify_bottlenecks_empty_when_healthy(self):
        bottlenecks = self.ie.identify_bottlenecks(self.bs)
        assert bottlenecks == []

    def test_identify_bottlenecks_detects_low_perf(self):
        self.bs.update_health("M1", ModuleStatus.DEGRADED, 0.3)
        bottlenecks = self.ie.identify_bottlenecks(self.bs)
        assert "M1" in bottlenecks

    def test_identify_limitations_offline_module(self):
        self.bs.update_health("M1", ModuleStatus.OFFLINE)
        lims = self.ie.identify_limitations(self.bs, self.ml)
        types = [l.limitation_type for l in lims]
        assert LimitationType.MISSING_CAPABILITY in types

    def test_identify_limitations_degraded_module(self):
        self.bs.update_health("M1", ModuleStatus.DEGRADED, 0.3)
        lims = self.ie.identify_limitations(self.bs, self.ml)
        types = [l.limitation_type for l in lims]
        assert LimitationType.PERFORMANCE_DEGRADATION in types

    def test_identify_limitations_high_load(self):
        self.ml.estimate_cognitive_load(9, 50, 1.0)
        lims = self.ie.identify_limitations(self.bs, self.ml)
        types = [l.limitation_type for l in lims]
        assert LimitationType.HIGH_LOAD in types

    def test_snapshot_returns_report(self):
        report = self.ie.snapshot(self.bs, self.ml, self.sn)
        assert report.system_integrity == pytest.approx(1.0)
        assert report.active_modules == 2
        assert isinstance(report.bottlenecks, list)

    def test_self_model_accuracy_healthy(self):
        acc = self.ie.compute_self_model_accuracy(self.bs, self.ml)
        assert acc > 0.8


# ── TestSelfModel ──────────────────────────────────────────────────────────────

class TestSelfModel:
    def test_init_registers_20_modules(self):
        sm = SelfModel()
        assert len(sm.body_schema._modules) == 20

    def test_introspect_structure(self):
        sm = SelfModel()
        r = sm.introspect()
        required = ["system_integrity", "body_schema", "limitations",
                    "metacognitive_state", "narrative_summary", "evolution_arc"]
        for key in required:
            assert key in r, f"Missing key: {key}"

    def test_update_returns_dict(self):
        sm = SelfModel()
        result = sm.update(active_module_count=5, queue_size=2)
        assert result["status"] == "updated"
        assert result["brn_id"] == "BRN-019"

    def test_cognitive_load_updates_on_update(self):
        sm = SelfModel()
        sm.update(active_module_count=8, queue_size=30)
        assert sm.metacognition._cognitive_load > 0

    def test_get_limitations_empty_when_healthy(self):
        sm = SelfModel()
        lims = sm.get_limitations()
        assert isinstance(lims, list)

    def test_get_limitations_after_offline(self):
        sm = SelfModel()
        sm.body_schema.update_health("BRN-016", ModuleStatus.OFFLINE)
        lims = sm.get_limitations()
        assert len(lims) >= 1
        assert any(l.limitation_type == LimitationType.MISSING_CAPABILITY for l in lims)

    def test_record_milestone(self):
        sm = SelfModel()
        sm.record_milestone("Test Milestone", "A test milestone was reached")
        assert sm.narrative.episode_count >= 2

    def test_record_capability_gain(self):
        sm = SelfModel()
        sm.record_capability_gain("BRN-017", "do_calculus")
        assert sm.narrative.episode_count >= 2

    def test_monitor_reasoning_integration(self):
        sm = SelfModel()
        trace = make_trace(conf=0.98, ms=1.0)
        result = sm.monitor_reasoning(trace)
        assert "detected_biases" in result
        assert "overconfidence_bias" in result["detected_biases"]

    def test_observe_causal_self_stub_safe(self):
        sm = SelfModel()
        sm.observe_causal_self(None)   # None should be safe

    def test_abstract_self_concepts_stub_safe(self):
        sm = SelfModel()
        sm.abstract_self_concepts(None)   # None should be safe

    def test_get_full_status(self):
        sm = SelfModel()
        status = sm.get_full_status()
        assert status["brn_id"] == "BRN-019"
        assert stat