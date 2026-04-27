"""
cortex.mesh.adapters.compartments — 9 Cortex compartments as mesh neurons (M4.8)

Mappatura Comparto → Neurone (input_type → output_type):

  Parietal Lobe  (L4 sensoriale)    : SensoryFrame → InterpretationFrame     need=integration
  Temporal Lobe  (L3 semantico/LLM) : SensoryFrame → InterpretationFrame     need=integration
  Hippocampus    (L3 memoria)       : InterpretationFrame → MemoryDelta      need=integration
  Prefrontal     (L2 planning)      : InterpretationFrame → DecisionFrame    need=expansion
  Safety         (L2 gate)          : DecisionFrame → SafetyVerdict          need=survival
  Cerebellum     (L5 esecuzione)    : DecisionFrame → ActionResult           need=expansion
  DMN            (L1 riflessione)   : InterpretationFrame → ReflectionFrame  need=self_improvement
  Curiosity      (L2 esplorazione)  : ReflectionFrame → MutationProposal     need=self_improvement
  Trading Cortex (L3 market)        : SensoryFrame → ActionResult            need=expansion   (opt-in)

Ogni adapter è lazy (istanzia il comparto solo al primo `execute`), thread-safe
per costruzione (il `@neuron` rebuild istanza per chiamata) e restituisce un
OLC frame anche in caso di errore (fail-soft).

Integrazione con i comparti esistenti:
  - I comparti implementano `process(state: dict) -> dict`. L'adapter costruisce
    lo `state` dict dall'OLC frame di input, chiama `process()`, e proietta il
    risultato sull'OLC frame di output atteso.
  - Nessuna modifica ai file di `cortex/comparti/`: gli adapter sono un layer
    puro di traduzione.
"""

from __future__ import annotations

import dataclasses
import threading
from typing import Any, Dict, Optional

from cortex.mesh.contract import neuron
from cortex.mesh.olc import (
    SensoryFrame,
    InterpretationFrame,
    DecisionFrame,
    SafetyVerdict,
    ActionResult,
    MemoryDelta,
    ReflectionFrame,
    MutationProposal,
)

# -----------------------------------------------------------------------------
# Lazy compartment cache (thread-safe)
# -----------------------------------------------------------------------------
#
# Evita di istanziare i comparti all'import (alcuni hanno side-effect di log,
# inizializzano LLM adapter, leggono stato bus). Prima chiamata del neurone →
# istanza cached.

_COMPARTMENT_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()


def _get(key: str, factory):
    """Restituisce istanza cached del comparto, creandola via `factory()` se assente."""
    inst = _COMPARTMENT_CACHE.get(key)
    if inst is not None:
        return inst
    with _CACHE_LOCK:
        inst = _COMPARTMENT_CACHE.get(key)
        if inst is None:
            inst = factory()
            _COMPARTMENT_CACHE[key] = inst
    return inst


def _reset_cache() -> None:
    """Solo per testing: svuota la cache comparti."""
    with _CACHE_LOCK:
        _COMPARTMENT_CACHE.clear()


def _frame_to_state(frame) -> Dict[str, Any]:
    """Converte un OLC frame in un dict `state` compatibile con BaseCompartment."""
    try:
        return dataclasses.asdict(frame)
    except Exception:
        # Fallback ultra-difensivo: introspezione attributi pubblici
        return {k: v for k, v in vars(frame).items() if not k.startswith("_")}


# =============================================================================
# 1. Parietal Lobe  (L4 sensory integration)
# =============================================================================

@neuron(
    name="neuron.compartment.parietal.perceive",
    input_type=SensoryFrame,
    output_type=InterpretationFrame,
    level=4,
    needs_served=["integration"],
    resource_budget={"max_ms": 200, "max_mb": 32},
    side_effects=[],
    version="1.0.0",
    description="Adapter mesh del Parietal Lobe: integra input sensoriali e produce interpretazione base.",
    tags=["compartment", "parietal", "perception"],
)
def parietal_perceive_neuron(frame: SensoryFrame) -> InterpretationFrame:
    try:
        from cortex.comparti.parietal_lobe import ParietalLobe
        pl = _get("parietal", ParietalLobe)
        state = {"sensory_input": _frame_to_state(frame)}
        pl.process(state)
        interp = state.get("interpretation", {}) or {}
        return InterpretationFrame(
            intent=str(interp.get("intent") or interp.get("goal") or "perceive"),
            confidence=float(interp.get("confidence", 0.6)),
            source=getattr(frame, "source", "parietal"),
            entities=list(interp.get("entities") or []),
            uncertainty=float(interp.get("uncertainty", 0.0)),
        )
    except Exception as exc:
        return InterpretationFrame(
            intent="perceive.error",
            confidence=0.0,
            source=getattr(frame, "source", "parietal"),
            uncertainty=1.0,
            entities=[f"error:{type(exc).__name__}"],
        )


# =============================================================================
# 2. Temporal Lobe  (L3 semantic / LLM)
# =============================================================================

@neuron(
    name="neuron.compartment.temporal.interpret",
    input_type=SensoryFrame,
    output_type=InterpretationFrame,
    level=3,
    needs_served=["integration", "self_improvement"],
    resource_budget={"max_ms": 5000, "max_mb": 128},
    side_effects=["llm:optional"],
    version="1.0.0",
    description="Adapter mesh del Temporal Lobe: interpretazione semantica (via LLM se abilitato).",
    tags=["compartment", "temporal", "semantic", "llm"],
)
def temporal_interpret_neuron(frame: SensoryFrame) -> InterpretationFrame:
    try:
        from cortex.comparti.temporal_lobe import TemporalLobe
        tl = _get("temporal", TemporalLobe)
        state = {"sensory_input": _frame_to_state(frame)}
        tl.process(state)
        interp = state.get("interpretation", {}) or {}
        return InterpretationFrame(
            intent=str(interp.get("intent") or "interpret"),
            confidence=float(interp.get("confidence", 0.7)),
            source=getattr(frame, "source", "temporal"),
            entities=list(interp.get("entities") or []),
            uncertainty=float(interp.get("uncertainty", 0.0)),
        )
    except Exception as exc:
        return InterpretationFrame(
            intent="interpret.error",
            confidence=0.0,
            source=getattr(frame, "source", "temporal"),
            uncertainty=1.0,
            entities=[f"error:{type(exc).__name__}"],
        )


# =============================================================================
# 3. Hippocampus  (L3 memory)
# =============================================================================

@neuron(
    name="neuron.compartment.hippocampus.consolidate",
    input_type=InterpretationFrame,
    output_type=MemoryDelta,
    level=3,
    needs_served=["integration"],
    resource_budget={"max_ms": 300, "max_mb": 64},
    side_effects=["fs_write:memory/episodes"],
    version="1.0.0",
    description="Adapter mesh dell'Hippocampus: traduce un'interpretazione in delta di memoria consolidabile.",
    tags=["compartment", "hippocampus", "memory"],
)
def hippocampus_consolidate_neuron(interp: InterpretationFrame) -> MemoryDelta:
    try:
        from cortex.comparti.hippocampus import Hippocampus
        import datetime as _dt

        hc = _get("hippocampus", Hippocampus)
        state = {"interpretation": _frame_to_state(interp), "cycle_id": _dt.datetime.utcnow().isoformat()}
        hc.process(state)
        episodes = state.get("memory_episodes") or [{
            "intent": interp.intent,
            "confidence": interp.confidence,
            "source": interp.source,
        }]
        score = min(1.0, max(0.0, float(interp.confidence) * 0.5 + 0.2))
        return MemoryDelta(
            cycle_id=state["cycle_id"],
            episodes=list(episodes),
            consolidation_score=score,
        )
    except Exception as exc:
        import datetime as _dt
        return MemoryDelta(
            cycle_id=_dt.datetime.utcnow().isoformat(),
            episodes=[{"error": f"{type(exc).__name__}: {exc}"}],
            consolidation_score=0.0,
        )


# =============================================================================
# 4. Prefrontal Cortex  (L2 planning)
# =============================================================================

@neuron(
    name="neuron.compartment.prefrontal.plan",
    input_type=InterpretationFrame,
    output_type=DecisionFrame,
    level=2,
    needs_served=["expansion"],
    resource_budget={"max_ms": 500, "max_mb": 64},
    side_effects=[],
    version="1.0.0",
    description="Adapter mesh del Prefrontal Cortex: pianifica decisione a partire dall'interpretazione.",
    tags=["compartment", "prefrontal", "planning"],
)
def prefrontal_plan_neuron(interp: InterpretationFrame) -> DecisionFrame:
    try:
        from cortex.comparti.prefrontal import PrefrontalCortex
        pfc = _get("prefrontal", PrefrontalCortex)
        state = {"interpretation": _frame_to_state(interp), "sensory_input": {}, "world_snapshot": {}}
        pfc.process(state)
        dec = state.get("decision", {}) or {}
        plan = dec.get("plan", {}) or {}
        steps = plan.get("steps") or []
        first_action = steps[0].get("action") if steps else "noop"
        return DecisionFrame(
            action=str(first_action),
            args={"plan": plan, "goal": dec.get("goal", "")},
            risk_level="low",
            pre_approved=False,
            rationale=f"planned:{dec.get('goal', 'none')}",
            risk=0.2,
        )
    except Exception as exc:
        return DecisionFrame(
            action="plan.error",
            args={"error": f"{type(exc).__name__}: {exc}"},
            risk_level="low",
            rationale="plan.failure",
            risk=0.0,
        )


# =============================================================================
# 5. Safety Module  (L2 gate)
# =============================================================================

@neuron(
    name="neuron.compartment.safety.verify",
    input_type=DecisionFrame,
    output_type=SafetyVerdict,
    level=2,
    needs_served=["survival"],
    resource_budget={"max_ms": 200, "max_mb": 32},
    side_effects=["fs_read:safeproactive/execution_rules.yaml"],
    version="1.0.0",
    description="Adapter mesh del Safety Module: valuta una decisione e produce verdetto safe/blocked.",
    tags=["compartment", "safety", "gate"],
)
def safety_verify_neuron(decision: DecisionFrame) -> SafetyVerdict:
    try:
        from cortex.comparti.safety_module import SafetyModule
        sm = _get("safety", SafetyModule)
        state = {"decision": _frame_to_state(decision), "safety_flags": {"blocked": False}}
        sm.process(state)
        flags = state.get("safety_flags", {}) or {}
        reasons = list(flags.get("reasons") or [])
        blocked = bool(flags.get("blocked", False))
        # risk_level: prende quello della decision se non sovrascritto da safety
        risk_level = str(flags.get("risk_level") or decision.risk_level or "low")
        if blocked and not reasons:
            reasons = ["blocked_by_safety_without_explicit_reason"]
        return SafetyVerdict(
            blocked=blocked,
            risk_level=risk_level,
            reasons=reasons,
            override_granted=bool(flags.get("override_granted", False)),
        )
    except Exception as exc:
        # Safety fail-closed: in caso di errore, blocchiamo.
        return SafetyVerdict(
            blocked=True,
            risk_level="high",
            reasons=[f"safety_adapter_error:{type(exc).__name__}:{exc}"],
            override_granted=False,
        )


# =============================================================================
# 6. Cerebellum  (L5 execution)
# =============================================================================

@neuron(
    name="neuron.compartment.cerebellum.execute",
    input_type=DecisionFrame,
    output_type=ActionResult,
    level=5,
    needs_served=["expansion"],
    resource_budget={"max_ms": 10000, "max_mb": 128},
    side_effects=["proposal:medium"],
    version="1.0.0",
    description="Adapter mesh del Cerebellum: esegue (o propone via SafeProactive con risk=medium) l'azione della decisione.",
    tags=["compartment", "cerebellum", "execution"],
)
def cerebellum_execute_neuron(decision: DecisionFrame) -> ActionResult:
    import time
    t0 = time.perf_counter()
    try:
        from cortex.comparti.cerebellum import Cerebellum
        cb = _get("cerebellum", Cerebellum)
        state = {"decision": _frame_to_state(decision)}
        cb.process(state)
        out = state.get("action_output", {}) or {}
        lat = (time.perf_counter() - t0) * 1000.0
        ok = bool(out.get("ok", True))
        err = out.get("error")
        return ActionResult(
            ok=ok,
            output=out if isinstance(out, dict) else {"raw": out},
            latency_ms=lat,
            error=(None if ok else (str(err) if err else "unknown_error")),
            action=decision.action,
        )
    except Exception as exc:
        lat = (time.perf_counter() - t0) * 1000.0
        return ActionResult(
            ok=False,
            output={},
            latency_ms=lat,
            error=f"{type(exc).__name__}: {exc}",
            action=decision.action,
        )


# =============================================================================
# 7. Default Mode Network  (L1 reflection)
# =============================================================================

@neuron(
    name="neuron.compartment.dmn.reflect",
    input_type=InterpretationFrame,
    output_type=ReflectionFrame,
    level=1,
    needs_served=["self_improvement"],
    resource_budget={"max_ms": 2000, "max_mb": 64},
    side_effects=["llm:optional"],
    version="1.0.0",
    description="Adapter mesh del Default Mode Network: auto-critique + suggerimenti.",
    tags=["compartment", "dmn", "reflection"],
)
def dmn_reflect_neuron(interp: InterpretationFrame) -> ReflectionFrame:
    try:
        from cortex.comparti.default_mode_network import DefaultModeNetwork
        dmn = _get("dmn", DefaultModeNetwork)
        state = {"interpretation": _frame_to_state(interp)}
        dmn.process(state)
        refl = state.get("reflection", {}) or {}
        return ReflectionFrame(
            summary=str(refl.get("summary") or f"reflect on {interp.intent}"),
            confidence=float(refl.get("confidence", 0.5)),
            suggestions=list(refl.get("suggestions") or []),
            source_cycle_id=str(refl.get("source_cycle_id", "")),
        )
    except Exception as exc:
        return ReflectionFrame(
            summary=f"reflection_error: {type(exc).__name__}",
            confidence=0.0,
            suggestions=[],
        )


# =============================================================================
# 8. Curiosity Module  (L2 exploration / novelty)
# =============================================================================

@neuron(
    name="neuron.compartment.curiosity.explore",
    input_type=ReflectionFrame,
    output_type=MutationProposal,
    level=2,
    needs_served=["self_improvement"],
    resource_budget={"max_ms": 1000, "max_mb": 64},
    side_effects=[],
    version="1.0.0",
    description="Adapter mesh del Curiosity Module: genera proposta di mutazione epigenetica a partire da una riflessione.",
    tags=["compartment", "curiosity", "exploration"],
)
def curiosity_explore_neuron(refl: ReflectionFrame) -> MutationProposal:
    try:
        from cortex.comparti.curiosity_module import CuriosityModule
        cm = _get("curiosity", CuriosityModule)
        state = {"reflection": _frame_to_state(refl)}
        cm.process(state)
        prop = state.get("mutation_proposal", {}) or {}
        title = str(prop.get("title") or f"explore:{refl.summary[:40]}")
        risk_level = str(prop.get("risk_level") or "low")
        change_spec = prop.get("change_spec") or {
            "type": "epigenome.explore",
            "suggestions": list(refl.suggestions),
        }
        return MutationProposal(
            title=title,
            risk_level=risk_level,
            change_spec=dict(change_spec) if isinstance(change_spec, dict) else {"raw": change_spec},
            rationale=str(prop.get("rationale") or refl.summary),
            target=str(prop.get("target") or "epigenome"),
        )
    except Exception as exc:
        return MutationProposal(
            title="curiosity.error",
            risk_level="low",
            change_spec={"error": f"{type(exc).__name__}: {exc}"},
            rationale="curiosity_adapter_failure",
            target="epigenome",
        )


# =============================================================================
# 9. Trading Cortex  (L3 market — opt-in)
# =============================================================================

@neuron(
    name="neuron.compartment.trading.read",
    input_type=SensoryFrame,
    output_type=ActionResult,
    level=3,
    needs_served=["expansion"],
    resource_budget={"max_ms": 5000, "max_mb": 128},
    side_effects=["net:optional"],
    version="1.0.0",
    description="Adapter mesh del Trading Cortex: read-only market snapshot. Non esegue trade (SafeProactive).",
    tags=["compartment", "trading", "readonly"],
)
def trading_read_neuron(frame: SensoryFrame) -> ActionResult:
    import time
    t0 = time.perf_counter()
    try:
        from cortex.comparti.trading_cortex import TradingCortex
        tc = _get("trading", TradingCortex)
        state = {"sensory_input": _frame_to_state(frame)}
        tc.process(state)
        out = state.get("market_snapshot", {}) or {}
        lat = (time.perf_counter() - t0) * 1000.0
        return ActionResult(
            ok=True,
            output=out if isinstance(out, dict) else {"raw": out},
            latency_ms=lat,
            action="trading.read",
        )
    except Exception as exc:
        lat = (time.perf_counter() - t0) * 1000.0
        return ActionResult(
            ok=False,
            output={},
            latency_ms=lat,
            error=f"{type(exc).__name__}: {exc}",
            action="trading.read",
        )


# =============================================================================
# Manifest: i 9 adapter registrati da questo modulo.
# =============================================================================

ADAPTER_NAMES = (
    "neuron.compartment.parietal.perceive",
    "neuron.compartment.temporal.interpret",
    "neuron.compartment.hippocampus.consolidate",
    "neuron.compartment.prefrontal.plan",
    "neuron.compartment.safety.verify",
    "neuron.compartment.cerebellum.execute",
    "neuron.compartment.dmn.reflect",
    "neuron.compartment.curiosity.explore",
    "neuron.compartment.trading.read",
)
