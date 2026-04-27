"""
MemoryBridge — M6.5 (World Model / Memory Bridge)

Ponte semantico bidirezionale tra AutobiographicalMemory (Hippocampus, M5.8)
e WorldSnapshot (World Model, M6.1).

Funzioni:
  - snapshot_to_memory(): proietta lo stato corrente del WorldSnapshot
    come episodio nell'AutobiographicalMemory
  - memory_to_snapshot(): estrae pattern statistici dalla memoria
    episodica e aggiorna il WorldSnapshot (sezione speace_state)
  - query_related_episodes(): trova episodi in memoria relativi
    a un'entità o evento del KG

Il bridge mantiene SPEACE "consapevole" della propria storia
attraverso l'integrazione tra memoria procedurale (World Model)
e memoria episodica (Autobiographical Memory).

Milestone: M6.5
Versione: 1.0 | 2026-04-27
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speace.world_model.memory_bridge")


# ---------------------------------------------------------------------------
# MemoryBridge
# ---------------------------------------------------------------------------

class MemoryBridge:
    """
    M6.5 — Ponte semantico WorldSnapshot ↔ AutobiographicalMemory.

    Usa duck-typing per entrambi i componenti: non richiede import diretto
    di AutobiographicalMemory (evita import circolare), basta che l'oggetto
    esponga `.store_episode()` e `.retrieve_episodes()`.
    """

    def __init__(
        self,
        snapshot,                        # WorldSnapshot
        autobio_memory = None,           # AutobiographicalMemory (opzionale)
    ) -> None:
        self._snapshot = snapshot
        self._memory   = autobio_memory
        self._bridge_events: List[Dict[str, Any]] = []

    def set_memory(self, autobio_memory) -> None:
        """Collega la memoria autobiografica (post-init)."""
        self._memory = autobio_memory
        logger.info("[MemoryBridge] memory connected: %s", type(autobio_memory).__name__)

    # ---------------------------------------------------------------- snapshot → memory

    def snapshot_to_memory(
        self,
        context: str = "world_model_sync",
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Proietta lo stato corrente del WorldSnapshot come episodio in memoria.

        Returns:
            episode_id se la memoria è connessa, None altrimenti.
        """
        if not self._memory:
            logger.debug("[MemoryBridge] memory not connected — skipping snapshot_to_memory")
            return None

        snap = self._snapshot.get()
        planet  = snap.get("planet_state", {})
        climate = planet.get("climate", {})
        speace  = snap.get("speace_state", {})

        content = (
            f"[WorldModel snapshot] "
            f"CO2={climate.get('co2_ppm', '?')} ppm | "
            f"Climate={climate.get('status', '?')} | "
            f"SPEACE phase={speace.get('phase', '?')} | "
            f"fitness={speace.get('fitness', '?')} | "
            f"M5={speace.get('m5_complete', False)}"
        )

        episode_tags = list(tags or []) + ["world_model", "planet_state", "speace_state"]

        try:
            episode_id = None
            if hasattr(self._memory, "store_episode"):
                episode_id = self._memory.store_episode(
                    content=content,
                    context=context,
                    tags=episode_tags,
                    metadata={
                        "source": "world_model_bridge",
                        "co2_ppm": climate.get("co2_ppm"),
                        "speace_phase": speace.get("phase"),
                        "m5_complete": speace.get("m5_complete"),
                    }
                )
            self._bridge_events.append({
                "direction": "snapshot→memory",
                "episode_id": episode_id,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            logger.info("[MemoryBridge] episode stored: %s", episode_id)
            return episode_id
        except Exception as e:
            logger.warning("[MemoryBridge] snapshot_to_memory failed: %s", e)
            return None

    # ---------------------------------------------------------------- memory → snapshot

    def memory_to_snapshot(
        self,
        query: str = "world_model climate speace",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Legge gli ultimi episodi dalla memoria e aggiorna il WorldSnapshot
        con pattern statistici (co2_ppm medio, conteggio cicli, ecc.).

        Returns:
            Dict con le statistiche estratte.
        """
        if not self._memory:
            return {"status": "memory_not_connected"}

        try:
            episodes = []
            if hasattr(self._memory, "retrieve_episodes"):
                episodes = self._memory.retrieve_episodes(query=query, limit=limit)
            elif hasattr(self._memory, "search"):
                episodes = self._memory.search(query, limit=limit)

            stats = self._extract_stats(episodes)

            # Aggiorna WorldSnapshot con le statistiche estratte
            if stats.get("cycle_count"):
                self._snapshot.patch(
                    "speace_state.memory_cycle_count", stats["cycle_count"], persist=False
                )
            if stats.get("last_co2_ppm"):
                self._snapshot.patch(
                    "planet_state.climate.co2_ppm_memory", stats["last_co2_ppm"], persist=False
                )

            self._bridge_events.append({
                "direction": "memory→snapshot",
                "episodes_read": len(episodes),
                "stats": stats,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            logger.info("[MemoryBridge] memory→snapshot: %d episodes → stats=%s",
                        len(episodes), stats)
            return stats

        except Exception as e:
            logger.warning("[MemoryBridge] memory_to_snapshot failed: %s", e)
            return {"status": "error", "error": str(e)}

    def _extract_stats(self, episodes: List[Any]) -> Dict[str, Any]:
        """Estrae statistiche aggregate da una lista di episodi."""
        if not episodes:
            return {"episode_count": 0}

        co2_values: List[float] = []
        phases: List[int] = []

        for ep in episodes:
            # Support dict episodes or object episodes
            meta = ep.get("metadata", {}) if isinstance(ep, dict) else getattr(ep, "metadata", {})
            content = ep.get("content", "") if isinstance(ep, dict) else getattr(ep, "content", "")

            if isinstance(meta, dict):
                if meta.get("co2_ppm"):
                    try:
                        co2_values.append(float(meta["co2_ppm"]))
                    except (ValueError, TypeError):
                        pass
                if meta.get("speace_phase"):
                    try:
                        phases.append(int(meta["speace_phase"]))
                    except (ValueError, TypeError):
                        pass

        stats: Dict[str, Any] = {"episode_count": len(episodes)}
        if co2_values:
            stats["avg_co2_ppm"]  = round(sum(co2_values) / len(co2_values), 2)
            stats["last_co2_ppm"] = co2_values[-1]
        if phases:
            stats["max_phase"] = max(phases)
            stats["cycle_count"] = len(phases)

        return stats

    # ---------------------------------------------------------------- KG query

    def query_related_episodes(
        self,
        entity_id: str,
        limit: int = 10,
    ) -> List[Any]:
        """
        Trova episodi in memoria relativi a un'entità del Knowledge Graph.
        Usa l'entity_id come query di ricerca testuale.
        """
        if not self._memory:
            return []
        try:
            if hasattr(self._memory, "retrieve_episodes"):
                return self._memory.retrieve_episodes(query=entity_id, limit=limit)
            elif hasattr(self._memory, "search"):
                return self._memory.search(entity_id, limit=limit)
        except Exception as e:
            logger.warning("[MemoryBridge] query_related_episodes failed: %s", e)
        return []

    # ---------------------------------------------------------------- stats

    def get_stats(self) -> Dict[str, Any]:
        return {
            "bridge_events":       len(self._bridge_events),
            "memory_connected":    self._memory is not None,
            "snapshot_connected":  self._snapshot is not None,
            "last_event":          self._bridge_events[-1] if self._bridge_events else None,
        }


__all__ = ["MemoryBridge"]
