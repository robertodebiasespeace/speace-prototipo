"""
cortex.cognitive_autonomy.executive.drive_executive
=====================================================
M7.0 — DriveExecutive: ponte causale tra HomeostaticController e comportamento.

Problema risolto:
  HomeostaticController calcola drive (viability, curiosity, coherence,
  energy, alignment) → li aggiorna nel display → fine.
  Nessun componente leggeva lo stato drive per modificare la selezione dei task,
  la profondità di pianificazione, la priorità della memoria o il gating delle
  mutazioni. I drive erano epifenomeni computazionali — non causali.

Soluzione:
  DriveExecutive.compute(drive_state) → BehavioralState
  BehavioralState è letto da TaskSelector, SMFOI_v3.py step 4,
  SelfRepairTrigger, e da qualsiasi componente che abbia bisogno di
  adattarsi allo stato interno di SPEACE.

Regole causali fondamentali (PROP-M7-DRIVE-EXECUTIVE):
  viability < 0.4  → self_repair_mode=True, sospendi task non critici
  viability < 0.6  → focus_shift="conserve", riduce parallelismo
  curiosity > 0.7  → exploration_bonus=+0.3, task esplorative spontanee
  coherence < 0.4  → memory_priority_boost=+0.5, consolida memoria
  energy < 0.3     → planning_depth=1, solo pianificazione superficiale
  alignment < 0.5  → mutation_gate_open=False, blocca mutazioni
  Phi > 0.7        → max_parallel_tasks=4, altrimenti 1-2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# DriveSnapshot — snapshot istantaneo dei drive (input del DriveExecutive)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DriveSnapshot:
    """
    Snapshot istantaneo dello stato dei drive interni di SPEACE.

    Tutti i valori sono in [0.0, 1.0].
    Compatibile con l'output di HomeostaticController.update()
    e ValueField.evaluate().
    """
    viability:  float = 1.0   # salute sistemica generale
    curiosity:  float = 0.5   # spinta esplorativa
    coherence:  float = 0.8   # coerenza interna / memoria
    energy:     float = 0.75  # risorse disponibili
    alignment:  float = 0.8   # allineamento con obiettivi TINA/Rigene
    phi:        float = 0.5   # Φ coscienza (ConsciousnessIndex)
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_homeostasis_result(cls, result: dict, phi: float = 0.5) -> "DriveSnapshot":
        """
        Costruisce DriveSnapshot dall'output di HomeostaticController.update().

        Args:
            result: dict restituito da hc.update(receptor_readings)
            phi: valore Φ corrente da ConsciousnessIndex (default 0.5)
        """
        h_state = result.get("h_state", {})
        return cls(
            viability=result.get("viability_score", 1.0),
            curiosity=h_state.get("curiosity", 0.5),
            coherence=h_state.get("coherence", 0.8),
            energy=h_state.get("energy", 0.75),
            alignment=h_state.get("alignment", 0.8),
            phi=phi,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "viability": self.viability,
            "curiosity": self.curiosity,
            "coherence": self.coherence,
            "energy": self.energy,
            "alignment": self.alignment,
            "phi": self.phi,
        }


# ──────────────────────────────────────────────────────────────────────────────
# BehavioralState — output del DriveExecutive (letto dai componenti a valle)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BehavioralState:
    """
    Stato comportamentale prodotto dal DriveExecutive.

    Questo dataclass è il "punto di accoppiamento" tra i drive interni
    e i comportamenti osservabili (selezione task, pianificazione,
    memoria, mutazioni genetiche).

    Viene letto da:
      - TaskSelector: per filtrare/ordinare i task
      - SMFOI_v3.py step 4: prima di Output Action
      - SelfRepairTrigger: per attivare modalità riparazione
      - DigitalDNA mutation gate: per bloccare mutazioni pericolose
    """
    # Parallelismo
    max_parallel_tasks: int = 2
    """Φ alto (>0.7) → 4 task paralleli; altrimenti 1-2."""

    # Esplorazione
    exploration_bonus: float = 0.0
    """curiosity > 0.7 → +0.3; aggiunto al punteggio dei task esplorativi."""

    # Memoria
    memory_priority_boost: float = 0.0
    """coherence < 0.4 → +0.5; aumenta priorità consolidamento episodi."""

    # Pianificazione
    planning_depth: int = 3
    """energy < 0.3 → 1 (superficiale); energy > 0.7 → 5 (profonda)."""

    # Modalità riparazione
    self_repair_mode: bool = False
    """viability < 0.4 → True; sospende task non critici."""

    # Gating mutazioni
    mutation_gate_open: bool = True
    """alignment < 0.5 → False; blocca mutazioni DigitalDNA."""

    # Focus shift
    focus_shift: Optional[str] = None
    """viability < 0.5 → 'conserve' | viability < 0.4 → 'repair' | None."""

    # Metadati diagnostici
    triggered_rules: List[str] = field(default_factory=list)
    """Lista delle regole causali che hanno modificato questo stato."""
    source_snapshot: Optional[DriveSnapshot] = field(default=None, repr=False)
    """DriveSnapshot che ha prodotto questo BehavioralState."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_critical(self) -> bool:
        """True se il sistema è in modalità critica (riparazione attiva)."""
        return self.self_repair_mode

    def to_dict(self) -> dict:
        return {
            "max_parallel_tasks":    self.max_parallel_tasks,
            "exploration_bonus":     self.exploration_bonus,
            "memory_priority_boost": self.memory_priority_boost,
            "planning_depth":        self.planning_depth,
            "self_repair_mode":      self.self_repair_mode,
            "mutation_gate_open":    self.mutation_gate_open,
            "focus_shift":           self.focus_shift,
            "triggered_rules":       self.triggered_rules,
            "timestamp":             self.timestamp,
        }


# ──────────────────────────────────────────────────────────────────────────────
# DriveExecutive — motore di traduzione Drive → BehavioralState
# ──────────────────────────────────────────────────────────────────────────────

class DriveExecutive:
    """
    Ponte causale tra i drive omeostatici e il comportamento di SPEACE.

    Uso tipico:
        executive = DriveExecutive()
        snap = DriveSnapshot.from_homeostasis_result(hc.update(readings), phi=phi)
        bstate = executive.compute(snap)
        # bstate è ora letto da TaskSelector, SMFOI, ecc.

    Internamente applica un insieme ordinato di regole causali:
    ogni regola modifica il BehavioralState in base a soglie sui drive.
    Le regole vengono applicate tutte (non si escludono a vicenda).
    """

    # Soglie (configurabili via costruttore)
    VIABILITY_REPAIR   = 0.4   # sotto → self_repair_mode
    VIABILITY_CONSERVE = 0.6   # sotto → focus_shift="conserve"
    VIABILITY_FOCUS    = 0.5   # sotto → focus_shift="conserve" o "repair"
    CURIOSITY_EXPLORE  = 0.7   # sopra → exploration_bonus
    COHERENCE_MEMORY   = 0.4   # sotto → memory_priority_boost
    ENERGY_SHALLOW     = 0.3   # sotto → planning_depth=1
    ENERGY_DEEP        = 0.7   # sopra → planning_depth=5
    ALIGNMENT_GATE     = 0.5   # sotto → mutation_gate_open=False
    PHI_PARALLEL       = 0.7   # sopra → max_parallel_tasks=4

    def __init__(
        self,
        viability_repair:   float = VIABILITY_REPAIR,
        viability_conserve: float = VIABILITY_CONSERVE,
        curiosity_explore:  float = CURIOSITY_EXPLORE,
        coherence_memory:   float = COHERENCE_MEMORY,
        energy_shallow:     float = ENERGY_SHALLOW,
        energy_deep:        float = ENERGY_DEEP,
        alignment_gate:     float = ALIGNMENT_GATE,
        phi_parallel:       float = PHI_PARALLEL,
    ) -> None:
        self.viability_repair   = viability_repair
        self.viability_conserve = viability_conserve
        self.curiosity_explore  = curiosity_explore
        self.coherence_memory   = coherence_memory
        self.energy_shallow     = energy_shallow
        self.energy_deep        = energy_deep
        self.alignment_gate     = alignment_gate
        self.phi_parallel       = phi_parallel
        self._last_state: Optional[BehavioralState] = None

    # ── API pubblica ──────────────────────────────────────────────────────────

    def compute(self, snap: DriveSnapshot) -> BehavioralState:
        """
        Traduce un DriveSnapshot in un BehavioralState applicando
        le regole causali fondamentali.

        Args:
            snap: DriveSnapshot corrente (da HomeostaticController)

        Returns:
            BehavioralState con tutti i campi calcolati e triggered_rules popolato.
        """
        bs = BehavioralState(source_snapshot=snap)
        rules: List[str] = []

        # ── Regola R1: viability critica → self_repair_mode ──────────────────
        if snap.viability < self.viability_repair:
            bs.self_repair_mode = True
            bs.focus_shift = "repair"
            bs.max_parallel_tasks = 1
            rules.append(f"R1:viability({snap.viability:.2f})<{self.viability_repair}→repair_mode")
            logger.warning(
                "[DriveExecutive] REPAIR MODE: viability=%.2f < %.2f",
                snap.viability, self.viability_repair
            )

        # ── Regola R2: viability bassa → conserva risorse ────────────────────
        elif snap.viability < self.viability_conserve:
            bs.focus_shift = "conserve"
            bs.max_parallel_tasks = max(1, bs.max_parallel_tasks - 1)
            rules.append(f"R2:viability({snap.viability:.2f})<{self.viability_conserve}→conserve")
            logger.info(
                "[DriveExecutive] CONSERVE: viability=%.2f < %.2f",
                snap.viability, self.viability_conserve
            )

        # ── Regola R3: curiosity alta → esplorazione spontanea ───────────────
        if snap.curiosity > self.curiosity_explore:
            bs.exploration_bonus = 0.3
            rules.append(f"R3:curiosity({snap.curiosity:.2f})>{self.curiosity_explore}→explore+0.3")
            logger.info(
                "[DriveExecutive] EXPLORE: curiosity=%.2f > %.2f → bonus +0.3",
                snap.curiosity, self.curiosity_explore
            )

        # ── Regola R4: coherence bassa → consolida memoria ───────────────────
        if snap.coherence < self.coherence_memory:
            bs.memory_priority_boost = 0.5
            rules.append(f"R4:coherence({snap.coherence:.2f})<{self.coherence_memory}→memory+0.5")
            logger.info(
                "[DriveExecutive] MEMORY BOOST: coherence=%.2f < %.2f",
                snap.coherence, self.coherence_memory
            )

        # ── Regola R5: energy bassa → pianificazione superficiale ────────────
        if snap.energy < self.energy_shallow:
            bs.planning_depth = 1
            rules.append(f"R5:energy({snap.energy:.2f})<{self.energy_shallow}→depth=1")
            logger.info(
                "[DriveExecutive] SHALLOW PLANNING: energy=%.2f < %.2f",
                snap.energy, self.energy_shallow
            )
        # ── Regola R5b: energy alta → pianificazione profonda ────────────────
        elif snap.energy > self.energy_deep:
            bs.planning_depth = 5
            rules.append(f"R5b:energy({snap.energy:.2f})>{self.energy_deep}→depth=5")

        # ── Regola R6: alignment basso → blocca mutazioni ────────────────────
        if snap.alignment < self.alignment_gate:
            bs.mutation_gate_open = False
            rules.append(f"R6:alignment({snap.alignment:.2f})<{self.alignment_gate}→mutation_blocked")
            logger.warning(
                "[DriveExecutive] MUTATION GATE CLOSED: alignment=%.2f < %.2f",
                snap.alignment, self.alignment_gate
            )

        # ── Regola R7: Φ alto → più parallelismo ─────────────────────────────
        if snap.phi > self.phi_parallel and not bs.self_repair_mode:
            bs.max_parallel_tasks = 4
            rules.append(f"R7:phi({snap.phi:.2f})>{self.phi_parallel}→parallel=4")
        elif not bs.self_repair_mode and bs.focus_shift is None:
            # Default: 2 task paralleli se Φ è nella norma
            bs.max_parallel_tasks = 2

        bs.triggered_rules = rules
        self._last_state = bs

        if rules:
            logger.debug("[DriveExecutive] triggered_rules=%s", rules)

        return bs

    def compute_from_homeostasis(
        self,
        hc_result: dict,
        phi: float = 0.5,
    ) -> BehavioralState:
        """
        Shortcut: costruisce DriveSnapshot da output HomeostaticController
        e chiama compute().

        Args:
            hc_result: dict da HomeostaticController.update()
            phi: valore Φ da ConsciousnessIndex

        Returns:
            BehavioralState
        """
        snap = DriveSnapshot.from_homeostasis_result(hc_result, phi=phi)
        return self.compute(snap)

    @property
    def last_state(self) -> Optional[BehavioralState]:
        """Ultimo BehavioralState calcolato (None se non ancora chiamato)."""
        return self._last_state

    def __repr__(self) -> str:
        state = self._last_state
        if state is None:
            return "DriveExecutive(no_state)"
        return (
            f"DriveExecutive("
            f"repair={state.self_repair_mode}, "
            f"parallel={state.max_parallel_tasks}, "
            f"explore_bonus={state.exploration_bonus:.2f}, "
            f"planning_depth={state.planning_depth}, "
            f"mutation_gate={state.mutation_gate_open})"
        )


__all__ = ["DriveExecutive", "BehavioralState", "DriveSnapshot"]
