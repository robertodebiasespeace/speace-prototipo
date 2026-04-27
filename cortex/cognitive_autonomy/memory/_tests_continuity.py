"""
Test suite M5.10 — continuity_score() multi-dimensionale
Tests: CS-01 → CS-14

Verifica:
  - 3 componenti: outcome stability (S1), type coherence (S2), temporal (S3)
  - Score cade visibilmente dopo simulazione mutazione DNA (cambio brusco)
  - continuity_breakdown() ritorna dict strutturato

Run:
    cd SPEACE-prototipo
    PYTHONPATH=. python cortex/cognitive_autonomy/memory/_tests_continuity.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.memory import (
    AutobiographicalMemory, Episode, MemoryType,
)

# ---------------------------------------------------------------------------
# Runner
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


def assert_range(name, val, lo, hi):
    if lo <= val <= hi:
        ok(name)
    else:
        fail(name, f"{val:.4f} not in [{lo}, {hi}]")


def assert_gt(name, val, threshold):
    if val > threshold:
        ok(name)
    else:
        fail(name, f"{val:.4f} not > {threshold}")


def assert_lt(name, val, threshold):
    if val < threshold:
        ok(name)
    else:
        fail(name, f"{val:.4f} not < {threshold}")


def assert_true(name, expr, msg=""):
    if expr:
        ok(name)
    else:
        fail(name, msg or "condition False")


def assert_in(name, key, d):
    if key in d:
        ok(name)
    else:
        fail(name, f"key '{key}' not in {list(d.keys())}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mem(tmp_dir: str) -> AutobiographicalMemory:
    return AutobiographicalMemory(
        db_path=Path(tmp_dir) / "continuity_test.sqlite", enabled=True
    )


def _record_stable(mem, n: int = 20, base: float = 0.70, jitter: float = 0.01):
    """Registra n episodi stabili attorno a base ± jitter."""
    import random
    random.seed(42)
    for i in range(n):
        outcome = base + random.uniform(-jitter, jitter)
        ep = Episode.create(
            cycle_id=f"stable-{i}",
            content={"type": "stable"},
            outcome=outcome,
            novelty=0.05,
            memory_type=MemoryType.STRUCTURE,
        )
        mem.store(ep)


def _record_chaotic(mem, n: int = 20, seed: int = 0):
    """Registra n episodi caotici con alta varianza (simula mutazione DNA)."""
    import random
    random.seed(seed)
    for i in range(n):
        outcome = random.uniform(0.1, 0.95)
        ep = Episode.create(
            cycle_id=f"chaotic-{i}",
            content={"type": "chaotic"},
            outcome=outcome,
            novelty=0.90,
            memory_type=MemoryType.EVENT,
        )
        mem.store(ep)


# ---------------------------------------------------------------------------
# CS-01: disabled → 1.0
# ---------------------------------------------------------------------------
def test_cs_01():
    with tempfile.TemporaryDirectory() as tmp:
        mem = AutobiographicalMemory(
            db_path=Path(tmp) / "d.sqlite", enabled=False
        )
        score = mem.continuity_score()
        assert_range("CS-01: disabled → 1.0", score, 1.0, 1.0)


# ---------------------------------------------------------------------------
# CS-02: empty db → 1.0
# ---------------------------------------------------------------------------
def test_cs_02():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        score = mem.continuity_score()
        assert_range("CS-02: empty → 1.0", score, 1.0, 1.0)


# ---------------------------------------------------------------------------
# CS-03: < 3 episodes → 1.0
# ---------------------------------------------------------------------------
def test_cs_03():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        for i in range(2):
            mem.store(Episode.create(f"c-{i}", {}, 0.7, 0.1, MemoryType.STRUCTURE))
        score = mem.continuity_score()
        assert_range("CS-03: <3 eps → 1.0", score, 1.0, 1.0)


# ---------------------------------------------------------------------------
# CS-04: stable outcomes → high score
# ---------------------------------------------------------------------------
def test_cs_04():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_stable(mem, n=20, base=0.70, jitter=0.01)
        score = mem.continuity_score()
        assert_gt("CS-04: stable → score > 0.70", score, 0.70)


# ---------------------------------------------------------------------------
# CS-05: chaotic outcomes → low score
# ---------------------------------------------------------------------------
def test_cs_05():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_chaotic(mem, n=20)
        score = mem.continuity_score()
        assert_lt("CS-05: chaotic → score < 0.60", score, 0.60)


# ---------------------------------------------------------------------------
# CS-06: DNA mutation simulation — score drops after mutation
# ---------------------------------------------------------------------------
def test_cs_06():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)

        # Phase 1: stable (pre-mutation)
        _record_stable(mem, n=25, base=0.70, jitter=0.01)
        score_pre = mem.continuity_score()

        # Phase 2: mutation — inject chaotic episodes (simulates DNA mutation)
        _record_chaotic(mem, n=15, seed=99)
        score_post = mem.continuity_score()

        drop = score_pre - score_post
        assert_gt("CS-06a: pre-mutation score > 0.60", score_pre, 0.60)
        assert_gt("CS-06b: score drops after mutation", drop, 0.05)
        print(f"         score_pre={score_pre:.4f} → score_post={score_post:.4f} "
              f"(drop={drop:.4f})")


# ---------------------------------------------------------------------------
# CS-07: score in [0, 1] always
# ---------------------------------------------------------------------------
def test_cs_07():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_chaotic(mem, n=30)
        score = mem.continuity_score()
        assert_range("CS-07: chaotic score in [0,1]", score, 0.0, 1.0)


# ---------------------------------------------------------------------------
# CS-08: continuity_breakdown() keys present
# ---------------------------------------------------------------------------
def test_cs_08():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_stable(mem, n=10)
        bd = mem.continuity_breakdown()
        for key in ["score", "s1_outcome_stability", "s2_type_coherence",
                    "s3_temporal_coherence", "n_episodes"]:
            assert_in(f"CS-08: key '{key}'", key, bd)


# ---------------------------------------------------------------------------
# CS-09: breakdown components in [0, 1]
# ---------------------------------------------------------------------------
def test_cs_09():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_stable(mem, n=15)
        bd = mem.continuity_breakdown()
        for key in ["s1_outcome_stability", "s2_type_coherence", "s3_temporal_coherence"]:
            val = bd[key]
            assert_range(f"CS-09: {key} in [0,1]", val, 0.0, 1.0)


# ---------------------------------------------------------------------------
# CS-10: S2 type_coherence = 1.0 when all STRUCTURE
# ---------------------------------------------------------------------------
def test_cs_10():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        for i in range(10):
            mem.store(Episode.create(f"s-{i}", {}, 0.70, 0.05, MemoryType.STRUCTURE))
        bd = mem.continuity_breakdown()
        assert_range("CS-10: all-STRUCTURE → S2=1.0", bd["s2_type_coherence"], 1.0, 1.0)


# ---------------------------------------------------------------------------
# CS-11: S2 type_coherence = 0.0 when all EVENT
# ---------------------------------------------------------------------------
def test_cs_11():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        for i in range(10):
            mem.store(Episode.create(f"e-{i}", {}, 0.70, 0.80, MemoryType.EVENT))
        bd = mem.continuity_breakdown()
        assert_range("CS-11: all-EVENT → S2=0.0", bd["s2_type_coherence"], 0.0, 0.0)


# ---------------------------------------------------------------------------
# CS-12: S1 outcome_stability near 1.0 when std ≈ 0
# ---------------------------------------------------------------------------
def test_cs_12():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        # All identical outcomes → std=0 → S1=1.0
        for i in range(10):
            mem.store(Episode.create(f"f-{i}", {}, 0.75, 0.05, MemoryType.STRUCTURE))
        bd = mem.continuity_breakdown()
        assert_range("CS-12: std=0 → S1≈1.0", bd["s1_outcome_stability"], 0.99, 1.0)


# ---------------------------------------------------------------------------
# CS-13: window parameter limits episodes
# ---------------------------------------------------------------------------
def test_cs_13():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        # 20 stable + 20 chaotic — window=5 should see only recent (chaotic)
        _record_stable(mem, n=20, base=0.70, jitter=0.01)
        _record_chaotic(mem, n=20, seed=7)
        score_narrow = mem.continuity_score(window=5)
        score_wide   = mem.continuity_score(window=40)
        bd_narrow = mem.continuity_breakdown(window=5)
        assert_range("CS-13a: narrow window score in [0,1]", score_narrow, 0.0, 1.0)
        assert_range("CS-13b: wide window score in [0,1]", score_wide, 0.0, 1.0)
        assert_true("CS-13c: n_episodes narrow ≤ 5", bd_narrow["n_episodes"] <= 5)
        print(f"         score(w=5)={score_narrow:.4f}  score(w=40)={score_wide:.4f}")


# ---------------------------------------------------------------------------
# CS-14: metrics() embeds continuity key
# ---------------------------------------------------------------------------
def test_cs_14():
    with tempfile.TemporaryDirectory() as tmp:
        mem = _mem(tmp)
        _record_stable(mem, n=10)
        m = mem.metrics()
        assert_in("CS-14a: 'continuity' in metrics", "continuity", m)
        assert_range("CS-14b: metrics continuity in [0,1]", m["continuity"], 0.0, 1.0)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TEST SUITE M5.10 — continuity_score() multi-dim")
    print("  Tests: CS-01 → CS-14")
    print("=" * 60)

    test_cs_01()
    test_cs_02()
    test_cs_03()
    test_cs_04()
    test_cs_05()
    test_cs_06()
    test_cs_07()
    test_cs_08()
    test_cs_09()
    test_cs_10()
    test_cs_11()
    test_cs_12()
    test_cs_13()
    test_cs_14()

    print("\n" + "=" * 60)
    print(f"  RISULTATO: {PASS} PASS  |  {FAIL} FAIL")
    if ERRORS:
        print("\n  Errori:")
        for e in ERRORS:
            print(f"    {e}")
    print("=" * 60 + "\n")
    sys.exit(0 if FAIL == 0 else 1)
