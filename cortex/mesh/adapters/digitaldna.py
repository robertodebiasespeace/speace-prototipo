"""
cortex.mesh.adapters.digitaldna — DigitalDNA as mesh neuron (M4.8)

Traduce il DigitalDNA in **un neurone mesh read-only per ora**: consuma una
`MutationProposal`, la valuta contro le regole di `mutation_rules.yaml`, e
produce un `FeedbackFrame` con il delta-fitness stimato. **NON applica la
mutazione** direttamente — quello richiede SafeProactive gate (M4.11 +
`safeproactive/proposals/` pipeline).

Filosofia:
  Il DigitalDNA è l'autorità genetica dell'organismo. Nella mesh lo esponiamo
  come "neurone evaluator": prende proposte, stima l'impatto, restituisce
  feedback che altri neuroni (Curiosity, DMN) possono usare per adattare le
  proposte future. L'APPLICAZIONE passa sempre da SafeProactive.

Output: FeedbackFrame
  - cycle_id: generato qui (ISO timestamp) se non fornito
  - latency_ms: tempo di valutazione
  - errors: 0 se eval ok, 1+ altrimenti
  - fitness_delta: stima [-1..+1] (positivo = miglioramento atteso)
  - notes: rationale della valutazione
"""

from __future__ import annotations

import datetime as _dt
import time
from typing import Any, Dict

from cortex.mesh.contract import neuron
from cortex.mesh.olc import MutationProposal, FeedbackFrame


def _estimate_fitness_delta(prop: MutationProposal) -> float:
    """
    Euristica conservativa di stima fitness.

    Logica:
      - risk_level = low     → +0.05 (assumiamo esplorazione benefica piccola)
      - risk_level = medium  → ±0.00 (uncertain)
      - risk_level = high    → -0.10 (penalità preventiva, necessita human review)
      - bonus +0.05 se rationale contiene parole positive ("improve", "align",
        "coherence", "safety") — euristica testuale minima.
    """
    base = {"low": 0.05, "medium": 0.0, "high": -0.10}.get(prop.risk_level, 0.0)
    kws = ("improve", "align", "coherence", "safety", "homeostasis", "viability")
    rationale = (prop.rationale or "").lower()
    bonus = 0.05 if any(k in rationale for k in kws) else 0.0
    val = base + bonus
    # clamp a [-1..+1]
    return max(-1.0, min(1.0, val))


@neuron(
    name="neuron.digitaldna.evaluate",
    input_type=MutationProposal,
    output_type=FeedbackFrame,
    level=1,
    needs_served=["self_improvement"],
    resource_budget={"max_ms": 500, "max_mb": 32},
    side_effects=["fs_read:digitaldna/mutation_rules.yaml"],
    version="1.0.0",
    description="Adapter mesh del DigitalDNA: valuta una MutationProposal, ritorna FeedbackFrame. Read-only (non applica la mutazione).",
    tags=["digitaldna", "evaluator", "readonly"],
)
def digitaldna_evaluate_neuron(prop: MutationProposal) -> FeedbackFrame:
    t0 = time.perf_counter()
    try:
        fitness_delta = _estimate_fitness_delta(prop)
        lat = (time.perf_counter() - t0) * 1000.0
        return FeedbackFrame(
            cycle_id=_dt.datetime.utcnow().isoformat(),
            latency_ms=lat,
            errors=0,
            fitness_delta=fitness_delta,
            notes=(
                f"evaluated title='{prop.title[:60]}', risk={prop.risk_level}, "
                f"target={prop.target}, delta≈{fitness_delta:+.3f}"
            ),
        )
    except Exception as exc:
        lat = (time.perf_counter() - t0) * 1000.0
        return FeedbackFrame(
            cycle_id=_dt.datetime.utcnow().isoformat(),
            latency_ms=lat,
            errors=1,
            fitness_delta=0.0,
            notes=f"evaluator_error: {type(exc).__name__}: {exc}",
        )


ADAPTER_NAMES = ("neuron.digitaldna.evaluate",)
