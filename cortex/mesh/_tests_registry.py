"""
Test suite per cortex.mesh.registry (M4.7)

Copre Acceptance Criteria:
  AC-R1  discovery su package inesistente → skipped con reason, non crash
  AC-R2  discovery su modulo senza neuroni → report vuoto ma senza errori
  AC-R3  discovery su modulo con @neuron → instance registrata + validate OK
  AC-R4  idempotenza (skip_existing=True): ri-chiamata non modifica nulla
  AC-R5  collision (skip_existing=False): ri-chiamata produce DUPLICATE_NAME
  AC-R6  predicate custom filtra i neuroni registrati
  AC-R7  integrazione con MeshGraph.attach_from_registry dopo discovery
  AC-R8  require_registered identifica correttamente i nomi mancanti
  AC-R9  DiscoveryReport.ok riflette presenza/assenza di violations
  AC-R10 walk_packages traversa submoduli ricorsivamente

Esecuzione: python -m cortex.mesh._tests_registry
"""

from __future__ import annotations

import sys
import types
import traceback
from typing import List, Tuple

from cortex.mesh.contract import (
    ContractViolationCode as CVC,
    NeuronRegistry,
    neuron,
)
from cortex.mesh.olc import SensoryFrame, InterpretationFrame
from cortex.mesh.graph import MeshGraph
from cortex.mesh.registry import (
    DiscoveryReport,
    discover_neurons,
    require_registered,
)


# ------------------------------------------------------------------
# Helpers — costruisce moduli fake in memoria per il walk.
# ------------------------------------------------------------------


def _mk_neuron_fn(name: str, level: int = 2, need: str = "integration"):
    @neuron(
        name=name,
        input_type=SensoryFrame,
        output_type=InterpretationFrame,
        level=level,
        needs_served=[need],
        resource_budget={"max_ms": 100, "max_mb": 16},
        side_effects=[],
        version="1.0.0",
        description=f"Test neurone {name}",
    )
    def _fn(inp):
        return InterpretationFrame(intent=name, confidence=1.0, source=inp.source)

    return _fn


def _inject_fake_package(pkg_name: str, submodules: dict) -> None:
    """Crea un fake package `pkg_name` con `submodules = {sub_name: {attr: val}}`."""
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = []  # marca come package
    sys.modules[pkg_name] = pkg

    for sub_name, attrs in submodules.items():
        full_name = f"{pkg_name}.{sub_name}"
        sub_mod = types.ModuleType(full_name)
        for aname, val in attrs.items():
            setattr(sub_mod, aname, val)
        sys.modules[full_name] = sub_mod
        setattr(pkg, sub_name, sub_mod)


def _cleanup_fake_packages(prefix: str) -> None:
    keys = [k for k in sys.modules.keys() if k == prefix or k.startswith(prefix + ".")]
    for k in keys:
        sys.modules.pop(k, None)


# ------------------------------------------------------------------
# Cases
# ------------------------------------------------------------------


def case_ac_r1_nonexistent_package():
    reg = NeuronRegistry()
    rep = discover_neurons("cortex.mesh.absolutely_does_not_exist_xyz", registry=reg)
    assert rep.registered == []
    assert len(rep.skipped) >= 1
    assert "ModuleNotFoundError" in rep.skipped[0][1]
    assert rep.ok  # no violations ≠ skipped
    return "AC-R1 nonexistent package → skipped senza crash"


def case_ac_r2_module_no_neurons():
    # cortex.mesh.olc è un package senza @neuron-decorated wrappers
    reg = NeuronRegistry()
    rep = discover_neurons("cortex.mesh.olc", registry=reg)
    assert rep.registered == []
    assert not rep.violations
    return f"AC-R2 module senza neuroni (scanned={len(rep.scanned_modules)}, reg=0)"


def case_ac_r3_basic_discovery():
    pkg = "cortex_test_fake_basic_m47"
    _inject_fake_package(pkg, {"mod_a": {"alpha": _mk_neuron_fn("neuron.test.r3.alpha")}})
    try:
        reg = NeuronRegistry()
        rep = discover_neurons(pkg, registry=reg)
        assert "neuron.test.r3.alpha" in rep.registered, rep.registered
        assert not rep.violations
        assert reg.lookup("neuron.test.r3.alpha") is not None
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R3 discovery base + validazione + registrazione"


def case_ac_r4_idempotency():
    pkg = "cortex_test_fake_idempo_m47"
    _inject_fake_package(pkg, {"m": {"beta": _mk_neuron_fn("neuron.test.r4.beta")}})
    try:
        reg = NeuronRegistry()
        r1 = discover_neurons(pkg, registry=reg)
        r2 = discover_neurons(pkg, registry=reg)
        r3 = discover_neurons(pkg, registry=reg)
        assert r1.registered == ["neuron.test.r4.beta"]
        assert r2.registered == [] and not r2.violations
        assert r3.registered == [] and not r3.violations
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R4 idempotenza: 3 call → 1 register, 0 duplicate"


def case_ac_r5_collision_when_skip_disabled():
    pkg = "cortex_test_fake_collision_m47"
    _inject_fake_package(pkg, {"m": {"gamma": _mk_neuron_fn("neuron.test.r5.gamma")}})
    try:
        reg = NeuronRegistry()
        c1 = discover_neurons(pkg, registry=reg, skip_existing=False)
        c2 = discover_neurons(pkg, registry=reg, skip_existing=False)
        assert c1.registered == ["neuron.test.r5.gamma"]
        assert not c1.violations
        assert c2.registered == []
        assert "neuron.test.r5.gamma" in c2.violations
        codes = [v.code for v in c2.violations["neuron.test.r5.gamma"]]
        assert CVC.REGISTRATION_DUPLICATE_NAME in codes
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R5 skip_existing=False → DUPLICATE_NAME come atteso"


def case_ac_r6_predicate_filter():
    pkg = "cortex_test_fake_pred_m47"
    _inject_fake_package(
        pkg,
        {
            "m": {
                "k1": _mk_neuron_fn("neuron.test.r6.keep"),
                "k2": _mk_neuron_fn("neuron.test.r6.drop"),
            }
        },
    )
    try:
        # Filtra solo wrapper il cui meta.name contiene "keep"
        pred = lambda obj: getattr(obj, "meta", {}).get("name", "").endswith(".keep")
        reg = NeuronRegistry()
        rep = discover_neurons(pkg, registry=reg, predicate=pred)
        assert rep.registered == ["neuron.test.r6.keep"], rep.registered
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R6 predicate filter restringe l'insieme scoperto"


def case_ac_r7_graph_integration():
    pkg = "cortex_test_fake_graph_m47"
    _inject_fake_package(pkg, {"m": {"g": _mk_neuron_fn("neuron.test.r7.graph")}})
    try:
        reg = NeuronRegistry()
        rep = discover_neurons(pkg, registry=reg)
        assert "neuron.test.r7.graph" in rep.registered

        graph = MeshGraph(neuron_registry=reg)
        attach_report = graph.attach_from_registry()
        assert attach_report == {}, attach_report
        assert "neuron.test.r7.graph" in graph.nodes()
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R7 MeshGraph.attach_from_registry consuma discovery output"


def case_ac_r8_require_registered():
    pkg = "cortex_test_fake_req_m47"
    _inject_fake_package(pkg, {"m": {"x": _mk_neuron_fn("neuron.test.r8.present")}})
    try:
        reg = NeuronRegistry()
        discover_neurons(pkg, registry=reg)
        missing = require_registered(
            ["neuron.test.r8.present", "neuron.test.r8.missing"],
            registry=reg,
        )
        assert missing == ["neuron.test.r8.missing"], missing
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R8 require_registered identifica i mancanti"


def case_ac_r9_discovery_report_ok_flag():
    # ok=True quando non ci sono violations
    rep_ok = DiscoveryReport(registered=["a"], scanned_modules=["m"])
    assert rep_ok.ok

    # ok=False quando c'è almeno una violation
    from cortex.mesh.contract import ContractViolation, Phase

    v = ContractViolation(
        code=CVC.REGISTRATION_MISSING_METADATA,
        message="test",
        neuron_name="n",
        phase=Phase.REGISTERED,
    )
    rep_bad = DiscoveryReport(violations={"n": [v]})
    assert not rep_bad.ok
    return "AC-R9 DiscoveryReport.ok coerente con violations"


def case_ac_r10_recursive_walk():
    pkg = "cortex_test_fake_recursive_m47"
    _inject_fake_package(
        pkg,
        {
            "layer_a": {"a_fn": _mk_neuron_fn("neuron.test.r10.a")},
            "layer_b": {"b_fn": _mk_neuron_fn("neuron.test.r10.b")},
        },
    )
    try:
        reg = NeuronRegistry()
        rep = discover_neurons(pkg, registry=reg)
        assert sorted(rep.registered) == [
            "neuron.test.r10.a",
            "neuron.test.r10.b",
        ], rep.registered
        # scanned contains: pkg, pkg.layer_a, pkg.layer_b
        assert pkg in rep.scanned_modules
        assert f"{pkg}.layer_a" in rep.scanned_modules
        assert f"{pkg}.layer_b" in rep.scanned_modules
    finally:
        _cleanup_fake_packages(pkg)
    return "AC-R10 walk ricorsivo trova neuroni in submoduli"


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------


CASES = [
    case_ac_r1_nonexistent_package,
    case_ac_r2_module_no_neurons,
    case_ac_r3_basic_discovery,
    case_ac_r4_idempotency,
    case_ac_r5_collision_when_skip_disabled,
    case_ac_r6_predicate_filter,
    case_ac_r7_graph_integration,
    case_ac_r8_require_registered,
    case_ac_r9_discovery_report_ok_flag,
    case_ac_r10_recursive_walk,
]


def run_all() -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    report_lines: List[str] = []
    for case in CASES:
        name = case.__name__
        try:
            desc = case()
            passed += 1
            report_lines.append(f"  [PASS] {name}: {desc}")
        except AssertionError as e:
            failed += 1
            report_lines.append(f"  [FAIL] {name}: {e}")
        except Exception as e:
            failed += 1
            report_lines.append(
                f"  [ERROR] {name}: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
    return passed, failed, report_lines


def main() -> int:
    p, f, lines = run_all()
    print(f"cortex.mesh._tests_registry — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
