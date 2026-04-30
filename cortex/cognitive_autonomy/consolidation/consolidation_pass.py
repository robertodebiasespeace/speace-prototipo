"""
cortex.cognitive_autonomy.consolidation.consolidation_pass
============================================================
M10.4 — ConsolidationPass: hippocampal replay per SPEACE.

Processo:
  1. SCAN     — legge episodi recenti da AutobiographicalMemory
  2. RANK     — calcola importanza composita (outcome × novelty × recency)
  3. EXTRACT  — raggruppa episodi per tag → estrae pattern
  4. COMPRESS — genera MemoryTrace compresse (1 trace per cluster)
  5. PRUNE    — marca per rimozione episodi sotto soglia importanza
  6. EMIT     — pubblica MEMORY_CONSOLIDATED su EventBus (se disponibile)

Questa classe è STANDALONE: funziona anche senza EventBus (bus=None)
e senza AutobiographicalMemory reale (accetta lista di dict come input).

M10.4 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("speace.consolidation")


# ─────────────────────────────────────────────────────────────────────────────
# ConsolidationConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConsolidationConfig:
    """
    Parametri del ciclo di consolidamento.

    Attributi:
        max_episodes:        numero massimo di episodi da processare per ciclo
        importance_threshold: soglia sotto cui un episodio viene candidato al pruning
        min_cluster_size:    episodi minimi per formare un pattern/trace
        recency_weight:      peso della recency nel calcolo importanza composita
                             (1.0 = recency piena, 0.0 = solo outcome+novelty)
        prune_ratio:         frazione degli episodi da prunare (0.0→0.50)
    """
    max_episodes:         int   = 50
    importance_threshold: float = 0.30
    min_cluster_size:     int   = 2
    recency_weight:       float = 0.20
    prune_ratio:          float = 0.20


# ─────────────────────────────────────────────────────────────────────────────
# MemoryTrace — traccia di lungo termine
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MemoryTrace:
    """
    Traccia di memoria compressa (da episodi multipli → 1 pattern).

    Attributi:
        trace_id:    identificatore univoco
        tags:        tag comuni del cluster
        summary:     sintesi testuale del pattern
        importance:  importanza media del cluster
        episode_ids: lista degli episodi sorgente
        timestamp:   quando è stata creata
        outcome_avg: outcome medio del cluster (−1.0 → +1.0)
    """
    trace_id:    str
    tags:        List[str]
    summary:     str
    importance:  float
    episode_ids: List[str]
    timestamp:   float = field(default_factory=time.time)
    outcome_avg: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trace_id":    self.trace_id,
            "tags":        self.tags,
            "summary":     self.summary[:200],
            "importance":  round(self.importance, 3),
            "episode_count": len(self.episode_ids),
            "outcome_avg": round(self.outcome_avg, 3),
            "timestamp":   self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ConsolidationResult — risultato di un ciclo
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConsolidationResult:
    """
    Risultato di un ciclo di consolidamento.

    Attributi:
        traces_created:    numero di MemoryTrace generate
        episodes_pruned:   numero di episodi candidati al pruning
        episodes_processed: numero totale di episodi esaminati
        patterns_found:    numero di pattern estratti
        duration_ms:       durata del ciclo in millisecondi
        traces:            lista delle MemoryTrace create
        pruned_ids:        lista degli episode_id da eliminare
    """
    traces_created:     int
    episodes_pruned:    int
    episodes_processed: int
    patterns_found:     int
    duration_ms:        float
    traces:             List[MemoryTrace] = field(default_factory=list)
    pruned_ids:         List[str]        = field(default_factory=list)

    @property
    def compression_ratio(self) -> float:
        """Rapporto di compressione: episodi → traces."""
        if self.episodes_processed == 0:
            return 0.0
        return 1.0 - (self.traces_created / max(self.episodes_processed, 1))

    def summary(self) -> str:
        return (
            f"[ConsolidationResult] "
            f"episodes={self.episodes_processed} "
            f"traces={self.traces_created} "
            f"pruned={self.episodes_pruned} "
            f"patterns={self.patterns_found} "
            f"compression={self.compression_ratio:.0%} "
            f"({self.duration_ms:.1f}ms)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ConsolidationPass — motore principale
# ─────────────────────────────────────────────────────────────────────────────

class ConsolidationPass:
    """
    M10.4 — Consolida la memoria episodica di SPEACE durante il deep sleep.

    Replica il ciclo ippocampale di replay→compressione→pruning.

    Uso con AutobiographicalMemory reale:
        memory = AutobiographicalMemory(enabled=True, ...)
        consolidator = ConsolidationPass(bus=event_bus)
        recent_episodes = [ep.to_dict() for ep in memory.recent(limit=50)]
        result = consolidator.run(recent_episodes)
        # Applica pruning
        for ep_id in result.pruned_ids:
            memory.forget(ep_id)  # se il metodo esiste

    Uso standalone (test / debug):
        episodes = [
            {"episode_id": "ep1", "action": "expand_mesh",
             "outcome": 0.8, "novelty": 0.7,
             "tags": ["evolution", "network"], "timestamp": time.time()},
            ...
        ]
        result = ConsolidationPass().run(episodes)
    """

    def __init__(
        self,
        config: Optional[ConsolidationConfig] = None,
        bus:    Any = None,   # EventBus opzionale
    ) -> None:
        self._config = config or ConsolidationConfig()
        self._bus    = bus
        self._traces: List[MemoryTrace] = []   # archivio long-term
        self._cycle_count = 0

    # ── API pubblica ──────────────────────────────────────────────────────────

    def run(
        self,
        episodes: List[Dict[str, Any]],
    ) -> ConsolidationResult:
        """
        Esegue un ciclo completo di consolidamento.

        Args:
            episodes: lista di dict con chiavi:
                      episode_id, action, outcome, novelty, tags, timestamp
                      (compatibile con Episode.to_dict() di AutobiographicalMemory)
        """
        t0 = time.monotonic()
        self._cycle_count += 1

        if not episodes:
            return ConsolidationResult(
                traces_created=0, episodes_pruned=0,
                episodes_processed=0, patterns_found=0, duration_ms=0.0,
            )

        # 1. Limita a max_episodes
        capped = episodes[: self._config.max_episodes]

        # 2. Calcola importanza composita
        ranked = self._rank(capped)

        # 3. Clustering per tag
        clusters = self._cluster(ranked)

        # 4. Estrai traces dai cluster abbastanza grandi
        new_traces: List[MemoryTrace] = []
        for cluster_tag, cluster_eps in clusters.items():
            if len(cluster_eps) >= self._config.min_cluster_size:
                trace = self._compress(cluster_tag, cluster_eps)
                new_traces.append(trace)
                self._traces.append(trace)

        # 5. Pruning: episodi sotto soglia (ordinati per importanza, peggiori per primi)
        prune_n = max(0, int(len(capped) * self._config.prune_ratio))
        pruned_ids = self._prune_candidates(ranked, prune_n)

        duration_ms = (time.monotonic() - t0) * 1000

        result = ConsolidationResult(
            traces_created=len(new_traces),
            episodes_pruned=len(pruned_ids),
            episodes_processed=len(capped),
            patterns_found=len(clusters),
            duration_ms=round(duration_ms, 2),
            traces=new_traces,
            pruned_ids=pruned_ids,
        )

        logger.info("[Consolidation] Ciclo %d — %s", self._cycle_count, result.summary())

        # 6. Emetti MEMORY_CONSOLIDATED su EventBus (se presente)
        self._maybe_emit(result)

        return result

    @property
    def long_term_traces(self) -> List[MemoryTrace]:
        """Tutte le traces accumulate nei cicli precedenti."""
        return list(self._traces)

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    # ── Step interni ──────────────────────────────────────────────────────────

    def _rank(
        self,
        episodes: List[Dict[str, Any]],
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Calcola importanza composita per ogni episodio.
        importance = outcome_norm * 0.50 + novelty * 0.30 + recency * weight
        """
        now = time.time()
        ranked = []
        for ep in episodes:
            outcome_raw = float(ep.get("outcome", 0.5))
            # Normalizza outcome da [-1,+1] o [0,1] → [0,1]
            if outcome_raw < 0:
                outcome_norm = (outcome_raw + 1.0) / 2.0
            else:
                outcome_norm = outcome_raw
            novelty     = float(ep.get("novelty", 0.5))
            ts          = float(ep.get("timestamp", now))
            age_h       = (now - ts) / 3600.0
            recency     = max(0.0, 1.0 - age_h / 24.0)  # decade su 24h

            importance = (
                outcome_norm * 0.50 +
                novelty      * 0.30 +
                recency      * self._config.recency_weight
            )
            ranked.append((importance, ep))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked

    def _cluster(
        self,
        ranked: List[Tuple[float, Dict[str, Any]]],
    ) -> Dict[str, List[Tuple[float, Dict[str, Any]]]]:
        """
        Raggruppa gli episodi per tag primario.
        Episodi senza tag vanno in cluster "untagged".
        """
        clusters: Dict[str, List] = defaultdict(list)
        for importance, ep in ranked:
            tags = ep.get("tags", [])
            if isinstance(tags, (list, tuple)) and tags:
                primary_tag = sorted(tags)[0]  # tag alfabeticamente primo
            elif isinstance(tags, set) and tags:
                primary_tag = sorted(tags)[0]
            else:
                primary_tag = "untagged"
            clusters[primary_tag].append((importance, ep))
        return dict(clusters)

    def _compress(
        self,
        cluster_tag: str,
        cluster_eps: List[Tuple[float, Dict[str, Any]]],
    ) -> MemoryTrace:
        """
        Crea una MemoryTrace compressa da un cluster di episodi.
        """
        importances   = [imp for imp, _ in cluster_eps]
        outcomes      = [float(ep.get("outcome", 0)) for _, ep in cluster_eps]
        episode_ids   = [ep.get("episode_id", ep.get("id", "?")) for _, ep in cluster_eps]

        avg_importance = sum(importances) / len(importances)
        avg_outcome    = sum(outcomes) / len(outcomes)

        # Raccoglie tutti i tag distinti del cluster
        all_tags: set = set()
        for _, ep in cluster_eps:
            t = ep.get("tags", [])
            if isinstance(t, (list, tuple, set)):
                all_tags.update(t)

        # Summary: le prime 2 azioni più importanti
        top_actions = [ep.get("action", "?") for _, ep in cluster_eps[:2]]
        summary = (
            f"Cluster '{cluster_tag}' — {len(cluster_eps)} episodi. "
            f"Azioni principali: {', '.join(top_actions)}. "
            f"Outcome medio: {avg_outcome:+.2f}."
        )

        trace_id = f"trace_{cluster_tag}_{self._cycle_count:04d}"
        return MemoryTrace(
            trace_id=trace_id,
            tags=sorted(all_tags),
            summary=summary,
            importance=round(avg_importance, 3),
            episode_ids=episode_ids,
            outcome_avg=round(avg_outcome, 3),
        )

    def _prune_candidates(
        self,
        ranked: List[Tuple[float, Dict[str, Any]]],
        n: int,
    ) -> List[str]:
        """
        Ritorna gli episode_id dei peggior N episodi (candidati al pruning).
        """
        if n <= 0:
            return []
        # ranked è ordinato per importanza decrescente → ultimi = da prunare
        low_importance = ranked[-n:]
        return [ep.get("episode_id", ep.get("id", "?")) for _, ep in low_importance]

    def _maybe_emit(self, result: ConsolidationResult) -> None:
        """Emette MEMORY_CONSOLIDATED su EventBus se disponibile."""
        if self._bus is None:
            return
        try:
            from cortex.events import EventType, SPEACEEvent
            event = SPEACEEvent(
                event_type=EventType.MEMORY_CONSOLIDATED,
                source="consolidation_pass",
                payload={
                    "traces": result.traces_created,
                    "pruned": result.episodes_pruned,
                    "cycle":  self._cycle_count,
                },
                priority=3,
            )
            self._bus.publish(event)
        except Exception as e:
            logger.debug("[Consolidation] EventBus emit failed: %s", e)


__all__ = [
    "ConsolidationPass",
    "ConsolidationConfig",
    "ConsolidationResult",
    "MemoryTrace",
]
