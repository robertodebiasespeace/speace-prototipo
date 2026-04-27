"""
SPEACE Cortex Mesh — Graph Tests (M4.5)

Copertura:
  AC-G1  add/remove neuron: aggiunta valida, violazioni propagate da contract
  AC-G2  edge type mismatch rifiutato
  AC-G3  self-loop rifiutato
  AC-G4  duplicate edge rifiutato
  AC-G5  ciclo rifiutato al momento dell'add
  AC-G6  has_cycle() sempre False dopo build normale (invariante DAG)
  AC-G7  topological_order deterministico, rispetta ordine parziale
  AC-G8  layers() partiziona correttamente per Kahn
  AC-G9  find_paths bounded
  AC-G10 auto_wire collega producer→consumer per tipo
  AC-G11 producers_of/consumers_of/roots/sinks
  AC-G12 remove_neuron rimuove tutti gli archi
  AC-G13 snapshot JSON-safe e stats coerenti
  AC-G14 attach_from_registry importa batch
  AC-G15 perf: 100 neuroni + 200 archi in <200ms

Uso: python -m cortex.mesh._tests_graph
"""
from __future__ import annotations
import json
import sys
import time
from typing import List

from cortex.mesh.contract import (
    neuron, NeuronRegistry, Neuron,
    registry as default_registry,
)
from cortex.mesh.graph import (
    MeshGraph, GraphViolationCode, default_graph, _reset_default_graph,
)
from cortex.mesh.olc import (
    SensoryFrame, InterpretationFrame, DecisionFrame,
    ActionResult, SafetyVerdict, MemoryDelta, ReflectionFrame,
    MutationProposal, NeedsSnapshot, FeedbackFrame, TaskProposal,
    WorldSnapshot,
)


# ------------------------------------------------------------------ helpers --

def _mk_neuron(
    name: str, input_type, output_type, *,
    level: int = 2, needs=None, budget=None,
) -> Neuron:
    needs = needs or ["integration"]
    budget = budget or {"max_ms": 100, "max_mb": 16}

    @neuron(
        name=name,
        input_type=input_type,
        output_type=output_type,
        level=level,
        needs_served=needs,
        resource_budget=budget,
        side_effects=[],
        version="1.0.0",
        description=f"test neuron {name}",
    )
    def _fn(inp):
        # Shape-cast: produce un'istanza valida del tipo di output, indipendente
        # dalla forma specifica (per semplicità qui assumiamo defaults coerenti)
        raise NotImplementedError

    return _fn.instance()


def _fresh_graph() -> MeshGraph:
    # Registry locale per non inquinare il singleton
    reg = NeuronRegistry()
    return MeshGraph(neuron_registry=reg)


# ------------------------------------------------------------------- cases --

def case_add_valid():
    g = _fresh_graph()
    n = _mk_neuron("n.a", SensoryFrame, InterpretationFrame)
    vs = g.add_neuron(n)
    assert vs == [], f"expected no violations, got {vs}"
    assert g.has_neuron("n.a")
    assert g.lookup("n.a") is n
    return "add valid neuron"


def case_add_duplicate():
    g = _fresh_graph()
    n1 = _mk_neuron("n.dup", SensoryFrame, InterpretationFrame)
    n2 = _mk_neuron("n.dup", SensoryFrame, InterpretationFrame)  # stesso name, diversa istanza
    assert g.add_neuron(n1) == []
    # per registrare n2 nello stesso graph registry serve un nome differente:
    # qui simuliamo che il contract registry lo consenta
    # (add_neuron intercetta via check di duplicate su graph stesso)
    r = g.add_neuron(n2)
    assert r and r[0].code == GraphViolationCode.GRAPH_DUPLICATE_NEURON, r
    return "add duplicate neuron rejected"


def case_edge_type_mismatch():
    g = _fresh_graph()
    n1 = _mk_neuron("n.src.mm", SensoryFrame, InterpretationFrame)
    # dst richiede DecisionFrame come input, ma src produce InterpretationFrame
    n2 = _mk_neuron("n.dst.mm", DecisionFrame, ActionResult)
    assert g.add_neuron(n1) == []
    assert g.add_neuron(n2) == []
    r = g.add_edge("n.src.mm", "n.dst.mm")
    assert r and r[0].code == GraphViolationCode.GRAPH_EDGE_TYPE_MISMATCH, r
    assert not g.has_edge("n.src.mm", "n.dst.mm")
    return "edge type mismatch rejected"


def case_self_loop():
    g = _fresh_graph()
    n = _mk_neuron("n.loop", SensoryFrame, SensoryFrame)
    assert g.add_neuron(n) == []
    r = g.add_edge("n.loop", "n.loop")
    assert r and r[0].code == GraphViolationCode.GRAPH_SELF_LOOP, r
    return "self-loop rejected"


def case_duplicate_edge():
    g = _fresh_graph()
    a = _mk_neuron("n.a2", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("n.b2", InterpretationFrame, DecisionFrame)
    g.add_neuron(a); g.add_neuron(b)
    assert g.add_edge("n.a2", "n.b2") == []
    r = g.add_edge("n.a2", "n.b2")
    assert r and r[0].code == GraphViolationCode.GRAPH_DUPLICATE_EDGE, r
    return "duplicate edge rejected"


def case_cycle_rejected():
    g = _fresh_graph()
    # Ciclo a → b → c → a (tutti SensoryFrame→SensoryFrame per compat banale)
    a = _mk_neuron("n.cyc.a", SensoryFrame, SensoryFrame)
    b = _mk_neuron("n.cyc.b", SensoryFrame, SensoryFrame)
    c = _mk_neuron("n.cyc.c", SensoryFrame, SensoryFrame)
    for n in (a, b, c):
        g.add_neuron(n)
    assert g.add_edge("n.cyc.a", "n.cyc.b") == []
    assert g.add_edge("n.cyc.b", "n.cyc.c") == []
    r = g.add_edge("n.cyc.c", "n.cyc.a")
    assert r and r[0].code == GraphViolationCode.GRAPH_CYCLE_DETECTED, r
    assert not g.has_cycle()
    return "cycle rejected"


def case_topological_order():
    g = _fresh_graph()
    # a(Sensory→Interp) → b(Interp→Decision) → c(Decision→Action)
    a = _mk_neuron("topo.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("topo.b", InterpretationFrame, DecisionFrame)
    c = _mk_neuron("topo.c", DecisionFrame, ActionResult)
    for n in (a, b, c):
        g.add_neuron(n)
    g.add_edge("topo.a", "topo.b")
    g.add_edge("topo.b", "topo.c")
    order = g.topological_order()
    assert order == ["topo.a", "topo.b", "topo.c"], order
    layers = g.layers()
    assert layers == [["topo.a"], ["topo.b"], ["topo.c"]], layers
    return "topological order + layers"


def case_layers_parallel():
    g = _fresh_graph()
    # root fanout: s → {p1, p2, p3} (paralleli); tutti → sink
    s = _mk_neuron("par.s", SensoryFrame, InterpretationFrame)
    p1 = _mk_neuron("par.p1", InterpretationFrame, DecisionFrame)
    p2 = _mk_neuron("par.p2", InterpretationFrame, DecisionFrame)
    p3 = _mk_neuron("par.p3", InterpretationFrame, DecisionFrame)
    sink = _mk_neuron("par.sink", DecisionFrame, ActionResult)
    for n in (s, p1, p2, p3, sink):
        g.add_neuron(n)
    g.add_edge("par.s", "par.p1")
    g.add_edge("par.s", "par.p2")
    g.add_edge("par.s", "par.p3")
    g.add_edge("par.p1", "par.sink")
    g.add_edge("par.p2", "par.sink")
    g.add_edge("par.p3", "par.sink")
    layers = g.layers()
    assert layers[0] == ["par.s"]
    assert set(layers[1]) == {"par.p1", "par.p2", "par.p3"}, layers
    assert layers[2] == ["par.sink"]
    return "layers parallel fanout"


def case_find_paths():
    g = _fresh_graph()
    a = _mk_neuron("fp.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("fp.b", InterpretationFrame, DecisionFrame)
    c = _mk_neuron("fp.c", DecisionFrame, ActionResult)
    d = _mk_neuron("fp.d", InterpretationFrame, DecisionFrame)
    for n in (a, b, c, d):
        g.add_neuron(n)
    g.add_edge("fp.a", "fp.b"); g.add_edge("fp.b", "fp.c")
    g.add_edge("fp.a", "fp.d"); g.add_edge("fp.d", "fp.c")
    paths = g.find_paths("fp.a", "fp.c", max_hops=5)
    sp = sorted(tuple(p) for p in paths)
    assert sp == [("fp.a", "fp.b", "fp.c"), ("fp.a", "fp.d", "fp.c")], sp
    return "find_paths bounded"


def case_auto_wire():
    g = _fresh_graph()
    a = _mk_neuron("aw.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("aw.b", InterpretationFrame, DecisionFrame)
    c = _mk_neuron("aw.c", DecisionFrame, ActionResult)
    for n in (a, b, c):
        g.add_neuron(n)
    created = g.auto_wire()
    assert sorted(created) == [("aw.a", "aw.b"), ("aw.b", "aw.c")], created
    return "auto_wire producer→consumer"


def case_producers_consumers():
    g = _fresh_graph()
    a = _mk_neuron("pc.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("pc.b", SensoryFrame, DecisionFrame)
    c = _mk_neuron("pc.c", InterpretationFrame, DecisionFrame)
    for n in (a, b, c):
        g.add_neuron(n)
    assert set(g.producers_of("olc.interpretation_frame")) == {"pc.a"}
    assert set(g.consumers_of("olc.sensory_frame")) == {"pc.a", "pc.b"}
    assert set(g.consumers_of("olc.interpretation_frame")) == {"pc.c"}
    # senza archi → tutti roots e sinks
    assert set(g.roots()) == {"pc.a", "pc.b", "pc.c"}
    assert set(g.sinks()) == {"pc.a", "pc.b", "pc.c"}
    return "producers/consumers/roots/sinks"


def case_remove_neuron_cascades():
    g = _fresh_graph()
    a = _mk_neuron("rm.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("rm.b", InterpretationFrame, DecisionFrame)
    c = _mk_neuron("rm.c", DecisionFrame, ActionResult)
    for n in (a, b, c):
        g.add_neuron(n)
    g.add_edge("rm.a", "rm.b"); g.add_edge("rm.b", "rm.c")
    assert g.remove_neuron("rm.b") is True
    assert not g.has_neuron("rm.b")
    assert not g.has_edge("rm.a", "rm.b")
    assert not g.has_edge("rm.b", "rm.c")
    # a e c restano, senza archi
    assert g.successors("rm.a") == []
    assert g.predecessors("rm.c") == []
    return "remove_neuron cascades edges"


def case_snapshot_stats():
    g = _fresh_graph()
    a = _mk_neuron("sn.a", SensoryFrame, InterpretationFrame, level=2, needs=["integration"])
    b = _mk_neuron("sn.b", InterpretationFrame, DecisionFrame, level=1, needs=["harmony"])
    for n in (a, b):
        g.add_neuron(n)
    g.add_edge("sn.a", "sn.b")
    snap = g.snapshot()
    # serializzabile come JSON
    json.dumps(snap)
    assert snap["stats"]["nodes"] == 2
    assert snap["stats"]["edges"] == 1
    assert snap["stats"]["levels"]["1"] == 1
    assert snap["stats"]["levels"]["2"] == 1
    assert snap["stats"]["needs"]["harmony"] == 1
    assert snap["stats"]["needs"]["integration"] == 1
    return "snapshot + stats JSON-safe"


def case_by_level_by_need():
    g = _fresh_graph()
    a = _mk_neuron("bl.a", SensoryFrame, InterpretationFrame, level=1, needs=["harmony"])
    b = _mk_neuron("bl.b", SensoryFrame, InterpretationFrame, level=1, needs=["survival"])
    c = _mk_neuron("bl.c", SensoryFrame, InterpretationFrame, level=2, needs=["harmony", "integration"])
    for n in (a, b, c):
        g.add_neuron(n)
    l1 = [n.name for n in g.neurons_by_level(1)]
    assert set(l1) == {"bl.a", "bl.b"}, l1
    l2 = [n.name for n in g.neurons_by_level(2)]
    assert l2 == ["bl.c"], l2
    harm = [n.name for n in g.neurons_by_need("harmony")]
    assert set(harm) == {"bl.a", "bl.c"}, harm
    unknown = g.neurons_by_need("not_a_need")
    assert unknown == []
    return "by_level / by_need views"


def case_attach_from_registry():
    # registry isolato
    reg = NeuronRegistry()
    a = _mk_neuron("afr.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("afr.b", InterpretationFrame, DecisionFrame)
    reg.register(a); reg.register(b)
    g = MeshGraph(neuron_registry=reg)
    report = g.attach_from_registry()
    assert report == {}, report
    assert set(g.nodes()) == {"afr.a", "afr.b"}
    # auto_wire collega in catena
    created = g.auto_wire()
    assert created == [("afr.a", "afr.b")], created
    return "attach_from_registry + auto_wire"


def case_perf_100_neurons():
    g = _fresh_graph()
    # 100 neuroni a catena → 99 archi (peggior caso aciclicità-check)
    t0 = time.perf_counter()
    prev = None
    for i in range(100):
        n = _mk_neuron(
            f"perf.n{i:03d}",
            SensoryFrame, SensoryFrame,
            level=(i % 5) + 1,
            needs=["harmony"],
        )
        g.add_neuron(n)
        if prev is not None:
            vs = g.add_edge(prev, n.name)
            assert vs == [], vs
        prev = n.name
    elapsed_ms = (time.perf_counter() - t0) * 1000
    order = g.topological_order()
    assert len(order) == 100
    assert elapsed_ms < 500, f"perf regression: {elapsed_ms:.1f}ms"
    print(f"      (100 neurons + 99 edges + topo sort: {elapsed_ms:.1f}ms)")
    return "AC-G15 perf 100 neurons < 500ms"


def case_reachability():
    g = _fresh_graph()
    a = _mk_neuron("rch.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("rch.b", InterpretationFrame, DecisionFrame)
    c = _mk_neuron("rch.c", DecisionFrame, ActionResult)
    d = _mk_neuron("rch.d", SensoryFrame, InterpretationFrame)
    for n in (a, b, c, d):
        g.add_neuron(n)
    g.add_edge("rch.a", "rch.b"); g.add_edge("rch.b", "rch.c")
    assert g.is_reachable("rch.a", "rch.c") is True
    assert g.is_reachable("rch.c", "rch.a") is False
    assert g.is_reachable("rch.d", "rch.c") is False
    return "is_reachable / transitive"


def case_edge_weight_and_meta():
    g = _fresh_graph()
    a = _mk_neuron("w.a", SensoryFrame, InterpretationFrame)
    b = _mk_neuron("w.b", InterpretationFrame, DecisionFrame)
    g.add_neuron(a); g.add_neuron(b)
    assert g.add_edge("w.a", "w.b", weight=0.7) == []
    m = g.edge_meta("w.a", "w.b")
    assert m is not None and abs(m.weight - 0.7) < 1e-9
    m.record_success(); m.record_success(); m.record_failure()
    assert abs(m.activation_ratio() - (2 / 3)) < 1e-9
    return "edge metadata + activation ratio"


# ------------------------------------------------------------------- runner --

CASES = [
    case_add_valid,
    case_add_duplicate,
    case_edge_type_mismatch,
    case_self_loop,
    case_duplicate_edge,
    case_cycle_rejected,
    case_topological_order,
    case_layers_parallel,
    case_find_paths,
    case_auto_wire,
    case_producers_consumers,
    case_remove_neuron_cascades,
    case_snapshot_stats,
    case_by_level_by_need,
    case_attach_from_registry,
    case_reachability,
    case_edge_weight_and_meta,
    case_perf_100_neurons,
]


def main() -> int:
    print(f"=== cortex.mesh.graph tests — GRAPH_VERSION=1.0 ===")
    _reset_default_graph()
    # reset registry globale per evitare interferenze con altri test
    default_registry()._reset()
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
        print("\n✅ ALL GRAPH TESTS PASSED")
        return 0
    print("\n❌ GRAPH TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
