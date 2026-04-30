"""
WorldModelCortex — M6.6 (9° Comparto SPEACE Cortex)

Facade unificata del World Model come comparto Cortex.
Coordina: WorldSnapshot + KnowledgeGraph + Feeds + Inference + MemoryBridge.

Interfaccia verso gli altri comparti Cortex:
  - query(path)         → legge dal WorldSnapshot
  - update(path, value) → scrive nel WorldSnapshot
  - ask(question)       → query semantica semplice (NL-like)
  - run_inference()     → esegue scenari standard
  - refresh_feeds()     → aggiorna dati esterni

Milestone: M6.6
Versione: 1.0 | 2026-04-27
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .snapshot       import WorldSnapshot
from .knowledge_graph import KnowledgeGraph, EntityType
from .inference      import InferenceEngine, BUILTIN_RULES
from .memory_bridge  import MemoryBridge
from .feeds          import NASADonkiFeed, NOAAClimateFeed, UNSDGFeed

logger = logging.getLogger("speace.world_model.cortex")

_DEFAULT_SEED = Path(__file__).resolve().parents[4] / "memory" / "world_model.json"
_DEFAULT_DB   = Path(__file__).resolve().parents[4] / "safeproactive" / "state" / "world_model.db"


class WorldModelCortex:
    """
    M6.6 — World Model come 9° comparto del SPEACE Cortex.

    Usage:
        wm = WorldModelCortex()
        wm.initialize()

        # Query
        co2 = wm.query("planet_state.climate.co2_ppm")

        # Update
        wm.update("speace_state.fitness", 0.75)

        # Inference
        scenarios = wm.run_inference()

        # Feed refresh
        wm.refresh_feeds()
    """

    def __init__(
        self,
        seed_path: Optional[Path] = _DEFAULT_SEED,
        db_path: Optional[Path] = None,       # None = in-memory only
        autobio_memory=None,
    ) -> None:
        # Core components
        self.snapshot  = WorldSnapshot(seed_path=seed_path, db_path=db_path)
        self.kg        = KnowledgeGraph()
        self.inference = InferenceEngine(rules=list(BUILTIN_RULES))
        self.bridge    = MemoryBridge(self.snapshot, autobio_memory)

        # Feed connectors
        self.feeds = {
            "nasa":   NASADonkiFeed(),
            "noaa":   NOAAClimateFeed(),
            "un_sdg": UNSDGFeed(),
        }

        self._initialized = False

    def initialize(self, seed_kg: bool = True) -> None:
        """Inizializza il WorldModelCortex."""
        if self._initialized:
            return

        # Seed KG from Rigene
        if seed_kg:
            self.kg.seed_from_rigene()

        # Load KG from existing snapshot
        existing_kg = self.snapshot.get("knowledge_graph")
        if existing_kg:
            self.kg.load_dict(existing_kg)

        # Sync KG back to snapshot
        self.snapshot.merge("knowledge_graph", self.kg.to_dict(), persist=False)

        self._initialized = True
        logger.info("[WorldModelCortex] initialized — KG entities: %d", self.kg.count())

    # ---------------------------------------------------------------- query / update

    def query(self, path: str = "", default: Any = None) -> Any:
        """Legge dal WorldSnapshot tramite path puntato."""
        return self.snapshot.get(path, default)

    def update(self, path: str, value: Any) -> None:
        """Aggiorna il WorldSnapshot."""
        self.snapshot.patch(path, value)

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Query semantica semplice (keyword matching).
        Ritorna un dict con le sezioni rilevanti del WorldSnapshot.
        """
        question_lower = question.lower()
        result: Dict[str, Any] = {"question": question, "answers": {}}

        keyword_map = {
            "co2":         "planet_state.climate.co2_ppm",
            "clima":       "planet_state.climate",
            "climate":     "planet_state.climate",
            "temperatura": "planet_state.climate.global_temp_anomaly_c",
            "sdg":         "planet_state.social.sdg_progress",
            "biodiversit": "planet_state.biodiversity",
            "speace":      "speace_state",
            "fase":        "speace_state.phase",
            "fitness":     "speace_state.fitness",
            "iot":         "technology_state.iot_connected_devices_bn",
            "ai":          "technology_state.ai_capability_level",
            "quantum":     "technology_state.quantum_readiness",
        }

        for kw, path in keyword_map.items():
            if kw in question_lower:
                result["answers"][path] = self.snapshot.get(path)

        if not result["answers"]:
            # Fallback: ritorna un summary generale
            result["answers"]["summary"] = self._build_summary()

        return result

    # ---------------------------------------------------------------- inference

    def run_inference(self, custom_scenario: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Esegue gli scenari standard (o uno custom) e aggiorna WorldSnapshot.scenarios.

        Args:
            custom_scenario: dict con {"name": ..., "interventions": {...}} opzionale

        Returns:
            Lista di dict scenario.
        """
        snap = self.snapshot.to_dict()
        scenarios = []

        if custom_scenario:
            sc = self.inference.simulate(
                snap,
                name=custom_scenario.get("name", "Custom"),
                interventions=custom_scenario.get("interventions", {}),
                description=custom_scenario.get("description", ""),
            )
            scenarios.append(sc)
        else:
            scenarios = self.inference.run_standard_scenarios(snap)

        # Persist scenarios to snapshot
        existing = self.snapshot.get("scenarios") or []
        existing.extend([s.to_dict() for s in scenarios])
        self.snapshot.patch("scenarios", existing[-10:])   # keep last 10

        logger.info("[WorldModelCortex] ran %d scenarios", len(scenarios))
        return [s.to_dict() for s in scenarios]

    # ---------------------------------------------------------------- feeds

    def refresh_feeds(self, force: bool = False) -> Dict[str, str]:
        """Aggiorna tutti i feed esterni e scrive nel WorldSnapshot."""
        statuses: Dict[str, str] = {}
        for name, feed in self.feeds.items():
            result = feed.fetch(force=force)
            self.snapshot.update_feed_cache(name, result.data, result.status)

            # Merge dati rilevanti nel planet_state / technology_state
            if name == "noaa" and result.ok:
                co2 = result.data.get("co2_ppm")
                if co2:
                    self.snapshot.patch("planet_state.climate.co2_ppm", co2, persist=False)
            elif name == "un_sdg" and result.ok:
                self.snapshot.patch(
                    "planet_state.social.sdg_goals_available",
                    result.data.get("goals_count", 17),
                    persist=False,
                )

            statuses[name] = result.status
            logger.info("[WorldModelCortex] feed %s → %s (source: %s)", name, result.status, result.source)

        return statuses

    # ---------------------------------------------------------------- memory bridge

    def sync_to_memory(self, context: str = "world_model_sync") -> Optional[str]:
        """Proietta snapshot corrente in AutobiographicalMemory."""
        return self.bridge.snapshot_to_memory(context=context)

    def sync_from_memory(self) -> Dict[str, Any]:
        """Integra pattern da AutobiographicalMemory nel WorldSnapshot."""
        return self.bridge.memory_to_snapshot()

    # ---------------------------------------------------------------- summary

    def _build_summary(self) -> Dict[str, Any]:
        """Costruisce un summary leggibile dello snapshot."""
        return {
            "speace_phase":    self.query("speace_state.phase"),
            "speace_fitness":  self.query("speace_state.fitness"),
            "m5_complete":     self.query("speace_state.m5_complete"),
            "co2_ppm":         self.query("planet_state.climate.co2_ppm"),
            "climate_status":  self.query("planet_state.climate.status"),
            "biodiversity":    self.query("planet_state.biodiversity.status"),
            "sdg_progress":    self.query("planet_state.social.sdg_progress"),
            "ai_level":        self.query("technology_state.ai_capability_level"),
            "kg_entities":     self.kg.count(),
        }

    def persist_state(self, path: Optional[Path] = None) -> None:
        """Salva snapshot + KG su file JSON."""
        if path is None:
            path = _DEFAULT_SEED
        # Sync KG to snapshot before saving
        self.snapshot.merge("knowledge_graph", self.kg.to_dict(), persist=False)
        self.snapshot.save_json(path)
        logger.info("[WorldModelCortex] state persisted to %s", path)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "initialized":    self._initialized,
            "snapshot":       self.snapshot.get_stats(),
            "knowledge_graph": self.kg.get_stats(),
            "inference":      self.inference.get_stats(),
            "bridge":         self.bridge.get_stats(),
            "feeds":          {n: f.__class__.__name__ for n, f in self.feeds.items()},
        }


__all__ = ["WorldModelCortex"]
