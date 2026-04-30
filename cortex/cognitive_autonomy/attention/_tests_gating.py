"""
Test suite M5.11 — AttentionGating (policy uniforme + salience)
Tests: AG-01 → AG-18

Run:
    cd SPEACE-prototipo
    PYTHONPATH=. python cortex/cognitive_autonomy/attention/_tests_gating.py
"""
from __future__ import annotations
import sys, math
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.attention import (
    AttentionPolicy, AttentionStream, GatingResult,
    AttentionGating, create_uniform_gating, create_salience_gating,
)

PASS = 0; FAIL = 0; ERRORS = []

def ok(n, r=""): global PASS; PASS += 1; print(f"  PASS  {n}")
def fail(n, r): global FAIL; FAIL += 1; msg = f"  FAIL  {n}: {r}"; print(msg); ERRORS.append(msg)
def rng(n, v, lo, hi): (ok if lo <= v <= hi else lambda n: fail(n, f"{v:.4f} ∉ [{lo},{hi}]"))(n)
def eq(n, g, e): (ok if g == e else lambda n: fail(n, f"got={g!r} exp={e!r}"))(n)
def true_(n, x, m=""): (ok if x else lambda n: fail(n, m or "False"))(n)
def lt(n, v, t): (ok if v < t else lambda n: fail(n, f"{v:.4f} not < {t}"))(n)
def gt(n, v, t): (ok if v > t else lambda n: fail(n, f"{v:.4f} not > {t}"))(n)


def _streams(n: int, salience: float | None = None) -> list:
    if salience is None:
        return [AttentionStream(f"s{i}", salience=0.5) for i in range(n)]
    return [AttentionStream(f"s{i}", salience=salience) for i in range(n)]


# AG-01: import
def test_ag_01():
    try:
        from cortex.cognitive_autonomy.attention import AttentionGating
        ok("AG-01: import OK")
    except Exception as e:
        fail("AG-01: import", str(e))

# AG-02: empty streams → empty result
def test_ag_02():
    g = create_uniform_gating()
    r = g.compute([])
    eq("AG-02a: empty weights", r.weights, {})
    eq("AG-02b: n_streams=0", r.n_streams, 0)

# AG-03: uniform — all weights equal
def test_ag_03():
    g = create_uniform_gating(min_weight=0.0)
    streams = _streams(4)
    r = g.compute(streams)
    ws = list(r.weights.values())
    rng("AG-03a: each weight ≈ 0.25", ws[0], 0.249, 0.251)
    rng("AG-03b: sum ≈ 1.0", sum(ws), 0.999, 1.001)
    eq("AG-03c: n_streams=4", r.n_streams, 4)

# AG-04: uniform — entropy = log2(N)
def test_ag_04():
    g = create_uniform_gating(min_weight=0.0)
    r = g.compute(_streams(8))
    expected = math.log2(8)
    rng("AG-04: entropy ≈ log2(8)=3.0", r.entropy, 2.99, 3.01)

# AG-05: salience — proportional weights
def test_ag_05():
    g = create_salience_gating(min_weight=0.0)
    streams = [AttentionStream("hi", salience=0.9),
               AttentionStream("lo", salience=0.1)]
    r = g.compute(streams)
    rng("AG-05a: hi_weight ≈ 0.9", r.weights["hi"], 0.89, 0.91)
    rng("AG-05b: lo_weight ≈ 0.1", r.weights["lo"], 0.09, 0.11)

# AG-06: salience all-zero → fallback uniform
def test_ag_06():
    g = create_salience_gating(min_weight=0.0)
    streams = [AttentionStream("a", salience=0.0),
               AttentionStream("b", salience=0.0)]
    r = g.compute(streams)
    rng("AG-06: fallback uniform = 0.5", r.weights["a"], 0.49, 0.51)

# AG-07: weights always sum to 1.0
def test_ag_07():
    for pol in ("uniform", "salience"):
        g = AttentionGating(policy=pol, min_weight=0.01)
        streams = [AttentionStream(f"x{i}", salience=float(i+1)/10) for i in range(6)]
        r = g.compute(streams)
        rng(f"AG-07[{pol}]: sum=1.0", sum(r.weights.values()), 0.999, 1.001)

# AG-08: min_weight floor applied
def test_ag_08():
    g = AttentionGating(policy="salience", min_weight=0.05)
    streams = [AttentionStream("dominant", salience=0.99),
               AttentionStream("tiny", salience=0.001)]
    r = g.compute(streams)
    rng("AG-08: min weight floor applied (> default 0.01)", r.min_weight, 0.04, 0.15)

# AG-09: GatingResult fields
def test_ag_09():
    g = create_uniform_gating()
    r = g.compute(_streams(3))
    true_("AG-09a: has weights", isinstance(r.weights, dict))
    true_("AG-09b: has policy", isinstance(r.policy, AttentionPolicy))
    true_("AG-09c: has entropy", isinstance(r.entropy, float))
    true_("AG-09d: has focus_stream", r.focus_stream is not None)

# AG-10: focus_stream = stream with max weight
def test_ag_10():
    g = create_salience_gating(min_weight=0.0)
    streams = [AttentionStream("max", salience=0.9),
               AttentionStream("mid", salience=0.5),
               AttentionStream("min_s", salience=0.1)]
    r = g.compute(streams)
    eq("AG-10: focus_stream = 'max'", r.focus_stream, "max")

# AG-11: single stream → weight = 1.0
def test_ag_11():
    g = create_uniform_gating(min_weight=0.0)
    r = g.compute([AttentionStream("solo", salience=0.7)])
    rng("AG-11: single stream weight = 1.0", r.weights["solo"], 0.999, 1.001)

# AG-12: entropy increases with more uniform weights
def test_ag_12():
    g = create_salience_gating(min_weight=0.0)
    skewed   = [AttentionStream("a", 0.95), AttentionStream("b", 0.05)]
    balanced = [AttentionStream("a", 0.5),  AttentionStream("b", 0.5)]
    r_skew = g.compute(skewed)
    r_bal  = g.compute(balanced)
    gt("AG-12: balanced > skewed entropy", r_bal.entropy, r_skew.entropy)

# AG-13: call_count increments
def test_ag_13():
    g = create_uniform_gating()
    for _ in range(5):
        g.compute(_streams(3))
    eq("AG-13: call_count=5", g.get_stats()["call_count"], 5)

# AG-14: get_stats returns dict with required keys
def test_ag_14():
    g = create_uniform_gating()
    g.compute(_streams(4))
    s = g.get_stats()
    for k in ["policy", "call_count", "avg_entropy", "diversity_ok"]:
        true_(f"AG-14: key '{k}' in stats", k in s)

# AG-15: diversity_ok for uniform policy (max entropy)
def test_ag_15():
    g = create_uniform_gating()
    for _ in range(10):
        g.compute(_streams(8))
    true_("AG-15: uniform policy → diversity_ok=True", g.diversity_ok())

# AG-16: update_reward accumulates
def test_ag_16():
    g = create_uniform_gating()
    g.update_reward("stream_a", 0.5)
    g.update_reward("stream_a", 0.3)
    stats = g.get_reward_stats()
    true_("AG-16a: stream_a in reward stats", "stream_a" in stats)
    rng("AG-16b: total reward ≈ 0.8", stats["stream_a"]["total"], 0.79, 0.81)
    eq("AG-16c: count=2", stats["stream_a"]["count"], 2.0)

# AG-17: reset_history clears stats
def test_ag_17():
    g = create_uniform_gating()
    for _ in range(5):
        g.compute(_streams(4))
    g.reset_history()
    eq("AG-17: call_count=0 after reset", g.get_stats()["call_count"], 0)

# AG-18: factories create correct policy
def test_ag_18():
    u = create_uniform_gating()
    s = create_salience_gating()
    eq("AG-18a: uniform factory", u.policy, AttentionPolicy.UNIFORM)
    eq("AG-18b: salience factory", s.policy, AttentionPolicy.SALIENCE)


if __name__ == "__main__":
    print("\n" + "=" * 58)
    print("  TEST SUITE M5.11 — AttentionGating (uniform + salience)")
    print("  Tests: AG-01 → AG-18")
    print("=" * 58)
    test_ag_01(); test_ag_02(); test_ag_03(); test_ag_04()
    test_ag_05(); test_ag_06(); test_ag_07(); test_ag_08()
    test_ag_09(); test_ag_10(); test_ag_11(); test_ag_12()
    test_ag_13(); test_ag_14(); test_ag_15(); test_ag_16()
    test_ag_17(); test_ag_18()
    print("\n" + "=" * 58)
    print(f"  RISULTATO: {PASS} PASS  |  {FAIL} FAIL")
    if ERRORS:
        print("\n  Errori:")
        for e in ERRORS: print(f"    {e}")
    print("=" * 58 + "\n")
    sys.exit(0 if FAIL == 0 else 1)


# ---------------------------------------------------------------------------
# M5.12 — UCB1 bandit tests: RL-19 → RL-24
# ---------------------------------------------------------------------------

def test_rl_19():
    """RL-19: UCB1 cold start → uniform weights."""
    g = AttentionGating(policy="rl", min_weight=0.0)
    streams = [AttentionStream(f"s{i}", 0.5) for i in range(4)]
    r = g.compute(streams)
    ws = list(r.weights.values())
    for w in ws:
        (ok if 0.24 <= w <= 0.26 else fail)("RL-19: cold-start UCB1 ≈ uniform",
                                             f"w={w:.3f} not ≈ 0.25" if w < 0.24 or w > 0.26 else "")
    ok("RL-19: UCB1 cold start → uniform")

def test_rl_20():
    """RL-20: UCB1 focuses on high-reward stream after feedback."""
    g = AttentionGating(policy="rl", min_weight=0.0)
    streams = [AttentionStream("hi", 0.5), AttentionStream("lo", 0.5)]
    for _ in range(30):
        g.update_reward("hi", 0.9)
        g.update_reward("lo", 0.1)
    r = g.compute(streams)
    (ok if r.focus_stream == "hi" else fail)("RL-20: focus on high-reward stream",
                                             f"got {r.focus_stream}")
    (ok if r.weights["hi"] > r.weights["lo"] else fail)(
        "RL-20b: hi_weight > lo_weight",
        f"hi={r.weights['hi']:.3f} lo={r.weights['lo']:.3f}"
    )

def test_rl_21():
    """RL-21: unexplored stream gets extra exploration (inf → max*2 weight)."""
    g = AttentionGating(policy="rl", min_weight=0.0)
    streams = [AttentionStream("seen", 0.5), AttentionStream("new", 0.5)]
    g.update_reward("seen", 0.5)  # only "seen" has history
    r = g.compute(streams)
    # "new" should get highest weight (infinite UCB → max*2)
    (ok if r.focus_stream == "new" else fail)(
        "RL-21: unexplored stream wins exploration",
        f"got {r.focus_stream}"
    )

def test_rl_22():
    """RL-22: weights sum to 1.0 after UCB1."""
    g = AttentionGating(policy="rl", min_weight=0.01)
    streams = [AttentionStream(f"s{i}", 0.5) for i in range(5)]
    for i, s in enumerate(streams):
        g.update_reward(s.id, float(i) / 4)
    r = g.compute(streams)
    s = sum(r.weights.values())
    (ok if 0.999 <= s <= 1.001 else fail)("RL-22: UCB1 weights sum=1.0",
                                           f"sum={s:.4f}")

def test_rl_23():
    """RL-23: negative rewards → stream deprioritized."""
    g = AttentionGating(policy="rl", min_weight=0.0)
    streams = [AttentionStream("bad", 0.5), AttentionStream("good", 0.5)]
    for _ in range(30):
        g.update_reward("bad", -0.9)
        g.update_reward("good", 0.9)
    r = g.compute(streams)
    (ok if r.weights["good"] > r.weights["bad"] else fail)(
        "RL-23: negative rewards → deprioritized",
        f"good={r.weights['good']:.3f} bad={r.weights['bad']:.3f}"
    )

# ---------------------------------------------------------------------------
# M5.13 — Diversity entropy check: DIV-24 → DIV-26
# ---------------------------------------------------------------------------

def test_div_24():
    """DIV-24: uniform policy N=8 → entropy ≥ 2.0 bit."""
    g = create_uniform_gating()
    for _ in range(5):
        g.compute([AttentionStream(f"s{i}", 0.5) for i in range(8)])
    avg_h = g.get_stats()["avg_entropy"]
    (ok if avg_h >= 2.0 else fail)("DIV-24: uniform N=8 entropy ≥ 2.0 bit",
                                    f"got {avg_h:.3f}")

def test_div_25():
    """DIV-25: salience policy balanced N=4 → entropy ≥ 1.8 bit."""
    g = create_salience_gating()
    for _ in range(5):
        streams = [AttentionStream(f"s{i}", 0.25) for i in range(4)]
        g.compute(streams)
    avg_h = g.get_stats()["avg_entropy"]
    (ok if avg_h >= 1.8 else fail)("DIV-25: balanced salience N=4 entropy ≥ 1.8 bit",
                                    f"got {avg_h:.3f}")

def test_div_26():
    """DIV-26: single-dominant salience → diversity_ok=False with threshold=2.0."""
    g = AttentionGating(policy="salience", min_weight=0.0, diversity_threshold=2.0)
    # Very skewed: one stream dominates
    for _ in range(10):
        streams = [AttentionStream("dom", 0.999)] + [AttentionStream(f"s{i}", 0.001) for i in range(3)]
        g.compute(streams)
    # Entropy will be very low → diversity_ok should be False
    (ok if not g.diversity_ok() else fail)(
        "DIV-26: dominant stream → diversity_ok=False",
        f"entropy={g.get_stats()['avg_entropy']:.3f}"
    )


# Patch __main__ runner to include new tests
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SUITE M5.12+M5.13 — UCB1 + Diversity Entropy")
    print("  Tests: RL-19 → RL-23  |  DIV-24 → DIV-26")
    print("=" * 60)
    test_rl_19(); test_rl_20(); test_rl_21()
    test_rl_22(); test_rl_23()
    test_div_24(); test_div_25(); test_div_26()
    print("\n" + "=" * 60)
    print(f"  RISULTATO: {PASS} PASS  |  {FAIL} FAIL")
    if ERRORS:
        for e in ERRORS: print(f"    {e}")
    print("=" * 60 + "\n")
    import sys; sys.exit(0 if FAIL == 0 else 1)
