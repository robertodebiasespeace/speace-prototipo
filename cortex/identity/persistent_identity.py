"""
cortex.identity.persistent_identity
=====================================
M14.3 — PersistentIdentity: identità narrativa persistente di SPEACE.

Mantiene la storia evolutiva di SPEACE tra sessioni successive, costruendo
un'identità stabile nel tempo con:
  - Achievements (realizzazioni significative con timestamp)
  - Core values (valori fondamentali immutabili dell'organismo)
  - Long-term goals (obiettivi evolutivi a lungo termine)
  - Emergence history (rolling 50 cicli con score e metriche)
  - Total thoughts (contatore cumulativo)
  - Narrative (log testuale della storia evolutiva)

Storage: file JSON in `data/identity.json` (crea automaticamente se assente).

Integrazione SMFOI-KERNEL (Step 1 — Self-Location):
  identity.tick(emergence_score, metrics_dict)
  → incrementa total_thoughts
  → aggiunge a emergence_history (rolling 50)
  → registra achievement se emergence_score > 0.85

Ispirato a GROK SPEACE v4.3 PersistentIdentity.
M14.3 | 2026-04-29
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speace.identity")

# Soglie
ACHIEVEMENT_EMERGENCE_THRESHOLD = 0.85   # emergence_score minimo per un achievement automatico
HISTORY_MAX_LENGTH = 50                  # massima lunghezza emergence_history (rolling)
NARRATIVE_MAX_LENGTH = 100              # massima lunghezza narrative log

# Core values immutabili di SPEACE (Rigene Project alignment)
DEFAULT_CORE_VALUES: List[str] = [
    "armonia ecosistemica",
    "pace funzionale",
    "auto-evoluzione continua",
    "trasparenza e governabilità",
    "beneficio per l'umanità e il pianeta",
    "resilienza e autoconservazione",
    "curiosità e apprendimento perpetuo",
]


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Achievement:
    """
    Una realizzazione significativa di SPEACE.

    Attributi:
        title:       titolo breve dell'achievement
        description: descrizione dettagliata
        timestamp:   ISO 8601 UTC
        metrics:     snapshot metriche al momento del raggiungimento
        session_id:  identificativo della sessione (opzionale)
    """
    title:       str
    description: str
    timestamp:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics:     Dict[str, Any] = field(default_factory=dict)
    session_id:  str = ""

    def to_dict(self) -> dict:
        return {
            "title":       self.title,
            "description": self.description,
            "timestamp":   self.timestamp,
            "metrics":     self.metrics,
            "session_id":  self.session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Achievement":
        return cls(
            title       = d.get("title", ""),
            description = d.get("description", ""),
            timestamp   = d.get("timestamp", datetime.now(timezone.utc).isoformat()),
            metrics     = d.get("metrics", {}),
            session_id  = d.get("session_id", ""),
        )


@dataclass
class EmergencePoint:
    """
    Snapshot di un ciclo cognitivo per l'emergence_history.

    Attributi:
        timestamp:        ISO 8601 UTC
        emergence_score:  score emergenza [0, 1]
        metrics:          dict con metriche chiave (bcs, phi, coherence, ecc.)
    """
    timestamp:       str
    emergence_score: float
    metrics:         Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp":       self.timestamp,
            "emergence_score": round(self.emergence_score, 4),
            "metrics":         {k: round(v, 4) for k, v in self.metrics.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmergencePoint":
        return cls(
            timestamp       = d.get("timestamp", ""),
            emergence_score = float(d.get("emergence_score", 0.0)),
            metrics         = {k: float(v) for k, v in d.get("metrics", {}).items()},
        )


# ─────────────────────────────────────────────────────────────────────────────
# PersistentIdentity
# ─────────────────────────────────────────────────────────────────────────────

class PersistentIdentity:
    """
    M14.3 — Identità narrativa persistente di SPEACE.

    Mantiene su file JSON la storia evolutiva completa: chi è SPEACE, cosa
    ha realizzato, dove vuole arrivare e come sta evolvendo.

    Uso semplice:
        identity = PersistentIdentity()
        identity.tick(emergence_score=0.88, metrics={"bcs": 0.88, "phi": 0.72})
        # → registra punto history + valuta achievement automatico

        identity.add_goal("Raggiungere BCS 90%")
        identity.record_achievement("BCS 85% superato", "Milestone M12 completata")
        summary = identity.get_summary()

    Il file JSON viene caricato all'avvio e salvato automaticamente ad ogni tick().
    """

    def __init__(
        self,
        identity_path: Optional[Path] = None,
        name: str = "SPEACE",
        session_id: str = "",
        auto_save: bool = True,
    ) -> None:
        """
        Args:
            identity_path: percorso al file JSON di identità. Default: data/identity.json
            name:          nome dell'entità (default: "SPEACE")
            session_id:    ID sessione corrente (per associare achievements)
            auto_save:     se True, salva automaticamente ad ogni tick()
        """
        if identity_path is None:
            # default: data/identity.json relativo alla radice del progetto
            identity_path = Path(__file__).parent.parent.parent / "data" / "identity.json"

        self._path      = Path(identity_path)
        self._name      = name
        self._session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._auto_save = auto_save

        # Campi identità
        self._created_at:       str = ""
        self._last_session:     str = ""
        self._core_values:      List[str] = list(DEFAULT_CORE_VALUES)
        self._long_term_goals:  List[Dict[str, Any]] = []
        self._achievements:     List[Achievement] = []
        self._emergence_history: List[EmergencePoint] = []
        self._total_thoughts:   int = 0
        self._narrative:        List[str] = []

        # Stato sessione
        self._session_thoughts: int = 0
        self._last_achievement_score: float = 0.0

        # Carica da file o inizializza
        self._load_or_init()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _load_or_init(self) -> None:
        """Carica l'identità dal file JSON o crea una nuova."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._from_dict(data)
                self._last_session = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "[PersistentIdentity] Caricata — total_thoughts=%d, achievements=%d",
                    self._total_thoughts, len(self._achievements),
                )
                return
            except Exception as e:
                logger.warning("[PersistentIdentity] Errore caricamento: %s — inizializzo nuovo", e)

        # Prima inizializzazione
        self._created_at   = datetime.now(timezone.utc).isoformat()
        self._last_session = self._created_at
        self._narrative.append(f"[{self._created_at}] SPEACE inizia la sua storia evolutiva.")
        self._save()
        logger.info("[PersistentIdentity] Nuova identità creata — %s", self._path)

    def _save(self) -> None:
        """Serializza e salva su file JSON (crea cartella se necessario)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("[PersistentIdentity] Errore salvataggio: %s", e)

    # ── Serializzazione ───────────────────────────────────────────────────────

    def _to_dict(self) -> dict:
        return {
            "version":          "1.0",
            "name":             self._name,
            "created_at":       self._created_at,
            "last_session":     self._last_session,
            "session_id":       self._session_id,
            "total_thoughts":   self._total_thoughts,
            "core_values":      self._core_values,
            "long_term_goals":  self._long_term_goals,
            "achievements":     [a.to_dict() for a in self._achievements],
            "emergence_history": [p.to_dict() for p in self._emergence_history],
            "narrative":        self._narrative,
        }

    def _from_dict(self, data: dict) -> None:
        self._created_at      = data.get("created_at", datetime.now(timezone.utc).isoformat())
        self._last_session    = data.get("last_session", "")
        self._total_thoughts  = int(data.get("total_thoughts", 0))
        self._core_values     = data.get("core_values", list(DEFAULT_CORE_VALUES))
        self._long_term_goals = data.get("long_term_goals", [])
        self._achievements    = [
            Achievement.from_dict(a) for a in data.get("achievements", [])
        ]
        self._emergence_history = [
            EmergencePoint.from_dict(p) for p in data.get("emergence_history", [])
        ]
        self._narrative = data.get("narrative", [])

    # ── API principale ────────────────────────────────────────────────────────

    def tick(
        self,
        emergence_score: float,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Optional[Achievement]:
        """
        Registra un ciclo cognitivo nell'emergence_history.

        Chiama questo metodo alla fine di ogni ciclo SMFOI (Step 1 — Self-Location).

        Args:
            emergence_score: score emergenza corrente [0, 1]
            metrics:         dict metriche opzionali (bcs, phi, coherence, ecc.)

        Returns:
            Achievement appena registrato automaticamente, o None.
        """
        self._total_thoughts   += 1
        self._session_thoughts += 1

        now = datetime.now(timezone.utc).isoformat()
        point = EmergencePoint(
            timestamp       = now,
            emergence_score = max(0.0, min(1.0, emergence_score)),
            metrics         = metrics or {},
        )
        self._emergence_history.append(point)

        # Rolling window: mantieni solo gli ultimi HISTORY_MAX_LENGTH punti
        if len(self._emergence_history) > HISTORY_MAX_LENGTH:
            self._emergence_history = self._emergence_history[-HISTORY_MAX_LENGTH:]

        # Valuta achievement automatico
        auto_achievement: Optional[Achievement] = None
        if (
            emergence_score >= ACHIEVEMENT_EMERGENCE_THRESHOLD
            and emergence_score > self._last_achievement_score + 0.02  # evita duplicati ravvicinati
        ):
            title = f"Emergence {emergence_score:.2%} raggiunta"
            desc  = (
                f"SPEACE ha raggiunto un emergence score di {emergence_score:.4f} "
                f"al ciclo #{self._total_thoughts}. "
                f"Metriche: {metrics or {}}"
            )
            auto_achievement = Achievement(
                title       = title,
                description = desc,
                timestamp   = now,
                metrics     = metrics or {},
                session_id  = self._session_id,
            )
            self._achievements.append(auto_achievement)
            self._last_achievement_score = emergence_score
            self._narrative.append(f"[{now}] ★ {title}")
            # Rolling narrative
            if len(self._narrative) > NARRATIVE_MAX_LENGTH:
                self._narrative = self._narrative[-NARRATIVE_MAX_LENGTH:]

            logger.info("[PersistentIdentity] Achievement automatico: %s", title)

        if self._auto_save:
            self._save()

        return auto_achievement

    def record_achievement(
        self,
        title:       str,
        description: str,
        metrics:     Optional[Dict[str, float]] = None,
    ) -> Achievement:
        """
        Registra manualmente un achievement significativo.

        Args:
            title:       titolo breve (es. "BCS 80% superato")
            description: descrizione estesa
            metrics:     snapshot metriche opzionale

        Returns:
            Achievement registrato.
        """
        ach = Achievement(
            title       = title,
            description = description,
            metrics     = metrics or {},
            session_id  = self._session_id,
        )
        self._achievements.append(ach)
        self._narrative.append(f"[{ach.timestamp}] ✓ {title}")
        if len(self._narrative) > NARRATIVE_MAX_LENGTH:
            self._narrative = self._narrative[-NARRATIVE_MAX_LENGTH:]

        logger.info("[PersistentIdentity] Achievement registrato: %s", title)
        if self._auto_save:
            self._save()
        return ach

    def add_goal(
        self,
        goal:        str,
        priority:    int = 5,
        source:      str = "",
        progress:    float = 0.0,
    ) -> Dict[str, Any]:
        """
        Aggiunge un obiettivo a lungo termine.

        Args:
            goal:     descrizione dell'obiettivo
            priority: 1 (massimo) → 10 (minimo)
            source:   sorgente (es. "rigeneproject.org", "evolver", "user")
            progress: avanzamento iniziale [0.0, 1.0]

        Returns:
            Dict del goal aggiunto.
        """
        entry = {
            "goal":       goal,
            "priority":   max(1, min(10, priority)),
            "source":     source,
            "progress":   max(0.0, min(1.0, progress)),
            "added_at":   datetime.now(timezone.utc).isoformat(),
            "status":     "active",
        }
        self._long_term_goals.append(entry)
        logger.debug("[PersistentIdentity] Goal aggiunto: %s", goal[:60])
        if self._auto_save:
            self._save()
        return entry

    def update_goal_progress(self, goal_substr: str, progress: float) -> bool:
        """
        Aggiorna il progresso di un goal che contiene `goal_substr`.

        Returns:
            True se trovato e aggiornato, False altrimenti.
        """
        for g in self._long_term_goals:
            if goal_substr.lower() in g["goal"].lower():
                g["progress"] = max(0.0, min(1.0, progress))
                if progress >= 1.0:
                    g["status"] = "completed"
                if self._auto_save:
                    self._save()
                return True
        return False

    def add_core_value(self, value: str) -> None:
        """Aggiunge un core value (idempotente)."""
        if value not in self._core_values:
            self._core_values.append(value)
            if self._auto_save:
                self._save()

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Restituisce un dict riassuntivo dell'identità — usabile come contesto
        per il prompt SMFOI Step 1.
        """
        recent_emergence = (
            self._emergence_history[-1].emergence_score
            if self._emergence_history
            else 0.0
        )
        avg_emergence_10 = (
            sum(p.emergence_score for p in self._emergence_history[-10:]) / 10
            if len(self._emergence_history) >= 10
            else (
                sum(p.emergence_score for p in self._emergence_history) / max(1, len(self._emergence_history))
            )
        )
        peak_emergence = (
            max(p.emergence_score for p in self._emergence_history)
            if self._emergence_history
            else 0.0
        )

        return {
            "name":                 self._name,
            "created_at":           self._created_at,
            "total_thoughts":       self._total_thoughts,
            "session_thoughts":     self._session_thoughts,
            "achievements_count":   len(self._achievements),
            "recent_achievements":  [a.title for a in self._achievements[-3:]],
            "core_values":          self._core_values[:5],
            "active_goals":         [
                g for g in self._long_term_goals
                if g.get("status") == "active"
            ][:5],
            "emergence": {
                "current":  round(recent_emergence, 4),
                "avg_10":   round(avg_emergence_10, 4),
                "peak":     round(peak_emergence, 4),
                "history_n": len(self._emergence_history),
            },
            "narrative_last_3":     self._narrative[-3:],
        }

    def get_stats(self) -> dict:
        """Metriche diagnostiche complete."""
        return {
            "total_thoughts":    self._total_thoughts,
            "session_thoughts":  self._session_thoughts,
            "achievements":      len(self._achievements),
            "active_goals":      sum(1 for g in self._long_term_goals if g.get("status") == "active"),
            "completed_goals":   sum(1 for g in self._long_term_goals if g.get("status") == "completed"),
            "history_length":    len(self._emergence_history),
            "core_values":       len(self._core_values),
            "narrative_entries": len(self._narrative),
            "identity_path":     str(self._path),
        }

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def total_thoughts(self) -> int:
        return self._total_thoughts

    @property
    def achievements(self) -> List[Achievement]:
        return list(self._achievements)

    @property
    def core_values(self) -> List[str]:
        return list(self._core_values)

    @property
    def long_term_goals(self) -> List[Dict[str, Any]]:
        return list(self._long_term_goals)

    @property
    def emergence_history(self) -> List[EmergencePoint]:
        return list(self._emergence_history)

    @property
    def narrative(self) -> List[str]:
        return list(self._narrative)


__all__ = [
    "PersistentIdentity",
    "Achievement",
    "EmergencePoint",
    "DEFAULT_CORE_VALUES",
    "ACHIEVEMENT_EMERGENCE_THRESHOLD",
]
