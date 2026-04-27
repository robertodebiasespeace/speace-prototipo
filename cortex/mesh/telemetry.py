"""
cortex.mesh.telemetry — Mesh State Logger (M4.13)

Telemetria append-only della Continuous Neural Mesh. Ogni "ciclo mesh" produce
un evento JSONL su `safeproactive/state/mesh_state.jsonl` (path configurabile).

Schema di un evento (linea JSON):

  {
    "ts": "2026-04-25T08:30:00Z",
    "cycle_id": "mesh-cyc-...",
    "verdict": "watch",                      # HarmonyVerdict
    "verdict_severity": 1,
    "needs": {survival, expansion, ...},     # 5 chiavi catalog
    "gap":   {survival, expansion, ...},
    "driving_need": "expansion",
    "graph": {nodes, edges, roots, sinks, levels, needs_count_by_need},
    "runtime": {cycles, errors, ...},
    "registry": {total, quarantined},
    "proposals": [{title, driving_need, priority, risk_level}, ...],
    "compensations": [{kind, target, severity}, ...],
    "allowed_risk_levels": ["low","medium","high"]
  }

Filosofia:
  - **Append-only & line-delimited**: nessun rewrite, log ricostruibile.
  - **JSON-safe**: nessun riferimento a oggetti Python in memoria.
  - **Best-effort**: errori di scrittura sono segnalati al chiamante ma non
    bloccano la mesh (telemetry NON deve causare side-effect critici).
  - **No side-effect ai cicli**: `record_cycle()` riceve snapshot già
    materializzati; non interroga registry/runtime al volo.

L'unico side-effect dichiarato è `fs_write:safeproactive/state/mesh_state.jsonl`.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import io
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from cortex.mesh.olc import NeedsSnapshot, TaskProposal
from cortex.mesh.harmony import HarmonyReport
from cortex.mesh.olc.base import NEEDS_CATALOG


# Path di default (relativo al root del progetto)
DEFAULT_MESH_STATE_PATH = "safeproactive/state/mesh_state.jsonl"

# Limite di linee dalla coda da leggere in tail()
DEFAULT_TAIL_LIMIT = 100


def _iso_now() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _new_cycle_id() -> str:
    return f"mesh-cyc-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_event(
    *,
    cycle_id: Optional[str] = None,
    needs_snapshot: Optional[NeedsSnapshot] = None,
    harmony_report: Optional[HarmonyReport] = None,
    graph_snapshot: Optional[Dict[str, Any]] = None,
    runtime_snapshot: Optional[Dict[str, Any]] = None,
    registry_summary: Optional[Dict[str, Any]] = None,
    proposals: Optional[List[TaskProposal]] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Costruisce un evento JSON-safe pronto da serializzare.

    Tutti i parametri sono opzionali — campi mancanti diventano `null` o `{}`.
    """
    cid = cycle_id or _new_cycle_id()

    needs_payload: Dict[str, Any] = {"needs": {}, "gap": {}, "ts": None, "driving_need": None}
    if needs_snapshot is not None:
        needs_payload["needs"] = dict(needs_snapshot.needs or {})
        needs_payload["gap"] = dict(needs_snapshot.gap or {})
        needs_payload["ts"] = getattr(needs_snapshot, "ts", None)
        if needs_payload["gap"]:
            sorted_gaps = sorted(
                ((k, float(v)) for k, v in needs_payload["gap"].items() if float(v) > 0),
                key=lambda x: x[1], reverse=True,
            )
            needs_payload["driving_need"] = sorted_gaps[0][0] if sorted_gaps else None

    verdict = None
    verdict_sev = None
    compensations: List[Dict[str, Any]] = []
    allowed_risk: List[str] = []
    if harmony_report is not None:
        verdict = str(harmony_report.verdict.value)
        verdict_sev = int(harmony_report.verdict.severity)
        compensations = [
            {"kind": c.kind, "target": c.target, "severity": int(c.severity)}
            for c in harmony_report.compensations
        ]
        allowed_risk = sorted(harmony_report.allowed_risk_levels)

    graph_payload: Dict[str, Any] = {}
    if graph_snapshot is not None:
        stats = dict(graph_snapshot.get("stats", {}) or {})
        graph_payload = {
            "nodes": int(stats.get("nodes", 0) or 0),
            "edges": int(stats.get("edges", 0) or 0),
            "roots": int(stats.get("roots", 0) or 0),
            "sinks": int(stats.get("sinks", 0) or 0),
            "levels": dict(stats.get("levels", {}) or {}),
            "needs_count_by_need": dict(stats.get("needs", {}) or {}),
        }

    proposals_payload: List[Dict[str, Any]] = []
    if proposals:
        for p in proposals:
            proposals_payload.append({
                "title": p.title,
                "driving_need": p.driving_need,
                "priority": float(p.priority),
                "risk_level": p.safeproactive_risk,
            })

    event: Dict[str, Any] = {
        "ts": _iso_now(),
        "cycle_id": cid,
        "verdict": verdict,
        "verdict_severity": verdict_sev,
        "needs": needs_payload["needs"],
        "gap": needs_payload["gap"],
        "driving_need": needs_payload["driving_need"],
        "graph": graph_payload,
        "runtime": dict(runtime_snapshot or {}),
        "registry": dict(registry_summary or {}),
        "proposals": proposals_payload,
        "compensations": compensations,
        "allowed_risk_levels": allowed_risk,
    }
    if extras:
        # Merge non distruttivo (extras NON può sovrascrivere chiavi standard)
        for k, v in extras.items():
            if k not in event:
                event[k] = v
    return event


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


class MeshTelemetry:
    """
    Logger thread-safe append-only verso un file JSONL.

    Uso tipico:
        tlm = MeshTelemetry("safeproactive/state/mesh_state.jsonl")
        tlm.record_cycle(
            needs_snapshot=snap,
            harmony_report=rep,
            graph_snapshot=g.snapshot(),
            proposals=props,
        )
    """

    def __init__(
        self,
        path: str = DEFAULT_MESH_STATE_PATH,
        *,
        ensure_dir: bool = True,
    ) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._ensure_dir = ensure_dir
        self._last_event: Optional[Dict[str, Any]] = None
        if ensure_dir:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    @property
    def path(self) -> Path:
        return self._path

    def last_event(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._last_event) if self._last_event else None

    # -------------------------------------------------------------- record --

    def record_cycle(self, **kwargs: Any) -> Dict[str, Any]:
        """Costruisce un evento, lo scrive e lo restituisce."""
        event = build_event(**kwargs)
        self._append(event)
        return event

    def record_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Scrive un evento già costruito (lo arricchisce con ts/cycle_id se mancanti)."""
        ev = dict(event)
        ev.setdefault("ts", _iso_now())
        ev.setdefault("cycle_id", _new_cycle_id())
        self._append(ev)
        return ev

    def _append(self, event: Dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8", newline="\n") as f:
                    f.write(line + "\n")
                self._last_event = event
            except OSError:
                # best-effort: non rilanciamo per non destabilizzare la mesh
                self._last_event = event

    # -------------------------------------------------------------- read --

    def read_all(self) -> Iterator[Dict[str, Any]]:
        """Itera tutti gli eventi nel file (senza caricarli in memoria)."""
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # linea corrotta: skip silenzioso
                    continue

    def tail(self, limit: int = DEFAULT_TAIL_LIMIT) -> List[Dict[str, Any]]:
        """Ritorna gli ultimi `limit` eventi (lista in ordine cronologico)."""
        if limit < 1:
            return []
        events = list(self.read_all())
        return events[-limit:]

    def stats(self) -> Dict[str, Any]:
        """Ritorna statistiche aggregate sull'intero file."""
        n = 0
        verdict_counts: Dict[str, int] = {}
        last_ts = None
        first_ts = None
        for ev in self.read_all():
            n += 1
            v = ev.get("verdict") or "none"
            verdict_counts[v] = verdict_counts.get(v, 0) + 1
            ts = ev.get("ts")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
        return {
            "events_total": n,
            "verdict_distribution": verdict_counts,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "path": str(self._path),
        }

    def clear(self) -> None:
        """Solo per testing: tronca il file."""
        with self._lock:
            if self._path.exists():
                self._path.unlink()
            if self._ensure_dir:
                self._path.parent.mkdir(parents=True, exist_ok=True)
            self._last_event = None


__all__ = [
    "MeshTelemetry",
    "build_event",
    "DEFAULT_MESH_STATE_PATH",
]
