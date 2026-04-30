"""
cortex.mesh.adapters.scientific_team — SPEACE Team Scientifico as mesh neuron (M4.8)

Espone lo `ScientificTeamOrchestrator` come un neurone mesh multi-expert: un
percorso cognitivo *parallelo* al Temporal Lobe per situazioni che richiedono
review multi-prospettiva (climate, economics, governance, ethics, adversarial,
evidence, regulatory).

Contratto:
  SensoryFrame → InterpretationFrame (arricchita da output SPT)

Policy di opt-in:
  Per default il neurone è **discoverable** ma la mesh decide se wire-arlo.
  L'orchestrator viene istanziato lazy alla prima chiamata. Se fallisce
  l'import (es. team non installato o agente mancante), il neurone restituisce
  una InterpretationFrame di fallback con confidence bassa — senza interrompere
  la mesh.

Costi:
  Un ciclo SPT completo è pesante (7 agenti + 1 orchestrator), quindi resource
  budget è generoso (max_ms=30000, max_mb=256). Il team è target di
  backpressure severa in execution_rules.yaml.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from cortex.mesh.contract import neuron
from cortex.mesh.olc import SensoryFrame, InterpretationFrame


_ORCHESTRATOR: Optional[Any] = None
_ORCH_LOCK = threading.Lock()


def _get_orchestrator():
    global _ORCHESTRATOR
    if _ORCHESTRATOR is not None:
        return _ORCHESTRATOR
    with _ORCH_LOCK:
        if _ORCHESTRATOR is None:
            from importlib import import_module
            mod = import_module("scientific-team.orchestrator".replace("-", "_"))  # noqa
            # "scientific-team" ha un trattino: non valido come dotted path, quindi
            # usiamo import dinamico via __path__. Fallback:
            _ORCHESTRATOR = mod.ScientificTeamOrchestrator()
    return _ORCHESTRATOR


def _try_import_orchestrator():
    """
    Import robusto: la directory si chiama `scientific-team` (con trattino), che
    NON è un identificatore Python valido. Lo carichiamo a mano via importlib.

    Ritorna (orchestrator_instance | None, error_str | None).
    """
    try:
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        orch_path = root / "scientific-team" / "orchestrator.py"
        if not orch_path.exists():
            return None, f"file_not_found:{orch_path}"
        spec = importlib.util.spec_from_file_location("_spt_orchestrator_module", orch_path)
        if spec is None or spec.loader is None:
            return None, "spec_load_failed"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "ScientificTeamOrchestrator"):
            return None, "ScientificTeamOrchestrator not found"
        return mod.ScientificTeamOrchestrator(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


@neuron(
    name="neuron.scientific_team.review",
    input_type=SensoryFrame,
    output_type=InterpretationFrame,
    level=2,
    needs_served=["integration", "self_improvement"],
    resource_budget={"max_ms": 30000, "max_mb": 256},
    side_effects=["llm:optional", "fs_write:scientific-team/outputs"],
    version="1.0.0",
    description="Adapter mesh dello SPEACE Team Scientifico: review multi-expert di un SensoryFrame.",
    tags=["scientific_team", "multi_expert", "review"],
)
def spt_review_neuron(frame: SensoryFrame) -> InterpretationFrame:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        with _ORCH_LOCK:
            if _ORCHESTRATOR is None:
                inst, err = _try_import_orchestrator()
                if inst is None:
                    # Fallback graceful: la mesh continua senza SPT.
                    return InterpretationFrame(
                        intent="spt.unavailable",
                        confidence=0.1,
                        source=getattr(frame, "source", "spt"),
                        uncertainty=0.9,
                        entities=[f"error:{err}"],
                    )
                _ORCHESTRATOR = inst

    try:
        # L'API esatta dipende dall'orchestrator; tipicamente `analyze(payload)`
        # o `run_cycle(...)`. Tentiamo metodi in ordine di preferenza.
        orch = _ORCHESTRATOR
        result: Any = None
        for method in ("analyze", "run_cycle", "review", "execute"):
            fn = getattr(orch, method, None)
            if callable(fn):
                try:
                    result = fn(frame.payload)
                except TypeError:
                    # Firma diversa: prova no-args, poi dict
                    try:
                        result = fn()
                    except Exception:
                        result = fn({"payload": frame.payload})
                break

        if result is None:
            # Non abbiamo trovato metodo noto, fallback soft
            return InterpretationFrame(
                intent="spt.no_method",
                confidence=0.2,
                source=getattr(frame, "source", "spt"),
                uncertainty=0.8,
            )

        # Normalizzazione: risultato può essere dict o oggetto con campi
        if isinstance(result, dict):
            intent = str(result.get("intent") or result.get("summary") or "spt.review")
            confidence = float(result.get("confidence", 0.7))
            entities = list(result.get("entities") or result.get("agents_engaged") or [])
        else:
            intent = str(getattr(result, "intent", "spt.review"))
            confidence = float(getattr(result, "confidence", 0.7))
            entities = list(getattr(result, "entities", []) or [])

        return InterpretationFrame(
            intent=intent,
            confidence=max(0.0, min(1.0, confidence)),
            source=getattr(frame, "source", "spt"),
            entities=entities,
            uncertainty=max(0.0, min(1.0, 1.0 - confidence)),
        )
    except Exception as exc:
        return InterpretationFrame(
            intent="spt.error",
            confidence=0.0,
            source=getattr(frame, "source", "spt"),
            uncertainty=1.0,
            entities=[f"error:{type(exc).__name__}:{exc}"],
        )


ADAPTER_NAMES = ("neuron.scientific_team.review",)
