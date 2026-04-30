"""
Test suite M5.8 + M5.9 — AutobiographicalMemory
Tests: MEM-01 → MEM-15

Run:
    cd SPEACE-prototipo
    PYTHONPATH=. python cortex/cognitive_autonomy/memory/_tests_memory.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.memory import (
    AutobiographicalMemory,
    Episode,
    MemoryType,
    EventClassifier,
    SPEACEOnlineLearner,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(tmp_dir: str) -> AutobiographicalMemory:
    db_path = Path(tmp_dir) / "test_autobio.sqlite"
    return AutobiographicalMemory(db_path=db_path, enabled=True)


def _smfoi(fitness: float = 0.6, cycle_id: str = "c-test") -> dict:
    return {
        "cycle_id": cycle_id,
        "outcome": {"fitness_after": fitness},
        "context": {"phase": "test"},
    }


def _brain(consciousness: float = 0.5, dopamine: float = 0.6) -> dict:
    return {
        "consciousness_index": consciousness,
        "dopamine_level": dopamine,
        "working_memory": {"total_items": 3},
        "cycle_count": 1,
    }


def _homeo(viability: float = 0.9) -> dict:
    return {"viability_score": viability, "alerts": []}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {name}")


def fail(name: str, reason: str) -> None:
    global FAIL
    FAIL += 1
    msg = f"  FAIL  {name}: {reason}"
    print(msg)
    ERRORS.append(msg)


def assert_eq(name, got, expected):
    if got == expected:
        ok(name)
    else:
        fail(name, f"got={got!r} expected={expected!r}")


def assert_true(name, expr, msg=""):
    if expr:
        ok(name)
    else:
        fail(name, msg or "condition False")


def assert_range(name, val, lo, hi):
    if lo <= val <= hi:
        ok(name)
    else:
        fail(name, f"{val:.4f} not in [{lo}, {hi}]")


# ---------------------------------------------------------------------------
# MEM-01: import
# ---------------------------------------------------------------------------
def test_mem_01():
    try:
        from cortex.cognitive_autonomy.memory import (
            AutobiographicalMemory, Episode, MemoryType,
            EventClassifier, SPEACEOnlineLearner,
        )
        ok("MEM-01: import __init__")
    except Exception as e:
        fail("MEM-01: import __init__", str(e))


# ---------------------------------------------------------------------------
# MEM-02: db creation with enabled=True
# ---------------------------------------------------------------------------
def test_mem_02():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_autobio.sqlite"
        mem = AutobiographicalMemory(db_path=db_path, enabled=True)
        assert_true("MEM-02a: enabled=True", mem.enabled)
        assert_true("MEM-02b: db file created", db_path.exists())


# ---------------------------------------------------------------------------
# MEM-03: record_cycle returns Episode
# ---------------------------------------------------------------------------
def test_mem_03():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        ep = mem.record_cycle("c-001", _smfoi(0.7), _brain(0.5), _homeo(0.9))
        assert_true("MEM-03a: returns Episode", isinstance(ep, Episode))
        assert_true("MEM-03b: id non-empty", bool(ep.id))
        assert_true("MEM-03c: ts > 0", ep.ts > 0)
        assert_eq("MEM-03d: cycle_id preserved", ep.cycle_id, "c-001")
        assert_range("MEM-03e: outcome in [0,1]", ep.outcome, 0.0, 1.0)


# ---------------------------------------------------------------------------
# MEM-04: disabled returns None
# ---------------------------------------------------------------------------
def test_mem_04():
    with tempfile.TemporaryDirectory() as tmp:
        mem = AutobiographicalMemory(db_path=Path(tmp) / "d.sqlite", enabled=False)
        result = mem.record_cycle("c-000", _smfoi(), _brain(), _homeo())
        assert_eq("MEM-04: disabled→None", result, None)


# ---------------------------------------------------------------------------
# MEM-05: episode count grows via metrics()
# ---------------------------------------------------------------------------
def test_mem_05():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        for i in range(5):
            mem.record_cycle(f"c-{i}", _smfoi(0.5 + i * 0.05), _brain(), _homeo())
        m = mem.metrics()
        assert_eq("MEM-05: 5 episodes", m["count"], 5)
        assert_true("MEM-05b: enabled in metrics", m["enabled"])


# ---------------------------------------------------------------------------
# MEM-06: recent() returns list ordered by ts
# ---------------------------------------------------------------------------
def test_mem_06():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        for i in range(10):
            mem.record_cycle(f"c-{i}", _smfoi(0.5), _brain(), _homeo())
        recent = mem.recent(n=3)
        assert_eq("MEM-06a: returns 3", len(recent), 3)
        assert_true("MEM-06b: list of Episode",
                    all(isinstance(e, Episode) for e in recent))


# ---------------------------------------------------------------------------
# MEM-07: MemoryType assigned (EVENT or STRUCTURE)
# ---------------------------------------------------------------------------
def test_mem_07():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        ep = mem.record_cycle("c-type", _smfoi(0.6), _brain(), _homeo())
        assert_true("MEM-07: memory_type is MemoryType",
                    isinstance(ep.memory_type, MemoryType))
        assert_true("MEM-07b: valid value",
                    ep.memory_type in (MemoryType.EVENT, MemoryType.STRUCTURE))


# ---------------------------------------------------------------------------
# MEM-08: EventClassifier standalone
# Requires 5+ history entries before STRUCTURE can be assigned.
# ---------------------------------------------------------------------------
def test_mem_08():
    clf = EventClassifier(structure_threshold=0.15)

    # Warm up with 20 stable outcomes ~0.70
    for _ in range(20):
        clf.classify(outcome=0.70, novelty=0.05)

    # Now stable outcome + low novelty should yield STRUCTURE
    t1 = clf.classify(outcome=0.70, novelty=0.05)
    assert_eq("MEM-08a: stable+low novelty → STRUCTURE", t1, MemoryType.STRUCTURE)

    # High novelty → EVENT regardless of history
    t2 = clf.classify(outcome=0.95, novelty=0.90)
    assert_eq("MEM-08b: high novelty → EVENT", t2, MemoryType.EVENT)

    # Fresh classifier, <5 entries → always EVENT
    clf2 = EventClassifier()
    t3 = clf2.classify(outcome=0.70, novelty=0.01)
    assert_eq("MEM-08c: <5 history → EVENT", t3, MemoryType.EVENT)


# ---------------------------------------------------------------------------
# MEM-09: SPEACEOnlineLearner learn + experience_replay
# learn(features, outcome) — n_samples kwarg
# ---------------------------------------------------------------------------
def test_mem_09():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        learner = SPEACEOnlineLearner(db=mem)
        for i in range(10):
            features = {"fitness": 0.4 + i * 0.05, "consciousness": 0.5}
            learner.learn(features=features, outcome=0.4 + i * 0.05,
                          cycle_id=f"learn-{i}")
        try:
            batch = learner.experience_replay(n_samples=5)
            assert_true("MEM-09a: returns list", isinstance(batch, list))
            assert_true("MEM-09b: len ≤ 10", len(batch) <= 10)
            if batch:
                assert_true("MEM-09c: items are Episode",
                            all(isinstance(e, Episode) for e in batch))
            m = learner.get_metrics()
            assert_true("MEM-09d: metrics dict", isinstance(m, dict))
            assert_true("MEM-09e: cycles_learned=10", m["cycles_learned"] == 10.0)
            ok("MEM-09: SPEACEOnlineLearner OK")
        except Exception as e:
            fail("MEM-09: experience_replay", str(e))


# ---------------------------------------------------------------------------
# MEM-10: recall() FTS search
# ---------------------------------------------------------------------------
def test_mem_10():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        mem.record_cycle("special-alpha-001", _smfoi(0.8), _brain(), _homeo())
        for i in range(3):
            mem.record_cycle(f"normal-{i}", _smfoi(0.5), _brain(), _homeo())
        try:
            results = mem.recall("alpha")
            assert_true("MEM-10a: returns list", isinstance(results, list))
            ok("MEM-10: recall() FTS runs without error")
        except Exception as e:
            fail("MEM-10: recall()", str(e))


# ---------------------------------------------------------------------------
# MEM-11: continuity_score in [0,1]
# ---------------------------------------------------------------------------
def test_mem_11():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        s0 = mem.continuity_score()
        assert_range("MEM-11a: empty → [0,1]", s0, 0.0, 1.0)
        for i in range(8):
            mem.record_cycle(f"c-{i}", _smfoi(0.60 + i * 0.01), _brain(), _homeo())
        s1 = mem.continuity_score()
        assert_range("MEM-11b: filled → [0,1]", s1, 0.0, 1.0)


# ---------------------------------------------------------------------------
# MEM-12: persistence across instances
# ---------------------------------------------------------------------------
def test_mem_12():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "persist.sqlite"
        mem1 = AutobiographicalMemory(db_path=db_path, enabled=True)
        ep = mem1.record_cycle("persist-test", _smfoi(0.77), _brain(), _homeo())
        ep_id = ep.id
        del mem1
        mem2 = AutobiographicalMemory(db_path=db_path, enabled=True)
        recent = mem2.recent(n=10)
        ids = [e.id for e in recent]
        assert_true("MEM-12: episode persists across instances", ep_id in ids)


# ---------------------------------------------------------------------------
# MEM-13: missing brain_state / homeostasis graceful
# ---------------------------------------------------------------------------
def test_mem_13():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        try:
            ep = mem.record_cycle("c-no-extras", _smfoi(),
                                  brain_state=None, homeostasis_result=None)
            assert_true("MEM-13: None args → Episode", isinstance(ep, Episode))
        except Exception as e:
            fail("MEM-13: None brain_state/homeostasis", str(e))


# ---------------------------------------------------------------------------
# MEM-14: Episode.create factory
# ---------------------------------------------------------------------------
def test_mem_14():
    ep = Episode.create(
        cycle_id="factory-test",
        content={"action": "test", "value": 42},
        outcome=0.75,
        novelty=0.3,
        memory_type=MemoryType.EVENT,
    )
    assert_true("MEM-14a: Episode created", isinstance(ep, Episode))
    assert_eq("MEM-14b: cycle_id", ep.cycle_id, "factory-test")
    assert_eq("MEM-14c: memory_type", ep.memory_type, MemoryType.EVENT)
    assert_range("MEM-14d: outcome", ep.outcome, 0.74, 0.76)
    assert_true("MEM-14e: id auto-assigned", bool(ep.id))


# ---------------------------------------------------------------------------
# MEM-15: metrics() structure counting + store()
# ---------------------------------------------------------------------------
def test_mem_15():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _make_memory(tmp)
        for i in range(5):
            ep = Episode.create(
                cycle_id=f"struct-{i}",
                content={"test": True},
                outcome=0.7,
                novelty=0.05,
                memory_type=MemoryType.STRUCTURE,
            )
            mem.store(ep)
        m = mem.metrics()
        assert_true("MEM-15a: structures ≥ 5", m["structures"] >= 5)
        assert_true("MEM-15b: count ≥ 5", m["count"] >= 5)
        assert_range("MEM-15c: avg_outcome in [0,1]", m["avg_outcome"], 0.0, 1.0)
        assert_true("MEM-15d: continuity in metrics", "continuity" in m)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TEST SUITE M5.8+M5.9 — AutobiographicalMemory")
    print("  Tests: MEM-01 → MEM-15")
    print("=" * 60)

    test_mem_01()
    test_mem_02()
    test_mem_03()
    test_mem_04()
    test_mem_05()
    test_mem_06()
    test_mem_07()
    test_mem_08()
    test_mem_09()
    test_mem_10()
    test_mem_11()
    test_mem_12()
    test_mem_13()
    test_mem_14()
    test_mem_15()

    print("\n" + "=" * 60)
    print(f"  RISULTATO: {PASS} PASS  |  {FAIL} FAIL")
    if ERRORS:
        print("\n  Errori:")
        for e in ERRORS:
            print(f"    {e}")
    print("=" * 60 + "\n")
    sys.exit(0 if FAIL == 0 else 1)
