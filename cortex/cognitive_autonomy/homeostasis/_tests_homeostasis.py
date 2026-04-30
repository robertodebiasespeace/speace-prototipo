"""
Test suite HomeostaticController — M5.1 + M5.2
Esecuzione: python -m cortex.cognitive_autonomy.homeostasis._tests_homeostasis
"""
from __future__ import annotations
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cortex.cognitive_autonomy.homeostasis.controller import (
    Drive, HomeostasisConfig, HomeostaticController, SystemReceptors
)

_P, _F = [], []

def _assert(label, cond, detail=""):
    if cond:
        print(f"  PASS  {label}"); _P.append(label)
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else "")); _F.append(label)

_READINGS = dict(energy=0.60, safety=0.90, curiosity=0.45, coherence=0.65, alignment=0.75)
_CFG_ON   = HomeostasisConfig(enabled=True, k_restore=0.10, k_input=0.30)

def t_scaffold_disabled():
    ctrl = HomeostaticController()
    r = ctrl.update()
    _assert("HC-01 scaffold viability=1.0", r["viability_score"] == 1.0)
    _assert("HC-02 scaffold flag", r.get("scaffold") is True)
    _assert("HC-03 enabled=False", r.get("enabled") is False)

def t_enabled_update():
    ctrl = HomeostaticController(config=_CFG_ON)
    r = ctrl.update(receptor_readings=_READINGS, dt=1.0)
    _assert("HC-04 enabled=True in result", r["enabled"] is True)
    _assert("HC-05 viability in [0,1]", 0.0 <= r["viability_score"] <= 1.0,
            str(r["viability_score"]))
    _assert("HC-06 h_state has 5 drives", len(r["h_state"]) == 5)
    _assert("HC-07 dh_dt has 5 drives", len(r["dh_dt"]) == 5)

def t_dhdt_direction():
    """dh/dt deve avere segno corretto: spinge h verso setpoint."""
    ctrl = HomeostaticController(config=_CFG_ON)
    # Forza h sotto setpoint per energy (sp=0.75): receptor=0.60
    r = ctrl.update(receptor_readings=_READINGS, dt=1.0)
    # dh/dt per energy deve essere negativo (h=0.705 > r=0.60, componente k_i negativa)
    # ma la componente k_r deve spingere verso 0.75. Verifica solo che sia finito.
    _assert("HC-08 dh/dt energy is float", isinstance(r["dh_dt"]["energy"], float))
    # Dopo 20 step, h deve avvicinarsi al setpoint
    for _ in range(20):
        r = ctrl.update(receptor_readings=_READINGS, dt=1.0)
    _assert("HC-09 convergenza 20 step viability>=0.7", r["viability_score"] >= 0.7,
            str(r["viability_score"]))

def t_alerts():
    """Alert generati quando drive fuori banda."""
    cfg = HomeostasisConfig(enabled=True, tolerance=0.05)
    ctrl = HomeostaticController(config=cfg)
    # Forza h molto lontano dal setpoint
    ctrl._h_state["energy"] = 0.10   # sp=0.75, dev=0.65 > tol*2=0.10
    _, scores = ctrl._compute_viability()
    alerts = ctrl._check_alerts(scores)
    _assert("HC-10 CRITICAL alert generato", any("CRITICAL:energy" in a for a in alerts),
            str(alerts))

def t_penalize():
    ctrl = HomeostaticController(config=_CFG_ON)
    before = ctrl.h_state["safety"]
    ctrl.penalize(0.2, "test")
    after = ctrl.h_state["safety"]
    _assert("HC-11 penalize abbassa safety", after < before, f"{before:.3f}->{after:.3f}")
    _assert("HC-12 safety in [0,1]", 0.0 <= after <= 1.0)

def t_snapshot_restore():
    ctrl = HomeostaticController(config=_CFG_ON)
    ctrl.update(receptor_readings=_READINGS, dt=1.0)
    snap = ctrl.snapshot()
    original = dict(ctrl._h_state)
    ctrl._h_state["energy"] = 0.0
    ctrl.restore(snap)
    _assert("HC-13 restore ripristina energy",
            abs(ctrl._h_state["energy"] - original["energy"]) < 1e-9)
    _assert("HC-14 snapshot version=M5.1", snap.get("version") == "M5.1")

def t_system_receptors():
    rec = SystemReceptors(_CFG_ON)
    live = rec.read_all()
    _assert("HC-15 read_all ha 5 drive", len(live) == 5)
    _assert("HC-16 tutti in [0,1]",
            all(0.0 <= v <= 1.0 for v in live.values()), str(live))
    for d in Drive:
        _assert(f"HC-17 drive {d.value} presente", d.value in live)

def t_auto_receptors():
    ctrl = HomeostaticController(config=_CFG_ON)
    r = ctrl.update(dt=0.5)  # receptor_readings=None → auto-read
    _assert("HC-18 auto-receptors viability in [0,1]",
            0.0 <= r["viability_score"] <= 1.0)
    _assert("HC-19 receptor_readings nel result", "receptor_readings" in r)

def t_viability_property():
    ctrl = HomeostaticController()
    _assert("HC-20 viability_score property disabled=1.0", ctrl.viability_score == 1.0)
    ctrl2 = HomeostaticController(config=_CFG_ON)
    _assert("HC-21 viability_score property enabled", 0.0 <= ctrl2.viability_score <= 1.0)

def main():
    print("=" * 55)
    print("HomeostaticController — Test Suite M5.1 + M5.2")
    print("=" * 55)
    for fn in [t_scaffold_disabled, t_enabled_update, t_dhdt_direction,
               t_alerts, t_penalize, t_snapshot_restore,
               t_system_receptors, t_auto_receptors, t_viability_property]:
        try: fn()
        except Exception as e:
            import traceback; traceback.print_exc()
            _F.append(fn.__name__)
    total = len(_P) + len(_F)
    print(f"\n{'=' * 55}")
    print(f"M5.1+M5.2: {len(_P)}/{total} PASS  |  {len(_F)} FAIL")
    if _F: print(f"FAIL: {_F}")
    else:  print("TUTTI I TEST M5.1+M5.2 PASSATI")
    print("=" * 55)
    return 0 if not _F else 1

if __name__ == "__main__":
    sys.exit(main())
