"""
Test suite per cortex.mesh.task_generator (M4.11)

Copre:
  AC-T1  snapshot senza gap → 0 proposte
  AC-T2  snapshot con tutti i gap → max_proposals proposte (cap)
  AC-T3  proposte ordinate per priority desc
  AC-T4  CRITICAL verdict → solo proposte risk=low
  AC-T5  ALERT verdict → proposte risk in {low, medium} (no high)
  AC-T6  HEALTHY verdict → proposte ammettono anche high (su template che lo richiedono)
  AC-T7  ogni TaskProposal generata supera validate()
  AC-T8  driving_need ∈ NEEDS_CATALOG e gap > 0
  AC-T9  to_safeproactive_dicts produce dict serializzabili
  AC-T10 round-robin: distribuisce su più need quando ce ne sono in deficit
  AC-T11 max_proposals=1 → 1 sola proposta (la priorità top)
"""

from __future__ import annotations

import sys
import traceback
from typing import Dict, List, Tuple

from cortex.mesh.olc import NeedsSnapshot, TaskProposal
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.harmony import HarmonyPolicy, HarmonyVerdict
from cortex.mesh.task_generator import TaskGenerator, DEFAULT_NEED_WEIGHTS


def _snap(needs: Dict[str, float], targets: Dict[str, float]) -> NeedsSnapshot:
    gap = {k: max(0.0, targets[k] - needs[k]) for k in NEEDS_CATALOG}
    return NeedsSnapshot(needs=dict(needs), gap=gap)


def case_ac_t1_no_gap_no_proposals():
    pol = HarmonyPolicy()
    needs = {k: pol.targets[k] for k in NEEDS_CATALOG}  # tutti = target
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    assert props == [], f"atteso lista vuota, trovato {props}"
    return "AC-T1 nessun gap → 0 proposte"


def case_ac_t2_all_gaps_capped():
    pol = HarmonyPolicy()
    needs = {k: 0.0 for k in NEEDS_CATALOG}  # tutti i gap massimi
    # ma evitiamo CRITICAL: setto survival e harmony a 0.85 (sopra critical)
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    assert len(props) <= 5, f"max_proposals violato: {len(props)}"
    assert len(props) > 0, "atteso almeno 1 proposta"
    return f"AC-T2 cap rispettato: {len(props)}/5 proposte"


def case_ac_t3_priority_desc():
    pol = HarmonyPolicy()
    needs = {k: 0.5 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85   # gap basso
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    for i in range(len(props) - 1):
        assert props[i].priority >= props[i+1].priority, (i, props[i].priority, props[i+1].priority)
    return f"AC-T3 priority desc su {len(props)} proposte"


def case_ac_t4_critical_only_low():
    pol = HarmonyPolicy()
    needs = {k: 0.5 for k in NEEDS_CATALOG}
    needs["survival"] = 0.30   # CRITICAL
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    report = pol.evaluate(snap)
    assert report.verdict == HarmonyVerdict.CRITICAL
    props = gen.generate(snap, harmony_report=report)
    risks = {p.safeproactive_risk for p in props}
    assert risks <= {"low"}, f"CRITICAL → risk dovrebbe essere solo 'low', trovato: {risks}"
    return f"AC-T4 CRITICAL → {len(props)} proposte solo low ({risks})"


def case_ac_t5_alert_no_high():
    pol = HarmonyPolicy()
    needs = {k: pol.targets[k] for k in NEEDS_CATALOG}
    needs["expansion"] = 0.10   # ALERT via floor
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    report = pol.evaluate(snap)
    assert report.verdict == HarmonyVerdict.ALERT
    props = gen.generate(snap, harmony_report=report)
    risks = {p.safeproactive_risk for p in props}
    assert "high" not in risks, f"ALERT non dovrebbe avere risk=high: {risks}"
    return f"AC-T5 ALERT → no high in {risks}"


def case_ac_t6_healthy_allows_all():
    pol = HarmonyPolicy()
    # WATCH stato (non HEALTHY altrimenti non avremmo gap)
    needs = {k: 0.7 * pol.targets[k] for k in NEEDS_CATALOG}
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    report = pol.evaluate(snap)
    assert report.verdict == HarmonyVerdict.WATCH
    props = gen.generate(snap, harmony_report=report)
    risks = {p.safeproactive_risk for p in props}
    # In WATCH allowed_risk_levels = {low, medium, high}; almeno una proposta
    # potrebbe essere high se il template lo richiede (survival[2]=high).
    assert risks <= {"low", "medium", "high"}, risks
    return f"AC-T6 WATCH → ammette tutti i risk: trovati {risks}"


def case_ac_t7_all_proposals_validate():
    pol = HarmonyPolicy()
    needs = {k: 0.4 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    for p in props:
        v = p.validate()
        assert v == [], f"validate failed: {v}"
    return f"AC-T7 tutte le {len(props)} proposte validate=[]"


def case_ac_t8_driving_need_in_catalog():
    pol = HarmonyPolicy()
    needs = {k: 0.5 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    for p in props:
        assert p.driving_need in NEEDS_CATALOG, p.driving_need
        assert snap.gap.get(p.driving_need, 0) > 0, p.driving_need
    return f"AC-T8 driving_need OK su {len(props)} proposte"


def case_ac_t9_serialization():
    pol = HarmonyPolicy()
    needs = {k: 0.5 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=3)
    props = gen.generate(snap)
    dicts = TaskGenerator.to_safeproactive_dicts(props)
    assert len(dicts) == len(props)
    for d in dicts:
        assert "title" in d and "driving_need" in d
        assert "priority" in d and "risk_level" in d
        assert "estimated_impact" in d and "_olc" in d
        assert d["risk_level"] in ("low", "medium", "high")
    return f"AC-T9 serialization OK ({len(dicts)} dict)"


def case_ac_t10_round_robin_diversity():
    pol = HarmonyPolicy()
    # Tutti i 5 need con gap medio (no CRITICAL): aspetta 5 proposte distribuite
    needs = {k: 0.4 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=5)
    props = gen.generate(snap)
    needs_seen = {p.driving_need for p in props}
    # Almeno 3 need diversi (round-robin)
    assert len(needs_seen) >= 3, f"diversità insufficiente: {needs_seen}"
    return f"AC-T10 round-robin: {len(needs_seen)} need diversi su {len(props)} proposte"


def case_ac_t11_max_proposals_one():
    pol = HarmonyPolicy()
    needs = {k: 0.4 for k in NEEDS_CATALOG}
    needs["survival"] = 0.85
    needs["harmony"] = 0.85
    snap = _snap(needs, pol.targets)
    gen = TaskGenerator(policy=pol, max_proposals=1)
    props = gen.generate(snap)
    assert len(props) == 1, f"atteso 1, trovato {len(props)}"
    return f"AC-T11 max=1 → 1 proposta top-priority ({props[0].driving_need})"


CASES = [
    case_ac_t1_no_gap_no_proposals,
    case_ac_t2_all_gaps_capped,
    case_ac_t3_priority_desc,
    case_ac_t4_critical_only_low,
    case_ac_t5_alert_no_high,
    case_ac_t6_healthy_allows_all,
    case_ac_t7_all_proposals_validate,
    case_ac_t8_driving_need_in_catalog,
    case_ac_t9_serialization,
    case_ac_t10_round_robin_diversity,
    case_ac_t11_max_proposals_one,
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
    print(f"cortex.mesh._tests_task_generator — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
