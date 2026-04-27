"""
Test suite M5.6 — PhiComponents (Φ a 3 componenti) + ConsciousnessIndex.calculate_from_phi3
Tests: PHI-01 → PHI-12

Run:
    cd SPEACE-prototipo
    PYTHONPATH=. python cortex/cognitive_autonomy/homeostasis/_tests_phi3.py
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.homeostasis.consciousness_index import (
    PhiComponents, CIndexResult, ConsciousnessIndex, calculate_speace_c_index
)

PASS = 0; FAIL = 0; ERRORS = []

def ok(n):
    global PASS; PASS += 1; print(f"  PASS  {n}")

def fail(n, r):
    global FAIL; FAIL += 1
    msg = f"  FAIL  {n}: {r}"; print(msg); ERRORS.append(msg)

def rng(n, v, lo, hi):
    (ok if lo <= v <= hi else lambda n: fail(n, f"{v:.4f} not in [{lo},{hi}]"))(n)

def eq(n, got, exp):
    (ok if got == exp else lambda n: fail(n, f"got={got!r} exp={exp!r}"))(n)

def true_(n, expr, msg=""):
    (ok if expr else lambda n: fail(n, msg or "False"))(n)

# PHI-01: PhiComponents import
def test_phi_01():
    try:
        from cortex.cognitive_autonomy.homeostasis.consciousness_index import PhiComponents
        ok("PHI-01: PhiComponents importable")
    except Exception as e:
        fail("PHI-01: import", str(e))

# PHI-02: composite weighted sum
def test_phi_02():
    pc = PhiComponents(integration=1.0, differentiation=0.0, global_workspace=0.0)
    rng("PHI-02: composite = w_int (0.45)", pc.composite(), 0.44, 0.46)

# PHI-03: composite clamp [0,1]
def test_phi_03():
    pc = PhiComponents(integration=2.0, differentiation=2.0, global_workspace=2.0)
    rng("PHI-03: composite clamped to 1.0", pc.composite(), 0.99, 1.0)

# PHI-04: from_scalar homogeneous
def test_phi_04():
    pc = PhiComponents.from_scalar(0.7)
    eq("PHI-04a: integration=0.7", round(pc.integration, 4), 0.7)
    eq("PHI-04b: differentiation=0.7", round(pc.differentiation, 4), 0.7)
    eq("PHI-04c: global_workspace=0.7", round(pc.global_workspace, 4), 0.7)
    rng("PHI-04d: composite≈0.7", pc.composite(), 0.69, 0.71)

# PHI-05: from_brain_state extraction
def test_phi_05():
    brain_state = {
        "consciousness_index": 0.6,
        "dopamine_level": 0.8,
        "working_memory": {"total_items": 5},
        "cycle_count": 10,
    }
    pc = PhiComponents.from_brain_state(brain_state)
    rng("PHI-05a: integration from c_index", pc.integration, 0.59, 0.61)
    rng("PHI-05b: global_workspace = 5/7", pc.global_workspace, 0.71, 0.72)
    rng("PHI-05c: composite in [0,1]", pc.composite(), 0.0, 1.0)

# PHI-06: from_brain_state with attention_weights
def test_phi_06():
    brain_state = {
        "consciousness_index": 0.7,
        "dopamine_level": 0.6,
        "working_memory": {"total_items": 3},
        "attention_weights": [0.25, 0.25, 0.25, 0.25],  # uniform → max entropy
    }
    pc = PhiComponents.from_brain_state(brain_state)
    # Uniform attention = max entropy → diff near 1.0
    rng("PHI-06: uniform attention → high differentiation", pc.differentiation, 0.8, 1.0)

# PHI-07: calculate_from_phi3 returns CIndexResult
def test_phi_07():
    ci = ConsciousnessIndex()
    pc = PhiComponents(integration=0.7, differentiation=0.5, global_workspace=0.6)
    result = ci.calculate_from_phi3(pc, w_activation=0.5, a_complexity=0.5)
    true_("PHI-07a: returns CIndexResult", isinstance(result, CIndexResult))
    rng("PHI-07b: c_index in [0,1]", result.c_index, 0.0, 1.0)
    true_("PHI-07c: phi_components attached", result.phi_components is not None)

# PHI-08: phi_components preserved in result
def test_phi_08():
    ci = ConsciousnessIndex()
    pc = PhiComponents(integration=0.8, differentiation=0.4, global_workspace=0.5)
    result = ci.calculate_from_phi3(pc, 0.5, 0.5)
    eq("PHI-08: phi_components.integration", result.phi_components.integration, 0.8)

# PHI-09: calculate_from_brain uses M5.6 path
def test_phi_09():
    ci = ConsciousnessIndex()
    brain = {"consciousness_index": 0.7, "dopamine_level": 0.6,
             "working_memory": {"total_items": 4}, "cycle_count": 5}
    result = ci.calculate_from_brain(brain)
    true_("PHI-09a: phi_components not None", result.phi_components is not None)
    rng("PHI-09b: c_index in [0,1]", result.c_index, 0.0, 1.0)
    true_("PHI-09c: integration matches", result.phi_components.integration > 0.0)

# PHI-10: high integration → higher C-index than low integration
def test_phi_10():
    ci_hi = ConsciousnessIndex()
    ci_lo = ConsciousnessIndex()
    pc_hi = PhiComponents(integration=0.9, differentiation=0.8, global_workspace=0.8)
    pc_lo = PhiComponents(integration=0.1, differentiation=0.1, global_workspace=0.1)
    r_hi = ci_hi.calculate_from_phi3(pc_hi, 0.5, 0.5)
    r_lo = ci_lo.calculate_from_phi3(pc_lo, 0.5, 0.5)
    true_("PHI-10: high Φ → higher C-index", r_hi.c_index > r_lo.c_index,
          f"r_hi={r_hi.c_index:.3f} r_lo={r_lo.c_index:.3f}")

# PHI-11: weights sum to 1.0 (default)
def test_phi_11():
    pc = PhiComponents()
    w_sum = pc.w_integration + pc.w_differentiation + pc.w_global_workspace
    rng("PHI-11: weights sum to 1.0", w_sum, 0.99, 1.01)

# PHI-12: EMA + emergent setpoint still works after M5.6 path
def test_phi_12():
    ci = ConsciousnessIndex()
    brain = {"consciousness_index": 0.5, "dopamine_level": 0.5,
             "working_memory": {"total_items": 3}, "cycle_count": 1}
    for _ in range(25):
        ci.calculate_from_brain(brain)
    sp = ci.emergent_coherence_setpoint
    true_("PHI-12a: emergent setpoint is set", sp is not None)
    rng("PHI-12b: emergent setpoint in [0.1, 0.95]", sp, 0.1, 0.95)

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  TEST SUITE M5.6 — PhiComponents + calculate_from_phi3")
    print("  Tests: PHI-01 → PHI-12")
    print("=" * 55)
    test_phi_01(); test_phi_02(); test_phi_03(); test_phi_04()
    test_phi_05(); test_phi_06(); test_phi_07(); test_phi_08()
    test_phi_09(); test_phi_10(); test_phi_11(); test_phi_12()
    print("\n" + "=" * 55)
    print(f"  RISULTATO: {PASS} PASS  |  {FAIL} FAIL")
    if ERRORS:
        print("\n  Errori:")
        for e in ERRORS: print(f"    {e}")
    print("=" * 55 + "\n")
    import sys; sys.exit(0 if FAIL == 0 else 1)
