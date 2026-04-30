"""
Test suite per cortex.mesh.telemetry e cortex.mesh.dashboard_cli (M4.13)

Copre:
  AC-TM1  build_event con tutti i campi → JSON-safe
  AC-TM2  build_event con campi mancanti → null/[] coerenti
  AC-TM3  record_cycle scrive una riga JSON valida sul file
  AC-TM4  record_cycle multipli → linee multiple in ordine cronologico
  AC-TM5  read_all itera correttamente tutte le linee
  AC-TM6  tail(N) ritorna le ultime N linee
  AC-TM7  stats aggrega verdict_distribution e count totale
  AC-TM8  riga corrotta → skip senza crash
  AC-TM9  dashboard render con file vuoto → mostra '(no events recorded yet)'
  AC-TM10 dashboard render con eventi → contiene VERDICT, NEED, PROPOSALS sections
  AC-TM11 dashboard --json output è JSON valido
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Tuple

from cortex.mesh.olc import NeedsSnapshot, TaskProposal
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.harmony import HarmonyPolicy, HarmonyVerdict
from cortex.mesh.task_generator import TaskGenerator
from cortex.mesh.telemetry import MeshTelemetry, build_event
from cortex.mesh.dashboard_cli import render_dashboard, _cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmpfile(suffix: str = ".jsonl") -> str:
    fd, path = tempfile.mkstemp(prefix="mesh_test_", suffix=suffix)
    os.close(fd)
    os.unlink(path)  # rimuove → telemetry ricreerà
    return path


def _snap(needs: Dict[str, float], targets: Dict[str, float]) -> NeedsSnapshot:
    gap = {k: max(0.0, targets[k] - needs[k]) for k in NEEDS_CATALOG}
    return NeedsSnapshot(needs=dict(needs), gap=gap)


def _full_run(needs_value: float = 0.5) -> Tuple[NeedsSnapshot, "HarmonyReport", List[TaskProposal]]:
    pol = HarmonyPolicy()
    needs = {k: needs_value for k in NEEDS_CATALOG}
    needs["survival"] = max(0.85, needs_value)
    needs["harmony"] = max(0.85, needs_value)
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    gen = TaskGenerator(policy=pol, max_proposals=3)
    props = gen.generate(snap, harmony_report=rep)
    return snap, rep, props


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def case_ac_tm1_build_event_full():
    snap, rep, props = _full_run(0.4)
    ev = build_event(
        cycle_id="cyc-test-1",
        needs_snapshot=snap,
        harmony_report=rep,
        graph_snapshot={"stats": {"nodes": 11, "edges": 13, "roots": 2, "sinks": 1, "levels": {"1": 2}, "needs": {"survival": 1}}},
        runtime_snapshot={"cycles": 100, "errors": 2},
        registry_summary={"total": 11, "quarantined": 0},
        proposals=props,
    )
    # Deve essere JSON-safe (dumps senza errori)
    s = json.dumps(ev)
    parsed = json.loads(s)
    assert parsed["cycle_id"] == "cyc-test-1"
    assert parsed["verdict"] in ("healthy", "watch", "alert", "critical")
    assert set(parsed["needs"].keys()) == set(NEEDS_CATALOG)
    assert parsed["graph"]["nodes"] == 11
    return f"AC-TM1 build_event full → JSON valido ({len(s)} byte)"


def case_ac_tm2_build_event_partial():
    ev = build_event()  # tutto vuoto
    s = json.dumps(ev)  # deve serializzare lo stesso
    parsed = json.loads(s)
    assert parsed["verdict"] is None
    assert parsed["needs"] == {}
    assert parsed["proposals"] == []
    assert parsed["compensations"] == []
    assert parsed["allowed_risk_levels"] == []
    assert "cycle_id" in parsed and parsed["cycle_id"]
    return "AC-TM2 build_event vuoto → struttura coerente"


def case_ac_tm3_record_single():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        snap, rep, props = _full_run()
        ev = tlm.record_cycle(
            needs_snapshot=snap, harmony_report=rep, proposals=props,
        )
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.count("\n") == 1, content
        parsed = json.loads(content.strip())
        assert parsed["cycle_id"] == ev["cycle_id"]
        return "AC-TM3 record_cycle → 1 linea JSON valida"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm4_record_multi_chronological():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        for i in range(5):
            tlm.record_cycle(extras={"i": i})
        events = list(tlm.read_all())
        assert len(events) == 5, len(events)
        # ts crescente (o pari)
        for i in range(4):
            assert events[i]["ts"] <= events[i+1]["ts"], (events[i]["ts"], events[i+1]["ts"])
        return "AC-TM4 5 record consecutivi in ordine cronologico"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm5_read_all_iter():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        for i in range(3):
            tlm.record_cycle(extras={"x": i})
        # Read_all è generator
        acc = []
        for ev in tlm.read_all():
            acc.append(ev)
        assert len(acc) == 3
        return "AC-TM5 read_all itera 3 eventi"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm6_tail_limit():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        for i in range(10):
            tlm.record_cycle(extras={"n": i})
        last3 = tlm.tail(3)
        assert len(last3) == 3
        # Devono essere gli ultimi 3
        ns = [e.get("n") for e in last3]
        assert ns == [7, 8, 9], ns
        return f"AC-TM6 tail(3) → ultimi 3 eventi (n={ns})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm7_stats_aggregation():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        pol = HarmonyPolicy()
        # 2 healthy, 1 watch, 1 critical
        for _ in range(2):
            snap = _snap({k: pol.targets[k] for k in NEEDS_CATALOG}, pol.targets)
            tlm.record_cycle(needs_snapshot=snap, harmony_report=pol.evaluate(snap))
        watch_needs = {k: 0.7 * pol.targets[k] for k in NEEDS_CATALOG}
        snap = _snap(watch_needs, pol.targets)
        tlm.record_cycle(needs_snapshot=snap, harmony_report=pol.evaluate(snap))
        crit_needs = {k: 0.9 for k in NEEDS_CATALOG}
        crit_needs["harmony"] = 0.1
        snap = _snap(crit_needs, pol.targets)
        tlm.record_cycle(needs_snapshot=snap, harmony_report=pol.evaluate(snap))

        stats = tlm.stats()
        assert stats["events_total"] == 4
        dist = stats["verdict_distribution"]
        assert dist.get("healthy", 0) == 2, dist
        assert dist.get("watch", 0) == 1, dist
        assert dist.get("critical", 0) == 1, dist
        return f"AC-TM7 stats aggregation OK ({dist})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm8_corrupt_line_skipped():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        tlm.record_cycle(extras={"k": 1})
        # Inietto una linea malformata
        with open(path, "a", encoding="utf-8") as f:
            f.write("{ this is not json ]\n")
        tlm.record_cycle(extras={"k": 2})
        events = list(tlm.read_all())
        assert len(events) == 2, len(events)
        ks = [e.get("k") for e in events]
        assert ks == [1, 2], ks
        return "AC-TM8 linea corrotta skippata (2 valid events)"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm9_dashboard_empty():
    path = _tmpfile()
    out = render_dashboard(path=path, last=1)
    assert "(no events recorded yet)" in out
    assert "SPEACE Continuous Neural Mesh" in out
    return "AC-TM9 dashboard vuota → messaggio corretto"


def case_ac_tm10_dashboard_with_events():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        snap, rep, props = _full_run(0.4)
        tlm.record_cycle(needs_snapshot=snap, harmony_report=rep, proposals=props,
                         graph_snapshot={"stats": {"nodes": 11, "edges": 13, "roots": 2,
                                                    "sinks": 1, "levels": {}, "needs": {"survival": 1}}})
        out = render_dashboard(path=path, last=1)
        assert "VERDICT" in out
        assert "NEED" in out
        assert "PROPOSALS" in out
        assert "GRAPH" in out
        return f"AC-TM10 dashboard render OK ({len(out)} char)"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_tm11_cli_json_mode():
    path = _tmpfile()
    try:
        tlm = MeshTelemetry(path)
        tlm.record_cycle(extras={"marker": "json-test"})
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _cli(["--path", path, "--json"])
        assert rc == 0
        out = buf.getvalue()
        parsed = json.loads(out)
        assert parsed.get("marker") == "json-test"
        return "AC-TM11 --json CLI output → JSON parsabile"
    finally:
        if os.path.exists(path):
            os.unlink(path)


CASES = [
    case_ac_tm1_build_event_full,
    case_ac_tm2_build_event_partial,
    case_ac_tm3_record_single,
    case_ac_tm4_record_multi_chronological,
    case_ac_tm5_read_all_iter,
    case_ac_tm6_tail_limit,
    case_ac_tm7_stats_aggregation,
    case_ac_tm8_corrupt_line_skipped,
    case_ac_tm9_dashboard_empty,
    case_ac_tm10_dashboard_with_events,
    case_ac_tm11_cli_json_mode,
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
    print(f"cortex.mesh._tests_telemetry — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
