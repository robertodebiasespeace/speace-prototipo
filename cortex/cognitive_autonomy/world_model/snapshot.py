"""
WorldSnapshot — M6.1 (World Model / Knowledge Graph)

Mantiene una fotografia dinamica del mondo fisico, tecnologico e SPEACE stesso.
Supporta due backend:
  - in-memory (default, veloce, volatile)
  - SQLite (opzionale, persistente tra sessioni)

Il WorldSnapshot è la fonte di verità centralizzata per tutti i comparti
del SPEACE Cortex. Gli altri sottosistemi (Perception, Reasoning, Planning, ecc.)
interrogano e aggiornano il WorldSnapshot.

Struttura del snapshot:
  meta          → versione, timestamp, update_count
  speace_state  → fase, fitness, agenti, ciclo corrente
  planet_state  → clima, biodiversità, sociale
  technology_state → AI, IoT, quantum
  rigene_objectives → obiettivi estratti dal Rigene Project
  knowledge_graph → entità + relazioni (gestito da KnowledgeGraph)
  scenarios     → lista scenari what-if generati da InferenceEngine
  feed_cache    → ultima lettura da feed esterni (NASA, NOAA, UN)

Milestone: M6.1
Versione: 1.0 | 2026-04-27
"""

from __future__ import annotations

import copy
import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speace.world_model.snapshot")

_DEFAULT_SEED_PATH = Path(__file__).resolve().parents[4] / "memory" / "world_model.json"
_DEFAULT_DB_PATH   = Path(__file__).resolve().parents[4] / "safeproactive" / "state" / "world_model.db"

# ---------------------------------------------------------------------------
# Default snapshot seed
# ---------------------------------------------------------------------------

_DEFAULT_SNAPSHOT: Dict[str, Any] = {
    "meta": {
        "version": "2.0",
        "created": None,
        "last_updated": None,
        "update_count": 0,
        "m6_enabled": True,
    },
    "speace_state": {
        "phase": 1,
        "fitness": None,
        "active_agents": [],
        "last_cycle": None,
        "proposals_pending": 0,
        "m5_score": 6,
        "m5_complete": True,
    },
    "planet_state": {
        "climate": {
            "status": "critical",
            "co2_ppm": 422.0,
            "global_temp_anomaly_c": 1.2,
            "last_updated": None,
        },
        "biodiversity": {
            "status": "declining",
            "species_at_risk_pct": 28.0,
            "last_updated": None,
        },
        "social": {
            "sdg_progress": "insufficient",
            "global_poverty_pct": 9.2,
            "last_updated": None,
        },
    },
    "technology_state": {
        "ai_capability_level": "narrow_general",
        "iot_connected_devices_bn": 16,
        "quantum_readiness": "experimental",
    },
    "rigene_objectives": [
        "Guide AI and tech ecosystem toward improvement of life and natural ecosystems",
        "Solve global problems: climate change, pollution, poverty, pandemic",
        "Develop Digital DNA framework for safe technological evolution",
        "Achieve UN SDGs Agenda 2030",
        "Create TINA - Technical Intelligent Nervous Adaptive System",
        "Build distributed cognitive collective brain",
        "Promote harmony, peace, ecological-social-technological balance",
    ],
    "knowledge_graph": {},
    "scenarios": [],
    "feed_cache": {
        "nasa": {"status": "offline", "last_fetch": None, "data": {}},
        "noaa": {"status": "offline", "last_fetch": None, "data": {}},
        "un_sdg": {"status": "offline", "last_fetch": None, "data": {}},
    },
}


# ---------------------------------------------------------------------------
# WorldSnapshot
# ---------------------------------------------------------------------------

class WorldSnapshot:
    """
    M6.1 — WorldSnapshot: store centralizzato dello stato del mondo.

    Thread-safe. Supporta merge parziale (patch) e query per path puntato.
    Persiste su SQLite se `db_path` è fornito.
    """

    def __init__(
        self,
        seed_path: Optional[Path] = _DEFAULT_SEED_PATH,
        db_path: Optional[Path] = None,   # None = in-memory only
        auto_load: bool = True,
    ) -> None:
        self._lock    = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._db_path = db_path
        self._db: Optional[sqlite3.Connection] = None

        # Init from default seed
        self._data = copy.deepcopy(_DEFAULT_SNAPSHOT)
        now_iso = self._now_iso()
        self._data["meta"]["created"]      = now_iso
        self._data["meta"]["last_updated"] = now_iso

        # Merge seed JSON if available
        if auto_load and seed_path and seed_path.exists():
            self._merge_seed(seed_path)

        # Optionally persist
        if db_path:
            self._init_db(db_path)
            if auto_load:
                self._load_from_db()

    # ------------------------------------------------------------------ init

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def _merge_seed(self, path: Path) -> None:
        """Merge il JSON seed nel snapshot (deep merge, non sovrascrive None)."""
        try:
            seed = json.loads(path.read_text(encoding="utf-8"))
            self._deep_merge(self._data, seed)
            logger.info("[WorldSnapshot] merged seed from %s", path)
        except Exception as e:
            logger.warning("[WorldSnapshot] seed load failed: %s", e)

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Merge ricorsivo: override sovrascrive base solo se valore non None."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            elif v is not None:
                base[k] = v

    # ------------------------------------------------------------------ SQLite

    def _init_db(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS world_snapshot (
                id      INTEGER PRIMARY KEY,
                ts      TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        self._db.commit()

    def _save_to_db(self) -> None:
        if not self._db:
            return
        try:
            payload = json.dumps(self._data, ensure_ascii=False)
            self._db.execute(
                "INSERT INTO world_snapshot (ts, payload) VALUES (?, ?)",
                (self._now_iso(), payload)
            )
            # Keep only last 100 snapshots
            self._db.execute(
                "DELETE FROM world_snapshot WHERE id NOT IN "
                "(SELECT id FROM world_snapshot ORDER BY id DESC LIMIT 100)"
            )
            self._db.commit()
        except Exception as e:
            logger.warning("[WorldSnapshot] db save failed: %s", e)

    def _load_from_db(self) -> None:
        if not self._db:
            return
        try:
            row = self._db.execute(
                "SELECT payload FROM world_snapshot ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                loaded = json.loads(row[0])
                self._deep_merge(self._data, loaded)
                logger.info("[WorldSnapshot] loaded from SQLite db")
        except Exception as e:
            logger.warning("[WorldSnapshot] db load failed: %s", e)

    # ------------------------------------------------------------------ read

    def get(self, path: str = "", default: Any = None) -> Any:
        """
        Legge un valore dal snapshot tramite path puntato.
        Esempi:
            get()                   → dict intero
            get("planet_state")     → dict planet_state
            get("planet_state.climate.co2_ppm") → float
        """
        with self._lock:
            if not path:
                return copy.deepcopy(self._data)
            node = self._data
            for part in path.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return copy.deepcopy(node)

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    # ------------------------------------------------------------------ write

    def patch(self, path: str, value: Any, persist: bool = True) -> None:
        """
        Aggiorna un singolo valore tramite path puntato.
        Crea i nodi intermedi se non esistono.
        """
        with self._lock:
            parts = path.split(".")
            node = self._data
            for part in parts[:-1]:
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]
            node[parts[-1]] = value
            self._data["meta"]["last_updated"] = self._now_iso()
            self._data["meta"]["update_count"] = self._data["meta"].get("update_count", 0) + 1
            if persist and self._db:
                self._save_to_db()

    def merge(self, section: str, data: Dict[str, Any], persist: bool = True) -> None:
        """Merge dict `data` nella sezione `section` del snapshot."""
        with self._lock:
            if section not in self._data:
                self._data[section] = {}
            self._deep_merge(self._data[section], data)
            self._data["meta"]["last_updated"] = self._now_iso()
            self._data["meta"]["update_count"] = self._data["meta"].get("update_count", 0) + 1
            if persist and self._db:
                self._save_to_db()

    def update_feed_cache(self, feed_name: str, data: Dict[str, Any], status: str = "ok") -> None:
        """Aggiorna la cache di un feed esterno."""
        with self._lock:
            if "feed_cache" not in self._data:
                self._data["feed_cache"] = {}
            self._data["feed_cache"][feed_name] = {
                "status": status,
                "last_fetch": self._now_iso(),
                "data": data,
            }
            self._data["meta"]["last_updated"] = self._now_iso()

    # ------------------------------------------------------------------ export

    def to_dict(self) -> Dict[str, Any]:
        """Restituisce una copia profonda dell'intero snapshot."""
        with self._lock:
            return copy.deepcopy(self._data)

    def to_json(self, indent: int = 2) -> str:
        with self._lock:
            return json.dumps(self._data, ensure_ascii=False, indent=indent, default=str)

    def save_json(self, path: Path) -> None:
        """Salva snapshot su file JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            path.write_text(self.to_json(), encoding="utf-8")
        logger.info("[WorldSnapshot] saved to %s", path)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            meta = self._data.get("meta", {})
            kg   = self._data.get("knowledge_graph", {})
            sc   = self._data.get("scenarios", [])
            return {
                "version":      meta.get("version"),
                "update_count": meta.get("update_count", 0),
                "last_updated": meta.get("last_updated"),
                "kg_entities":  len(kg),
                "scenarios":    len(sc),
                "feeds": {
                    k: v.get("status")
                    for k, v in self._data.get("feed_cache", {}).items()
                },
                "db_enabled": self._db is not None,
            }


__all__ = ["WorldSnapshot"]
