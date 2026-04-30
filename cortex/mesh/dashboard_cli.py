"""
cortex.mesh.dashboard_cli — Dashboard CLI per mesh telemetry (M4.13)

CLI minimale, **read-only**, che legge `mesh_state.jsonl` e mostra:
  - Verdict corrente + severity
  - Top need con gap maggiori
  - Distribuzione verdetti su finestra
  - Ultime proposte generate
  - Eventuali compensazioni attive

Uso:
  python -m cortex.mesh.dashboard_cli
  python -m cortex.mesh.dashboard_cli --path safeproactive/state/mesh_state.jsonl --last 20
  python -m cortex.mesh.dashboard_cli --json   # raw JSON dell'ultimo evento

Nessun side-effect oltre `fs_read` sul jsonl di telemetria.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from cortex.mesh.telemetry import MeshTelemetry, DEFAULT_MESH_STATE_PATH
from cortex.mesh.olc.base import NEEDS_CATALOG


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


_BAR_W = 20


def _bar(value: float, width: int = _BAR_W, fill: str = "█", empty: str = "·") -> str:
    v = max(0.0, min(1.0, float(value)))
    n = int(round(v * width))
    return fill * n + empty * (width - n)


def _fmt_needs_block(needs: Dict[str, float], gap: Dict[str, float]) -> str:
    out = ["NEED              VALUE          GAP"]
    out.append("-" * 50)
    for k in NEEDS_CATALOG:
        v = float(needs.get(k, 0.0))
        g = float(gap.get(k, 0.0))
        bar = _bar(v)
        out.append(f"{k:<17} {v:.2f} {bar}  Δ {g:+.2f}")
    return "\n".join(out)


def _fmt_verdict_block(event: Dict[str, Any]) -> str:
    verdict = event.get("verdict") or "—"
    severity = event.get("verdict_severity")
    sev_str = f" (severity={severity})" if severity is not None else ""
    driving = event.get("driving_need") or "—"
    allowed = ", ".join(event.get("allowed_risk_levels") or []) or "—"
    return (
        f"VERDICT: {verdict.upper()}{sev_str}\n"
        f"DRIVING NEED: {driving}\n"
        f"ALLOWED RISK LEVELS: {allowed}"
    )


def _fmt_graph_block(graph: Dict[str, Any]) -> str:
    if not graph:
        return "GRAPH: <no data>"
    nodes = graph.get("nodes", 0)
    edges = graph.get("edges", 0)
    roots = graph.get("roots", 0)
    sinks = graph.get("sinks", 0)
    needs_by = graph.get("needs_count_by_need", {}) or {}
    served = sum(1 for v in needs_by.values() if int(v) > 0)
    return (
        f"GRAPH: nodes={nodes} edges={edges} roots={roots} sinks={sinks} | "
        f"needs_served={served}/5"
    )


def _fmt_proposals_block(proposals: List[Dict[str, Any]]) -> str:
    if not proposals:
        return "PROPOSALS: <empty>"
    lines = ["PROPOSALS:"]
    for i, p in enumerate(proposals, 1):
        title = p.get("title", "—")
        nd = p.get("driving_need", "—")
        pr = float(p.get("priority", 0.0))
        rl = p.get("risk_level", "—")
        lines.append(f"  {i}. [{rl:<6}] [{nd:<16}] p={pr:.2f}  {title}")
    return "\n".join(lines)


def _fmt_compensations_block(comps: List[Dict[str, Any]]) -> str:
    if not comps:
        return "COMPENSATIONS: none"
    lines = ["COMPENSATIONS:"]
    for c in comps:
        sev = c.get("severity", 0)
        kind = c.get("kind", "—")
        target = c.get("target", "—")
        lines.append(f"  · sev={sev}  {kind:<32} → {target}")
    return "\n".join(lines)


def _fmt_distribution_block(stats: Dict[str, Any]) -> str:
    dist = stats.get("verdict_distribution", {}) or {}
    if not dist:
        return "VERDICT DISTRIBUTION: <empty>"
    total = sum(dist.values())
    lines = [f"VERDICT DISTRIBUTION over {total} events:"]
    for k in ("healthy", "watch", "alert", "critical", "none"):
        n = dist.get(k, 0)
        if n == 0 and k == "none":
            continue
        pct = (n / total * 100) if total else 0
        lines.append(f"  {k:<10} {n:>5}  ({pct:5.1f}%)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def render_dashboard(
    *,
    path: str = DEFAULT_MESH_STATE_PATH,
    last: int = 1,
) -> str:
    """Renderizza la dashboard come stringa multi-line ASCII."""
    tlm = MeshTelemetry(path)
    events = tlm.tail(limit=max(1, last))
    stats = tlm.stats()

    out: List[str] = []
    out.append("=" * 50)
    out.append("  SPEACE Continuous Neural Mesh — Telemetry")
    out.append("=" * 50)
    out.append(f"  source: {stats.get('path')}")
    out.append(f"  events: {stats.get('events_total', 0)}  "
               f"first={stats.get('first_ts') or '—'}  "
               f"last={stats.get('last_ts') or '—'}")
    out.append("")

    if not events:
        out.append("(no events recorded yet)")
        return "\n".join(out)

    last_ev = events[-1]
    out.append(_fmt_verdict_block(last_ev))
    out.append("")
    out.append(_fmt_needs_block(last_ev.get("needs", {}) or {},
                                 last_ev.get("gap", {}) or {}))
    out.append("")
    out.append(_fmt_graph_block(last_ev.get("graph", {}) or {}))
    out.append("")
    out.append(_fmt_proposals_block(last_ev.get("proposals", []) or []))
    out.append("")
    out.append(_fmt_compensations_block(last_ev.get("compensations", []) or []))
    out.append("")
    out.append(_fmt_distribution_block(stats))
    out.append("=" * 50)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def _cli(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m cortex.mesh.dashboard_cli",
        description="SPEACE CNM telemetry dashboard (read-only).",
    )
    p.add_argument("--path", default=DEFAULT_MESH_STATE_PATH,
                   help=f"Path to mesh_state.jsonl (default: {DEFAULT_MESH_STATE_PATH})")
    p.add_argument("--last", type=int, default=1,
                   help="Mostra metriche dell'ultimo evento (default: 1)")
    p.add_argument("--json", action="store_true",
                   help="Output JSON raw dell'ultimo evento")
    p.add_argument("--stats", action="store_true",
                   help="Solo stats aggregate")
    args = p.parse_args(argv)

    tlm = MeshTelemetry(args.path)

    if args.stats:
        print(json.dumps(tlm.stats(), indent=2, ensure_ascii=False))
        return 0

    if args.json:
        events = tlm.tail(limit=1)
        if not events:
            print("{}")
            return 0
        print(json.dumps(events[-1], indent=2, ensure_ascii=False))
        return 0

    print(render_dashboard(path=args.path, last=args.last))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
