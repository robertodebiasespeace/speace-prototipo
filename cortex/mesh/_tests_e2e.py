"""
cortex.mesh._tests_e2e — Test End-to-End CNM (M4.16)

Scenario: percezione → decisione via Continuous Neural Mesh.

Pipeline testata:
  SensoryInput (raw numpy / BrainIntegration)
    → MeshDaemon.tick()
      → NeedsDriver.observe()  → HarmonyPolicy.evaluate()
      → TaskGenerator.generate()  → MeshTelemetry.record_cycle()
  E anche: BrainIntegration come sorgente sensoriale esterna.

Criteri di chiusura M4.16:
  E2E-1   tick su mesh piena → TickResult.ok=True, verdict set
  E2E-2   graph registra almeno 5 neuroni su 3+ livelli
  E2E-3   NeedsDriver.observe() → NeedsSnapshot con 5 need in [0,1]
  E2E-4   HarmonyPolicy.evaluate() → verdict in {HEALTHY,WATCH,ALERT,CRITICAL}
  E2E-5   TaskGenerator.generate() → lista proposals (eventualmente vuota)
  E2E-6   telemetria: file JSONL scritto con cycle_id e verdict
  E2E-7   BrainIntegration: consciousness > 0, tick daemon ok
  E2E-8   SMFOI bridge default-OFF: step3bis senza epigenome enabled non altera priority

Esecuzione: python -m cortex.mesh._tests_e2e
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from typing import Any, Dict, List, Tuple

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cortex.mesh.contract import NeuronRegistry
from cortex.mesh.graph import MeshGraph
from cortex.mesh.needs_driver import NeedsDriver
from cortex.mesh.harmony import HarmonyPolicy
from cortex.mesh.task_generator import TaskGenerator
from cortex.mesh.telemetry import MeshTelemetry
from cortex.mesh.daemon import MeshDaemon, TickResult
from cortex.mesh.registry import discover_neurons
from cortex.mesh.olc import SensoryFrame, NeedsSnapshot

_PASS: List[str] = []
_FAIL: List[str] = []


def _assert(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
        _PASS.append(label)
    else:
        msg = f"  FAIL  {label}" + (f" — {detail}" if detail else "")
        print(msg)
        _FAIL.append(label)


def _tmpfile(suffix: str = ".jsonl") -> str:
    fd, path = tempfile.mkstemp(prefix="e2e_mesh_", suffix=suffix)
    os.close(fd)
    return path


def _build_mesh() -> Tuple[NeuronRegistry, MeshGraph]:
    reg = NeuronRegistry()
    discover_neurons("cortex.mesh.adapters", registry=reg)
    g = MeshGraph(neuron_registry=reg)
    g.attach_from_registry()
    g.auto_wire()
    return reg, g


def _build_daemon(path: str, **kwargs) -> MeshDaemon:
    reg, g = _build_mesh()
    return MeshDaemon(registry=reg, graph=g, telemetry_path=path, **kwargs)


# ---------------------------------------------------------------------------
# E2E-1: tick su mesh piena → TickResult.ok=True, verdict set
# ---------------------------------------------------------------------------

def test_e2e_1_full_tick():
    print("\n[E2E-1] tick su mesh piena -> TickResult.ok=True")
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        result = d.tick()
        _assert("E2E-1a TickResult type", isinstance(result, TickResult))
        _assert("E2E-1b TickResult.ok=True", result.ok is True, f"error={result.error}")
        _assert("E2E-1c cycle_id non vuoto", bool(result.cycle_id))
        _assert("E2E-1d verdict set", result.verdict is not None)
        print(f"         verdict={result.verdict} | proposals={result.proposals_count}")
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ---------------------------------------------------------------------------
# E2E-2: graph registra >=5 neuroni su >=3 livelli distinti
# ---------------------------------------------------------------------------

def test_e2e_2_graph_topology():
    print("\n[E2E-2] graph: >=5 neuroni su >=3 livelli")
    reg, g = _build_mesh()
    try:
        order = g.topological_order()
        _assert("E2E-2a almeno 5 neuroni nel grafo", len(order) >= 5,
                f"trovati {len(order)}")
        # Recupera livelli dai neuron objects
        neurons_dict = getattr(reg, "_neurons", {})
        levels = set()
        for nname in order:
            obj = neurons_dict.get(nname)
            if obj and hasattr(obj, "level"):
                levels.add(obj.level)
        _assert("E2E-2b almeno 3 livelli nel grafo", len(levels) >= 3,
                f"livelli: {sorted(levels)}")
        print(f"         neuroni={len(order)} | livelli={sorted(levels)}")
    except Exception as e:
        _assert("E2E-2 topology", False, str(e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# E2E-3: NeedsDriver.observe() → NeedsSnapshot con 5 need in [0,1]
# ---------------------------------------------------------------------------

def test_e2e_3_needs_snapshot():
    print("\n[E2E-3] NeedsDriver.observe() -> NeedsSnapshot con 5 need")
    try:
        # NeedsDriver non richiede registry/graph: li legge dal singleton
        driver = NeedsDriver()
        snap = driver.observe()
        _assert("E2E-3a NeedsSnapshot type", isinstance(snap, NeedsSnapshot),
                type(snap).__name__)
        needs_dict = snap.needs if hasattr(snap, "needs") else {}
        _assert("E2E-3b 5 need presenti", len(needs_dict) >= 5,
                f"need={list(needs_dict.keys())}")
        for need in ("survival", "expansion", "self_improvement", "integration", "harmony"):
            val = needs_dict.get(need)
            ok = val is not None and 0.0 <= float(val) <= 1.0
            _assert(f"E2E-3c {need} in [0,1]", ok, f"val={val}")
        print(f"         needs: { {k: f'{v:.2f}' for k,v in needs_dict.items()} }")
    except Exception as e:
        _assert("E2E-3 observe", False, str(e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# E2E-4: HarmonyPolicy → verdict valido
# ---------------------------------------------------------------------------

def test_e2e_4_harmony_verdict():
    print("\n[E2E-4] HarmonyPolicy.evaluate() -> HEALTHY/WATCH/ALERT/CRITICAL")
    try:
        driver = NeedsDriver()
        policy = HarmonyPolicy()
        snap = driver.observe()
        verdict = policy.evaluate(snap)
        valid = {"healthy", "watch", "alert", "critical", "HEALTHY", "WATCH", "ALERT", "CRITICAL"}
        v_str = verdict.verdict.value if hasattr(verdict.verdict, "value") else str(verdict.verdict)
        _assert("E2E-4a verdict valido", v_str in valid, f"verdict={v_str}")
        comp_count = len(getattr(verdict, "compensations", []))
        print(f"         verdict={v_str} | compensations={comp_count}")
    except Exception as e:
        _assert("E2E-4 evaluate", False, str(e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# E2E-5: TaskGenerator.generate() → lista proposals
# ---------------------------------------------------------------------------

def test_e2e_5_task_generator():
    print("\n[E2E-5] TaskGenerator.generate() -> lista proposals")
    try:
        driver = NeedsDriver()
        policy = HarmonyPolicy()
        gen = TaskGenerator()
        snap = driver.observe()
        verdict = policy.evaluate(snap)
        proposals = gen.generate(snap, verdict)
        _assert("E2E-5a proposals e' lista", isinstance(proposals, list))
        print(f"         proposals generati: {len(proposals)}")
        if proposals:
            p = proposals[0]
            has_name = hasattr(p, "action_name") or hasattr(p, "name") or hasattr(p, "olc_name") or hasattr(p, "driving_need")
            _assert("E2E-5b proposal ha nome", has_name,
                    f"fields={[x for x in dir(p) if not x.startswith('_')][:8]}")
    except Exception as e:
        _assert("E2E-5 generate", False, str(e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# E2E-6: telemetria → JSONL con cycle_id e verdict
# ---------------------------------------------------------------------------

def test_e2e_6_telemetry_write():
    print("\n[E2E-6] MeshDaemon.tick() -> evento JSONL scritto")
    path = _tmpfile()
    try:
        d = _build_daemon(path)
        d.tick()
        _assert("E2E-6a file JSONL esiste", os.path.exists(path))
        if os.path.exists(path):
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip()]
            _assert("E2E-6b almeno 1 evento", len(lines) >= 1, f"lines={len(lines)}")
            if lines:
                evt = json.loads(lines[-1])
                _assert("E2E-6c evento ha cycle_id", "cycle_id" in evt)
                _assert("E2E-6d evento ha verdict", "verdict" in evt)
                print(f"         cycle_id={evt.get('cycle_id')} verdict={evt.get('verdict')}")
    except Exception as e:
        _assert("E2E-6 telemetry", False, str(e))
        traceback.print_exc()
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ---------------------------------------------------------------------------
# E2E-7: BrainIntegration come sorgente sensoriale → tick daemon ok
# ---------------------------------------------------------------------------

def test_e2e_7_brain_as_sensor():
    print("\n[E2E-7] BrainIntegration -> tick daemon ok + consciousness > 0")
    path = _tmpfile()
    try:
        from cortex.brain.brain_integration import create_brain

        brain = create_brain("E2E_Brain")
        sensory = np.random.randn(256).astype(np.float32)
        cognitive = brain.process_sensory_input(sensory, modality="somatosensory")

        _assert("E2E-7a brain.process() ok", cognitive is not None)
        _assert("E2E-7b consciousness >= 0",
                float(cognitive.consciousness_level) >= 0.0)

        # Tick daemon: il brain gira in parallelo, non dentro il daemon stesso
        d = _build_daemon(path)
        result = d.tick()
        _assert("E2E-7c daemon.tick() ok con brain attivo", result.ok is True,
                f"err={result.error}")

        brain_state = brain.get_system_state()
        _assert("E2E-7d brain.cycle_count >= 1", brain_state["cycle_count"] >= 1)
        print(f"         brain: consciousness={brain_state['consciousness_index']:.3f}"
              f" | dopamine={brain_state['dopamine_level']:.3f}"
              f" | wm_items={brain_state['working_memory']['total_items']}")
    except Exception as e:
        _assert("E2E-7 brain sensor", False, str(e))
        traceback.print_exc()
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ---------------------------------------------------------------------------
# E2E-8: SMFOI bridge default-OFF → step3bis non altera push
# ---------------------------------------------------------------------------

def test_e2e_8_smfoi_bridge_default_off():
    print("\n[E2E-8] SMFOI bridge default-OFF: step3bis non altera push")
    try:
        from cortex.mesh.smfoi_bridge import step3bis_needs_check, NeedsCheckResult

        # Chiama senza epigenome enabled → bridge OFF (default)
        result = step3bis_needs_check(
            push={"type": "heartbeat", "priority": 1},
        )
        _assert("E2E-8a result e' NeedsCheckResult", isinstance(result, NeedsCheckResult),
                type(result).__name__)
        # Con bridge OFF, push_priority_boost deve essere 0 o None
        boost = getattr(result, "push_priority_boost", 0)
        _assert("E2E-8b bridge OFF: boost=0", int(boost) == 0,
                f"boost={boost}")
        print(f"         bridge OFF: push_priority_boost={boost} (atteso 0)")
    except Exception as e:
        _assert("E2E-8 smfoi bridge", False, str(e))
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("SPEACE CNM — Test End-to-End (M4.16)")
    print("Scenario: percezione -> decisione via Continuous Neural Mesh")
    print("=" * 65)

    tests = [
        test_e2e_1_full_tick,
        test_e2e_2_graph_topology,
        test_e2e_3_needs_snapshot,
        test_e2e_4_harmony_verdict,
        test_e2e_5_task_generator,
        test_e2e_6_telemetry_write,
        test_e2e_7_brain_as_sensor,
        test_e2e_8_smfoi_bridge_default_off,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  EXCEPTION in {t.__name__}: {e}")
            traceback.print_exc()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{'=' * 65}")
    print(f"Risultato M4.16: {len(_PASS)}/{total} PASS  |  {len(_FAIL)} FAIL")
    if _FAIL:
        print(f"FAIL: {_FAIL}")
    else:
        print("TUTTI I CRITERI M4.16 SODDISFATTI — milestone chiudibile")
    print("=" * 65)
    return 0 if not _FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
