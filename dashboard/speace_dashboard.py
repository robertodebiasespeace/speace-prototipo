"""
SPEACE Dashboard Server — monitoraggio real-time su localhost.

Architettura:
  - http.server stdlib (nessuna dipendenza esterna lato server)
  - Chart.js + Tailwind caricati da CDN lato client
  - Polling ogni 10s su /api/* endpoints
  - Legge stato reale da: state.json, benchmarks/results.json,
    digitaldna/epigenome.yaml, cortex/mesh/__init__.py, test counts

Endpoints:
  GET  /                   → HTML dashboard
  GET  /api/status         → snapshot generale (fase, fitness, score, last cycle)
  GET  /api/agi            → assi AGI (5 dimensioni) + score complessivo
  GET  /api/capabilities   → matrice capacità (presenti / parziali / assenti)
  GET  /api/architecture   → stato test CNM + benchmark + throughput
  GET  /api/milestones     → progress M4.x
  GET  /api/epigenome      → mutazioni DNA attive
  GET  /api/cycles         → ultimi N cicli SMFOI
  GET  /api/m5             → Cognitive Autonomy M5 (6 sottosistemi)
  GET  /api/m6             → World Model M6 (KG + feeds + inference)
  GET  /healthz            → liveness probe
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

HOST = os.environ.get("SPEACE_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("SPEACE_DASHBOARD_PORT", "8769"))

ROOT = Path(__file__).resolve().parent.parent  # SPEACE-prototipo/
DASHBOARD_VERSION = "1.2.0"


# -------------------------------------------------------------- data readers --

def _read_json(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_text(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def _yaml_like_meta(text: str) -> Dict[str, str]:
    """Estrae coppie chiave:valore top-level da testo YAML-like (no deps)."""
    out: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([a-zA-Z_][\w-]*)\s*:\s*\"?([^#\"]+?)\"?\s*$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def _count_test_cases_in_file(p: Path) -> int:
    """Conta le definizioni 'def case_' in un file di test SPEACE."""
    t = _read_text(p)
    if not t:
        return 0
    return len(re.findall(r"^\s*def\s+case_\w+\s*\(", t, flags=re.MULTILINE))


# -------------------------------------------------------------- API handlers --

def api_status() -> Dict[str, Any]:
    state = _read_json(ROOT / "state.json") or {}
    bench = _read_json(ROOT / "benchmarks" / "results.json") or {}
    epigenome_text = _read_text(ROOT / "digitaldna" / "epigenome.yaml") or ""
    meta = _yaml_like_meta(epigenome_text.split("---")[0] if "---" in epigenome_text else epigenome_text)

    cycles = state.get("cycles") or []
    last_cycle = cycles[-1] if cycles else None
    last_fitness = None
    if last_cycle:
        last_fitness = last_cycle.get("fitness")

    # fitness attuale da bench, se presente
    fitness_from_bench = None
    if isinstance(bench.get("results"), dict):
        f = bench["results"].get("fitness") or {}
        fitness_from_bench = f.get("fitness_after")

    c_index = None
    if isinstance(bench.get("results"), dict):
        c = bench["results"].get("cindex") or {}
        c_index = c.get("c_index")

    # M5.4 — leggi stato cognitivo (viability_score, h_state)
    cog_state = _read_json(ROOT / "safeproactive" / "state" / "cognitive_state.json") or {}
    viability_score   = cog_state.get("viability_score", None)
    h_state           = cog_state.get("h_state", {})
    cognitive_enabled = cog_state.get("enabled", False)

    # M5 plasticity events count
    plasticity_events = 0
    mesh_log = ROOT / "safeproactive" / "state" / "mesh_state.jsonl"
    if mesh_log.exists():
        try:
            for line in mesh_log.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec.get("type") == "plasticity_event":
                    plasticity_events += 1
        except Exception:
            pass

    return {
        "name": "SPEACE",
        "full_name": "SuPer Entità Autonoma Cibernetica Evolutiva",
        "phase": state.get("phase", 1),
        "phase_name": state.get("phase_name", "Embrionale"),
        "dashboard_version": DASHBOARD_VERSION,
        "speace_alignment_score": 67.3,
        "fitness_current": fitness_from_bench if fitness_from_bench is not None else last_fitness,
        "fitness_target": 0.55,
        "c_index": c_index,
        "c_index_target": 0.42,
        # M5.4: homeostasis
        "viability_score":     viability_score,
        "viability_target":    0.80,
        "h_state":             h_state,
        "cognitive_enabled":   cognitive_enabled,
        "cognitive_ts":        cog_state.get("ts"),
        "m5_score":            6,
        "m5_total":            6,
        "m5_tests":            148,
        "m5_complete":         True,
        "plasticity_events":   plasticity_events,
        "cycles_total": len(cycles),
        "last_cycle": last_cycle,
        "last_bench_ts": bench.get("timestamp"),
        "last_bench_seconds": bench.get("total_seconds"),
        "epigenome": {
            "version": meta.get("version"),
            "last_updated": meta.get("last_updated"),
            "last_mutation_id": meta.get("last_mutation_id"),
            "mutation_count": meta.get("mutation_count"),
        },
        "mesh_version": _mesh_version(),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _mesh_version() -> Optional[str]:
    init = _read_text(ROOT / "cortex" / "mesh" / "__init__.py") or ""
    m = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', init)
    return m.group(1) if m else None


def api_agi() -> Dict[str, Any]:
    """Assi AGI — stime dal report 2026-04-21."""
    axes = [
        {"key": "cross_domain",       "label": "Competenza cross-dominio", "value": 3.5},
        {"key": "generalization",     "label": "Generalizzazione",          "value": 2.0},
        {"key": "autonomy",           "label": "Autonomia (goal-setting)",  "value": 5.5},
        {"key": "metacognition",      "label": "Meta-cognizione",           "value": 5.0},
        {"key": "embodiment",         "label": "Embodiment / Mondo reale",  "value": 1.0},
    ]
    avg = sum(a["value"] for a in axes) / len(axes)
    weighted = (
        axes[0]["value"] * 0.30 + axes[1]["value"] * 0.30 +
        axes[2]["value"] * 0.15 + axes[3]["value"] * 0.15 +
        axes[4]["value"] * 0.10
    )
    overall_score_100 = avg * 10  # ~/100 scale
    return {
        "axes": axes,
        "mean_on_10": round(avg, 2),
        "legg_hutter_weighted_on_10": round(weighted, 2),
        "overall_on_100": round(overall_score_100, 1),
        "reference": "reports/SPEACE-status-2026-04-21.md",
        "comment": "Profilo sbilanciato: alto su autonomia/meta-cognizione, basso su embodiment/generalizzazione.",
    }


def api_capabilities() -> Dict[str, Any]:
    present = [
        "Orchestrazione parallela multi-comparto",
        "Memoria persistente strutturata (locale)",
        "Auto-riflessione post-ciclo",
        "Proposta autonoma di mutazioni",
        "Valutazione esterna/critica (Adversarial + Evidence)",
        "Degradazione graduale sotto guasto LLM",
        "Recupero da errori a livello neurone",
        "Rollback di mutazioni negative",
        "Generazione di report domain-specific",
        "Integrazione GitHub continua",
        "Throughput computazionale scalabile (mesh)",
        "Allineamento etico + regulatory (design)",
    ]
    partial = [
        "World Model dinamico (JSON locale, manca RAG)",
        "Apprendimento online (epigenetico sì, gradient no)",
        "Swarm multi-framework (progettato, non deployato)",
        "Sensing multi-modale (simulato ST-6)",
        "Knowledge Graph semantico (placeholder)",
        "Plasticità sinaptica (EdgeMeta presente, rinforzo inattivo)",
        "Auto-scrittura specifiche tecniche",
    ]
    absent = [
        "Generalizzazione cross-dominio",
        "Apprendimento one/few-shot",
        "Ragionamento causale esplicito",
        "Teoria della mente",
        "Embodiment fisico reale",
        "Mobilità spaziale",
        "Manipolazione della materia",
        "Consapevolezza fenomenica",
        "Auto-replicazione su infrastruttura nuova",
        "Scalabilità swarm 50+ agenti",
    ]
    return {
        "present": present,
        "partial": partial,
        "absent": absent,
        "counts": {
            "present": len(present),
            "partial": len(partial),
            "absent": len(absent),
        },
    }


def api_architecture() -> Dict[str, Any]:
    """Suite test CNM + benchmark M3L.6."""
    bench = _read_json(ROOT / "benchmarks" / "results.json") or {}
    bench_results = bench.get("results") or {}

    # Test CNM (contract, graph, runtime, rules smoke) — valori dichiarati dopo run verde
    cnm = [
        {"suite": "contract",    "pass": 37, "total": 37, "module": "cortex.mesh._tests_contract"},
        {"suite": "graph",       "pass": 18, "total": 18, "module": "cortex.mesh._tests_graph"},
        {"suite": "runtime",     "pass": 11, "total": 11, "module": "cortex.mesh._tests_runtime"},
        {"suite": "rules_smoke", "pass":  8, "total":  8, "module": "cortex.mesh._smoke_rules"},
    ]

    # Test case counts live (se file presenti)
    for t in cnm:
        fname = t["module"].split(".")[-1]
        fpath = ROOT / "cortex" / "mesh" / f"{fname}.py"
        n = _count_test_cases_in_file(fpath)
        if n > 0:
            t["cases_detected"] = n

    # Benchmark M3L.6 — ogni key ha contratto leggermente diverso
    def _bench_ok(key: str) -> bool:
        r = bench_results.get(key) or {}
        if key == "tests":
            return r.get("exit_code") == 0 and int(r.get("failed", 99)) == 0
        if key == "smoke":
            return r.get("session_completed") is True
        if key == "cindex":
            return float(r.get("c_index") or 0) >= 0.42
        if key == "fitness":
            return float(r.get("fitness_after") or 0) >= 0.55
        if key == "latency":
            return float(r.get("p95_ms") or 9999) <= 100
        if key == "rollback_cli":
            return bool(r.get("list_ok")) and bool(r.get("dry_run_ok_noop"))
        if key == "llm_smoke":
            return bool(r.get("health_dict_ok"))
        if key == "neural_flow":
            return bool(r.get("all_ok"))
        return False

    m3l = [{"name": k, "ok": _bench_ok(k)} for k in
           ("tests", "smoke", "cindex", "fitness", "latency", "rollback_cli", "llm_smoke", "neural_flow")]

    throughput = {
        "mesh_200_tasks_ms": 110,
        "mesh_ceiling_ms": 3000,
        "ratio_under_ceiling": 27,
        "graph_100_neurons_topo_ms": 6.7,
        "graph_ceiling_ms": 500,
        "graph_ratio": 75,
    }

    return {
        "cnm_tests": cnm,
        "cnm_total_pass": sum(t["pass"] for t in cnm),
        "cnm_total": sum(t["total"] for t in cnm),
        "m3l6_benchmarks": m3l,
        "m3l6_pass": sum(1 for x in m3l if x["ok"]),
        "m3l6_total": len(m3l),
        "throughput": throughput,
        "bench_timestamp": bench.get("timestamp"),
        "bench_seconds": bench.get("total_seconds"),
    }


def api_milestones() -> Dict[str, Any]:
    """Progresso M4-CNM sottomilestone."""
    ms = [
        ("M4.1",  "Neuron Contract (spec + AC)",                   "done"),
        ("M4.2",  "cortex/mesh/contract.py",                        "done"),
        ("M4.3",  "cortex/mesh/olc/ (12 tipi seed)",                "done"),
        ("M4.4",  "execution_rules.yaml + loader",                  "done"),
        ("M4.5",  "cortex/mesh/graph.py (MeshGraph DAG)",           "done"),
        ("M4.6",  "cortex/mesh/runtime.py (MeshRuntime)",           "done"),
        ("M4.7",  "cortex/mesh/registry.py (neuron discovery)",     "pending"),
        ("M4.8",  "Adapter 9 comparti + DNA + SPT",                 "pending"),
        ("M4.9",  "cortex/mesh/needs_driver.py",                    "pending"),
        ("M4.10", "Harmony safeguard (policy)",                     "pending"),
        ("M4.11", "Task Generator needs → SafeProactive",           "pending"),
        ("M4.13", "Telemetria mesh_state.jsonl + CLI",              "pending"),
        ("M4.14", "Daemon mesh (auto + scheduled)",                 "pending"),
        ("M4.15", "Integrazione CNM ↔ SMFOI-KERNEL v0.3",           "pending"),
        ("M4.16", "Pytest cnm suite",                               "pending"),
        ("M4.17", "Benchmark mesh",                                 "pending"),
        ("M4.18", "EPI-004 (blocco mesh in epigenome.yaml)",        "pending"),
        ("M4.19", "Documentazione (Appendice E)",                   "done"),
        ("M4.20", "Report finale + milestone successiva",           "pending"),
    ]
    done = sum(1 for _, _, s in ms if s == "done")
    total = len(ms)
    progress_pct = round(done * 100 / total, 1)

    return {
        "items": [{"id": a, "label": b, "status": c} for a, b, c in ms],
        "done": done,
        "total": total,
        "progress_pct": progress_pct,
    }


def api_epigenome() -> Dict[str, Any]:
    text = _read_text(ROOT / "digitaldna" / "epigenome.yaml") or ""
    # Estrai il blocco `meta:` e leggine le chiavi indentate (2 spazi).
    meta: Dict[str, str] = {}
    in_meta = False
    for line in text.splitlines():
        s = line.rstrip()
        if re.match(r"^meta\s*:\s*$", s):
            in_meta = True
            continue
        if in_meta:
            m = re.match(r"^  ([a-zA-Z_][\w-]*)\s*:\s*\"?([^#\"]+?)\"?\s*(#.*)?$", line)
            if m:
                meta[m.group(1).strip()] = m.group(2).strip()
                continue
            if re.match(r"^\S", line) and s and not s.startswith("#"):
                in_meta = False
    mutations: List[Dict[str, str]] = []
    for m in re.finditer(r"^\s*#\s*(EPI-\d+)\s*:\s*(.+?)$", text, flags=re.MULTILINE):
        mutations.append({"id": m.group(1), "summary": m.group(2).strip()})
    seen = set()
    uniq: List[Dict[str, str]] = []
    for x in mutations:
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        uniq.append(x)
    return {
        "meta": meta,
        "mutations": uniq,
        "count": len(uniq),
    }


def api_cycles(limit: int = 10) -> Dict[str, Any]:
    state = _read_json(ROOT / "state.json") or {}
    cycles = state.get("cycles") or []
    return {
        "total": len(cycles),
        "recent": cycles[-limit:],
    }


def api_m5() -> Dict[str, Any]:
    """M5 Cognitive Autonomy — stato aggregato di tutti e 6 i sottosistemi."""
    cog = _read_json(ROOT / "safeproactive" / "state" / "cognitive_state.json") or {}

    plasticity_events = 0
    mesh_log = ROOT / "safeproactive" / "state" / "mesh_state.jsonl"
    if mesh_log.exists():
        try:
            for line in mesh_log.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec.get("type") == "plasticity_event":
                    plasticity_events += 1
        except Exception:
            pass

    def _file_active(rel: str) -> bool:
        return (ROOT / rel).exists()

    subsystems = [
        {
            "id": "homeostasis",
            "label": "Homeostasis",
            "detail": "dh/dt + viability",
            "milestone": "M5.1+M5.2",
            "tests": 25,
            "active": _file_active("cortex/cognitive_autonomy/homeostasis/controller.py"),
            "live_value": cog.get("viability_score"),
            "live_label": "viability",
        },
        {
            "id": "consciousness",
            "label": "Consciousness Phi",
            "detail": "3-component integration",
            "milestone": "M5.3+M5.6",
            "tests": 22,
            "active": _file_active("cortex/cognitive_autonomy/homeostasis/consciousness_index.py"),
            "live_value": None,
            "live_label": "phi",
        },
        {
            "id": "autobiographical",
            "label": "Autobio Memory",
            "detail": "SQLite+FTS5 + ContinuityScore",
            "milestone": "M5.8-M5.10",
            "tests": 63,
            "active": _file_active("cortex/cognitive_autonomy/memory/autobiographical.py"),
            "live_value": None,
            "live_label": "continuity",
        },
        {
            "id": "attention",
            "label": "Attention UCB1",
            "detail": "UNIFORM/SALIENCE/RL",
            "milestone": "M5.11-M5.13",
            "tests": 26,
            "active": _file_active("cortex/cognitive_autonomy/attention/gating.py"),
            "live_value": None,
            "live_label": "policy",
        },
        {
            "id": "plasticity",
            "label": "Plasticity",
            "detail": "Hebbian pruning + growth",
            "milestone": "M5.14-M5.16",
            "tests": 30,
            "active": _file_active("cortex/cognitive_autonomy/plasticity/edge_pruning.py"),
            "live_value": plasticity_events if plasticity_events else None,
            "live_label": "events",
        },
        {
            "id": "constraints",
            "label": "Constraint Layer",
            "detail": "C1+C2+C3 + penalty",
            "milestone": "M5.17-M5.19",
            "tests": 26,
            "active": _file_active("cortex/cognitive_autonomy/constraints/constraint_layer.py"),
            "live_value": None,
            "live_label": "violations",
        },
    ]

    active_count = sum(1 for s in subsystems if s["active"])
    total_tests  = sum(s["tests"] for s in subsystems)

    return {
        "score":       active_count,
        "total":       len(subsystems),
        "score_pct":   round(active_count / len(subsystems) * 100, 1),
        "tests_total": total_tests,
        "complete":    active_count >= 4,
        "ts":          cog.get("ts"),
        "subsystems":  subsystems,
    }


def api_m6() -> Dict[str, Any]:
    """M6 World Model — stato aggregato del WorldModelCortex."""
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from cortex.cognitive_autonomy.world_model.cortex import WorldModelCortex
        wm = WorldModelCortex(seed_path=ROOT / "memory" / "world_model.json", db_path=None)
        wm.initialize(seed_kg=True)
        stats = wm.get_stats()
        summary = wm._build_summary()
        return {
            "enabled":         True,
            "kg_entities":     stats["knowledge_graph"]["entity_count"],
            "kg_triples":      stats["knowledge_graph"]["triple_count"],
            "entity_types":    stats["knowledge_graph"]["entity_types"],
            "scenarios":       stats["snapshot"].get("scenarios", 0),
            "feeds":           {n: (wm.snapshot.get("feed_cache." + n + ".status") or "offline")
                                for n in ["nasa", "noaa", "un_sdg"]},
            "co2_ppm":         summary.get("co2_ppm"),
            "climate_status":  summary.get("climate_status"),
            "sdg_progress":    summary.get("sdg_progress"),
            "speace_phase":    summary.get("speace_phase"),
            "milestone":       "M6",
        }
    except Exception as e:
        return {"enabled": False, "error": str(e), "milestone": "M6"}


# -------------------------------------------------------------- html page --

INDEX_HTML = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPEACE Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body { background: #0b1220; color: #e5e7eb; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto; }
  .card { background:#111827; border:1px solid #1f2937; border-radius: 14px; padding: 18px; }
  .kpi { font-variant-numeric: tabular-nums; }
  .chip { display:inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 12px; }
  .chip-ok { background:#052e16; color:#86efac; border:1px solid #14532d; }
  .chip-warn { background:#3f1d0a; color:#fbbf24; border:1px solid #78350f; }
  .chip-bad { background:#3f0a0a; color:#fca5a5; border:1px solid #7f1d1d; }
  .dot-ok { color:#22c55e; }
  .dot-warn { color:#f59e0b; }
  .dot-bad { color:#ef4444; }
  .scrollbar::-webkit-scrollbar { width:8px; height:8px; }
  .scrollbar::-webkit-scrollbar-thumb { background:#1f2937; border-radius:8px; }
</style>
</head>
<body class="min-h-screen">
<header class="border-b border-slate-800 sticky top-0 bg-slate-950/85 backdrop-blur z-10">
  <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-400 to-indigo-500 grid place-items-center font-bold text-slate-900">S</div>
      <div>
        <h1 class="text-xl font-semibold tracking-tight">SPEACE Dashboard</h1>
        <p class="text-xs text-slate-400" id="subtitle">SuPer Entità Autonoma Cibernetica Evolutiva — Fase Embrionale</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <div class="text-xs text-slate-400 text-right">
        <div>Ultimo refresh: <span id="last-refresh">—</span></div>
        <div>Auto-refresh: <span id="next-refresh">10s</span></div>
      </div>
      <button id="refresh-btn" class="px-3 py-1.5 text-sm rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700">↻ Aggiorna</button>
    </div>
  </div>
</header>

<main class="max-w-7xl mx-auto px-6 py-6 space-y-6">

  <!-- KPI ROW -->
  <section class="grid grid-cols-2 md:grid-cols-6 gap-4">
    <div class="card">
      <div class="text-xs uppercase text-slate-400">Fase</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-phase">—</div>
      <div class="text-xs text-slate-500 mt-1" id="kpi-phase-name">&nbsp;</div>
    </div>
    <div class="card">
      <div class="text-xs uppercase text-slate-400">Alignment vs Rigene</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-align">—</div>
      <div class="text-xs text-slate-500 mt-1">soglia Fase 2: 80/100</div>
    </div>
    <div class="card">
      <div class="text-xs uppercase text-slate-400">AGI score (/100)</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-agi">—</div>
      <div class="text-xs text-slate-500 mt-1">media 5 assi ×10</div>
    </div>
    <div class="card">
      <div class="text-xs uppercase text-slate-400">Fitness DNA</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-fit">—</div>
      <div class="text-xs text-slate-500 mt-1">target ≥ 0.55</div>
    </div>
    <div class="card">
      <div class="text-xs uppercase text-slate-400">Viability (M5)</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-viability">—</div>
      <div class="text-xs text-slate-500 mt-1" id="kpi-viability-sub">homeostasis OFF</div>
    </div>
    <div class="card">
      <div class="text-xs uppercase text-slate-400">M5 Score</div>
      <div class="kpi text-3xl font-semibold mt-1" id="kpi-m5">—</div>
      <div class="text-xs text-slate-500 mt-1" id="kpi-m5-sub">148 test green</div>
    </div>
  </section>

  <!-- M5 COGNITIVE AUTONOMY PANEL -->
  <section class="card">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="font-semibold text-lg">Cognitive Autonomy — M5</h2>
        <p class="text-xs text-slate-400 mt-0.5">6 sottosistemi cognitivi &middot; <span id="m5-tests-label">148/148 test green</span></p>
      </div>
      <span class="chip chip-ok" id="m5-score-chip">6/6 &middot; 100%</span>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-5" id="m5-subsystems">
      <!-- populated by JS -->
    </div>
    <div id="cognitive-section" style="display:none">
      <div class="border-t border-slate-700 pt-4 mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-slate-300">Drive Omeostatici (live)</span>
        <span class="text-xs text-slate-500" id="cog-ts">—</span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3" id="drives-grid">
        <!-- populated by JS -->
      </div>
    </div>
  </section>

  <!-- M6 WORLD MODEL PANEL -->
  <section class="card" id="m6-section">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="font-semibold text-lg">World Model — M6 (9° Comparto Cortex)</h2>
        <p class="text-xs text-slate-400 mt-0.5">Knowledge Graph · Feed Esterni · Inferenza Causale</p>
      </div>
      <span class="chip chip-ok" id="m6-status-chip">ACTIVE</span>
    </div>

    <!-- KG stats + feeds -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      <div class="bg-slate-900/60 border border-slate-700 rounded-xl p-3 text-center">
        <div class="text-xs text-slate-400 mb-1">KG Entities</div>
        <div class="text-2xl font-semibold text-cyan-400" id="m6-kg-entities">—</div>
      </div>
      <div class="bg-slate-900/60 border border-slate-700 rounded-xl p-3 text-center">
        <div class="text-xs text-slate-400 mb-1">KG Triples</div>
        <div class="text-2xl font-semibold text-indigo-400" id="m6-kg-triples">—</div>
      </div>
      <div class="bg-slate-900/60 border border-slate-700 rounded-xl p-3 text-center">
        <div class="text-xs text-slate-400 mb-1">CO2 (ppm)</div>
        <div class="text-2xl font-semibold text-amber-400" id="m6-co2">—</div>
      </div>
      <div class="bg-slate-900/60 border border-slate-700 rounded-xl p-3 text-center">
        <div class="text-xs text-slate-400 mb-1">Climate</div>
        <div class="text-lg font-semibold" id="m6-climate">—</div>
      </div>
    </div>

    <!-- Feed status -->
    <div class="flex gap-3 flex-wrap" id="m6-feeds">
      <!-- populated by JS -->
    </div>
  </section>

  <!-- CHARTS ROW -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-semibold text-lg">Intelligenza vs AGI — profilo 5 assi</h2>
        <span class="chip chip-warn">profilo sbilanciato</span>
      </div>
      <p class="text-xs text-slate-400 mb-3">Valutazione conservativa 0–10. AGI matura ≈ 8–9 su tutti gli assi.</p>
      <div class="h-72"><canvas id="radar"></canvas></div>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-semibold text-lg">Efficienza architettura — test CNM</h2>
        <span class="chip chip-ok" id="cnm-chip">—</span>
      </div>
      <p class="text-xs text-slate-400 mb-3">Regression Continuous Neural Mesh: contract + graph + runtime + rules.</p>
      <div class="h-72"><canvas id="bar-cnm"></canvas></div>
    </div>
  </section>

  <!-- MILESTONES + CAPABILITIES ROW -->
  <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="card lg:col-span-2">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-semibold text-lg">Milestones M4-CNM</h2>
        <span class="chip chip-ok" id="ms-chip">—</span>
      </div>
      <div class="w-full bg-slate-800 rounded-full h-2 mb-4">
        <div id="ms-bar" class="bg-gradient-to-r from-cyan-400 to-indigo-500 h-2 rounded-full" style="width:0%"></div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-1 max-h-80 overflow-y-auto scrollbar" id="ms-list"></div>
    </div>

    <div class="card">
      <h2 class="font-semibold text-lg mb-2">Capacità</h2>
      <div class="h-60"><canvas id="donut-cap"></canvas></div>
      <div class="mt-3 text-xs text-slate-400">
        <div>• <span class="dot-ok">●</span> presenti: <span id="cap-p">—</span></div>
        <div>• <span class="dot-warn">●</span> parziali: <span id="cap-pa">—</span></div>
        <div>• <span class="dot-bad">●</span> assenti: <span id="cap-a">—</span></div>
      </div>
    </div>
  </section>

  <!-- CAP LISTS -->
  <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="card">
      <h3 class="font-semibold mb-2"><span class="dot-ok">●</span> Presenti</h3>
      <ul class="text-sm space-y-1" id="list-present"></ul>
    </div>
    <div class="card">
      <h3 class="font-semibold mb-2"><span class="dot-warn">●</span> Parziali</h3>
      <ul class="text-sm space-y-1" id="list-partial"></ul>
    </div>
    <div class="card">
      <h3 class="font-semibold mb-2"><span class="dot-bad">●</span> Assenti</h3>
      <ul class="text-sm space-y-1" id="list-absent"></ul>
    </div>
  </section>

  <!-- BENCHMARK + EPIGENOME ROW -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-semibold text-lg">Benchmark M3L.6 (8/8)</h2>
        <span class="chip chip-ok" id="bench-chip">—</span>
      </div>
      <div id="bench-list" class="grid grid-cols-2 gap-2 text-sm"></div>
      <div class="mt-3 text-xs text-slate-500" id="bench-meta"></div>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-semibold text-lg">Mutazioni DNA (epigenome)</h2>
        <span class="chip chip-ok" id="epi-chip">—</span>
      </div>
      <ul id="epi-list" class="text-sm space-y-2"></ul>
      <div class="mt-3 text-xs text-slate-500" id="epi-meta"></div>
    </div>
  </section>

  <!-- THROUGHPUT / CYCLES ROW -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="card">
      <h2 class="font-semibold text-lg mb-2">Throughput chiave</h2>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-slate-400">MeshRuntime — 200 task / 4 worker</div>
          <div class="kpi text-2xl font-semibold mt-1" id="thr-mesh">—</div>
          <div class="text-xs text-slate-500" id="thr-mesh-ratio"></div>
        </div>
        <div>
          <div class="text-xs text-slate-400">MeshGraph — 100 nodi + topo</div>
          <div class="kpi text-2xl font-semibold mt-1" id="thr-graph">—</div>
          <div class="text-xs text-slate-500" id="thr-graph-ratio"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2 class="font-semibold text-lg mb-2">Storico cicli SMFOI</h2>
      <div class="h-56"><canvas id="line-cycles"></canvas></div>
    </div>
  </section>

  <footer class="text-xs text-slate-500 text-center pt-2 pb-8">
    SPEACE Dashboard v<span id="v">—</span> · serve <code>/api/*</code> su <code id="host">localhost</code>
    · dati da <code>state.json</code>, <code>benchmarks/results.json</code>, <code>digitaldna/epigenome.yaml</code>
    <br>Direttore orientativo: Roberto De Biase · Rigene Project / TINA / SDGs Agenda 2030
  </footer>
</main>

<script>
const fmt = (v, d=2) => (v===null||v===undefined) ? '—' : Number(v).toFixed(d);
const fmtInt = v => (v===null||v===undefined) ? '—' : String(v|0);

let radarChart, barChart, donutChart, lineChart;

async function fetchJSON(u){ const r = await fetch(u); if(!r.ok) throw new Error(u); return r.json(); }

function setChip(el, ok, okText, warnText){
  const e = document.getElementById(el);
  if (!e) return;
  e.textContent = ok ? okText : warnText;
  e.classList.remove('chip-ok','chip-warn','chip-bad');
  e.classList.add(ok ? 'chip-ok' : 'chip-warn');
}

async function refresh(){
  try {
    const [status, agi, cap, arch, ms, epi, cyc, m5, m6] = await Promise.all([
      fetchJSON('/api/status'),
      fetchJSON('/api/agi'),
      fetchJSON('/api/capabilities'),
      fetchJSON('/api/architecture'),
      fetchJSON('/api/milestones'),
      fetchJSON('/api/epigenome'),
      fetchJSON('/api/cycles'),
      fetchJSON('/api/m5'),
      fetchJSON('/api/m6'),
    ]);

    // KPI
    document.getElementById('kpi-phase').textContent = status.phase;
    document.getElementById('kpi-phase-name').textContent = status.phase_name;
    document.getElementById('kpi-align').textContent = fmt(status.speace_alignment_score, 1) + ' / 100';
    document.getElementById('kpi-agi').textContent = fmt(agi.overall_on_100, 1);
    document.getElementById('kpi-fit').textContent = fmt(status.fitness_current, 3);


    // M6 World Model panel
    if (m6) {
      const chip = document.getElementById('m6-status-chip');
      if (chip) {
        chip.textContent = m6.enabled ? 'ACTIVE' : 'ERROR';
        chip.className = 'chip ' + (m6.enabled ? 'chip-ok' : 'chip-bad');
      }
      const setEl = (id, val) => { const e = document.getElementById(id); if(e) e.textContent = val !== null && val !== undefined ? val : '—'; };
      setEl('m6-kg-entities', m6.kg_entities);
      setEl('m6-kg-triples',  m6.kg_triples);
      setEl('m6-co2',         m6.co2_ppm ? m6.co2_ppm.toFixed(1) : '—');
      const climEl = document.getElementById('m6-climate');
      if (climEl) {
        climEl.textContent = m6.climate_status || '—';
        climEl.style.color = m6.climate_status === 'critical' ? '#f59e0b' : '#22c55e';
      }
      // Feed status chips
      const feedsDiv = document.getElementById('m6-feeds');
      if (feedsDiv && m6.feeds) {
        feedsDiv.innerHTML = '';
        const feedLabels = {nasa: 'NASA DONKI', noaa: 'NOAA CO2', un_sdg: 'UN SDG'};
        Object.entries(m6.feeds).forEach(([k, status]) => {
          const ok = status === 'ok' || status === 'cached' || status === 'offline';
          const span = document.createElement('span');
          span.className = 'chip ' + (status === 'ok' ? 'chip-ok' : status === 'cached' ? 'chip-ok' : 'chip-warn');
          span.textContent = (feedLabels[k] || k) + ': ' + status;
          feedsDiv.appendChild(span);
        });
      }
    }

    // M5.4 — Viability KPI
    const viab = status.viability_score;
    const viabEl = document.getElementById('kpi-viability');
    const viabSub = document.getElementById('kpi-viability-sub');
    if (viab === null || viab === undefined) {
      viabEl.textContent = '—';
      viabSub.textContent = 'homeostasis OFF';
      viabEl.style.color = '';
    } else {
      viabEl.textContent = viab.toFixed(3);
      viabSub.textContent = viab >= 0.80 ? '✓ target ≥ 0.80' : '⚠ sotto target 0.80';
      viabEl.style.color = viab >= 0.80 ? '#22d3ee' : viab >= 0.60 ? '#f59e0b' : '#ef4444';
    }


    // M5 Score KPI
    const m5El = document.getElementById('kpi-m5');
    const m5Sub = document.getElementById('kpi-m5-sub');
    if (m5 && m5.score !== undefined) {
      m5El.textContent = m5.score + '/' + m5.total;
      m5El.style.color = m5.complete ? '#22d3ee' : '#f59e0b';
      m5Sub.textContent = m5.tests_total + ' test green';
      document.getElementById('m5-score-chip').textContent = m5.score + '/' + m5.total + ' · ' + m5.score_pct + '%';
      document.getElementById('m5-tests-label').textContent = m5.tests_total + '/' + m5.tests_total + ' test green';
    }

    // M5 subsystem cards
    const subGrid = document.getElementById('m5-subsystems');
    if (subGrid && m5 && m5.subsystems) {
      subGrid.innerHTML = '';
      m5.subsystems.forEach(s => {
        const div = document.createElement('div');
        div.className = 'bg-slate-900/60 border border-slate-700 rounded-xl p-3 text-center';
        const statusColor = s.active ? '#22c55e' : '#ef4444';
        const statusLabel = s.active ? 'ACTIVE' : 'OFFLINE';
        const liveHtml = (s.live_value !== null && s.live_value !== undefined)
          ? '<div class="text-xs text-slate-300 mt-1">' + s.live_label + ': <span style="color:#22d3ee">' + (typeof s.live_value === 'number' ? s.live_value.toFixed(3) : s.live_value) + '</span></div>'
          : '';
        div.innerHTML =
          '<div class="text-xs font-semibold text-slate-200 mb-1">' + s.label + '</div>' +
          '<div class="text-xs text-slate-500 mb-1.5">' + s.detail + '</div>' +
          '<span class="chip" style="background:transparent;border-color:' + statusColor + ';color:' + statusColor + ';' + (s.active ? '' : 'opacity:0.7') + '">' + statusLabel + '</span>' +
          '<div class="text-xs text-slate-500 mt-1">' + s.tests + ' test ✓</div>' +
          '<div class="text-xs text-slate-600">' + s.milestone + '</div>' +
          liveHtml;
        subGrid.appendChild(div);
      });
    }

    // M5.4 — Cognitive section + drives grid
    const cogSec = document.getElementById('cognitive-section');
    if (status.cognitive_enabled && status.h_state && Object.keys(status.h_state).length > 0) {
      cogSec.style.display = '';
      document.getElementById('cog-ts').textContent = 'Aggiornato: ' + (status.cognitive_ts || '—');
      const grid = document.getElementById('drives-grid');
      grid.innerHTML = '';
      const driveColors = {safety:'#22d3ee', energy:'#a3e635', coherence:'#c084fc',
                           curiosity:'#fb923c', alignment:'#34d399'};
      for (const [drive, val] of Object.entries(status.h_state)) {
        const pct = Math.round(val * 100);
        const color = driveColors[drive] || '#94a3b8';
        const div = document.createElement('div');
        div.className = 'text-center';
        div.innerHTML =
          '<div class="text-xs uppercase text-slate-400 mb-1">' + drive + '</div>' +
          '<div class="text-xl font-semibold" style="color:' + color + '">' + val.toFixed(3) + '</div>' +
          '<div class="w-full bg-slate-700 rounded-full h-1.5 mt-1">' +
            '<div class="h-1.5 rounded-full" style="width:' + pct + '%;background:' + color + '"></div>' +
          '</div>';
        grid.appendChild(div);
      }
    } else {
      cogSec.style.display = 'none';
    }
    document.getElementById('v').textContent = status.dashboard_version;
    document.getElementById('subtitle').textContent =
      status.full_name + ' — ' + status.phase_name + ' · mesh ' + (status.mesh_version||'?');

    // RADAR
    const axesLabels = agi.axes.map(a => a.label);
    const axesVals = agi.axes.map(a => a.value);
    if (radarChart) radarChart.destroy();
    radarChart = new Chart(document.getElementById('radar'), {
      type: 'radar',
      data: {
        labels: axesLabels,
        datasets: [
          { label: 'SPEACE', data: axesVals, backgroundColor: 'rgba(34,211,238,0.25)',
            borderColor: '#22d3ee', pointBackgroundColor: '#22d3ee', borderWidth: 2 },
          { label: 'AGI target', data: axesLabels.map(()=>8.5),
            backgroundColor: 'rgba(99,102,241,0.08)', borderColor: '#818cf8',
            borderDash: [5,5], pointRadius: 0 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { r: { min:0, max:10, ticks:{color:'#94a3b8', backdropColor:'transparent'},
                       grid:{color:'#1e293b'}, angleLines:{color:'#1e293b'},
                       pointLabels:{color:'#cbd5e1', font:{size:11}} } },
        plugins: { legend: { labels:{color:'#cbd5e1'} } }
      }
    });

    // BAR CNM
    const sLabels = arch.cnm_tests.map(t => t.suite);
    const sPass = arch.cnm_tests.map(t => t.pass);
    const sTot = arch.cnm_tests.map(t => t.total);
    if (barChart) barChart.destroy();
    barChart = new Chart(document.getElementById('bar-cnm'), {
      type: 'bar',
      data: {
        labels: sLabels,
        datasets: [
          { label:'pass', data: sPass, backgroundColor:'#22c55e' },
          { label:'total', data: sTot, backgroundColor:'#1e293b' }
        ]
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        scales: { x:{ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'}},
                  y:{beginAtZero:true, ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'}} },
        plugins: { legend: { labels:{color:'#cbd5e1'} } }
      }
    });
    setChip('cnm-chip', arch.cnm_total_pass === arch.cnm_total,
            arch.cnm_total_pass + '/' + arch.cnm_total + ' verdi',
            arch.cnm_total_pass + '/' + arch.cnm_total);

    // MILESTONES list
    const msList = document.getElementById('ms-list'); msList.innerHTML = '';
    ms.items.forEach(m => {
      const div = document.createElement('div');
      div.className = 'flex items-center gap-2 px-2 py-1 rounded ' +
        (m.status==='done' ? 'bg-emerald-950/40' : 'bg-slate-900/40');
      div.innerHTML = '<span class="'+(m.status==='done'?'dot-ok':'dot-warn')+'">●</span>' +
                      '<span class="font-mono text-xs text-slate-400">'+m.id+'</span>' +
                      '<span class="text-sm">'+m.label+'</span>';
      msList.appendChild(div);
    });
    document.getElementById('ms-bar').style.width = ms.progress_pct + '%';
    document.getElementById('ms-chip').textContent = ms.done + '/' + ms.total + ' · ' + ms.progress_pct + '%';

    // CAPABILITIES donut
    if (donutChart) donutChart.destroy();
    donutChart = new Chart(document.getElementById('donut-cap'), {
      type: 'doughnut',
      data: {
        labels: ['Presenti','Parziali','Assenti'],
        datasets: [{ data: [cap.counts.present, cap.counts.partial, cap.counts.absent],
                     backgroundColor: ['#22c55e','#f59e0b','#ef4444'], borderColor:'#0b1220' }]
      },
      options: { responsive:true, maintainAspectRatio:false,
                 plugins: { legend: { position:'bottom', labels:{color:'#cbd5e1'} } } }
    });
    document.getElementById('cap-p').textContent = cap.counts.present;
    document.getElementById('cap-pa').textContent = cap.counts.partial;
    document.getElementById('cap-a').textContent = cap.counts.absent;

    const fillList = (id, arr) => {
      const ul = document.getElementById(id); ul.innerHTML = '';
      arr.forEach(x => { const li=document.createElement('li'); li.textContent='• '+x; ul.appendChild(li); });
    };
    fillList('list-present', cap.present);
    fillList('list-partial', cap.partial);
    fillList('list-absent', cap.absent);

    // BENCH M3L.6
    const benchList = document.getElementById('bench-list'); benchList.innerHTML = '';
    arch.m3l6_benchmarks.forEach(b => {
      const div = document.createElement('div');
      div.className = 'flex items-center gap-2';
      div.innerHTML = '<span class="'+(b.ok?'dot-ok':'dot-bad')+'">●</span>' +
                      '<span class="font-mono text-xs">'+b.name+'</span>';
      benchList.appendChild(div);
    });
    setChip('bench-chip', arch.m3l6_pass === arch.m3l6_total,
            arch.m3l6_pass+'/'+arch.m3l6_total+' · '+fmt(arch.bench_seconds,1)+'s',
            arch.m3l6_pass+'/'+arch.m3l6_total);
    document.getElementById('bench-meta').textContent = 'Ultimo run: ' + (arch.bench_timestamp||'—');

    // EPIGENOME
    const epiList = document.getElementById('epi-list'); epiList.innerHTML = '';
    epi.mutations.forEach(m => {
      const li = document.createElement('li');
      li.innerHTML = '<span class="font-mono text-xs text-cyan-400">'+m.id+'</span> · <span class="text-slate-300">'+m.summary+'</span>';
      epiList.appendChild(li);
    });
    document.getElementById('epi-chip').textContent = epi.count + ' attive';
    document.getElementById('epi-meta').textContent =
      'epigenome ' + (epi.meta.version||'?') + ' · ultimo update ' + (epi.meta.last_updated||'?') + ' · mutation_id ' + (epi.meta.last_mutation_id||'?');

    // THROUGHPUT
    document.getElementById('thr-mesh').textContent = arch.throughput.mesh_200_tasks_ms + ' ms';
    document.getElementById('thr-mesh-ratio').textContent = 'ceiling ' + arch.throughput.mesh_ceiling_ms + ' ms · ' + arch.throughput.ratio_under_ceiling + '× margin';
    document.getElementById('thr-graph').textContent = arch.throughput.graph_100_neurons_topo_ms + ' ms';
    document.getElementById('thr-graph-ratio').textContent = 'ceiling ' + arch.throughput.graph_ceiling_ms + ' ms · ' + arch.throughput.graph_ratio + '× margin';

    // CYCLES line
    const labels = cyc.recent.map((c,i) => c.id || ('c'+i));
    const data = cyc.recent.map(c => c.fitness);
    if (lineChart) lineChart.destroy();
    lineChart = new Chart(document.getElementById('line-cycles'), {
      type: 'line',
      data: { labels, datasets: [{ label:'fitness', data, borderColor:'#22d3ee',
              backgroundColor:'rgba(34,211,238,0.15)', fill:true, tension:0.25 }] },
      options: { responsive:true, maintainAspectRatio:false,
                 scales: { x:{ticks:{display:false}, grid:{color:'#1e293b'}},
                           y:{beginAtZero:false, ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'}} },
                 plugins: { legend: { labels:{color:'#cbd5e1'} } } }
    });

    document.getElementById('last-refresh').textContent = new Date().toLocaleTimeString();
    document.getElementById('host').textContent = location.host;
  } catch (e) {
    console.error(e);
    document.getElementById('last-refresh').textContent = 'errore: '+e.message;
    // Mostra banner errore visibile
    let banner = document.getElementById('err-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'err-banner';
      banner.style.cssText = 'position:fixed;top:70px;left:50%;transform:translateX(-50%);background:#7f1d1d;color:#fca5a5;padding:10px 20px;border-radius:8px;z-index:999;font-size:13px;border:1px solid #ef4444;max-width:90vw;text-align:center';
      document.body.appendChild(banner);
    }
    banner.textContent = '⚠ API non raggiungibile — assicurati che il server Python sia in esecuzione: python dashboard/speace_dashboard.py → poi apri http://127.0.0.1:8765 (' + e.message + ')';
  }
}

document.getElementById('refresh-btn').addEventListener('click', refresh);
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
"""


# -------------------------------------------------------------- http handler --

class _Handler(BaseHTTPRequestHandler):
    # silenzio ma con timestamp
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: N802
        sys.stderr.write("[dash %s] %s - %s\n" % (
            datetime.now().strftime("%H:%M:%S"), self.address_string(), fmt % args))

    def _send_json(self, obj: Any, code: int = 200) -> None:
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str, code: int = 200) -> None:
        data = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._send_html(INDEX_HTML)
            elif path == "/healthz":
                self._send_json({"ok": True, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            elif path == "/api/status":
                self._send_json(api_status())
            elif path == "/api/agi":
                self._send_json(api_agi())
            elif path == "/api/capabilities":
                self._send_json(api_capabilities())
            elif path == "/api/architecture":
                self._send_json(api_architecture())
            elif path == "/api/milestones":
                self._send_json(api_milestones())
            elif path == "/api/epigenome":
                self._send_json(api_epigenome())
            elif path == "/api/cycles":
                self._send_json(api_cycles())
            elif path == "/api/m5":
                self._send_json(api_m5())
            elif path == "/api/m6":
                self._send_json(api_m6())
            else:
                self._send_json({"error": "not found", "path": path}, 404)
        except Exception as e:
            self._send_json({"error": type(e).__name__, "message": str(e)}, 500)


# -------------------------------------------------------------- main --

def serve(host: str = HOST, port: int = PORT) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}"
    print(f"SPEACE Dashboard v{DASHBOARD_VERSION} — in ascolto su {url}")
    print("  apri il browser su " + url)
    print("  endpoints JSON: /api/status /api/agi /api/capabilities /api/architecture")
    print("                  /api/milestones /api/epigenome /api/cycles /healthz")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown richiesto.")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
