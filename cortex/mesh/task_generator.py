"""
cortex.mesh.task_generator — Task Generator dai bisogni → SafeProactive (M4.11)

Trasforma uno stato `NeedsSnapshot` (+ opzionalmente un `HarmonyReport`) in una
lista di `TaskProposal` (OLC) **già pronte per il pipeline SafeProactive**.

Pipeline logica:
  NeedsDriver.observe() ─→ NeedsSnapshot ──┐
                                            ├─→ TaskGenerator.generate() ─→ List[TaskProposal]
  HarmonyPolicy.evaluate() ─→ HarmonyReport ┘                                  │
                                                                                ▼
                                                              SafeProactive (M4.x esterno)

Filosofia:
  - **Stateless / deterministico**: stesso input → stesso output (a meno di
    timestamp impliciti nel `NeedsSnapshot.ts`).
  - **Allineato alla policy di equilibrio**: rispetta `allowed_risk_levels` di
    `HarmonyReport`. Se la policy proibisce HIGH, ogni proposta `high` viene
    declassata a `medium` (o scartata se anche `medium` è proibito).
  - **Diversità garantita**: distribuisce le proposte sui need con gap > 0
    (almeno 1 proposta per need critico, fino a `max_proposals`).
  - **No side-effect**: il generator non scrive su disco. La persistenza
    in `safeproactive/proposals/` è responsabilità del caller (o del daemon
    M4.14).

Output:
  TaskProposal(
      title: str,
      driving_need: str ∈ NEEDS_CATALOG,
      priority: float ∈ [0..1],
      estimated_impact: Dict[str, Any] = {"target_need": "...", "delta_estimate": 0.x},
      safeproactive_risk: "low" | "medium" | "high",
  )
"""

from __future__ import annotations

import dataclasses
import threading
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from cortex.mesh.olc import NeedsSnapshot, TaskProposal
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.harmony import (
    HarmonyPolicy,
    HarmonyReport,
    HarmonyVerdict,
)


# ---------------------------------------------------------------------------
# Templates: per ogni need, lista ordinata di template di proposta
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProposalTemplate:
    title: str
    rationale: str
    base_risk: str                 # "low" | "medium" | "high"
    delta_estimate: float          # impatto atteso sul need [0..1]


# Templates per need. Ordinati per riskAscending (low first).
TEMPLATES: Dict[str, Tuple[ProposalTemplate, ...]] = {
    "survival": (
        ProposalTemplate(
            title="Audit quarantene attive e ricalibrare error budget",
            rationale="Survival in deficit: rivedere quarantene, abbassare strike threshold se ingiustificato.",
            base_risk="low",
            delta_estimate=0.10,
        ),
        ProposalTemplate(
            title="Aumentare ridondanza neuronale (replica 2x prefrontal/safety)",
            rationale="Survival sotto soglia: replicare neuroni critici per resilienza.",
            base_risk="medium",
            delta_estimate=0.20,
        ),
        ProposalTemplate(
            title="Rollback ultima mutazione DigitalDNA se correlata a quarantene",
            rationale="Survival critico e self_improvement negativo: ipotizzare regressione genetica.",
            base_risk="high",
            delta_estimate=0.30,
        ),
    ),
    "expansion": (
        ProposalTemplate(
            title="Caricare adapter neuron per i need scoperti (compartments)",
            rationale="Expansion bassa: garantire copertura 5/5 needs servite via adapter mancanti.",
            base_risk="low",
            delta_estimate=0.15,
        ),
        ProposalTemplate(
            title="Aggiungere connettore IoT (sensore ambiente) come neurone parietal",
            rationale="Expansion: estendere ricezione sensoriale per i bisogni di integration.",
            base_risk="medium",
            delta_estimate=0.25,
        ),
    ),
    "self_improvement": (
        ProposalTemplate(
            title="Eseguire benchmark suite e proporre mutazione fitness-positiva",
            rationale="Self_improvement basso: generare mutazione MutationProposal con risk_level=low.",
            base_risk="low",
            delta_estimate=0.10,
        ),
        ProposalTemplate(
            title="Promuovere ciclo Curiosity → DigitalDNA evaluator → SafeProactive",
            rationale="Self_improvement deficit: stimolare path mesh `curiosity.explore → digitaldna.evaluate`.",
            base_risk="medium",
            delta_estimate=0.20,
        ),
    ),
    "integration": (
        ProposalTemplate(
            title="Eseguire MeshGraph.auto_wire() per riconnettere edge persi",
            rationale="Integration bassa: ricostruire pipeline canonica e riconnettere sub-grafi.",
            base_risk="low",
            delta_estimate=0.15,
        ),
        ProposalTemplate(
            title="Promuovere SPT review come secondo path interpretation",
            rationale="Integration: aggiungere percorso parallelo multi-expert oltre temporal lobe.",
            base_risk="medium",
            delta_estimate=0.20,
        ),
    ),
    "harmony": (
        ProposalTemplate(
            title="Rilasciare quarantene scadute o riabilitare neuroni stabilizzati",
            rationale="Harmony bassa: ridurre concentrazione di componenti dormienti.",
            base_risk="low",
            delta_estimate=0.10,
        ),
        ProposalTemplate(
            title="Bilanciare distribuzione level (L1..L5) aggiungendo neuroni nei layer scarsi",
            rationale="Harmony: skew di livelli rilevato, riequilibrare carichi.",
            base_risk="medium",
            delta_estimate=0.15,
        ),
    ),
}


# Pesi per priorità (allineabili a epigenome.mesh.needs.weights)
DEFAULT_NEED_WEIGHTS: Dict[str, float] = {
    "survival": 1.00,
    "expansion": 0.70,
    "self_improvement": 0.65,
    "integration": 0.75,
    "harmony": 0.85,
}


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
_RISK_REVERSE = {v: k for k, v in _RISK_ORDER.items()}


def _downgrade_risk(risk: str, allowed: FrozenSet[str]) -> Optional[str]:
    """Declassa il risk al massimo consentito; None se nemmeno 'low' è ammesso."""
    if risk in allowed:
        return risk
    if "low" not in allowed:
        return None
    cur = _RISK_ORDER.get(risk, 0)
    while cur >= 0:
        candidate = _RISK_REVERSE[cur]
        if candidate in allowed:
            return candidate
        cur -= 1
    return None


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class TaskGenerator:
    """
    Generator di TaskProposal a partire da NeedsSnapshot + HarmonyReport.
    """

    def __init__(
        self,
        *,
        policy: Optional[HarmonyPolicy] = None,
        max_proposals: int = 5,
        need_weights: Optional[Dict[str, float]] = None,
        templates: Optional[Dict[str, Tuple[ProposalTemplate, ...]]] = None,
    ) -> None:
        if max_proposals < 1:
            raise ValueError("max_proposals deve essere >= 1")
        self._policy = policy or HarmonyPolicy()
        self._max = int(max_proposals)
        self._weights = dict(DEFAULT_NEED_WEIGHTS)
        if need_weights:
            for k, v in need_weights.items():
                if k not in NEEDS_CATALOG:
                    raise ValueError(f"weight sconosciuto: {k}")
                self._weights[k] = max(0.0, float(v))
        self._templates = templates or TEMPLATES

    # ------------------------------------------------------------ API --

    def generate(
        self,
        snapshot: NeedsSnapshot,
        harmony_report: Optional[HarmonyReport] = None,
    ) -> List[TaskProposal]:
        """Produce fino a `max_proposals` TaskProposal ordinate per priority desc."""
        if not isinstance(snapshot, NeedsSnapshot):
            raise TypeError(f"atteso NeedsSnapshot, trovato {type(snapshot).__name__}")
        report = harmony_report or self._policy.evaluate(snapshot)

        gaps = dict(snapshot.gap or {})
        # Need con gap > 0 ordinati per priorità (gap * weight)
        ranked = self._rank_needs_by_priority(gaps)
        if not ranked:
            return []

        allowed = report.allowed_risk_levels
        proposals: List[TaskProposal] = []

        # Round-robin sui need ranked finché non raggiungiamo max_proposals
        # o esauriamo i template.
        per_need_idx: Dict[str, int] = {k: 0 for k, _ in ranked}
        attempts = 0
        max_attempts = self._max * 3 + 5

        while len(proposals) < self._max and attempts < max_attempts:
            attempts += 1
            advanced = False
            for need, weight_priority in ranked:
                if len(proposals) >= self._max:
                    break
                idx = per_need_idx[need]
                tmpls = self._templates.get(need, ())
                if idx >= len(tmpls):
                    continue
                tpl = tmpls[idx]
                per_need_idx[need] = idx + 1
                advanced = True

                final_risk = _downgrade_risk(tpl.base_risk, allowed)
                if final_risk is None:
                    # Tutti i livelli proibiti per questa proposta → skip
                    continue

                proposals.append(self._build_proposal(
                    need=need,
                    template=tpl,
                    final_risk=final_risk,
                    weight_priority=weight_priority,
                ))
            if not advanced:
                break

        # Sort finale per priority desc (e tie-break su severity di rischio asc)
        proposals.sort(
            key=lambda p: (-float(p.priority), _RISK_ORDER.get(p.safeproactive_risk, 0))
        )

        # Validazione difensiva: ogni proposta deve passare validate()
        valid = [p for p in proposals if not p.validate()]
        return valid

    # ------------------------------------------------------------ internals --

    def _rank_needs_by_priority(
        self, gaps: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        ranked: List[Tuple[str, float]] = []
        for k in NEEDS_CATALOG:
            gap = float(gaps.get(k, 0.0))
            if gap <= 0:
                continue
            w = float(self._weights.get(k, 0.5))
            ranked.append((k, gap * w))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _build_proposal(
        self,
        *,
        need: str,
        template: ProposalTemplate,
        final_risk: str,
        weight_priority: float,
    ) -> TaskProposal:
        # Priority normalizzata in [0..1]
        priority = max(0.0, min(1.0, float(weight_priority)))
        return TaskProposal(
            title=template.title,
            driving_need=need,
            priority=priority,
            estimated_impact={
                "target_need": need,
                "delta_estimate": float(template.delta_estimate),
                "rationale": template.rationale,
                "base_risk": template.base_risk,
                "downgraded": final_risk != template.base_risk,
            },
            safeproactive_risk=final_risk,
        )

    # ------------------------------------------------------------ serialization --

    @staticmethod
    def to_safeproactive_dicts(proposals: List[TaskProposal]) -> List[Dict[str, Any]]:
        """
        Serializzazione in dict pronto per `safeproactive/proposals/PROP-XXX.md` o
        per il bus PROPOSALS.md di SPEACE.
        """
        out: List[Dict[str, Any]] = []
        for p in proposals:
            out.append({
                "title": p.title,
                "driving_need": p.driving_need,
                "priority": p.priority,
                "risk_level": p.safeproactive_risk,
                "estimated_impact": dict(p.estimated_impact),
                "_olc": {"name": p.olc_name(), "version": p.olc_version()},
            })
        return out


__all__ = [
    "TaskGenerator",
    "ProposalTemplate",
    "TEMPLATES",
    "DEFAULT_NEED_WEIGHTS",
]
