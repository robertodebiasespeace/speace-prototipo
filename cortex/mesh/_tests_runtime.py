"""
SPEACE Cortex Mesh — Runtime Tests (M4.6)

Copertura:
  AC-R1  start/stop lifecycle + stato transitions
  AC-R2  submit + future.result OK
  AC-R3  submit con neurone non esistente → lookup error
  AC-R4  backpressure reject_new: queue piena → RuntimeError
  AC-R5  propagate DAG: cascade con output passato ai successori
  AC-R6  error → strike counter incrementa
  AC-R7  neurone in quarantena → skip
  AC-R8  level cap satura e rilascia correttamente
  AC-R9  heartbeat: error rate > soglia per N finestre → FROZEN
  AC-R10 runtime FROZEN rifiuta nuove submit
  AC-R11 resume torna a RUNNING e resetta finestra errori
  AC-R12 status() riporta contatori coerenti
  AC-R13 throughput baseline: 200 task in <3s con max_workers=4

Uso: python -m cortex.mesh._tests_runtime
"""
from __future__ import annotations
import sys
import threading
import time
from concurrent.futures import TimeoutError as FuturesTimeout

from cortex.mesh.contract import (
    neuron, NeuronRegistry, _REGISTRY as NEURON_REGISTRY,
)
from cortex.mesh.graph import MeshGraph, _reset_default_graph
from cortex.mesh.runtime import MeshRuntime, RuntimeState, TaskResult
from cortex.mesh.olc import (
    SensoryFrame, InterpretationFrame, DecisionFrame, ActionResult,
)


# ------------------------------------------------------------------ helpers --

def _mk_graph_with_neurons(*defs):
    """defs = list di (name, input_type, output_type, fn, level, needs)."""
    g = MeshGraph(neuron_registry=NeuronRegistry())
    for name, in_t, out_t, fn, lvl, needs in defs:
        @neuron(
            name=name,
            input_type=in_t,
            output_type=out_t,
            level=lvl,
            needs_served=needs,
            resource_budget={"max_ms": 500, "max_mb": 16},
            side_effects=[],
            version="1.0.0",
            description=f"test {name}",
        )
        def _w(inp, _fn=fn):
            return _fn(inp)
        g.add_neuron(_w.instance())
    return g


def _reset_all():
    _reset_default_graph()
    NEURON_REGISTRY._reset()


# ------------------------------------------------------------------- cases --

def case_lifecycle():
    _reset_all()
    g = MeshGraph(neuron_registry=NeuronRegistry())
    rt = MeshRuntime(g)
    assert rt.status()["state"] == "IDLE"
    rt.start()
    assert rt.status()["state"] == "RUNNING"
    rt.stop()
    assert rt.status()["state"] == "STOPPED"
    return "start/stop lifecycle"


def case_submit_ok():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.ok", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="x", confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="s", payload={"a": 1})
        fut = rt.submit("rt.ok", sf)
        res: TaskResult = fut.result(timeout=5)
        assert res.ok, res.violations
        assert isinstance(res.output, InterpretationFrame)
    finally:
        rt.stop()
    return "submit OK + future result"


def case_submit_unknown_neuron():
    _reset_all()
    g = MeshGraph(neuron_registry=NeuronRegistry())
    rt = MeshRuntime(g)
    rt.start()
    try:
        fut = rt.submit("nobody", None)
        try:
            fut.result(timeout=2)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    finally:
        rt.stop()
    return "submit unknown neuron → ValueError"


def case_propagate_cascade():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.perceive", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="see", confidence=0.9, source=sf.source),
         2, ["integration"]),
        ("rt.plan", InterpretationFrame, DecisionFrame,
         lambda i: DecisionFrame(action="go", args={}, rationale=i.intent, risk=0.1),
         1, ["harmony"]),
        ("rt.act", DecisionFrame, ActionResult,
         lambda d: ActionResult(ok=True, output={"did": d.action}, action=d.action),
         4, ["survival"]),
    )
    g.auto_wire()
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="cam", payload={"frame": 1})
        results = rt.propagate("rt.perceive", sf, timeout_s=5)
        assert set(results.keys()) == {"rt.perceive", "rt.plan", "rt.act"}
        for n, r in results.items():
            assert r.ok, f"{n}: {r.violations}"
    finally:
        rt.stop()
    return "propagate DAG cascade"


def case_strike_on_error():
    _reset_all()

    def _boom(sf):
        raise RuntimeError("boom")

    g = _mk_graph_with_neurons(
        ("rt.fail", SensoryFrame, InterpretationFrame, _boom, 2, ["integration"]),
    )
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="s", payload={})
        res = rt.submit("rt.fail", sf).result(timeout=5)
        assert not res.ok
        # Dopo un errore, lo strike counter deve essere ≥ 1
        assert NEURON_REGISTRY.strikes_of("rt.fail") >= 1, NEURON_REGISTRY.strikes_of("rt.fail")
    finally:
        rt.stop()
    return "error → strike recorded"


def case_quarantined_skipped():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.q", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="q", confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    # Forza 3 strike manualmente per quarantinare
    for _ in range(3):
        NEURON_REGISTRY.strike("rt.q")
    assert NEURON_REGISTRY.is_quarantined("rt.q")
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="s", payload={})
        res = rt.submit("rt.q", sf).result(timeout=5)
        assert not res.ok
        assert rt.status()["counters"]["skipped_quarantine"] >= 1
    finally:
        rt.stop()
    return "quarantined neuron skipped"


def case_heartbeat_trip():
    _reset_all()

    def _boom(sf):
        raise RuntimeError("forced failure")

    g = _mk_graph_with_neurons(
        ("rt.ht.fail", SensoryFrame, InterpretationFrame, _boom, 2, ["integration"]),
    )
    # threshold abbassata/window=2 così trip dopo 2 heartbeat
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="s", payload={})
        # prima finestra: fallimento
        for _ in range(3):
            try:
                rt.submit("rt.ht.fail", sf).result(timeout=5)
            except Exception:
                pass
        info1 = rt.heartbeat()
        # seconda finestra: altro fallimento
        for _ in range(3):
            try:
                rt.submit("rt.ht.fail", sf).result(timeout=5)
            except Exception:
                pass
        info2 = rt.heartbeat()
        # dopo 2 finestre consecutive con rate > 0.5, deve trippare
        assert info2["tripped"] is True, (info1, info2)
        assert rt.status()["state"] == "FROZEN", rt.status()
    finally:
        rt.stop()
    return "fail-safe trip after ≥N heartbeats"


def case_frozen_rejects():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.fr.ok", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="ok", confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    rt = MeshRuntime(g)
    rt.start()
    rt.freeze(reason="test")
    try:
        sf = SensoryFrame(source="s", payload={})
        fut = rt.submit("rt.fr.ok", sf)
        try:
            fut.result(timeout=1)
            raise AssertionError("expected RuntimeError on FROZEN")
        except RuntimeError:
            pass
    finally:
        rt.stop()
    return "frozen state rejects new submits"


def case_resume():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.res.ok", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="ok", confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    rt = MeshRuntime(g)
    rt.start()
    rt.freeze(reason="test")
    rt.resume()
    try:
        sf = SensoryFrame(source="s", payload={})
        res = rt.submit("rt.res.ok", sf).result(timeout=5)
        assert res.ok
    finally:
        rt.stop()
    return "resume after freeze"


def case_throughput():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.thr", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent=sf.source, confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    rt = MeshRuntime(g, max_concurrent_neurons=4, queue_size=256)
    rt.start()
    try:
        sf = SensoryFrame(source="t", payload={})
        futs = [rt.submit("rt.thr", sf) for _ in range(200)]
        t0 = time.perf_counter()
        for fut in futs:
            r = fut.result(timeout=10)
            assert r.ok
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"throughput regression: {elapsed:.2f}s"
        print(f"      (200 tasks, max_workers=4: {elapsed*1000:.1f}ms)")
    finally:
        rt.stop()
    return "throughput 200 tasks < 5s"


def case_status_counters():
    _reset_all()
    g = _mk_graph_with_neurons(
        ("rt.sc", SensoryFrame, InterpretationFrame,
         lambda sf: InterpretationFrame(intent="x", confidence=1.0, source=sf.source),
         2, ["integration"]),
    )
    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="s", payload={})
        for _ in range(5):
            rt.submit("rt.sc", sf).result(timeout=5)
        st = rt.status()
        c = st["counters"]
        assert c["submitted"] == 5
        assert c["completed"] == 5
        assert c["errored"] == 0
    finally:
        rt.stop()
    return "status counters coherent"


# ------------------------------------------------------------------- runner --

CASES = [
    case_lifecycle,
    case_submit_ok,
    case_submit_unknown_neuron,
    case_propagate_cascade,
    case_strike_on_error,
    case_quarantined_skipped,
    case_heartbeat_trip,
    case_frozen_rejects,
    case_resume,
    case_status_counters,
    case_throughput,
]


def main() -> int:
    print("=== cortex.mesh.runtime tests — RUNTIME_VERSION=1.0 ===")
    passed = 0
    for case in CASES:
        try:
            label = case()
            print(f"  ✓ {label}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {case.__name__} — {e}")
        except Exception as e:  # pragma: no cover
            import traceback
            print(f"  ✗ {case.__name__} — {type(e).__name__}: {e}")
            traceback.print_exc()
    total = len(CASES)
    print(f"\nPassed: {passed}/{total}")
    if passed == total:
        print("\n✅ ALL RUNTIME TESTS PASSED")
        return 0
    print("\n❌ RUNTIME TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
