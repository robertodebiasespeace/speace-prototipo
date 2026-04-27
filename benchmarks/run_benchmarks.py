"""
SPEACE Benchmark Runner – M2 + M3L.6
Esegue tutti i benchmark, confronta con thresholds.yaml,
scrive results.json e stampa un report pass/fail.

Suite attuale (8 bench):
  1. tests          — pytest regression
  2. smoke          — SPEACE-main.py multi-ciclo
  3. cindex         — C-index regression (ACF)
  4. fitness        — fitness v2.0 regression
  5. latency        — call_compartment p95/mean
  6. rollback_cli   — scripts/rollback.py --list/--dry-run
  7. llm_smoke      — cascade LLM (M3L.6)
  8. neural_flow    — 9 comparti end-to-end (M3L.6)

Exit code:
  0 → tutti i benchmark hanno superato le soglie
  1 → almeno un benchmark sotto soglia
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from benchmarks import (  # noqa: E402
    bench_tests,
    bench_smoke,
    bench_cindex,
    bench_fitness,
    bench_latency,
    bench_llm_smoke,
    bench_neural_flow,
)


def load_thresholds() -> dict:
    with open(BENCH_DIR / "thresholds.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_rollback_cli() -> dict:
    """Verifica che scripts/rollback.py --list funzioni e --dry-run sia no-op."""
    # --list
    proc = subprocess.run(
        [sys.executable, "scripts/rollback.py", "--list"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    list_ok = proc.returncode == 0 and "Snapshot disponibili" in (proc.stdout or "")

    # Prendi uno snap esistente per dry-run
    from safeproactive.safeproactive import SafeProactive
    sp = SafeProactive()
    snaps = sp.list_snapshots()
    dry_ok = False
    if snaps:
        target = snaps[-1]["id"]
        # Hash del file epigenome pre/post dry-run
        epi = ROOT / "digitaldna" / "epigenome.yaml"
        pre = epi.read_bytes() if epi.exists() else b""
        proc2 = subprocess.run(
            [sys.executable, "scripts/rollback.py", "--dry-run", target],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        post = epi.read_bytes() if epi.exists() else b""
        dry_ok = proc2.returncode == 0 and pre == post and "DRY-RUN" in (proc2.stdout or "")

    return {
        "name": "bench_rollback_cli",
        "list_ok": list_ok,
        "snapshots_found": len(snaps),
        "dry_run_ok_noop": dry_ok,
    }


def evaluate(results: dict, thr: dict) -> list:
    findings = []

    # Tests
    r = results["tests"]
    passed = r.get("passed", 0) >= thr["tests"]["pytest_min_passed"]
    no_fail = r.get("failed", 0) <= thr["tests"]["pytest_allowed_failures"]
    findings.append(("tests", passed and no_fail,
                     f"passed={r.get('passed')}, failed={r.get('failed')}"))

    # Smoke
    s = results["smoke"]
    smoke_ok = (s.get("exit_code", 1) == thr["smoke"]["max_exit_code"] and
                s.get("cycles_observed", 0) >= thr["smoke"]["min_cycles_ok"] and
                s.get("session_completed", False))
    findings.append(("smoke", smoke_ok,
                     f"exit={s.get('exit_code')}, cycles={s.get('cycles_observed')}, "
                     f"completed={s.get('session_completed')}"))

    # C-index
    c = results["cindex"]
    cindex_ok = c.get("c_index", 0.0) >= thr["cindex"]["min_value"]
    findings.append(("cindex", cindex_ok,
                     f"c_index={c.get('c_index')} (min {thr['cindex']['min_value']})"))

    # Fitness
    f = results["fitness"]
    fit_ok = f.get("fitness_after", 0.0) >= thr["fitness"]["min_value"]
    findings.append(("fitness", fit_ok,
                     f"fitness_after={f.get('fitness_after')} (min {thr['fitness']['min_value']})"))

    # Latency
    l = results["latency"]
    lat_ok = (l.get("p95_ms", 999.0) <= thr["latency"]["max_p95_ms"] and
              l.get("mean_ms", 999.0) <= thr["latency"]["max_mean_ms"])
    findings.append(("latency", lat_ok,
                     f"p95={l.get('p95_ms')}ms, mean={l.get('mean_ms')}ms "
                     f"(max p95 {thr['latency']['max_p95_ms']}ms)"))

    # Rollback CLI
    rb = results["rollback_cli"]
    rb_ok = (rb.get("list_ok", False) and
             rb.get("snapshots_found", 0) >= thr["rollback_cli"]["must_list_at_least"] and
             rb.get("dry_run_ok_noop", False))
    findings.append(("rollback_cli", rb_ok,
                     f"list={rb.get('list_ok')}, snaps={rb.get('snapshots_found')}, "
                     f"dry_run_noop={rb.get('dry_run_ok_noop')}"))

    # LLM smoke (M3L.6)
    llm = results.get("llm_smoke", {})
    llm_thr = thr.get("llm_smoke", {})
    llm_ok = (
        bool(llm.get("any_responded", False)) is llm_thr.get("must_any_respond", True)
        and bool(llm.get("health_dict_ok", False)) is llm_thr.get("must_health_dict_ok", True)
        and float(llm.get("complete_latency_ms", 99999.0))
            <= float(llm_thr.get("max_complete_latency_ms", 5000))
    )
    # Se require_real_backend=true, serve un backend non-mock up.
    if llm_thr.get("require_real_backend", False):
        llm_ok = llm_ok and bool(llm.get("any_real_backend_up", False))
    findings.append((
        "llm_smoke", llm_ok,
        f"backend={llm.get('backend_used')}, responded={llm.get('any_responded')}, "
        f"real_up={llm.get('any_real_backend_up')}, "
        f"latency={llm.get('complete_latency_ms')}ms"
    ))

    # Neural Flow (M3L.6)
    nf = results.get("neural_flow", {})
    nf_thr = thr.get("neural_flow", {})
    nominal = nf.get("nominal", {}) or {}
    hazard = nf.get("hazard", {}) or {}
    nominal_ok = (
        nominal.get("errors", 99) <= nf_thr.get("max_errors", 0)
        and nominal.get("compartments_in_log", 0)
            >= nf_thr.get("min_compartments_in_log", 8)
        and set(nominal.get("levels_seen", []))
            .issuperset(set(nf_thr.get("must_cover_levels", [1, 2, 3, 4])))
    )
    hazard_ok = (
        bool(hazard.get("safety_blocked", False))
            is nf_thr.get("must_safety_block", True)
        and bool(hazard.get("downstream_respected", False))
            is nf_thr.get("must_downstream_respect_block", True)
    )
    nf_ok = nominal_ok and hazard_ok
    findings.append((
        "neural_flow", nf_ok,
        f"nominal(comp={nominal.get('compartments_in_log')}/"
        f"{nominal.get('compartments_total')}, errors={nominal.get('errors')}), "
        f"hazard(blocked={hazard.get('safety_blocked')}, "
        f"respected={hazard.get('downstream_respected')})"
    ))

    return findings


def main() -> int:
    t0 = time.perf_counter()
    thr = load_thresholds()

    print("=" * 60)
    print(" SPEACE BENCHMARK SUITE — M2 + M3L.6")
    print("=" * 60)

    print("\n[1/8] Pytest regression...")
    tests_res = bench_tests.run()
    print(f"      passed={tests_res['passed']} failed={tests_res['failed']} exit={tests_res['exit_code']}")

    print("\n[2/8] Smoke multi-ciclo (3 cicli)...")
    smoke_res = bench_smoke.run(cycles=3)
    print(f"      cycles={smoke_res['cycles_observed']}/{smoke_res['cycles_requested']} "
          f"exit={smoke_res['exit_code']} completed={smoke_res['session_completed']}")

    print("\n[3/8] C-index regression...")
    cindex_res = bench_cindex.run()
    print(f"      c_index={cindex_res['c_index']} level={cindex_res['consciousness_level']}")

    print("\n[4/8] Fitness v2.0 regression...")
    fitness_res = bench_fitness.run()
    print(f"      fitness_after={fitness_res['fitness_after']} (Δ={fitness_res['delta']})")

    print("\n[5/8] Latency call_compartment...")
    latency_res = bench_latency.run(sample_size=thr["latency"]["sample_size"])
    print(f"      mean={latency_res['mean_ms']}ms p95={latency_res['p95_ms']}ms "
          f"max={latency_res['max_ms']}ms")

    print("\n[6/8] Rollback CLI smoke...")
    rb_res = check_rollback_cli()
    print(f"      list_ok={rb_res['list_ok']} snaps={rb_res['snapshots_found']} "
          f"dry_run_noop={rb_res['dry_run_ok_noop']}")

    print("\n[7/8] LLM cascade smoke (LM Studio → Anthropic → mock)...")
    llm_res = bench_llm_smoke.run()
    print(f"      primary={llm_res.get('primary')} backend_used={llm_res.get('backend_used')} "
          f"responded={llm_res.get('any_responded')} "
          f"latency={llm_res.get('complete_latency_ms')}ms")

    print("\n[8/8] Neural Flow end-to-end (9 comparti, 2 scenari)...")
    nf_res = bench_neural_flow.run()
    _nom = nf_res.get("nominal", {}) or {}
    _haz = nf_res.get("hazard", {}) or {}
    print(f"      nominal(comp={_nom.get('compartments_in_log')}/"
          f"{_nom.get('compartments_total')}, errors={_nom.get('errors')}, "
          f"levels={_nom.get('levels_seen')}) "
          f"hazard(blocked={_haz.get('safety_blocked')}, "
          f"respected={_haz.get('downstream_respected')})")

    results = {
        "tests": tests_res,
        "smoke": smoke_res,
        "cindex": cindex_res,
        "fitness": fitness_res,
        "latency": latency_res,
        "rollback_cli": rb_res,
        "llm_smoke": llm_res,
        "neural_flow": nf_res,
    }

    findings = evaluate(results, thr)
    total_seconds = round(time.perf_counter() - t0, 2)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_seconds": total_seconds,
        "results": results,
        "findings": [{"bench": n, "ok": ok, "detail": d} for (n, ok, d) in findings],
        "all_passed": all(ok for (_, ok, _) in findings),
    }

    out_path = BENCH_DIR / "results.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(" BENCHMARK REPORT")
    print("=" * 60)
    for name, ok, detail in findings:
        mark = "✅" if ok else "❌"
        print(f"  {mark} {name:15s}  {detail}")
    print("-" * 60)
    if report["all_passed"]:
        print(f"  ✅ ALL BENCHMARKS PASSED  ({total_seconds}s)")
    else:
        print(f"  ❌ SOME BENCHMARKS FAILED  ({total_seconds}s)")
    print("=" * 60)
    print(f"\nReport salvato in: {out_path}")

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
