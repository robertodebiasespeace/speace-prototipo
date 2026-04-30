"""
SPEACE Cortex Mesh — OLC Types (seed v1.0)

12 tipi fondamentali scambiabili fra neuroni della Continuous Neural Mesh.
Tabella completa in SPEC_NEURON_CONTRACT.md §2.1.

Convenzione:
  - `@dataclass(frozen=True)` per immutabilità shallow
  - `_OLC_NAME = "olc.<snake_case>"`, `_OLC_VERSION = "1.0"`
  - campi required senza default; opzionali con default
  - `validate()` estende OLCBase.validate() con vincoli di dominio

Ogni tipo è automaticamente registrato nell'OLC registry via
`@register_olc_type` al primo import di questo modulo.

Milestone: M4.3 (PROP-CORTEX-NEURAL-MESH-M4)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import OLCBase, OLCValidationError, iso_now, NEEDS_CATALOG
from .registry import register as _reg

_RISK_LEVELS = {"low", "medium", "high"}


# =============================================================================
# 1. SensoryFrame — input raw dal mondo
# =============================================================================

@_reg
@dataclass(frozen=True)
class SensoryFrame(OLCBase):
    _OLC_NAME = "olc.sensory_frame"
    _OLC_VERSION = "1.0"

    source: str                                    # es. "user_input", "noaa_feed", "iot_camera_01"
    payload: Dict[str, Any]                        # dict arbitrario sotto schema informale
    timestamp: str = field(default_factory=iso_now)
    modality: str = "text"                         # text | audio | image | numeric | composite
    confidence: float = 1.0                        # [0..1] — affidabilità sorgente

    def validate(self) -> List[str]:
        v = super().validate()
        if not isinstance(self.source, str) or not self.source.strip():
            v.append("SensoryFrame.source: stringa non vuota richiesta")
        if not (0.0 <= float(self.confidence) <= 1.0):
            v.append("SensoryFrame.confidence: deve essere in [0..1]")
        return v


# =============================================================================
# 2. InterpretationFrame — intent + entità + confidenza
# =============================================================================

@_reg
@dataclass(frozen=True)
class InterpretationFrame(OLCBase):
    _OLC_NAME = "olc.interpretation_frame"
    _OLC_VERSION = "1.0"

    intent: str
    confidence: float
    source: str = "unknown"
    entities: List[str] = field(default_factory=list)
    uncertainty: float = 0.0                       # complemento di `confidence` se non 1-confidence

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.intent:
            v.append("InterpretationFrame.intent: non può essere vuoto")
        if not (0.0 <= float(self.confidence) <= 1.0):
            v.append("InterpretationFrame.confidence: deve essere in [0..1]")
        if not (0.0 <= float(self.uncertainty) <= 1.0):
            v.append("InterpretationFrame.uncertainty: deve essere in [0..1]")
        return v


# =============================================================================
# 3. WorldSnapshot — subset rilevante del World Model per il ciclo
# =============================================================================

@_reg
@dataclass(frozen=True)
class WorldSnapshot(OLCBase):
    _OLC_NAME = "olc.world_snapshot"
    _OLC_VERSION = "1.0"

    snapshot_id: str
    scope: str                                     # es. "planet_health", "team_state", "regulatory"
    data: Dict[str, Any]
    drift: float = 0.0                             # [0..1] disallineamento vs realtà (triggers ConditionalScheduler)
    timestamp: str = field(default_factory=iso_now)

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.snapshot_id:
            v.append("WorldSnapshot.snapshot_id: non può essere vuoto")
        if not (0.0 <= float(self.drift) <= 1.0):
            v.append("WorldSnapshot.drift: deve essere in [0..1]")
        return v


# =============================================================================
# 4. DecisionFrame — azione proposta dal Prefrontal
# =============================================================================

@_reg
@dataclass(frozen=True)
class DecisionFrame(OLCBase):
    _OLC_NAME = "olc.decision_frame"
    _OLC_VERSION = "1.0"

    action: str
    args: Dict[str, Any]
    risk_level: str = "low"                        # low | medium | high
    pre_approved: bool = False
    rationale: str = ""
    risk: float = 0.0                              # [0..1] — score numerico complementare

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.action:
            v.append("DecisionFrame.action: non può essere vuoto")
        if self.risk_level not in _RISK_LEVELS:
            v.append(f"DecisionFrame.risk_level: deve essere in {_RISK_LEVELS}")
        if not (0.0 <= float(self.risk) <= 1.0):
            v.append("DecisionFrame.risk: deve essere in [0..1]")
        if self.risk_level == "high" and self.pre_approved:
            # non è violazione di OLC ma del contratto di SafeProactive — solo warning-level
            v.append("DecisionFrame: pre_approved=True con risk_level=high richiede verifica SafeProactive")
        return v


# =============================================================================
# 5. SafetyVerdict — verdetto del Safety Module
# =============================================================================

@_reg
@dataclass(frozen=True)
class SafetyVerdict(OLCBase):
    _OLC_NAME = "olc.safety_verdict"
    _OLC_VERSION = "1.0"

    blocked: bool
    risk_level: str                                # low | medium | high
    reasons: List[str] = field(default_factory=list)
    override_granted: bool = False                 # solo Safety può settare True

    def validate(self) -> List[str]:
        v = super().validate()
        if self.risk_level not in _RISK_LEVELS:
            v.append(f"SafetyVerdict.risk_level: deve essere in {_RISK_LEVELS}")
        if self.blocked and not self.reasons:
            v.append("SafetyVerdict: blocked=True senza reasons[] — obbligatorio motivare")
        return v


# =============================================================================
# 6. ActionResult — esito dell'azione (Cerebellum)
# =============================================================================

@_reg
@dataclass(frozen=True)
class ActionResult(OLCBase):
    _OLC_NAME = "olc.action_result"
    _OLC_VERSION = "1.0"

    ok: bool
    output: Dict[str, Any]
    latency_ms: float = 0.0
    error: Optional[str] = None
    action: str = ""                               # eco dell'azione eseguita

    def validate(self) -> List[str]:
        v = super().validate()
        if self.ok and self.error:
            v.append("ActionResult: ok=True con error non None è incoerente")
        if not self.ok and not self.error:
            v.append("ActionResult: ok=False richiede un messaggio di error")
        if float(self.latency_ms) < 0:
            v.append("ActionResult.latency_ms: non negativo")
        return v


# =============================================================================
# 7. MemoryDelta — episodi da consolidare (Hippocampus)
# =============================================================================

@_reg
@dataclass(frozen=True)
class MemoryDelta(OLCBase):
    _OLC_NAME = "olc.memory_delta"
    _OLC_VERSION = "1.0"

    cycle_id: str
    episodes: List[Dict[str, Any]]
    consolidation_score: float = 0.0               # [0..1] importanza per consolidamento long-term

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.cycle_id:
            v.append("MemoryDelta.cycle_id: non può essere vuoto")
        if not (0.0 <= float(self.consolidation_score) <= 1.0):
            v.append("MemoryDelta.consolidation_score: deve essere in [0..1]")
        return v


# =============================================================================
# 8. ReflectionFrame — self-critique del Default Mode Network
# =============================================================================

@_reg
@dataclass(frozen=True)
class ReflectionFrame(OLCBase):
    _OLC_NAME = "olc.reflection_frame"
    _OLC_VERSION = "1.0"

    summary: str
    confidence: float
    suggestions: List[str] = field(default_factory=list)
    source_cycle_id: str = ""

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.summary:
            v.append("ReflectionFrame.summary: non può essere vuoto")
        if not (0.0 <= float(self.confidence) <= 1.0):
            v.append("ReflectionFrame.confidence: deve essere in [0..1]")
        return v


# =============================================================================
# 9. MutationProposal — proposta di mutazione DNA/struttura
# =============================================================================

@_reg
@dataclass(frozen=True)
class MutationProposal(OLCBase):
    _OLC_NAME = "olc.mutation_proposal"
    _OLC_VERSION = "1.0"

    title: str
    risk_level: str                                # low | medium | high
    change_spec: Dict[str, Any]                    # descrizione machine-readable della mutazione
    rationale: str = ""
    target: str = "epigenome"                      # epigenome | mesh | genome (futuro)

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.title:
            v.append("MutationProposal.title: non può essere vuoto")
        if self.risk_level not in _RISK_LEVELS:
            v.append(f"MutationProposal.risk_level: deve essere in {_RISK_LEVELS}")
        if not self.change_spec:
            v.append("MutationProposal.change_spec: dict non vuoto richiesto")
        return v


# =============================================================================
# 10. NeedsSnapshot — stato dei 5 bisogni (Needs Driver)
# =============================================================================

@_reg
@dataclass(frozen=True)
class NeedsSnapshot(OLCBase):
    _OLC_NAME = "olc.needs_snapshot"
    _OLC_VERSION = "1.0"

    needs: Dict[str, float]                        # 5 chiavi di NEEDS_CATALOG → valore [0..1]
    gap: Dict[str, float]                          # target-current per ciascun need
    ts: str = field(default_factory=iso_now)

    def validate(self) -> List[str]:
        v = super().validate()
        catalog = set(NEEDS_CATALOG)
        k_needs = set(self.needs.keys()) if self.needs else set()
        if k_needs != catalog:
            missing = catalog - k_needs
            extra = k_needs - catalog
            if missing:
                v.append(f"NeedsSnapshot.needs: chiavi mancanti {sorted(missing)}")
            if extra:
                v.append(f"NeedsSnapshot.needs: chiavi extra non in catalog {sorted(extra)}")
        for k, val in (self.needs or {}).items():
            try:
                fv = float(val)
            except (TypeError, ValueError):
                v.append(f"NeedsSnapshot.needs[{k}]: valore non numerico")
                continue
            if not (0.0 <= fv <= 1.0):
                v.append(f"NeedsSnapshot.needs[{k}]={fv}: atteso in [0..1]")
        return v


# =============================================================================
# 11. FeedbackFrame — segnali di fitness per ciclo
# =============================================================================

@_reg
@dataclass(frozen=True)
class FeedbackFrame(OLCBase):
    _OLC_NAME = "olc.feedback_frame"
    _OLC_VERSION = "1.0"

    cycle_id: str
    latency_ms: float
    errors: int
    fitness_delta: float                           # Δ fitness rispetto al ciclo precedente
    notes: str = ""

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.cycle_id:
            v.append("FeedbackFrame.cycle_id: non può essere vuoto")
        if float(self.latency_ms) < 0:
            v.append("FeedbackFrame.latency_ms: non negativo")
        if int(self.errors) < 0:
            v.append("FeedbackFrame.errors: non negativo")
        return v


# =============================================================================
# 12. TaskProposal — task emergente da need sotto soglia
# =============================================================================

@_reg
@dataclass(frozen=True)
class TaskProposal(OLCBase):
    _OLC_NAME = "olc.task_proposal"
    _OLC_VERSION = "1.0"

    title: str
    driving_need: str                              # uno di NEEDS_CATALOG
    priority: float                                # [0..1] — calcolato da need_gap * weight
    estimated_impact: Dict[str, Any] = field(default_factory=dict)
    safeproactive_risk: str = "low"                # suggerimento per SafeProactive

    def validate(self) -> List[str]:
        v = super().validate()
        if not self.title:
            v.append("TaskProposal.title: non può essere vuoto")
        if self.driving_need not in NEEDS_CATALOG:
            v.append(f"TaskProposal.driving_need: deve essere in {NEEDS_CATALOG}")
        if not (0.0 <= float(self.priority) <= 1.0):
            v.append("TaskProposal.priority: deve essere in [0..1]")
        if self.safeproactive_risk not in _RISK_LEVELS:
            v.append(f"TaskProposal.safeproactive_risk: deve essere in {_RISK_LEVELS}")
        return v


# =============================================================================
# Manifest (tupla dei 12 tipi, comodo per testing / introspection)
# =============================================================================

ALL_TYPES = (
    SensoryFrame,
    InterpretationFrame,
    WorldSnapshot,
    DecisionFrame,
    SafetyVerdict,
    ActionResult,
    MemoryDelta,
    ReflectionFrame,
    MutationProposal,
    NeedsSnapshot,
    FeedbackFrame,
    TaskProposal,
)

__all__ = [t.__name__ for t in ALL_TYPES] + ["ALL_TYPES"]
