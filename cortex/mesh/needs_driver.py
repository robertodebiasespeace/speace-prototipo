"""
cortex.mesh.needs_driver — Modello dei 5 bisogni dell'organismo (M4.9)

Il NeedsDriver è il cuore omeostatico della Continuous Neural Mesh: osserva lo
stato dell'organismo (mesh graph, runtime, registry, feedback fitness) e produce
un `NeedsSnapshot` (OLC) che quantifica il livello attuale dei 5 bisogni
canonici e il loro `gap` rispetto ai target di equilibrio.

I 5 bisogni (NEEDS_CATALOG):
  - survival         → integrità tecnica: errori, quarantene, latenze
  - expansion        → copertura funzionale: needs serviti, neuroni attivi
  - self_improvement → trend di fitness positivo, mutazioni accettate
  - integration      → coerenza del grafo: rapporto edge/nodi, sink/root
  - harmony          → equilibrio sistemico: assenza di concentrazioni di rischio

Output OLC:
  `NeedsSnapshot(needs=Dict[need→[0..1]], gap=Dict[need→[0..1]], ts=...)`
  - needs[k] = 1.0 → bisogno completamente soddisfatto
  - needs[k] = 0.0 → bisogno in stato critico
  - gap[k]   = max(0, target[k] - needs[k]) → solo i DEFICIT (non i surplus)

Filosofia:
  Il driver è **read-only**: non modifica la mesh, non fa side-effect, non
  schedula. Produce solo l'osservazione strutturale. M4.10 (harmony safeguard)
  e M4.11 (task generator) sono i CONSUMATORI di questo segnale.

Idempotenza & determinismo:
  Stesso input → stesso output (a meno del timestamp `ts`). I valori sono
  calcolati con euristiche dichiarate, semplici e clampate in [0..1].

API principale:
  driver = NeedsDriver(target_levels={"survival": 0.85, ...})
  snap   = driver.observe(graph_snapshot=..., runtime_snapshot=..., registry=..., fitness_history=...)
  driver.history() → list[NeedsSnapshot] (ring buffer)
  driver.priority_gap() → list[(need, gap)] sorted desc
"""

from __future__ import annotations

import dataclasses
import threading
from collections import deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from cortex.mesh.olc import NeedsSnapshot, FeedbackFrame
from cortex.mesh.olc.base import NEEDS_CATALOG

# ---------------------------------------------------------------------------
# Default target levels (epigenome.mesh.needs.targets, §6.2)
# ---------------------------------------------------------------------------

DEFAULT_TARGETS: Dict[str, float] = {
    "survival": 0.90,           # alto: la sopravvivenza è prioritaria
    "expansion": 0.70,
    "self_improvement": 0.65,
    "integration": 0.75,
    "harmony": 0.80,
}

# Pesi storici per fitness EWMA (più recente conta di più)
_EWMA_ALPHA = 0.4


def _clamp01(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


# ---------------------------------------------------------------------------
# NeedsDriver
# ---------------------------------------------------------------------------


class NeedsDriver:
    """
    Modello osservazionale dei 5 bisogni dell'organismo SPEACE-mesh.

    Thread-safe (lock interno solo per history/cache).
    """

    def __init__(
        self,
        *,
        target_levels: Optional[Dict[str, float]] = None,
        history_size: int = 64,
        baseline_neurons: int = 10,
    ) -> None:
        # Validazione target
        targets = dict(DEFAULT_TARGETS)
        if target_levels:
            for k, v in target_levels.items():
                if k not in NEEDS_CATALOG:
                    raise ValueError(f"target sconosciuto: {k} (catalog={NEEDS_CATALOG})")
                targets[k] = _clamp01(float(v))
        # Garantisce tutte le 5 chiavi
        for k in NEEDS_CATALOG:
            targets.setdefault(k, 0.7)
        self._targets: Dict[str, float] = targets
        self._baseline_neurons = max(1, int(baseline_neurons))

        self._history: Deque[NeedsSnapshot] = deque(maxlen=int(history_size))
        self._last: Optional[NeedsSnapshot] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------ properties --

    @property
    def targets(self) -> Dict[str, float]:
        return dict(self._targets)

    def last(self) -> Optional[NeedsSnapshot]:
        with self._lock:
            return self._last

    def history(self) -> List[NeedsSnapshot]:
        with self._lock:
            return list(self._history)

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._last = None

    # ------------------------------------------------------------ core observe --

    def observe(
        self,
        *,
        graph_snapshot: Optional[Dict[str, Any]] = None,
        runtime_snapshot: Optional[Dict[str, Any]] = None,
        registry: Any = None,
        fitness_history: Optional[Iterable[FeedbackFrame]] = None,
        risk_proposals: Optional[Dict[str, int]] = None,
    ) -> NeedsSnapshot:
        """
        Calcola il NeedsSnapshot corrente.

        Parameters
        ----------
        graph_snapshot : dict | None
            Output di `MeshGraph.snapshot()`. Se None, l'integration & expansion
            ricadono su euristiche conservative (medie basse).
        runtime_snapshot : dict | None
            Output di `MeshRuntime.snapshot()` (counters errori/cicli).
        registry : NeuronRegistry | None
            Per consultare quarantene attive.
        fitness_history : iterable[FeedbackFrame] | None
            Sequenza recente di feedback frame (per stimare self_improvement).
        risk_proposals : dict | None
            Counter per livello di rischio: {"low": n, "medium": n, "high": n}.
            Concorre al calcolo di `harmony`.
        """
        survival = self._compute_survival(graph_snapshot, runtime_snapshot, registry)
        expansion = self._compute_expansion(graph_snapshot)
        self_improvement = self._compute_self_improvement(fitness_history)
        integration = self._compute_integration(graph_snapshot)
        harmony = self._compute_harmony(graph_snapshot, registry, risk_proposals)

        needs: Dict[str, float] = {
            "survival": _clamp01(survival),
            "expansion": _clamp01(expansion),
            "self_improvement": _clamp01(self_improvement),
            "integration": _clamp01(integration),
            "harmony": _clamp01(harmony),
        }
        gap: Dict[str, float] = {
            k: _clamp01(self._targets[k] - needs[k]) for k in NEEDS_CATALOG
        }

        snap = NeedsSnapshot(needs=needs, gap=gap)

        # Validazione difensiva (NeedsSnapshot.validate() controlla catalog & range)
        violations = snap.validate()
        if violations:
            # Fallback: fabbrichiamo uno snapshot neutro (0.5 ovunque) e includiamo
            # le violations come segnale leggibile in `notes` via wrapper esterno.
            neutral = {k: 0.5 for k in NEEDS_CATALOG}
            neutral_gap = {k: max(0.0, self._targets[k] - 0.5) for k in NEEDS_CATALOG}
            snap = NeedsSnapshot(needs=neutral, gap=neutral_gap)

        with self._lock:
            self._history.append(snap)
            self._last = snap
        return snap

    # ------------------------------------------------------------ priority --

    def priority_gap(self, snapshot: Optional[NeedsSnapshot] = None) -> List[Tuple[str, float]]:
        """
        Ritorna [(need, gap)] ordinato per gap discendente (priorità decrescente).
        Solo i need con gap > 0 vengono inclusi.
        """
        snap = snapshot or self._last
        if snap is None:
            return []
        items = [(k, float(snap.gap.get(k, 0.0))) for k in NEEDS_CATALOG]
        items = [it for it in items if it[1] > 0.0]
        items.sort(key=lambda x: x[1], reverse=True)
        return items

    def driving_need(self, snapshot: Optional[NeedsSnapshot] = None) -> Optional[str]:
        """Need con il gap più alto (None se nessun gap > 0)."""
        pri = self.priority_gap(snapshot)
        return pri[0][0] if pri else None

    # ------------------------------------------------------------ computations --

    def _compute_survival(
        self,
        graph_snapshot: Optional[Dict[str, Any]],
        runtime_snapshot: Optional[Dict[str, Any]],
        registry: Any,
    ) -> float:
        """
        survival ∈ [0..1]
          1.0 se nessuna quarantena, nessun errore, nessun fallimento edge.
          decade con quarantene, error_rate, failure_rate edge.

        Modello:
          survival = 1.0
                  - 0.5 * quarantine_rate
                  - 0.3 * error_rate
                  - 0.2 * edge_failure_rate
        """
        total_nodes = 0
        quarantined = 0
        if graph_snapshot:
            total_nodes = int(graph_snapshot.get("stats", {}).get("nodes", 0))

        if registry is not None and total_nodes > 0:
            try:
                names = list(registry.names())
                quarantined = sum(1 for nm in names if registry.is_quarantined(nm))
            except Exception:
                quarantined = 0

        quar_rate = (quarantined / total_nodes) if total_nodes > 0 else 0.0

        # Error rate da runtime snapshot
        err_rate = 0.0
        if runtime_snapshot:
            cycles = float(runtime_snapshot.get("cycles", 0) or 0)
            errors = float(runtime_snapshot.get("errors", 0) or 0)
            if cycles > 0:
                err_rate = min(1.0, errors / cycles)

        # Edge failure rate da graph snapshot edges
        edge_fail_rate = 0.0
        if graph_snapshot:
            edges = graph_snapshot.get("edges", []) or []
            tot_succ = sum(int(e.get("successes", 0)) for e in edges)
            tot_fail = sum(int(e.get("failures", 0)) for e in edges)
            denom = tot_succ + tot_fail
            if denom > 0:
                edge_fail_rate = tot_fail / denom

        return 1.0 - 0.5 * quar_rate - 0.3 * err_rate - 0.2 * edge_fail_rate

    def _compute_expansion(self, graph_snapshot: Optional[Dict[str, Any]]) -> float:
        """
        expansion ∈ [0..1]
          combina:
            * coverage = need-served-coverage / 5  (frazione di need con almeno 1 neurone)
            * scale    = min(1, total_nodes / baseline)

          expansion = 0.6 * coverage + 0.4 * scale
        """
        if not graph_snapshot:
            return 0.2  # bassa: organismo embrionale

        stats = graph_snapshot.get("stats", {}) or {}
        nodes = int(stats.get("nodes", 0) or 0)
        needs_counts = stats.get("needs", {}) or {}
        served = sum(1 for k in NEEDS_CATALOG if int(needs_counts.get(k, 0) or 0) > 0)
        coverage = served / float(len(NEEDS_CATALOG))

        scale = min(1.0, nodes / float(self._baseline_neurons))
        return 0.6 * coverage + 0.4 * scale

    def _compute_self_improvement(
        self, fitness_history: Optional[Iterable[FeedbackFrame]]
    ) -> float:
        """
        self_improvement ∈ [0..1]
          Stima EWMA dei fitness_delta recenti, mappata su [0..1] tramite:
            score = (ewma + 1) / 2     # [-1..+1] → [0..1]

          Nessuna storia → 0.5 (neutro, non penalizziamo l'assenza).
        """
        if fitness_history is None:
            return 0.5

        deltas: List[float] = []
        for f in fitness_history:
            try:
                deltas.append(float(f.fitness_delta))
            except Exception:
                continue
        if not deltas:
            return 0.5

        # EWMA con alpha verso il più recente
        ewma = deltas[0]
        for d in deltas[1:]:
            ewma = _EWMA_ALPHA * d + (1.0 - _EWMA_ALPHA) * ewma

        # Mappiamo [-1..+1] → [0..1]
        return _clamp01((ewma + 1.0) / 2.0)

    def _compute_integration(self, graph_snapshot: Optional[Dict[str, Any]]) -> float:
        """
        integration ∈ [0..1]
          Quanto il grafo è connesso/integrato:
            edge_density = edges / max(1, nodes)        # ~2 = mesh ricca
            edge_score   = min(1, edge_density / 1.5)   # 1.5 edge/node = pieno
            balance      = 1 - |roots - sinks| / max(1, nodes)

          integration = 0.7 * edge_score + 0.3 * balance
        """
        if not graph_snapshot:
            return 0.3

        stats = graph_snapshot.get("stats", {}) or {}
        nodes = int(stats.get("nodes", 0) or 0)
        edges = int(stats.get("edges", 0) or 0)
        roots = int(stats.get("roots", 0) or 0)
        sinks = int(stats.get("sinks", 0) or 0)
        if nodes <= 0:
            return 0.0

        density = edges / float(nodes)
        edge_score = min(1.0, density / 1.5)
        imbalance = abs(roots - sinks) / float(nodes)
        balance = max(0.0, 1.0 - imbalance)
        return 0.7 * edge_score + 0.3 * balance

    def _compute_harmony(
        self,
        graph_snapshot: Optional[Dict[str, Any]],
        registry: Any,
        risk_proposals: Optional[Dict[str, int]],
    ) -> float:
        """
        harmony ∈ [0..1]
          Equilibrio sistemico — penalizza concentrazione di rischio:
            * proposte HIGH in coda
            * quarantene
            * sbilanci di livelli (un solo level dominante)

          harmony = 1.0 - 0.5 * high_risk_share - 0.3 * quar_rate - 0.2 * level_skew
        """
        # 1) high-risk proposals share
        high_share = 0.0
        if risk_proposals:
            tot = sum(int(v) for v in risk_proposals.values()) or 0
            high = int(risk_proposals.get("high", 0) or 0)
            if tot > 0:
                high_share = high / float(tot)

        # 2) quarantine rate
        total_nodes = 0
        quarantined = 0
        if graph_snapshot:
            total_nodes = int(graph_snapshot.get("stats", {}).get("nodes", 0) or 0)
        if registry is not None and total_nodes > 0:
            try:
                names = list(registry.names())
                quarantined = sum(1 for nm in names if registry.is_quarantined(nm))
            except Exception:
                quarantined = 0
        quar_rate = (quarantined / total_nodes) if total_nodes > 0 else 0.0

        # 3) level skew = |max_level_share - 1/5|
        level_skew = 0.0
        if graph_snapshot:
            levels = graph_snapshot.get("stats", {}).get("levels", {}) or {}
            counts = [int(v or 0) for v in levels.values() if int(v or 0) > 0]
            if counts:
                tot = sum(counts)
                if tot > 0:
                    max_share = max(counts) / float(tot)
                    expected = 1.0 / max(1, len(counts))
                    level_skew = max(0.0, max_share - expected)
                    # normalizza: skew massimo possibile = 1 - 1/n
                    if len(counts) > 1:
                        level_skew = level_skew / (1.0 - 1.0 / len(counts))

        return 1.0 - 0.5 * high_share - 0.3 * quar_rate - 0.2 * level_skew

    # ------------------------------------------------------------ utils --

    def to_dict(self, snapshot: Optional[NeedsSnapshot] = None) -> Dict[str, Any]:
        """Serializzazione JSON-safe per telemetria (M4.13)."""
        snap = snapshot or self._last
        if snap is None:
            return {"needs": {}, "gap": {}, "targets": dict(self._targets), "ts": None}
        return {
            "needs": dict(snap.needs),
            "gap": dict(snap.gap),
            "targets": dict(self._targets),
            "ts": snap.ts,
            "priority": [list(it) for it in self.priority_gap(snap)],
            "driving_need": self.driving_need(snap),
        }


# ---------------------------------------------------------------------------
# Convenience: singleton (opt-in)
# ---------------------------------------------------------------------------

_DEFAULT_DRIVER: Optional[NeedsDriver] = None
_DEFAULT_LOCK = threading.Lock()


def default_driver() -> NeedsDriver:
    """Singleton lazy: solo se richiesto esplicitamente."""
    global _DEFAULT_DRIVER
    if _DEFAULT_DRIVER is not None:
        return _DEFAULT_DRIVER
    with _DEFAULT_LOCK:
        if _DEFAULT_DRIVER is None:
            _DEFAULT_DRIVER = NeedsDriver()
    return _DEFAULT_DRIVER


__all__ = [
    "NeedsDriver",
    "DEFAULT_TARGETS",
    "default_driver",
]
