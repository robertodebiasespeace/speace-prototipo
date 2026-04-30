"""
AutobiographicalMemory — M5.8 + M5.9 (Cognitive Autonomy)

Implementa la memoria autobiografica di SPEACE con backend SQLite + FTS5.
Classifica automaticamente ogni esperienza in EVENT (episodio singolo)
o STRUCTURE (pattern ricorrente / apprendimento strutturale).

Schema SQLite:
    episodes       — ogni ciclo SMFOI / brain cycle registrato
    structures     — pattern consolidati estratti dagli episodi
    fts_index      — Full Text Search su content degli episodi

Port selettivo da:
    speaceorganismocibernetico/SPEACE_Cortex/learning_core/online_learner.py
    → Experience Replay con pesi per importanza (outcome, novelty, recency)

M5.9 aggiunge:
    - EventClassifier: EVENT vs STRUCTURE tramite frequenza + deviazione
    - SPEACEOnlineLearner (port): Experience Replay su buffer SQLite
    - continuity_score: misura coerenza identitativa nel tempo (M5.10)

Milestone: M5.8 + M5.9 + M5.10
Versione: 1.1 | 2026-04-26
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.memory.autobiographical")

_DEFAULT_DB = Path("memory") / "autobiographical.sqlite"


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class MemoryType(str, Enum):
    EVENT     = "event"       # episodio singolo (ciclo, percezione, azione)
    STRUCTURE = "structure"   # pattern consolidato (apprendimento strutturale)
    REPLAY    = "replay"      # episodio riattivato da Experience Replay


@dataclass
class Episode:
    """Un'esperienza registrata nella memoria autobiografica."""
    id:          str
    ts:          float          # unix timestamp
    cycle_id:    str
    memory_type: MemoryType
    content:     Dict[str, Any] # dati grezzi dell'episodio
    outcome:     float          # fitness/reward [0, 1]
    novelty:     float          # quanto è insolito [0, 1]
    importance:  float          # peso per Experience Replay
    tags:        List[str]

    @classmethod
    def create(
        cls,
        cycle_id: str,
        content: Dict[str, Any],
        outcome: float = 0.5,
        novelty: float = 0.3,
        memory_type: MemoryType = MemoryType.EVENT,
        tags: Optional[List[str]] = None,
    ) -> "Episode":
        importance = 0.5 * outcome + 0.3 * novelty + 0.2 * (1.0 if memory_type == MemoryType.STRUCTURE else 0.0)
        return cls(
            id=str(uuid.uuid4())[:8],
            ts=time.time(),
            cycle_id=cycle_id,
            memory_type=memory_type,
            content=content,
            outcome=float(np.clip(outcome, 0.0, 1.0)),
            novelty=float(np.clip(novelty, 0.0, 1.0)),
            importance=float(np.clip(importance, 0.0, 1.0)),
            tags=tags or [],
        )


# ---------------------------------------------------------------------------
# M5.9 — Event Classifier
# ---------------------------------------------------------------------------

class EventClassifier:
    """
    M5.9 — Classifica un episodio come EVENT o STRUCTURE.

    Logica:
    - Se outcome e novelty sono coerenti con pattern storici recenti
      (bassa deviazione) → STRUCTURE (il sistema ha imparato)
    - Se l'episodio è insolito o outcome alto (nuovo massimo) → EVENT

    Il threshold si adatta alla storia: più episodi ci sono,
    più selettivo diventa il classificatore per STRUCTURE.
    """

    def __init__(self, window: int = 50, structure_threshold: float = 0.15) -> None:
        self._window = window
        self._threshold = structure_threshold
        self._outcome_history: List[float] = []

    def classify(self, outcome: float, novelty: float) -> MemoryType:
        self._outcome_history.append(outcome)
        if len(self._outcome_history) > self._window:
            self._outcome_history = self._outcome_history[-self._window:]

        if len(self._outcome_history) < 5:
            return MemoryType.EVENT  # troppo pochi dati per riconoscere strutture

        recent = self._outcome_history[-20:]
        std = float(np.std(recent))
        mean = float(np.mean(recent))
        deviation = abs(outcome - mean)

        # Pattern stabile + bassa novelty = STRUCTURE
        if std < self._threshold and deviation < self._threshold and novelty < 0.25:
            return MemoryType.STRUCTURE

        return MemoryType.EVENT

    def reset(self) -> None:
        self._outcome_history.clear()


# ---------------------------------------------------------------------------
# M5.9 — Online Learner (port da speaceorganismocibernetico)
# ---------------------------------------------------------------------------

class SPEACEOnlineLearner:
    """
    M5.9 — Experience Replay con pesi per importanza.
    Port da speaceorganismocibernetico/learning_core/online_learner.py
    con backend SQLite invece di lista in-memory.

    Differenze dal port originale:
    - Buffer backed da SQLite (persistente tra sessioni)
    - Campionamento pesato per importance (non uniforme)
    - Metriche estese: best/avg/recent fitness
    """

    def __init__(self, db: "AutobiographicalMemory", max_buffer: int = 1000) -> None:
        self._db = db
        self._max_buffer = max_buffer
        self.metrics: Dict[str, float] = {
            "cycles_learned": 0.0,
            "avg_fitness": 0.0,
            "best_fitness": 0.0,
            "last_outcome": 0.0,
        }

    def learn(
        self,
        features: Dict[str, float],
        outcome: float,
        context: Optional[Dict] = None,
        cycle_id: Optional[str] = None,
    ) -> None:
        """Registra un'esperienza e aggiorna le metriche."""
        cid = cycle_id or f"ol-{int(time.time())}"
        content = {"features": features, "context": context or {}}
        novelty = self._estimate_novelty(outcome)
        ep = Episode.create(
            cycle_id=cid,
            content=content,
            outcome=outcome,
            novelty=novelty,
            tags=["online_learner"],
        )
        self._db.store(ep)

        self.metrics["cycles_learned"] += 1
        self.metrics["last_outcome"] = outcome
        self.metrics["best_fitness"] = max(self.metrics["best_fitness"], outcome)

        recent = self._db.recent(n=200)
        if recent:
            self.metrics["avg_fitness"] = float(np.mean([e.outcome for e in recent]))

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Predizione basata su esperienze recenti."""
        recent = self._db.recent(n=300)
        if not recent:
            return {"prediction": 0.75, "confidence": 0.5, "samples": 0}
        outcomes = [e.outcome for e in recent]
        avg = float(np.mean(outcomes))
        return {
            "prediction": avg,
            "confidence": min(0.95, 0.6 + len(recent) / 400.0),
            "samples": len(recent),
            "avg_fitness": self.metrics["avg_fitness"],
            "best_fitness": self.metrics["best_fitness"],
        }

    def experience_replay(self, n_samples: int = 64) -> List[Episode]:
        """
        Campiona n episodi pesati per importance per consolidamento.
        Prioritizza episodi ad alta importanza (outcome alto + novelty alta).
        """
        episodes = self._db.recent(n=self._max_buffer)
        if len(episodes) < n_samples:
            return episodes

        weights = np.array([e.importance for e in episodes], dtype=float)
        weights = weights / weights.sum()
        indices = np.random.choice(len(episodes), size=n_samples, replace=False, p=weights)
        sampled = [episodes[i] for i in indices]
        logger.debug("Experience replay: %d/%d campioni", n_samples, len(episodes))
        return sampled

    def _estimate_novelty(self, outcome: float) -> float:
        """Stima novelty come deviazione dall'outcome medio recente."""
        recent = self._db.recent(n=50)
        if not recent:
            return 0.5
        avg = float(np.mean([e.outcome for e in recent]))
        return float(np.clip(abs(outcome - avg) * 2.0, 0.0, 1.0))

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


# ---------------------------------------------------------------------------
# AutobiographicalMemory — M5.8
# ---------------------------------------------------------------------------

class AutobiographicalMemory:
    """
    M5.8 — Memoria autobiografica persistente con backend SQLite.

    Fornisce:
    - store(episode) → inserisce episodio
    - recall(query)  → ricerca FTS full-text
    - recent(n)      → ultimi n episodi
    - structures()   → solo episodi di tipo STRUCTURE
    - continuity_score() → M5.10 (3 components)
    - continuity_breakdown() → M5.10 detailed dict
    """

    def __init__(
        self,
        db_path: Path = _DEFAULT_DB,
        enabled: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.enabled = enabled
        self._classifier = EventClassifier()
        self._learner: Optional[SPEACEOnlineLearner] = None
        self._episode_count = 0

        if enabled:
            self._init_db()
            self._learner = SPEACEOnlineLearner(self)
            logger.info("AutobiographicalMemory init: %s", self.db_path)

    # ------------------------------------------------------------------ #
    # DB setup
    # ------------------------------------------------------------------ #

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id          TEXT PRIMARY KEY,
                    ts          REAL NOT NULL,
                    cycle_id    TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    outcome     REAL NOT NULL DEFAULT 0.5,
                    novelty     REAL NOT NULL DEFAULT 0.3,
                    importance  REAL NOT NULL DEFAULT 0.5,
                    tags        TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_ts ON episodes(ts DESC);
                CREATE INDEX IF NOT EXISTS idx_type ON episodes(memory_type);
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_index
                    USING fts5(episode_id UNINDEXED, content, tokenize='porter ascii');
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def store(self, episode: Episode) -> str:
        """Inserisce un episodio. Se disabled, no-op."""
        if not self.enabled:
            return episode.id
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO episodes VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    episode.id, episode.ts, episode.cycle_id,
                    episode.memory_type.value,
                    json.dumps(episode.content),
                    episode.outcome, episode.novelty, episode.importance,
                    json.dumps(episode.tags),
                ),
            )
            # FTS index
            text_content = json.dumps(episode.content)
            conn.execute(
                "INSERT INTO fts_index(episode_id, content) VALUES (?,?)",
                (episode.id, text_content),
            )
        self._episode_count += 1
        return episode.id

    def recall(self, query: str, limit: int = 10) -> List[Episode]:
        """Ricerca FTS full-text negli episodi."""
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT e.* FROM episodes e
                   JOIN fts_index f ON e.id = f.episode_id
                   WHERE f.content MATCH ?
                   ORDER BY e.ts DESC LIMIT ?""",
                (query, limit),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def recent(self, n: int = 50) -> List[Episode]:
        """Ultimi n episodi per timestamp."""
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY ts DESC LIMIT ?", (n,)
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    def structures(self, limit: int = 20) -> List[Episode]:
        """Solo episodi di tipo STRUCTURE (pattern consolidati)."""
        if not self.enabled:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE memory_type=? ORDER BY importance DESC LIMIT ?",
                (MemoryType.STRUCTURE.value, limit),
            ).fetchall()
        return [self._row_to_episode(r) for r in rows]

    # ------------------------------------------------------------------ #
    # High-level API
    # ------------------------------------------------------------------ #

    def record_cycle(
        self,
        cycle_id: str,
        smfoi_result: Dict[str, Any],
        brain_state: Optional[Dict[str, Any]] = None,
        homeostasis_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Episode]:
        """
        Registra un ciclo completo come episodio autobiografico.
        Classifica automaticamente EVENT vs STRUCTURE.
        """
        if not self.enabled:
            return None

        outcome = float(smfoi_result.get("outcome", {}).get("fitness_after", 0.5))
        content: Dict[str, Any] = {
            "cycle_id":    cycle_id,
            "smfoi":       smfoi_result.get("action", "heartbeat"),
            "fitness":     outcome,
        }
        if brain_state:
            content["consciousness"] = brain_state.get("consciousness_index", 0.0)
            content["dopamine"]      = brain_state.get("dopamine_level", 0.5)
        if homeostasis_result:
            content["viability"]     = homeostasis_result.get("viability_score", 1.0)
            content["alerts"]        = homeostasis_result.get("alerts", [])

        # Classificazione M5.9
        novelty = abs(outcome - (self.metrics().get("avg_outcome", 0.5)))
        memory_type = self._classifier.classify(outcome, novelty)

        ep = Episode.create(
            cycle_id=cycle_id,
            content=content,
            outcome=outcome,
            novelty=float(np.clip(novelty * 2, 0.0, 1.0)),
            memory_type=memory_type,
            tags=["cycle", memory_type.value],
        )
        self.store(ep)
        return ep

    # ------------------------------------------------------------------ #
    # M5.10 — Continuity score (full implementation)
    # ------------------------------------------------------------------ #

    def continuity_score(self, window: int = 30) -> float:
        """
        M5.10 — Misura la coerenza identitativa di SPEACE nel tempo.

        Tre componenti con pesi diversi:

        1. Outcome stability (peso 0.45)
           Formula: max(0, 1 - std(outcomes) * 4)

        2. Type coherence (peso 0.30)
           Proporzione episodi STRUCTURE su totale nella finestra.
           Alta proportion STRUCTURE = alta maturità cognitiva.

        3. Temporal coherence (peso 0.25)
           Varianza residua rispetto al trend lineare degli outcome.
           Formula: max(0, 1 - residual_std * 4)

        Score aggregato: C = 0.45*S1 + 0.30*S2 + 0.25*S3

        Un cambio brusco (mutazione DNA) causa picco std→drop S1,
        più EVENT→drop S2, rottura trend→drop S3 → score diminuisce.

        Returns:
            float in [0.0, 1.0]
        """
        if not self.enabled:
            return 1.0

        episodes = self.recent(n=window)
        if len(episodes) < 3:
            return 1.0

        outcomes = np.array([e.outcome for e in episodes], dtype=float)
        types    = [e.memory_type for e in episodes]
        n        = len(outcomes)

        # S1: Outcome stability
        std_out = float(np.std(outcomes))
        s1 = float(max(0.0, 1.0 - std_out * 4.0))

        # S2: Type coherence
        n_struct = sum(1 for t in types if t == MemoryType.STRUCTURE)
        s2 = float(n_struct / n)

        # S3: Temporal coherence (linear detrending)
        t_axis = np.arange(n, dtype=float)
        t_mean = t_axis.mean()
        o_mean = outcomes.mean()
        denom  = float(np.sum((t_axis - t_mean) ** 2))
        if denom > 1e-9:
            slope = float(np.sum((t_axis - t_mean) * (outcomes - o_mean)) / denom)
            trend = t_axis * slope + (o_mean - slope * t_mean)
        else:
            trend = np.full(n, o_mean)
        resid_std = float(np.std(outcomes - trend))
        s3 = float(max(0.0, 1.0 - resid_std * 4.0))

        score = 0.45 * s1 + 0.30 * s2 + 0.25 * s3
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    def continuity_breakdown(self, window: int = 30) -> Dict[str, float]:
        """
        M5.10 — Dettaglio delle 3 componenti del continuity score.
        Utile per diagnostica e dashboard.

        Returns dict con keys: score, s1_outcome_stability,
        s2_type_coherence, s3_temporal_coherence, n_episodes,
        outcome_std, residual_std.
        """
        if not self.enabled:
            return {"score": 1.0, "s1_outcome_stability": 1.0,
                    "s2_type_coherence": 1.0, "s3_temporal_coherence": 1.0,
                    "n_episodes": 0}

        episodes = self.recent(n=window)
        n = len(episodes)
        if n < 3:
            return {"score": 1.0, "s1_outcome_stability": 1.0,
                    "s2_type_coherence": 1.0, "s3_temporal_coherence": 1.0,
                    "n_episodes": n}

        outcomes = np.array([e.outcome for e in episodes], dtype=float)
        types    = [e.memory_type for e in episodes]

        std_out  = float(np.std(outcomes))
        s1 = float(max(0.0, 1.0 - std_out * 4.0))

        n_struct = sum(1 for t in types if t == MemoryType.STRUCTURE)
        s2 = float(n_struct / n)

        t_axis = np.arange(n, dtype=float)
        t_mean = t_axis.mean(); o_mean = outcomes.mean()
        denom  = float(np.sum((t_axis - t_mean) ** 2))
        if denom > 1e-9:
            slope = float(np.sum((t_axis - t_mean) * (outcomes - o_mean)) / denom)
            trend = t_axis * slope + (o_mean - slope * t_mean)
        else:
            trend = np.full(n, o_mean)
        resid_std = float(np.std(outcomes - trend))
        s3 = float(max(0.0, 1.0 - resid_std * 4.0))

        score = 0.45 * s1 + 0.30 * s2 + 0.25 * s3
        return {
            "score":                 round(float(np.clip(score, 0.0, 1.0)), 4),
            "s1_outcome_stability":  round(s1, 4),
            "s2_type_coherence":     round(s2, 4),
            "s3_temporal_coherence": round(s3, 4),
            "n_episodes":            n,
            "outcome_std":           round(std_out, 4),
            "residual_std":          round(resid_std, 4),
        }

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #

    def metrics(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "count": 0}
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            n_struct = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE memory_type=?",
                (MemoryType.STRUCTURE.value,)
            ).fetchone()[0]
            avg_out = conn.execute("SELECT AVG(outcome) FROM episodes").fetchone()[0] or 0.5
        return {
            "enabled":     True,
            "count":       total,
            "structures":  n_struct,
            "events":      total - n_struct,
            "avg_outcome": round(float(avg_out), 4),
            "continuity":  self.continuity_score(),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        return Episode(
            id=row["id"],
            ts=row["ts"],
            cycle_id=row["cycle_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=json.loads(row["content"]),
            outcome=row["outcome"],
            novelty=row["novelty"],
            importance=row["importance"],
            tags=json.loads(row["tags"]),
        )

    def __repr__(self) -> str:
        m = self.metrics()
        return (f"AutobiographicalMemory(enabled={self.enabled}, "
                f"count={m.get('count',0)}, "
                f"structures={m.get('structures',0)})")


__all__ = [
    "MemoryType", "Episode", "EventClassifier",
    "SPEACEOnlineLearner", "AutobiographicalMemory",
    # M5.10: continuity_breakdown exposed via AutobiographicalMemory.continuity_breakdown()
]
