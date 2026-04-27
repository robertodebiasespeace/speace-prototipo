"""
Tests M5.17 + M5.18 + M5.19 — ConstraintLayer

Copertura:
  CL-01 to CL-06   ConstraintLayer base checks (M5.17)
  C1-07 to C1-10   C1_COHERENCE constraint
  C2-11 to C2-14   C2_HOMEOSTASIS_BALANCE constraint
  C3-15 to C3-17   C3_AUDIT_TRAIL constraint
  PEN-18 to PEN-22 apply_penalties wiring (M5.18)
  E2E-23 to E2E-26 end-to-end injection + viability degradation (M5.19)

Run:
    cd SPEACE-prototipo
    python -m pytest cortex/cognitive_autonomy/constraints/_tests_constraints.py -v

Milestone: M5.17 + M5.18 + M5.19
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any

import pytest

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE
for _ in range(6):
    if (_ROOT / "cortex").is_dir():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.constraints.constraint_layer import (
    ConstraintResult, ConstraintConfig, ConstraintLayer,
)
from cortex.cognitive_autonomy.homeostasis.controller import (
    HomeostaticController, HomeostasisConfig,
)


# =============================================================================
# Helpers
# =============================================================================

_SP = {
    "safety": 0.80, "energy": 0.60, "coherence": 0.70,
    "curiosity": 0.50, "alignment": 0.75,
}

def _healthy_h() -> Dict[str, float]:
    """Drive in setpoint — nessuna violazione attesa."""
    return dict(_SP)

def _make_controller(update_count: int = 1) -> HomeostaticController:
    cfg = HomeostasisConfig()
    ctrl = HomeostaticController(cfg)
    ctrl._update_count = update_count
    ctrl._h_state = _healthy_h()
    return ctrl


# =============================================================================
# CL — ConstraintLayer base (M5.17)
# =============================================================================

class TestConstraintLayerBase:

    def test_cl01_check_returns_list_of_3(self):
        """CL-01: check() ritorna esattamente 3 ConstraintResult."""
        layer = ConstraintLayer()
        results = layer.check(_healthy_h(), update_count=5)
        assert len(results) == 3

    def test_cl02_all_satisfied_on_healthy_state(self):
        """CL-02: stato sano -> tutti i vincoli soddisfatti."""
        layer = ConstraintLayer()
        results = layer.check(_healthy_h(), update_count=5)
        assert all(r.satisfied for r in results)
        assert all(r.violation_severity == 0.0 for r in results)

    def test_cl03_violations_filters_unsatisfied(self):
        """CL-03: violations() ritorna solo i risultati non soddisfatti."""
        # max_drive_imbalance=0.70 ensure C2 not triggered when coherence=0.10
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.30, max_drive_imbalance=0.70))
        h = _healthy_h()
        h["coherence"] = 0.10   # C1 violato (|0.10-0.70|=0.60 < 0.70 -> C2 ok)
        results = layer.check(h, update_count=5)
        viols = layer.violations(results)
        assert len(viols) == 1
        assert viols[0].constraint_id == "C1_COHERENCE"

    def test_cl04_disabled_layer_returns_empty(self):
        """CL-04: layer disabilitato ritorna lista vuota."""
        layer = ConstraintLayer(ConstraintConfig(enabled=False))
        results = layer.check(_healthy_h(), update_count=0)
        assert results == []

    def test_cl05_violation_history_accumulates(self):
        """CL-05: le violazioni vengono accumulate in violation_history."""
        layer = ConstraintLayer()
        h = _healthy_h()
        h["coherence"] = 0.05
        layer.check(h, update_count=0)   # C1 + C3 violati
        layer.check(h, update_count=0)
        assert layer.violation_count() >= 2

    def test_cl06_get_stats_keys(self):
        """CL-06: get_stats() restituisce check_count, violation_count, enabled, thresholds."""
        layer = ConstraintLayer()
        layer.check(_healthy_h(), update_count=5)
        stats = layer.get_stats()
        assert "check_count" in stats
        assert stats["check_count"] == 1
        assert "violation_count" in stats
        assert "enabled" in stats
        assert "thresholds" in stats


# =============================================================================
# C1 — C1_COHERENCE
# =============================================================================

class TestC1Coherence:

    def test_c1_07_satisfied_above_threshold(self):
        """C1-07: coherence >= min_coherence -> satisfied=True."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.30))
        h = _healthy_h()
        h["coherence"] = 0.50
        results = layer.check(h, update_count=5)
        c1 = next(r for r in results if r.constraint_id == "C1_COHERENCE")
        assert c1.satisfied is True
        assert c1.violation_severity == 0.0

    def test_c1_08_violated_below_threshold(self):
        """C1-08: coherence < min_coherence -> satisfied=False, severity > 0."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.30))
        h = _healthy_h()
        h["coherence"] = 0.10
        results = layer.check(h, update_count=5)
        c1 = next(r for r in results if r.constraint_id == "C1_COHERENCE")
        assert c1.satisfied is False
        assert c1.violation_severity > 0.0
        assert c1.drive_target == "coherence"

    def test_c1_09_severity_proportional_to_deficit(self):
        """C1-09: severity aumenta con il deficit di coerenza."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.50))
        h_mild = _healthy_h()
        h_mild["coherence"] = 0.45   # lieve
        h_severe = _healthy_h()
        h_severe["coherence"] = 0.05  # severo
        r_mild = layer.check(h_mild, 5)
        r_sev = layer.check(h_severe, 5)
        sev_mild = next(r for r in r_mild if r.constraint_id == "C1_COHERENCE").violation_severity
        sev_severe = next(r for r in r_sev if r.constraint_id == "C1_COHERENCE").violation_severity
        assert sev_severe > sev_mild

    def test_c1_10_at_threshold_is_satisfied(self):
        """C1-10: coherence == min_coherence e' soddisfatto (>= non >)."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.30))
        h = _healthy_h()
        h["coherence"] = 0.30
        results = layer.check(h, update_count=5)
        c1 = next(r for r in results if r.constraint_id == "C1_COHERENCE")
        assert c1.satisfied is True


# =============================================================================
# C2 — C2_HOMEOSTASIS_BALANCE
# =============================================================================

class TestC2HomeostasisBalance:

    def test_c2_11_satisfied_small_deviation(self):
        """C2-11: deviation <= max_imbalance -> satisfied=True."""
        layer = ConstraintLayer(ConstraintConfig(max_drive_imbalance=0.40))
        h = _healthy_h()   # h == setpoint -> deviation=0
        results = layer.check(h, update_count=5)
        c2 = next(r for r in results if r.constraint_id == "C2_HOMEOSTASIS_BALANCE")
        assert c2.satisfied is True

    def test_c2_12_violated_large_deviation(self):
        """C2-12: deviation > max_imbalance -> satisfied=False."""
        layer = ConstraintLayer(ConstraintConfig(max_drive_imbalance=0.10))
        h = _healthy_h()
        h["energy"] = 0.95   # dev = |0.95 - 0.60| = 0.35 > 0.10
        results = layer.check(h, update_count=5)
        c2 = next(r for r in results if r.constraint_id == "C2_HOMEOSTASIS_BALANCE")
        assert c2.satisfied is False
        assert c2.violation_severity > 0.0

    def test_c2_13_drive_target_is_worst_drive(self):
        """C2-13: drive_target e' il drive piu' sbilanciato."""
        layer = ConstraintLayer(ConstraintConfig(max_drive_imbalance=0.10))
        h = _healthy_h()
        h["safety"] = 0.10   # dev = |0.10 - 0.80| = 0.70  (worst)
        h["energy"] = 0.70   # dev = |0.70 - 0.60| = 0.10
        results = layer.check(h, update_count=5)
        c2 = next(r for r in results if r.constraint_id == "C2_HOMEOSTASIS_BALANCE")
        assert c2.drive_target == "safety"

    def test_c2_14_severity_bounded_01(self):
        """C2-14: violation_severity in [0, 1]."""
        layer = ConstraintLayer(ConstraintConfig(max_drive_imbalance=0.05))
        h = _healthy_h()
        h["safety"] = 0.0   # massima deviazione
        results = layer.check(h, update_count=5)
        c2 = next(r for r in results if r.constraint_id == "C2_HOMEOSTASIS_BALANCE")
        assert 0.0 <= c2.violation_severity <= 1.0


# =============================================================================
# C3 — C3_AUDIT_TRAIL
# =============================================================================

class TestC3AuditTrail:

    def test_c3_15_satisfied_with_updates(self):
        """C3-15: update_count >= min_update_count -> satisfied=True."""
        layer = ConstraintLayer(ConstraintConfig(min_update_count=3))
        results = layer.check(_healthy_h(), update_count=5)
        c3 = next(r for r in results if r.constraint_id == "C3_AUDIT_TRAIL")
        assert c3.satisfied is True

    def test_c3_16_violated_no_updates(self):
        """C3-16: update_count=0 con min_update_count=1 -> violated."""
        layer = ConstraintLayer(ConstraintConfig(min_update_count=1))
        results = layer.check(_healthy_h(), update_count=0)
        c3 = next(r for r in results if r.constraint_id == "C3_AUDIT_TRAIL")
        assert c3.satisfied is False
        assert c3.violation_severity > 0.0
        assert c3.drive_target == "alignment"

    def test_c3_17_severity_decreases_with_updates(self):
        """C3-17: piu' update_count si avvicina a threshold, meno severo e' il vincolo."""
        layer = ConstraintLayer(ConstraintConfig(min_update_count=10))
        r0 = layer.check(_healthy_h(), update_count=0)
        r5 = layer.check(_healthy_h(), update_count=5)
        sev0 = next(r for r in r0 if r.constraint_id == "C3_AUDIT_TRAIL").violation_severity
        sev5 = next(r for r in r5 if r.constraint_id == "C3_AUDIT_TRAIL").violation_severity
        assert sev5 < sev0


# =============================================================================
# PEN — apply_penalties (M5.18)
# =============================================================================

class TestApplyPenalties:

    def test_pen18_no_penalty_on_healthy_state(self):
        """PEN-18: stato sano -> apply_penalties ritorna dict vuoto."""
        layer = ConstraintLayer()
        ctrl = _make_controller(update_count=5)
        results = layer.check(_healthy_h(), update_count=5)
        penalties = layer.apply_penalties(ctrl, results)
        assert penalties == {}

    def test_pen19_penalty_reduces_drive(self):
        """PEN-19: violazione C1 -> coherence drive ridotto nel controller."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.50,
            coherence_penalty_scale=0.10,
        ))
        ctrl = _make_controller(update_count=5)
        ctrl._h_state["coherence"] = 0.20   # viola C1
        h_before = ctrl._h_state["coherence"]
        results = layer.check(ctrl._h_state, update_count=5)
        layer.apply_penalties(ctrl, results)
        h_after = ctrl._h_state["coherence"]
        assert h_after < h_before, f"Penalty non applicata: {h_before} -> {h_after}"

    def test_pen20_penalty_clamps_to_zero(self):
        """PEN-20: penalty non porta il drive sotto 0.0."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.90,
            coherence_penalty_scale=1.0,   # scala massima
        ))
        ctrl = _make_controller(update_count=5)
        ctrl._h_state["coherence"] = 0.05
        results = layer.check(ctrl._h_state, update_count=5)
        layer.apply_penalties(ctrl, results)
        assert ctrl._h_state["coherence"] >= 0.0

    def test_pen21_penalty_returns_dict_with_affected_drives(self):
        """PEN-21: apply_penalties ritorna dict con i drive penalizzati."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.50,
            coherence_penalty_scale=0.05,
        ))
        ctrl = _make_controller(update_count=5)
        ctrl._h_state["coherence"] = 0.10
        results = layer.check(ctrl._h_state, update_count=5)
        penalties = layer.apply_penalties(ctrl, results)
        assert "coherence" in penalties
        assert penalties["coherence"] > 0.0

    def test_pen22_viability_recomputed_after_penalty(self):
        """PEN-22: dopo apply_penalties viability viene ricalcolata."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.60,
            coherence_penalty_scale=0.20,
        ))
        ctrl = _make_controller(update_count=5)
        ctrl._h_state["coherence"] = 0.10   # viola fortemente C1
        # Viability prima
        v_before, _ = ctrl._compute_viability()
        results = layer.check(ctrl._h_state, update_count=5)
        layer.apply_penalties(ctrl, results)
        # Viability dopo (ctrl._viability aggiornato da apply_penalties)
        v_after = ctrl._viability
        assert v_after <= v_before, f"Viability non degradata: {v_before} -> {v_after}"


# =============================================================================
# E2E — end-to-end iniezione violazione + degrado viability (M5.19)
# =============================================================================

class TestE2EConstraintViolation:

    def test_e2e23_inject_coherence_violation_degrades_viability(self):
        """E2E-23: iniezione violazione C1 -> viability degrada."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.40,
            coherence_penalty_scale=0.15,
        ))
        ctrl = _make_controller(update_count=3)

        # Baseline: stato sano
        ctrl._h_state["coherence"] = 0.70
        v_baseline, _ = ctrl._compute_viability()

        # Inietta violazione: abbassa coherence sotto soglia
        ctrl._h_state["coherence"] = 0.10
        results = layer.check(ctrl._h_state, update_count=3)
        viols = layer.violations(results)
        assert any(v.constraint_id == "C1_COHERENCE" for v in viols)

        # Applica penalità
        layer.apply_penalties(ctrl, results)
        v_after = ctrl._viability

        assert v_after < v_baseline, (
            f"Viability non degradata dopo violazione C1: "
            f"baseline={v_baseline:.4f}, after={v_after:.4f}"
        )

    def test_e2e24_multiple_violations_compound_penalty(self):
        """E2E-24: violazioni multiple su drive diversi compongono la penalità."""
        layer = ConstraintLayer(ConstraintConfig(
            min_coherence=0.60,
            coherence_penalty_scale=0.10,
            min_update_count=5,
            audit_penalty_scale=0.05,
        ))
        ctrl = _make_controller(update_count=0)  # viola C3
        ctrl._h_state["coherence"] = 0.10        # viola C1
        v_before, _ = ctrl._compute_viability()

        results = layer.check(ctrl._h_state, update_count=0)
        viols = layer.violations(results)
        assert len(viols) >= 2   # C1 + C3

        layer.apply_penalties(ctrl, results)
        v_after = ctrl._viability
        assert v_after < v_before

    def test_e2e25_recovery_restores_viability(self):
        """E2E-25: dopo una violazione, il ripristino del drive ripristina la viability."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.40, coherence_penalty_scale=0.05))
        ctrl = _make_controller(update_count=5)

        # Fase 1: violazione
        ctrl._h_state["coherence"] = 0.10
        results_viol = layer.check(ctrl._h_state, update_count=5)
        layer.apply_penalties(ctrl, results_viol)
        v_violated = ctrl._viability

        # Fase 2: ripristino manuale del drive (simula healing)
        ctrl._h_state["coherence"] = 0.70
        v_restored, _ = ctrl._compute_viability()

        assert v_restored > v_violated

    def test_e2e26_constraint_stats_reflect_violations(self):
        """E2E-26: dopo un ciclo con violazioni, get_stats() li conta."""
        layer = ConstraintLayer(ConstraintConfig(min_coherence=0.50, min_update_count=3))
        h_bad = _healthy_h()
        h_bad["coherence"] = 0.05
        layer.check(h_bad, update_count=0)   # C1 + C3 violated
        stats = layer.get_stats()
        assert stats["check_count"] == 1
        assert stats["violation_count"] >= 2
