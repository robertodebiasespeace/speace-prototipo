"""
Test suite per cortex.mesh.needs_driver (M4.9)

Copre:
  AC-N1  driver inizializza con target di default e produce snapshot vuoto neutro
  AC-N2  observe() con grafo vuoto → expansion bassa, integration bassa, ma valido
  AC-N3  observe() con mesh canonica (11 adapter) → tutti i 5 need calcolati
  AC-N4  fitness_history positiva → self_improvement > 0.5
  AC-N5  fitness_history negativa → self_improvement < 0.5
  AC-N6  proposte HIGH dominanti → harmony degradata
  AC-N7  quarantena → survival e harmony degradati
  AC-N8  priority_gap & driving_need ritornano need con gap massimo
  AC-N9  history ring buffer rispetta size limit
  AC-N10 to_dict serializzazione completa con priority

Esecuzione: python -m cortex.mesh._tests_needs
"""

from __future__ import annotations

import sys
import traceback
from typing import List, Tuple

from cortex.mesh.needs_driver import NeedsDriver, DEFAULT_TARGETS, default_driver
from cortex.mesh.olc import NeedsSnapshot, FeedbackFrame
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.contract import NeuronRegistry
from cortex.mesh.registry import discover_neurons
from cortex.mesh.graph import MeshGraph


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _build_canonical_mesh():
    reg = NeuronRegistry()
    discover_neurons("cortex.mesh.adapters", registry=reg)
    g = MeshGraph(neuron_registry=reg)
    g.attach_from_registry()
    g.auto_wire()
    return reg, g


def _fb(delta: float) -> FeedbackFrame:
    return FeedbackFrame(
        cycle_id="test", latency_ms=10.0, errors=0, fitness_delta=delta, notes=""
    )


# ------------------------------------------------------------------
# Cases
# ------------------------------------------------------------------


def case_ac_n1_init_defaults():
    drv = NeedsDriver()
    assert set(drv.targets.keys()) == set(NEEDS_CATALOG)
    assert drv.last() is None
    assert drv.history() == []
    return f"AC-N1 init OK (5 target catalogati)"


def case_ac_n2_empty_graph():
    drv = NeedsDriver()
    snap = drv.observe()  # nessun input
    assert isinstance(snap, NeedsSnapshot)
    # Validazione strutturale OK (no violations)
    assert snap.validate() == [], snap.validate()
    # Aspettativa euristica: senza input expansion ~0.2, integration ~0.3
    assert snap.needs["expansion"] <= 0.5
    assert snap.needs["integration"] <= 0.5
    # gap survival presente (target 0.90, current 1.0 senza errori → gap 0)
    return f"AC-N2 empty input → snapshot neutro valido (5 chiavi)"


def case_ac_n3_canonical_mesh():
    reg, g = _build_canonical_mesh()
    drv = NeedsDriver(baseline_neurons=11)
    snap = drv.observe(graph_snapshot=g.snapshot(), registry=reg)
    assert isinstance(snap, NeedsSnapshot)
    assert snap.validate() == []
    assert set(snap.needs.keys()) == set(NEEDS_CATALOG)
    # Con 11 adapter su mesh canonica:
    #   - survival alto (no errori, no quarantene)
    #   - expansion alto (5/5 needs serviti, 11/11 nodes)
    #   - integration > 0 (auto_wire ha generato edge)
    assert snap.needs["survival"] >= 0.85, snap.needs
    assert snap.needs["expansion"] >= 0.7, snap.needs
    assert snap.needs["integration"] > 0.0, snap.needs
    return f"AC-N3 canonical mesh → survival={snap.needs['survival']:.2f} expansion={snap.needs['expansion']:.2f} integration={snap.needs['integration']:.2f}"


def case_ac_n4_fitness_positive_trend():
    drv = NeedsDriver()
    history = [_fb(0.1), _fb(0.2), _fb(0.3), _fb(0.4)]
    snap = drv.observe(fitness_history=history)
    # EWMA dovrebbe essere positiva → self_improvement > 0.5
    assert snap.needs["self_improvement"] > 0.5, snap.needs["self_improvement"]
    return f"AC-N4 fitness positivo → self_improvement={snap.needs['self_improvement']:.2f}"


def case_ac_n5_fitness_negative_trend():
    drv = NeedsDriver()
    history = [_fb(-0.1), _fb(-0.2), _fb(-0.3)]
    snap = drv.observe(fitness_history=history)
    assert snap.needs["self_improvement"] < 0.5, snap.needs["self_improvement"]
    return f"AC-N5 fitness negativo → self_improvement={snap.needs['self_improvement']:.2f}"


def case_ac_n6_high_risk_proposals_degrade_harmony():
    drv = NeedsDriver()
    snap_low = drv.observe(risk_proposals={"low": 10, "medium": 0, "high": 0})
    drv.reset()
    snap_high = drv.observe(risk_proposals={"low": 0, "medium": 0, "high": 5})
    assert snap_high.needs["harmony"] < snap_low.needs["harmony"], (
        snap_low.needs["harmony"], snap_high.needs["harmony"]
    )
    return f"AC-N6 high-risk-only harmony={snap_high.needs['harmony']:.2f} < low-only={snap_low.needs['harmony']:.2f}"


def case_ac_n7_quarantine_degrades_survival():
    reg, g = _build_canonical_mesh()
    # baseline (no quarantine)
    drv = NeedsDriver(baseline_neurons=11)
    snap_base = drv.observe(graph_snapshot=g.snapshot(), registry=reg)
    base_surv = snap_base.needs["survival"]
    base_harm = snap_base.needs["harmony"]
    # Forziamo una quarantena: threshold=2 + 2 strike → quarantena attiva
    target_name = list(reg.names())[0]
    reg.strike(target_name, 2)
    reg.strike(target_name, 2)
    assert reg.is_quarantined(target_name), f"{target_name} non quarantinato"

    drv2 = NeedsDriver(baseline_neurons=11)
    snap_q = drv2.observe(graph_snapshot=g.snapshot(), registry=reg)
    assert snap_q.needs["survival"] < base_surv, (snap_q.needs["survival"], base_surv)
    assert snap_q.needs["harmony"] < base_harm, (snap_q.needs["harmony"], base_harm)
    return f"AC-N7 quarantine → survival {base_surv:.3f}→{snap_q.needs['survival']:.3f}, harmony {base_harm:.3f}→{snap_q.needs['harmony']:.3f}"


def case_ac_n8_priority_and_driving():
    drv = NeedsDriver()
    # Costruisco uno scenario con expansion in deficit forte (no graph) e
    # integration in deficit (no graph), ma harmony e survival ai massimi.
    snap = drv.observe()
    pri = drv.priority_gap(snap)
    drv_need = drv.driving_need(snap)
    # Tutti i need con gap > 0 ordinati discendenti
    for i in range(len(pri) - 1):
        assert pri[i][1] >= pri[i + 1][1], pri
    if pri:
        assert drv_need == pri[0][0]
    return f"AC-N8 priority_gap ordinata, driving_need={drv_need}"


def case_ac_n9_history_ring_buffer():
    drv = NeedsDriver(history_size=4)
    for _ in range(7):
        drv.observe()
    h = drv.history()
    assert len(h) == 4, len(h)
    assert drv.last() is h[-1]
    return f"AC-N9 ring buffer size=4 (osservati 7, conservati 4)"


def case_ac_n10_to_dict_serialization():
    drv = NeedsDriver()
    drv.observe()
    d = drv.to_dict()
    assert "needs" in d and "gap" in d and "targets" in d and "ts" in d
    assert "priority" in d and "driving_need" in d
    # Tutte le chiavi catalog presenti
    assert set(d["needs"].keys()) == set(NEEDS_CATALOG)
    assert set(d["gap"].keys()) == set(NEEDS_CATALOG)
    return f"AC-N10 to_dict serializza needs+gap+targets+priority+ts"


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------


CASES = [
    case_ac_n1_init_defaults,
    case_ac_n2_empty_graph,
    case_ac_n3_canonical_mesh,
    case_ac_n4_fitness_positive_trend,
    case_ac_n5_fitness_negative_trend,
    case_ac_n6_high_risk_proposals_degrade_harmony,
    case_ac_n7_quarantine_degrades_survival,
    case_ac_n8_priority_and_driving,
    case_ac_n9_history_ring_buffer,
    case_ac_n10_to_dict_serialization,
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
    print(f"cortex.mesh._tests_needs — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
