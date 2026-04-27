"""
Test suite per cortex.mesh.harmony (M4.10)

Copre:
  AC-H1  policy con tutti i need ≥ healthy → HEALTHY
  AC-H2  uno o più need in fascia watch → WATCH
  AC-H3  gap > soglia o sotto floor → ALERT
  AC-H4  survival < critical_survival → CRITICAL
  AC-H5  harmony < critical_harmony → CRITICAL
  AC-H6  CRITICAL produce compensations richieste umane + restrizione risk a {low}
  AC-H7  ALERT ammette {low, medium} ma non high
  AC-H8  HEALTHY/WATCH ammettono {low, medium, high}
  AC-H9  CompensationAction.kind invalido → ValueError
  AC-H10 HarmonyReport.to_dict serializza completamente
  AC-H11 dedupe compensations preserva la severity max
  AC-H12 idempotenza: stesso snapshot → stesso report (a meno di ts)

Esecuzione: python -m cortex.mesh._tests_harmony
"""

from __future__ import annotations

import sys
import traceback
from typing import Dict, List, Tuple

from cortex.mesh.olc import NeedsSnapshot
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.harmony import (
    HarmonyPolicy,
    HarmonyVerdict,
    HarmonyReport,
    CompensationAction,
    COMPENSATION_KINDS,
)


# -------------------------------------------------------------- helpers --


def _snap(needs: Dict[str, float], targets: Dict[str, float]) -> NeedsSnapshot:
    gap = {k: max(0.0, targets[k] - needs[k]) for k in NEEDS_CATALOG}
    return NeedsSnapshot(needs=dict(needs), gap=gap)


def _full(value: float) -> Dict[str, float]:
    return {k: value for k in NEEDS_CATALOG}


# -------------------------------------------------------------- cases --


def case_ac_h1_healthy():
    pol = HarmonyPolicy()
    needs = {k: pol.targets[k] for k in NEEDS_CATALOG}  # tutti = target
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.HEALTHY, rep.verdict
    assert rep.allowed_risk_levels == frozenset({"low", "medium", "high"})
    assert rep.compensations == ()
    return f"AC-H1 HEALTHY (5/5 need a target)"


def case_ac_h2_watch():
    pol = HarmonyPolicy()
    # Tutti a 0.7×target → fascia watch (sotto healthy_ratio=0.85)
    needs = {k: 0.7 * pol.targets[k] for k in NEEDS_CATALOG}
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.WATCH, (rep.verdict, needs)
    return f"AC-H2 WATCH ({len(rep.needs_below_target)} need sotto soglia healthy)"


def case_ac_h3_alert_via_floor():
    pol = HarmonyPolicy()
    # expansion sotto watch_floor (0.5*target)
    needs = {k: pol.targets[k] for k in NEEDS_CATALOG}
    needs["expansion"] = 0.20  # < 0.5 * 0.7
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.ALERT, rep.verdict
    return f"AC-H3 ALERT via floor (expansion={needs['expansion']})"


def case_ac_h4_critical_survival():
    pol = HarmonyPolicy()
    needs = _full(0.9)
    needs["survival"] = 0.40  # < critical_survival 0.5
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.CRITICAL, rep.verdict
    return f"AC-H4 CRITICAL via survival={needs['survival']}"


def case_ac_h5_critical_harmony():
    pol = HarmonyPolicy()
    needs = _full(0.9)
    needs["harmony"] = 0.20  # < critical_harmony 0.30
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.CRITICAL, rep.verdict
    return f"AC-H5 CRITICAL via harmony={needs['harmony']}"


def case_ac_h6_critical_compensations():
    pol = HarmonyPolicy()
    needs = _full(0.9)
    needs["survival"] = 0.30
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    kinds = {c.kind for c in rep.compensations}
    # CRITICAL → block high+medium, throttle, elevate_human_review, alert_operator,
    # request_quarantine_review (survival<0.7)
    expected = {
        "block_high_risk_proposals",
        "block_medium_risk_proposals",
        "throttle_side_effects",
        "elevate_human_review",
        "alert_operator",
        "request_quarantine_review",
    }
    missing = expected - kinds
    assert not missing, f"missing comp kinds: {missing} (got: {kinds})"
    assert rep.allowed_risk_levels == frozenset({"low"})
    return f"AC-H6 CRITICAL compensations completi ({len(rep.compensations)} actions)"


def case_ac_h7_alert_allows_low_medium():
    pol = HarmonyPolicy()
    needs = {k: pol.targets[k] for k in NEEDS_CATALOG}
    needs["expansion"] = 0.10  # alert via floor
    snap = _snap(needs, pol.targets)
    rep = pol.evaluate(snap)
    assert rep.verdict == HarmonyVerdict.ALERT
    assert rep.allowed_risk_levels == frozenset({"low", "medium"}), rep.allowed_risk_levels
    return f"AC-H7 ALERT → allowed=low+medium (no high)"


def case_ac_h8_healthy_watch_allow_high():
    pol = HarmonyPolicy()
    # HEALTHY
    healthy = pol.evaluate(_snap({k: pol.targets[k] for k in NEEDS_CATALOG}, pol.targets))
    assert "high" in healthy.allowed_risk_levels
    # WATCH
    watch_needs = {k: 0.7 * pol.targets[k] for k in NEEDS_CATALOG}
    watch = pol.evaluate(_snap(watch_needs, pol.targets))
    assert watch.verdict == HarmonyVerdict.WATCH
    assert "high" in watch.allowed_risk_levels
    return "AC-H8 HEALTHY/WATCH ammettono high (con human approver via contract)"


def case_ac_h9_invalid_compensation_kind():
    try:
        CompensationAction(
            kind="not_a_real_kind",
            target="x",
            rationale="y",
            severity=1,
        )
    except ValueError as e:
        return f"AC-H9 invalid kind → ValueError ({str(e)[:60]}...)"
    raise AssertionError("ValueError atteso ma non sollevato")


def case_ac_h10_to_dict_serialization():
    pol = HarmonyPolicy()
    needs = _full(0.9)
    needs["harmony"] = 0.20  # CRITICAL
    rep = pol.evaluate(_snap(needs, pol.targets))
    d = rep.to_dict()
    assert d["verdict"] == "critical"
    assert d["severity"] == 3
    assert isinstance(d["compensations"], list) and len(d["compensations"]) > 0
    assert "low" in d["allowed_risk_levels"]
    assert "rationale" in d and "snapshot_ts" in d
    # Tutte le compensations devono avere kind in COMPENSATION_KINDS
    for c in d["compensations"]:
        assert c["kind"] in COMPENSATION_KINDS, c["kind"]
    return f"AC-H10 to_dict serializza CRITICAL report ({len(d['compensations'])} actions)"


def case_ac_h11_dedupe_severity():
    pol = HarmonyPolicy()
    # Triggera CRITICAL: dovrebbe produrre block_high_risk_proposals con severity=3
    # invece di quello dell'harmony<0.5 (severity=2). Verifichiamo dedupe.
    needs = _full(0.9)
    needs["harmony"] = 0.10  # CRITICAL via harmony
    rep = pol.evaluate(_snap(needs, pol.targets))
    blocks = [c for c in rep.compensations if c.kind == "block_high_risk_proposals"]
    assert len(blocks) == 1, f"dedupe failed: {len(blocks)} block_high_risk_proposals"
    assert blocks[0].severity == 3, f"dedupe should keep severity=3, got {blocks[0].severity}"
    return "AC-H11 dedupe preserva severity max (3)"


def case_ac_h12_idempotency():
    pol = HarmonyPolicy()
    needs = _full(0.6)
    snap = _snap(needs, pol.targets)
    r1 = pol.evaluate(snap)
    r2 = pol.evaluate(snap)
    assert r1.verdict == r2.verdict
    assert r1.allowed_risk_levels == r2.allowed_risk_levels
    assert tuple(c.kind for c in r1.compensations) == tuple(c.kind for c in r2.compensations)
    return f"AC-H12 idempotenza: 2 evaluate identiche → stesso verdict={r1.verdict.value}"


CASES = [
    case_ac_h1_healthy,
    case_ac_h2_watch,
    case_ac_h3_alert_via_floor,
    case_ac_h4_critical_survival,
    case_ac_h5_critical_harmony,
    case_ac_h6_critical_compensations,
    case_ac_h7_alert_allows_low_medium,
    case_ac_h8_healthy_watch_allow_high,
    case_ac_h9_invalid_compensation_kind,
    case_ac_h10_to_dict_serialization,
    case_ac_h11_dedupe_severity,
    case_ac_h12_idempotency,
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
    print(f"cortex.mesh._tests_harmony — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
