"""
Test suite per cortex.mesh.daemon (M4.14)

Copre:
  AC-D1   tick singolo su mesh canonica → TickResult.ok=True
  AC-D2   tick scrive un evento telemetry sul jsonl
  AC-D3   run_n esegue N tick con TickResult coerenti
  AC-D4   fail-soft: graph che solleva non rompe il daemon
  AC-D5   tick_count incrementa correttamente
  AC-D6   record_fitness rispetta fitness_history_size
  AC-D7   proposal_listener invocato con la lista di proposte
  AC-D8   start/stop background loop produce ≥1 tick e si chiude pulito
  AC-D9   last_tick riflette l'ultimo TickResult
  AC-D10  registry summary appare nell'evento di telemetria
  AC-D11  listener che solleva non rompe il loop

Esecuzione: python -m cortex.mesh._tests_daemon
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import traceback
from typing import Any, Dict, List, Tuple

from cortex.mesh.contract import NeuronRegistry
from cortex.mesh.graph import MeshGraph
from cortex.mesh.registry import discover_neurons
from cortex.mesh.needs_driver import NeedsDriver
from cortex.mesh.harmony import HarmonyPolicy
from cortex.mesh.task_generator import TaskGenerator
from cortex.mesh.telemetry import MeshTelemetry
from cortex.mesh.daemon import MeshDaemon, TickResult
from cortex.mesh.olc import FeedbackFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmpfile(suffix: str = ".jsonl") -> str:
    fd, path = tempfile.mkstemp(prefix="mesh_daemon_test_", suffix=suffix)
    os.close(fd)
    os.unlink(path)
    return path


def _build_canonical_mesh() -> Tuple[NeuronRegistry, MeshGraph]:
    """Costruisce la mesh canonica con i 11 adapter discovery."""
    reg = NeuronRegistry()
    discover_neurons("cortex.mesh.adapters", registry=reg)
    g = MeshGraph(neuron_registry=reg)
    g.attach_from_registry()
    g.auto_wire()
    return reg, g


def _build_daemon(path: str, **kwargs: Any) -> MeshDaemon:
    reg, g = _build_canonical_mesh()
    return MeshDaemon(
        registry=reg, graph=g,
        telemetry_path=path,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def case_ac_d1_single_tick_ok():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        res = d.tick()
        assert isinstance(res, TickResult)
        assert res.ok is True, f"tick failed: {res.error}"
        assert res.cycle_id, res.cycle_id
        assert res.ts, res.ts
        assert res.verdict in ("healthy", "watch", "alert", "critical"), res.verdict
        return f"AC-D1 single tick OK (verdict={res.verdict}, props={res.proposals_count})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d2_tick_writes_telemetry():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        d.tick()
        # Una linea JSON sul file
        with open(path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        assert len(lines) == 1, f"expected 1 line, got {len(lines)}"
        ev = json.loads(lines[0])
        assert "cycle_id" in ev
        assert "verdict" in ev
        assert "needs" in ev
        return "AC-D2 tick → 1 evento JSONL valido"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d3_run_n_ticks():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        results = d.run_n(5)
        assert len(results) == 5
        for r in results:
            assert r.ok is True, f"tick error: {r.error}"
        # 5 linee sul file
        with open(path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        assert len(lines) == 5, len(lines)
        return f"AC-D3 run_n(5) → 5 tick OK, 5 linee telemetry"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d4_fail_soft_broken_graph():
    """Se graph.snapshot() solleva, il daemon registra un error event ma non crash."""
    path = _tmpfile()
    try:
        reg, g = _build_canonical_mesh()

        # Mock: sostituisci snapshot con un raiser
        class _BrokenGraph:
            def snapshot(self):
                raise RuntimeError("boom")

        d = MeshDaemon(registry=reg, graph=_BrokenGraph(), telemetry_path=path)
        res = d.tick()
        assert res.ok is False
        assert res.verdict == "error"
        assert res.error and "RuntimeError" in res.error
        # Telemetria dovrebbe avere almeno 1 evento (di tipo error)
        with open(path, "r", encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        assert len(lines) >= 1
        return f"AC-D4 fail-soft on broken graph → {res.error[:40]}..."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d5_tick_count_increments():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        assert d.tick_count() == 0
        d.tick()
        assert d.tick_count() == 1
        d.run_n(3)
        assert d.tick_count() == 4
        return f"AC-D5 tick_count = {d.tick_count()} (expected 4)"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d6_record_fitness_window():
    path = _tmpfile()
    try:
        d = _build_daemon(path, fitness_history_size=3)
        for i in range(10):
            d.record_fitness(FeedbackFrame(
                cycle_id=f"cyc-{i}",
                latency_ms=10.0,
                errors=0,
                fitness_delta=0.1 * i,
            ))
        # La finestra deve avere al massimo 3
        with d._lock:  # type: ignore[attr-defined]
            window = list(d._fitness_window)  # type: ignore[attr-defined]
        assert len(window) == 3, len(window)
        # Devono essere gli ultimi 3 (i=7,8,9 → 0.7, 0.8, 0.9 con tolleranza FP)
        assert abs(window[-1].fitness_delta - 0.9) < 1e-6, window[-1].fitness_delta
        assert abs(window[0].fitness_delta - 0.7) < 1e-6, window[0].fitness_delta
        return f"AC-D6 fitness window cap = 3 (deltas={[f.fitness_delta for f in window]})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d7_proposal_listener_invoked():
    path = _tmpfile()
    try:
        captured: List[List[Any]] = []

        def listener(props: List[Any]) -> None:
            captured.append(list(props))

        # Forziamo bisogni bassi → genera proposte
        reg, g = _build_canonical_mesh()
        # Usiamo un driver che ritorni snapshot con bisogni < target
        from cortex.mesh.olc import NeedsSnapshot
        from cortex.mesh.olc.base import NEEDS_CATALOG

        class _ForcedDriver:
            def __init__(self):
                self._t = {k: 0.8 for k in NEEDS_CATALOG}
            @property
            def targets(self):
                return dict(self._t)
            def observe(self, **kw):
                needs = {k: 0.3 for k in NEEDS_CATALOG}
                gap = {k: 0.5 for k in NEEDS_CATALOG}
                return NeedsSnapshot(needs=needs, gap=gap)

        d = MeshDaemon(
            registry=reg, graph=g,
            needs_driver=_ForcedDriver(),  # type: ignore[arg-type]
            telemetry_path=path,
            proposal_listener=listener,
        )
        res = d.tick()
        assert res.ok, res.error
        assert res.proposals_count > 0, res.proposals_count
        assert len(captured) == 1, len(captured)
        assert len(captured[0]) == res.proposals_count
        return f"AC-D7 listener chiamato 1× con {res.proposals_count} proposte"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d8_start_stop_background():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        assert not d.is_running()
        # Heartbeat molto rapido (0.05s) per test
        d.start(interval_s=0.05)
        assert d.is_running()
        # Lascia girare un attimo
        time.sleep(0.25)
        d.stop(timeout=2.0)
        assert not d.is_running()
        # Almeno 2 tick (1 immediato + 1 heartbeat)
        assert d.tick_count() >= 2, d.tick_count()
        return f"AC-D8 start/stop OK ({d.tick_count()} tick in 0.25s)"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d9_last_tick():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        assert d.last_tick() is None
        r1 = d.tick()
        last = d.last_tick()
        assert last is not None
        assert last.cycle_id == r1.cycle_id
        # Nuovo tick → last_tick cambia
        r2 = d.tick()
        assert d.last_tick().cycle_id == r2.cycle_id
        assert r1.cycle_id != r2.cycle_id
        return "AC-D9 last_tick si aggiorna ad ogni tick"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d10_registry_summary_in_event():
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        d.tick()
        with open(path, "r", encoding="utf-8") as f:
            ev = json.loads(f.read().splitlines()[0])
        reg = ev.get("registry", {})
        assert "total" in reg
        assert "quarantined" in reg
        assert int(reg["total"]) >= 1, reg["total"]
        return f"AC-D10 registry summary in telemetry (total={reg['total']}, q={reg['quarantined']})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_d11_listener_exception_does_not_crash():
    path = _tmpfile()
    try:
        def bad_listener(props):
            raise RuntimeError("listener boom")

        from cortex.mesh.olc import NeedsSnapshot
        from cortex.mesh.olc.base import NEEDS_CATALOG

        class _ForcedDriver:
            def __init__(self):
                self._t = {k: 0.8 for k in NEEDS_CATALOG}
            @property
            def targets(self):
                return dict(self._t)
            def observe(self, **kw):
                return NeedsSnapshot(
                    needs={k: 0.3 for k in NEEDS_CATALOG},
                    gap={k: 0.5 for k in NEEDS_CATALOG},
                )

        reg, g = _build_canonical_mesh()
        d = MeshDaemon(
            registry=reg, graph=g,
            needs_driver=_ForcedDriver(),  # type: ignore[arg-type]
            telemetry_path=path,
            proposal_listener=bad_listener,
        )
        res = d.tick()
        # Il tick deve restare ok=True nonostante l'errore del listener
        assert res.ok is True, res.error
        return "AC-D11 listener che solleva non rompe il tick"
    finally:
        if os.path.exists(path):
            os.unlink(path)


CASES = [
    case_ac_d1_single_tick_ok,
    case_ac_d2_tick_writes_telemetry,
    case_ac_d3_run_n_ticks,
    case_ac_d4_fail_soft_broken_graph,
    case_ac_d5_tick_count_increments,
    case_ac_d6_record_fitness_window,
    case_ac_d7_proposal_listener_invoked,
    case_ac_d8_start_stop_background,
    case_ac_d9_last_tick,
    case_ac_d10_registry_summary_in_event,
    case_ac_d11_listener_exception_does_not_crash,
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
    print(f"cortex.mesh._tests_daemon — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
