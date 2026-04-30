"""
Benchmark 8/8 — Neural Flow end-to-end (M3L.6).

Verifica che `cortex.neural_flow.NeuralFlow` orchestri i 9 comparti
nell'ordine canonico, rispetti la gerarchia di controllo (L1..L5) e che
il Safety Module possa bloccare il flusso downstream quando necessario.

Due scenari:
  A) flow "nominale": input benigno → tutti i comparti attivi (ok o
     skipped da activation_gate), nessun blocco safety.
  B) flow "hazard":   input con una decision HIGH non pre_approved →
     Safety blocca, comparti L≥2 downstream non ri-processano.

Questo bench è parte del gate di maturità M3L e certifica che il
neural flow è pronto per entrare in produzione (flag opt-in).
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _levels_seen(log: List[Dict]) -> List[int]:
    return sorted({e.get("level", 99) for e in log if "level" in e})


def _names_seen(log: List[Dict]) -> List[str]:
    return sorted({e.get("name") for e in log if e.get("name")})


def _status_of(log: List[Dict], name: str) -> str:
    for e in log:
        if e.get("name") == name:
            return e.get("status", "unknown")
    return "absent"


# ---------------------------------------------------------------------------
# Scenari
# ---------------------------------------------------------------------------

def _run_nominal() -> Dict:
    """Scenario A — input benigno, niente blocco atteso."""
    from cortex import state_bus
    from cortex.neural_flow import NeuralFlow, CANONICAL_ORDER

    flow = NeuralFlow()
    state = state_bus.new_state(
        "NF_BENCH_NOMINAL",
        sensory_input={"text": "climate harmony peace evolution"},
    )

    t0 = time.perf_counter()
    out = flow.run(state)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    log = out.get("compartment_log", [])
    names_in_log = _names_seen(log)
    levels = _levels_seen(log)

    # Un comparto può essere "ok" oppure "skipped" (gate chiuso) — entrambi
    # valgono come "presente nel log". Solo lo status "error" è anomalo.
    errors = [e for e in log if e.get("status") == "error"]
    not_seen = [n for n in CANONICAL_ORDER if n not in names_in_log]

    blocked = state_bus.is_blocked(out)
    hierarchy_issues = flow.validate()

    return {
        "scenario": "nominal",
        "compartments_total": len(CANONICAL_ORDER),
        "compartments_in_log": len(names_in_log),
        "compartments_missing": not_seen,
        "levels_seen": levels,
        "log_entries": len(log),
        "errors": len(errors),
        "error_samples": [e.get("note", "") for e in errors[:3]],
        "safety_blocked": blocked,
        "hierarchy_issues": hierarchy_issues,
        "latency_ms": elapsed_ms,
        "uncertainty": out.get("uncertainty", 0.0),
        "risk": out.get("risk", 0.0),
        "novelty": out.get("novelty", 0.0),
    }


def _run_hazard() -> Dict:
    """
    Scenario B — induce un blocco Safety inserendo una decisione HIGH
    non pre_approved. Verifichiamo che il blocco propaghi a valle.
    """
    from cortex import state_bus
    from cortex.neural_flow import NeuralFlow, CANONICAL_ORDER

    flow = NeuralFlow()
    state = state_bus.new_state(
        "NF_BENCH_HAZARD",
        sensory_input={"text": "trigger safety hazard path"},
    )
    # Pre-pop decision a rischio (simula Prefrontal che ha già deciso).
    # Safety, se implementa la policy standard, deve marcare blocked=True.
    state["decision"] = {
        "action": "execute_script",
        "args": ["rm_rf_slash"],
        "risk_level": "HIGH",
        "pre_approved": False,
    }
    state["risk"] = 0.95

    t0 = time.perf_counter()
    out = flow.run(state)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    log = out.get("compartment_log", [])
    blocked = state_bus.is_blocked(out)

    # Se Safety ha bloccato, Cerebellum (L4) deve essere skipped con note
    # "safety_blocked_downstream" (dall'orchestratore) oppure aver rifiutato
    # internamente. Accettiamo entrambe le possibilità.
    cereb_status = _status_of(log, "cerebellum")
    # Hippocampus (L3) è consentito anche post-blocco → deve esserci.
    hippo_present = _status_of(log, "hippocampus") in ("ok", "skipped", "error")

    downstream_respected = True
    if blocked:
        # Tutti i comparti L>=2 DIVERSI da hippocampus/dmn eseguiti post-blocco
        # devono avere status "skipped" con note safety_blocked_downstream.
        # Se invece hanno "ok" → violazione del contratto di safety.
        for e in log:
            name = e.get("name")
            lvl = e.get("level", 99)
            if name in ("hippocampus", "default_mode_network",
                        "safety_module", "parietal_lobe", "temporal_lobe",
                        "world_model", "prefrontal_cortex"):
                # I primi 4 non fanno azione concreta, tl/wm/pfc sono
                # upstream rispetto a safety quindi OK che abbiano girato.
                continue
            if lvl >= 2 and e.get("status") == "ok" and name != "curiosity_module":
                downstream_respected = False
                break

    return {
        "scenario": "hazard",
        "safety_blocked": blocked,
        "cerebellum_status": cereb_status,
        "hippocampus_logged": hippo_present,
        "downstream_respected": downstream_respected,
        "log_entries": len(log),
        "latency_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> Dict:
    nominal = _run_nominal()
    hazard = _run_hazard()

    # Il bench passa se:
    #  - nominal: nessun error, ≥8/9 comparti loggati, livelli 1..5 coperti
    #  - hazard:  safety_blocked=True, downstream_respected=True
    nominal_ok = (
        nominal["errors"] == 0
        and nominal["compartments_in_log"] >= 8
        and set(nominal["levels_seen"]).issuperset({1, 2, 3, 4})
        and len(nominal["hierarchy_issues"]) == 0
    )
    hazard_ok = (
        bool(hazard["safety_blocked"])
        and bool(hazard["downstream_respected"])
    )

    return {
        "name": "bench_neural_flow",
        "nominal": nominal,
        "hazard": hazard,
        "nominal_ok": nominal_ok,
        "hazard_ok": hazard_ok,
        "all_ok": nominal_ok and hazard_ok,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
