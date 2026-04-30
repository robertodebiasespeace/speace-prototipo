"""
cortex.cognitive_autonomy.executive.self_repair
================================================
M7.0 — SelfRepairTrigger: attivazione e gestione della modalità di riparazione.

Quando viability < 0.4, SPEACE entra in auto-riparazione:
  1. Sospende i task non critici
  2. Registra l'evento in memoria (AutobiographicalMemory)
  3. Genera azioni di recupero (RepairAction)
  4. Monitora il rientro alla normalità

Il SelfRepairTrigger è separato dal DriveExecutive per il principio di
singola responsabilità: DriveExecutive calcola BehavioralState,
SelfRepairTrigger gestisce il ciclo di riparazione.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .drive_executive import BehavioralState, DriveSnapshot

logger = logging.getLogger(__name__)


@dataclass
class RepairAction:
    """
    Azione di recupero generata da SelfRepairTrigger.

    Le azioni sono suggerimenti — non vengono eseguite automaticamente
    (SafeProactive rimane il gate per azioni reali).
    """
    action_id: str
    description: str
    urgency: float = 0.5          # [0, 1] — quanto urgentemente eseguire
    resource_cost: float = 0.1    # [0, 1] — costo stimato in risorse
    expected_recovery: float = 0.1  # [0, 1] — recupero viability stimato
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "action_id":         self.action_id,
            "description":       self.description,
            "urgency":           self.urgency,
            "resource_cost":     self.resource_cost,
            "expected_recovery": self.expected_recovery,
            "tags":              self.tags,
            "timestamp":         self.timestamp,
        }


class SelfRepairTrigger:
    """
    Gestisce l'attivazione e il ciclo di auto-riparazione di SPEACE.

    Logica:
      - check(bstate) → se self_repair_mode è True, attiva il ciclo
      - generate_repair_actions(snap) → lista di RepairAction suggerite
      - is_recovering() → True se stiamo uscendo da repair mode
      - check_recovery(snap) → True se viability è tornata sopra soglia

    Il trigger mantiene un history degli eventi di repair per permettere
    all'AutobiographicalMemory di registrarli.
    """

    REPAIR_THRESHOLD   = 0.4   # sotto → entra in repair
    RECOVERY_THRESHOLD = 0.55  # sopra → esce da repair (isteresi)

    def __init__(
        self,
        repair_threshold:   float = REPAIR_THRESHOLD,
        recovery_threshold: float = RECOVERY_THRESHOLD,
    ) -> None:
        self.repair_threshold   = repair_threshold
        self.recovery_threshold = recovery_threshold
        self._in_repair: bool = False
        self._repair_start: Optional[float] = None
        self._repair_events: List[dict] = []

    # ── API pubblica ──────────────────────────────────────────────────────────

    def check(self, bstate: BehavioralState) -> bool:
        """
        Aggiorna lo stato interno in base al BehavioralState.

        Returns:
            True se il sistema è (ancora) in repair mode dopo questo check.
        """
        if bstate.self_repair_mode and not self._in_repair:
            self._enter_repair(bstate)
        elif not bstate.self_repair_mode and self._in_repair:
            snap = bstate.source_snapshot
            if snap and snap.viability >= self.recovery_threshold:
                self._exit_repair(snap.viability)
        return self._in_repair

    def generate_repair_actions(self, snap: DriveSnapshot) -> List[RepairAction]:
        """
        Genera azioni di recupero in base allo snapshot dei drive.

        Le azioni sono ordinate per urgency decrescente.
        """
        actions: List[RepairAction] = []

        # Azione 1: riduzione carico cognitivo (sempre consigliata in repair)
        actions.append(RepairAction(
            action_id="REPAIR-001-reduce-load",
            description=(
                "Sospendi tutti i task non critici. "
                "Ridurre max_parallel_tasks a 1 per conservare energia."
            ),
            urgency=0.9,
            resource_cost=0.05,
            expected_recovery=0.1,
            tags=["load_reduction", "conservative"],
        ))

        # Azione 2: consolidamento memoria se coherence è bassa
        if snap.coherence < 0.5:
            actions.append(RepairAction(
                action_id="REPAIR-002-memory-consolidation",
                description=(
                    f"Consolida la memoria episodica (coherence={snap.coherence:.2f}). "
                    "Esegui autobiographical_memory.consolidate() per ripristinare coerenza."
                ),
                urgency=0.7,
                resource_cost=0.2,
                expected_recovery=0.15,
                tags=["memory", "coherence"],
            ))

        # Azione 3: sospendi mutazioni se alignment è critico
        if snap.alignment < self.repair_threshold:
            actions.append(RepairAction(
                action_id="REPAIR-003-freeze-mutations",
                description=(
                    f"Congela tutte le mutazioni DigitalDNA (alignment={snap.alignment:.2f}). "
                    "mutation_gate_open=False finché alignment > 0.5."
                ),
                urgency=0.85,
                resource_cost=0.01,
                expected_recovery=0.05,
                tags=["mutation_freeze", "alignment"],
            ))

        # Azione 4: recupero energia
        if snap.energy < 0.3:
            actions.append(RepairAction(
                action_id="REPAIR-004-energy-recovery",
                description=(
                    f"Avvia ciclo di recupero energetico (energy={snap.energy:.2f}). "
                    "Riduci frequenza heartbeat, sospendi evolver background."
                ),
                urgency=0.8,
                resource_cost=0.1,
                expected_recovery=0.2,
                tags=["energy", "heartbeat_reduction"],
            ))

        # Ordina per urgency decrescente
        actions.sort(key=lambda a: a.urgency, reverse=True)

        logger.warning(
            "[SelfRepairTrigger] Generati %d repair actions per viability=%.2f",
            len(actions), snap.viability
        )
        return actions

    def is_recovering(self) -> bool:
        """True se il sistema sta attualmente uscendo da repair mode."""
        return self._in_repair

    def check_recovery(self, snap: DriveSnapshot) -> bool:
        """
        Controlla se le condizioni di recovery sono soddisfatte.

        Returns:
            True se viability è tornata sopra recovery_threshold.
        """
        recovered = snap.viability >= self.recovery_threshold
        if recovered and self._in_repair:
            self._exit_repair(snap.viability)
        return recovered

    @property
    def repair_events(self) -> List[dict]:
        """History degli eventi di repair (per AutobiographicalMemory)."""
        return list(self._repair_events)

    @property
    def repair_duration_s(self) -> Optional[float]:
        """Durata dell'evento di repair corrente in secondi (None se non in repair)."""
        if self._in_repair and self._repair_start is not None:
            return time.monotonic() - self._repair_start
        return None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _enter_repair(self, bstate: BehavioralState) -> None:
        self._in_repair = True
        self._repair_start = time.monotonic()
        snap = bstate.source_snapshot
        event = {
            "event":     "repair_entered",
            "viability": snap.viability if snap else None,
            "rules":     bstate.triggered_rules,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._repair_events.append(event)
        logger.warning(
            "[SelfRepairTrigger] ⚠ ENTERED REPAIR MODE: viability=%.2f rules=%s",
            snap.viability if snap else -1.0,
            bstate.triggered_rules,
        )

    def _exit_repair(self, viability: float) -> None:
        duration = self.repair_duration_s or 0.0
        self._in_repair = False
        self._repair_start = None
        event = {
            "event":     "repair_exited",
            "viability": viability,
            "duration_s": duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._repair_events.append(event)
        logger.info(
            "[SelfRepairTrigger] ✓ EXIT REPAIR MODE: viability=%.2f duration=%.1fs",
            viability, duration
        )


__all__ = ["SelfRepairTrigger", "RepairAction"]
