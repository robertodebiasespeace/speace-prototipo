"""
Test suite per cortex.mesh.adapters (M4.8)

Copre:
  AC-A1  discovery completo: 11 adapter registrati senza violations
  AC-A2  ogni adapter esegue fail-soft (non raise mai) su input normale
  AC-A3  ogni adapter esegue fail-soft anche su input edge (values minimi)
  AC-A4  graph auto_wire produce edge compatibili per la pipeline canonica
  AC-A5  Cerebellum side_effect proposal:medium rispetta il contratto SafeProactive
  AC-A6  DigitalDNA evaluator ritorna FeedbackFrame con fitness_delta in [-1..+1]
  AC-A7  SPT adapter ritorna fallback graceful se orchestrator non importabile
  AC-A8  Tutti gli adapter producono OLC frames validi (validate() vuoto)

Esecuzione: python -m cortex.mesh._tests_adapters
"""

from __future__ import annotations

import sys
import traceback
from typing import List, Tuple

from cortex.mesh.registry import discover_neurons, require_registered
from cortex.mesh.contract import NeuronRegistry, registry as default_registry
from cortex.mesh.graph import MeshGraph
from cortex.mesh.olc import (
    SensoryFrame,
    InterpretationFrame,
    DecisionFrame,
    SafetyVerdict,
    ActionResult,
    MemoryDelta,
    ReflectionFrame,
    MutationProposal,
    FeedbackFrame,
)

from cortex.mesh.adapters.compartments import (
    ADAPTER_NAMES as COMP_NAMES,
    parietal_perceive_neuron,
    temporal_interpret_neuron,
    hippocampus_consolidate_neuron,
    prefrontal_plan_neuron,
    safety_verify_neuron,
    cerebellum_execute_neuron,
    dmn_reflect_neuron,
    curiosity_explore_neuron,
    trading_read_neuron,
    _reset_cache,
)
from cortex.mesh.adapters.digitaldna import (
    ADAPTER_NAMES as DNA_NAMES,
    digitaldna_evaluate_neuron,
)
from cortex.mesh.adapters.scientific_team import (
    ADAPTER_NAMES as SPT_NAMES,
    spt_review_neuron,
)


# ------------------------------------------------------------------
# Fixture helpers
# ------------------------------------------------------------------


def _fresh_sensory() -> SensoryFrame:
    return SensoryFrame(
        source="test",
        payload={"note": "hello mesh"},
        modality="text",
        confidence=0.9,
    )


def _fresh_interpretation() -> InterpretationFrame:
    return InterpretationFrame(
        intent="test.intent",
        confidence=0.8,
        source="test",
    )


def _fresh_decision() -> DecisionFrame:
    return DecisionFrame(
        action="noop",
        args={},
        risk_level="low",
        rationale="unit test",
    )


def _fresh_reflection() -> ReflectionFrame:
    return ReflectionFrame(
        summary="alignment coherence improved",
        confidence=0.7,
        suggestions=["explore novel mutation"],
    )


def _fresh_mutation() -> MutationProposal:
    return MutationProposal(
        title="Improve coherence via curiosity amplification",
        risk_level="low",
        change_spec={"type": "epigenome.curiosity_amp", "delta": 0.1},
        rationale="align with homeostasis setpoint",
        target="epigenome",
    )


# ------------------------------------------------------------------
# Cases
# ------------------------------------------------------------------


def case_ac_a1_full_discovery():
    reg = NeuronRegistry()
    rep = discover_neurons("cortex.mesh.adapters", registry=reg)
    assert not rep.violations, f"violations: {list(rep.violations.keys())}"
    expected = list(COMP_NAMES) + list(DNA_NAMES) + list(SPT_NAMES)
    missing = require_registered(expected, registry=reg)
    assert not missing, f"missing: {missing}"
    return f"AC-A1 discovery completo ({len(rep.registered)}/{len(expected)} adapter registrati)"


def case_ac_a2_execute_each_adapter_normal():
    _reset_cache()
    out1 = parietal_perceive_neuron(_fresh_sensory())
    assert isinstance(out1, InterpretationFrame)
    out2 = temporal_interpret_neuron(_fresh_sensory())
    assert isinstance(out2, InterpretationFrame)
    out3 = hippocampus_consolidate_neuron(_fresh_interpretation())
    assert isinstance(out3, MemoryDelta)
    out4 = prefrontal_plan_neuron(_fresh_interpretation())
    assert isinstance(out4, DecisionFrame)
    out5 = safety_verify_neuron(_fresh_decision())
    assert isinstance(out5, SafetyVerdict)
    out6 = cerebellum_execute_neuron(_fresh_decision())
    assert isinstance(out6, ActionResult)
    out7 = dmn_reflect_neuron(_fresh_interpretation())
    assert isinstance(out7, ReflectionFrame)
    out8 = curiosity_explore_neuron(_fresh_reflection())
    assert isinstance(out8, MutationProposal)
    out9 = trading_read_neuron(_fresh_sensory())
    assert isinstance(out9, ActionResult)
    return "AC-A2 9 comparti eseguibili fail-soft con input normale"


def case_ac_a3_execute_each_adapter_minimal_input():
    _reset_cache()
    minimal_sensory = SensoryFrame(source="min", payload={})
    minimal_interp = InterpretationFrame(intent="x", confidence=0.0, source="min")
    minimal_decision = DecisionFrame(action="noop", args={}, risk_level="low")
    minimal_reflection = ReflectionFrame(summary="s", confidence=0.0)

    # Nessuno dovrebbe sollevare
    assert isinstance(parietal_perceive_neuron(minimal_sensory), InterpretationFrame)
    assert isinstance(temporal_interpret_neuron(minimal_sensory), InterpretationFrame)
    assert isinstance(hippocampus_consolidate_neuron(minimal_interp), MemoryDelta)
    assert isinstance(prefrontal_plan_neuron(minimal_interp), DecisionFrame)
    assert isinstance(safety_verify_neuron(minimal_decision), SafetyVerdict)
    assert isinstance(cerebellum_execute_neuron(minimal_decision), ActionResult)
    assert isinstance(dmn_reflect_neuron(minimal_interp), ReflectionFrame)
    assert isinstance(curiosity_explore_neuron(minimal_reflection), MutationProposal)
    assert isinstance(trading_read_neuron(minimal_sensory), ActionResult)
    return "AC-A3 9 comparti resistono a input minimale (no crash)"


def case_ac_a4_graph_auto_wire_canonical():
    reg = NeuronRegistry()
    discover_neurons("cortex.mesh.adapters", registry=reg)
    graph = MeshGraph(neuron_registry=reg)
    graph.attach_from_registry()
    edges = graph.auto_wire()

    # Verifica presenza di edge canonici della pipeline
    edge_set = set(edges)
    # sensory → prefrontal via interpretation (tramite parietal/temporal)
    assert any(
        s.endswith("parietal.perceive") and d.endswith("prefrontal.plan") for s, d in edge_set
    )
    # prefrontal → cerebellum
    assert any(
        s.endswith("prefrontal.plan") and d.endswith("cerebellum.execute") for s, d in edge_set
    )
    # prefrontal → safety
    assert any(
        s.endswith("prefrontal.plan") and d.endswith("safety.verify") for s, d in edge_set
    )
    # dmn → curiosity
    assert any(
        s.endswith("dmn.reflect") and d.endswith("curiosity.explore") for s, d in edge_set
    )
    # curiosity → digitaldna
    assert any(
        s.endswith("curiosity.explore") and d.endswith("digitaldna.evaluate") for s, d in edge_set
    )
    return f"AC-A4 pipeline canonica presente ({len(edges)} edges totali)"


def case_ac_a5_cerebellum_side_effect_contract():
    _reset_cache()
    # Istanzia il Neuron contract dall'adapter decorated function
    n = cerebellum_execute_neuron.instance()
    # side_effects dovrebbe essere proposal:medium
    assert "proposal:medium" in n.side_effects
    # Safety: requires_human_approver può essere False per medium
    assert n.requires_human_approver is False
    return "AC-A5 Cerebellum side_effect=proposal:medium conforme"


def case_ac_a6_digitaldna_fitness_delta_range():
    _reset_cache()
    for risk_level in ("low", "medium", "high"):
        prop = MutationProposal(
            title=f"test {risk_level}",
            risk_level=risk_level,
            change_spec={"k": "v"},
            rationale="align with coherence",
        )
        out = digitaldna_evaluate_neuron(prop)
        assert isinstance(out, FeedbackFrame)
        assert -1.0 <= out.fitness_delta <= 1.0, out.fitness_delta
        assert out.errors == 0
    return "AC-A6 DigitalDNA fitness_delta ∈ [-1..+1] per ogni risk_level"


def case_ac_a7_spt_graceful_fallback():
    _reset_cache()
    # Non possiamo garantire che lo SPT orchestrator sia importabile — il
    # test verifica solo che il neurone NON raise e ritorni InterpretationFrame.
    out = spt_review_neuron(_fresh_sensory())
    assert isinstance(out, InterpretationFrame)
    assert 0.0 <= out.confidence <= 1.0
    # Intent deve essere uno tra i valori attesi (ok, no_method, unavailable, error)
    assert out.intent.startswith("spt.") or out.intent in (
        "noop", "interpret", "spt.review"
    ), f"unexpected intent: {out.intent}"
    return f"AC-A7 SPT adapter fail-safe (intent={out.intent})"


def case_ac_a8_all_frames_validate():
    """Ogni adapter produce frame OLC che passa .validate() (lista vuota)."""
    _reset_cache()
    frames = [
        parietal_perceive_neuron(_fresh_sensory()),
        temporal_interpret_neuron(_fresh_sensory()),
        hippocampus_consolidate_neuron(_fresh_interpretation()),
        prefrontal_plan_neuron(_fresh_interpretation()),
        safety_verify_neuron(_fresh_decision()),
        cerebellum_execute_neuron(_fresh_decision()),
        dmn_reflect_neuron(_fresh_interpretation()),
        curiosity_explore_neuron(_fresh_reflection()),
        trading_read_neuron(_fresh_sensory()),
        digitaldna_evaluate_neuron(_fresh_mutation()),
        spt_review_neuron(_fresh_sensory()),
    ]
    errors = []
    for f in frames:
        vs = f.validate()
        if vs:
            errors.append(f"{type(f).__name__}: {vs}")
    assert not errors, f"validation errors: {errors}"
    return f"AC-A8 11/11 frame OLC validi (validate() == [])"


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------


CASES = [
    case_ac_a1_full_discovery,
    case_ac_a2_execute_each_adapter_normal,
    case_ac_a3_execute_each_adapter_minimal_input,
    case_ac_a4_graph_auto_wire_canonical,
    case_ac_a5_cerebellum_side_effect_contract,
    case_ac_a6_digitaldna_fitness_delta_range,
    case_ac_a7_spt_graceful_fallback,
    case_ac_a8_all_frames_validate,
]


def run_all() -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    lines: List[str] = []
    for case in CASES:
        name = case.__name__
        try:
            desc = case()
            passed += 1
            lines.append(f"  [PASS] {name}: {desc}")
        except AssertionError as e:
            failed += 1
            lines.append(f"  [FAIL] {name}: {e}")
        except Exception as e:
            failed += 1
            lines.append(
                f"  [ERROR] {name}: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
    return passed, failed, lines


def main() -> int:
    p, f, lines = run_all()
    print(f"cortex.mesh._tests_adapters — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
