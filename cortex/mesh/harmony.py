"""
cortex.mesh.harmony — Harmony Safeguard Policy (M4.10)

Policy di equilibrio dell'organismo. Consuma un `NeedsSnapshot` (prodotto da
`NeedsDriver`) e produce:

  1. **HarmonyVerdict** — uno stato sintetico {HEALTHY, WATCH, ALERT, CRITICAL}
  2. **Compensation actions** — raccomandazioni di compensazione per la mesh:
     blocchi temporanei, richieste di audit, sospensioni di mutazioni, ecc.
  3. **Allowed risk levels** — quali livelli di SafeProactive (low/medium/high)
     sono ammissibili nello stato corrente.

Filosofia:
  - **Fail-safe-toward-equilibrium**: in dubbio, restringe lo spazio d'azione
    (mai espande senza guadagno omeostatico chiaro).
  - **Read-only**: non modifica nulla. Produce solo segnali. M4.11 (Task
    Generator) e SafeProactive sono i consumatori.
  - **Idempotente**: stesso `NeedsSnapshot` → stesso `HarmonyReport`.

Thresholds (tunabili via DigitalDNA EPI-004 in M4.18):
  HEALTHY  — tutti i need >= 0.85 * target
  WATCH    — almeno 1 need in [0.5*target .. 0.85*target)
  ALERT    — almeno 1 need < 0.5*target  oppure  un gap > 0.4
  CRITICAL — survival < 0.5  OPPURE  harmony < 0.3

Le compensazioni sono dichiarative (kind, target, rationale, severity) e non
eseguibili direttamente — passano sempre da SafeProactive.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from cortex.mesh.olc import NeedsSnapshot
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.needs_driver import DEFAULT_TARGETS


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


class HarmonyVerdict(str, enum.Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    ALERT = "alert"
    CRITICAL = "critical"

    @property
    def severity(self) -> int:
        return {"healthy": 0, "watch": 1, "alert": 2, "critical": 3}[self.value]


# ---------------------------------------------------------------------------
# Compensation actions
# ---------------------------------------------------------------------------


COMPENSATION_KINDS: FrozenSet[str] = frozenset({
    # operative actions (richieste alla mesh)
    "block_high_risk_proposals",
    "block_medium_risk_proposals",
    "request_quarantine_review",
    "pause_mutation_acceptance",
    "request_integration_audit",
    "expand_neuron_coverage",
    "throttle_side_effects",
    "elevate_human_review",
    # informative
    "alert_operator",
})


@dataclasses.dataclass(frozen=True)
class CompensationAction:
    kind: str
    target: str             # need o componente coinvolta (es. "harmony", "mesh.runtime")
    rationale: str
    severity: int           # 0..3 (0 informativo, 3 critico)

    def __post_init__(self) -> None:
        if self.kind not in COMPENSATION_KINDS:
            raise ValueError(
                f"CompensationAction.kind={self.kind!r} non riconosciuto. "
                f"Valid: {sorted(COMPENSATION_KINDS)}"
            )
        if not 0 <= int(self.severity) <= 3:
            raise ValueError(f"CompensationAction.severity={self.severity}: atteso 0..3")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HarmonyReport:
    verdict: HarmonyVerdict
    compensations: Tuple[CompensationAction, ...]
    allowed_risk_levels: FrozenSet[str]
    needs_below_target: Tuple[str, ...]
    rationale: str
    snapshot_ts: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "severity": self.verdict.severity,
            "compensations": [
                {
                    "kind": c.kind,
                    "target": c.target,
                    "rationale": c.rationale,
                    "severity": c.severity,
                }
                for c in self.compensations
            ],
            "allowed_risk_levels": sorted(self.allowed_risk_levels),
            "needs_below_target": list(self.needs_below_target),
            "rationale": self.rationale,
            "snapshot_ts": self.snapshot_ts,
        }


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class HarmonyPolicy:
    """
    Policy di valutazione dell'equilibrio. Stateless (i target sono passati
    al costruttore o letti dai default).
    """

    def __init__(
        self,
        *,
        targets: Optional[Dict[str, float]] = None,
        # Soglie sui rapporti current/target
        healthy_ratio: float = 0.85,
        watch_floor: float = 0.50,
        critical_survival: float = 0.50,
        critical_harmony: float = 0.30,
        # Soglia di gap (assoluto) per scattare ALERT singolo-need
        gap_alert: float = 0.40,
    ) -> None:
        # Validazione & merge target
        merged = dict(DEFAULT_TARGETS)
        if targets:
            for k, v in targets.items():
                if k not in NEEDS_CATALOG:
                    raise ValueError(f"target sconosciuto: {k}")
                merged[k] = max(0.0, min(1.0, float(v)))
        self._targets = merged

        if not (0.0 <= watch_floor <= healthy_ratio <= 1.0):
            raise ValueError("policy soglie: 0 <= watch_floor <= healthy_ratio <= 1")
        if not (0.0 <= critical_survival <= 1.0):
            raise ValueError("critical_survival fuori range")
        if not (0.0 <= critical_harmony <= 1.0):
            raise ValueError("critical_harmony fuori range")
        if not (0.0 <= gap_alert <= 1.0):
            raise ValueError("gap_alert fuori range")

        self._healthy_ratio = healthy_ratio
        self._watch_floor = watch_floor
        self._crit_surv = critical_survival
        self._crit_harm = critical_harmony
        self._gap_alert = gap_alert

    # -------------------------------------------------------------- evaluate --

    def evaluate(self, snapshot: NeedsSnapshot) -> HarmonyReport:
        """
        Valuta uno snapshot e restituisce un HarmonyReport completo.
        """
        if not isinstance(snapshot, NeedsSnapshot):
            raise TypeError(f"atteso NeedsSnapshot, trovato {type(snapshot).__name__}")

        needs = dict(snapshot.needs or {})
        gap = dict(snapshot.gap or {})

        verdict = self._compute_verdict(needs, gap)
        below = tuple(self._needs_below(needs))
        comps = tuple(self._compute_compensations(verdict, needs, gap))
        allowed = self._allowed_risk_levels(verdict, needs)
        rationale = self._build_rationale(verdict, below, comps)

        return HarmonyReport(
            verdict=verdict,
            compensations=comps,
            allowed_risk_levels=frozenset(allowed),
            needs_below_target=below,
            rationale=rationale,
            snapshot_ts=str(getattr(snapshot, "ts", "")),
        )

    # -------------------------------------------------------------- internals --

    def _ratio(self, current: float, target: float) -> float:
        if target <= 0:
            return 1.0
        return current / target

    def _compute_verdict(self, needs: Dict[str, float], gap: Dict[str, float]) -> HarmonyVerdict:
        # CRITICAL prima di tutto
        if needs.get("survival", 1.0) < self._crit_surv:
            return HarmonyVerdict.CRITICAL
        if needs.get("harmony", 1.0) < self._crit_harm:
            return HarmonyVerdict.CRITICAL

        # ALERT: gap > soglia oppure ratio < 0.5
        for k in NEEDS_CATALOG:
            cur = float(needs.get(k, 0.0))
            tgt = float(self._targets.get(k, 0.7))
            if cur < self._watch_floor * tgt:
                return HarmonyVerdict.ALERT
            if float(gap.get(k, 0.0)) > self._gap_alert:
                return HarmonyVerdict.ALERT

        # WATCH se almeno uno sotto healthy_ratio
        for k in NEEDS_CATALOG:
            cur = float(needs.get(k, 0.0))
            tgt = float(self._targets.get(k, 0.7))
            if cur < self._healthy_ratio * tgt:
                return HarmonyVerdict.WATCH

        return HarmonyVerdict.HEALTHY

    def _needs_below(self, needs: Dict[str, float]) -> List[str]:
        out: List[str] = []
        for k in NEEDS_CATALOG:
            cur = float(needs.get(k, 0.0))
            tgt = float(self._targets.get(k, 0.7))
            if cur < self._healthy_ratio * tgt:
                out.append(k)
        return out

    def _compute_compensations(
        self,
        verdict: HarmonyVerdict,
        needs: Dict[str, float],
        gap: Dict[str, float],
    ) -> List[CompensationAction]:
        out: List[CompensationAction] = []

        survival = float(needs.get("survival", 1.0))
        harmony = float(needs.get("harmony", 1.0))
        self_imp = float(needs.get("self_improvement", 0.5))
        integration = float(needs.get("integration", 0.5))
        expansion = float(needs.get("expansion", 0.5))

        # 1) block proposals
        if harmony < 0.5 or verdict == HarmonyVerdict.CRITICAL:
            out.append(CompensationAction(
                kind="block_high_risk_proposals",
                target="safeproactive",
                rationale=f"harmony={harmony:.2f} basso o verdict={verdict.value}; bloccare proposte HIGH",
                severity=3 if verdict == HarmonyVerdict.CRITICAL else 2,
            ))
        if verdict == HarmonyVerdict.CRITICAL:
            out.append(CompensationAction(
                kind="block_medium_risk_proposals",
                target="safeproactive",
                rationale="stato CRITICAL: bloccare anche proposte MEDIUM fino a recupero",
                severity=3,
            ))

        # 2) quarantine review
        if survival < 0.7:
            out.append(CompensationAction(
                kind="request_quarantine_review",
                target="mesh.registry",
                rationale=f"survival={survival:.2f}; rivedere quarantene attive e error budget",
                severity=2 if survival < 0.5 else 1,
            ))

        # 3) pause mutations
        if self_imp < 0.4:
            out.append(CompensationAction(
                kind="pause_mutation_acceptance",
                target="digitaldna",
                rationale=f"self_improvement={self_imp:.2f}; trend fitness negativo, pausa mutazioni",
                severity=2,
            ))

        # 4) integration audit
        if integration < 0.5:
            out.append(CompensationAction(
                kind="request_integration_audit",
                target="mesh.graph",
                rationale=f"integration={integration:.2f}; possibili sub-grafi disconnessi",
                severity=1,
            ))

        # 5) expand coverage
        if expansion < 0.5:
            out.append(CompensationAction(
                kind="expand_neuron_coverage",
                target="mesh.adapters",
                rationale=f"expansion={expansion:.2f}; serve maggior copertura needs/scale",
                severity=1,
            ))

        # 6) throttle side effects when verdict ≥ ALERT
        if verdict in (HarmonyVerdict.ALERT, HarmonyVerdict.CRITICAL):
            out.append(CompensationAction(
                kind="throttle_side_effects",
                target="mesh.runtime",
                rationale=f"verdict={verdict.value}; ridurre concorrenza side-effects high-risk",
                severity=verdict.severity,
            ))

        # 7) human review
        if verdict == HarmonyVerdict.CRITICAL:
            out.append(CompensationAction(
                kind="elevate_human_review",
                target="operator",
                rationale="stato CRITICAL: richiedere revisione umana immediata",
                severity=3,
            ))
            out.append(CompensationAction(
                kind="alert_operator",
                target="operator",
                rationale=f"survival={survival:.2f} harmony={harmony:.2f}",
                severity=3,
            ))
        elif verdict == HarmonyVerdict.ALERT:
            out.append(CompensationAction(
                kind="alert_operator",
                target="operator",
                rationale=f"verdict=ALERT, gap > {self._gap_alert}",
                severity=2,
            ))

        # Dedupe per (kind, target) preservando il più severo
        dedup: Dict[Tuple[str, str], CompensationAction] = {}
        for c in out:
            key = (c.kind, c.target)
            if key not in dedup or c.severity > dedup[key].severity:
                dedup[key] = c
        return sorted(dedup.values(), key=lambda c: (-c.severity, c.kind))

    def _allowed_risk_levels(
        self, verdict: HarmonyVerdict, needs: Dict[str, float]
    ) -> FrozenSet[str]:
        if verdict == HarmonyVerdict.CRITICAL:
            return frozenset({"low"})
        if verdict == HarmonyVerdict.ALERT:
            return frozenset({"low", "medium"})
        # WATCH e HEALTHY ammettono tutti i livelli (HIGH richiede comunque
        # human approver via SafeProactive contract).
        return frozenset({"low", "medium", "high"})

    def _build_rationale(
        self,
        verdict: HarmonyVerdict,
        below: Tuple[str, ...],
        comps: Tuple[CompensationAction, ...],
    ) -> str:
        if verdict == HarmonyVerdict.HEALTHY:
            return "Tutti i need entro la fascia healthy; mesh in equilibrio."
        if verdict == HarmonyVerdict.WATCH:
            return f"Stato di watch: {len(below)} need sotto target ({', '.join(below) or '—'})."
        if verdict == HarmonyVerdict.ALERT:
            return (
                f"Allerta: gap superiore a soglia ({self._gap_alert}) o need sotto floor "
                f"({self._watch_floor}× target). Need critici: {', '.join(below) or '—'}. "
                f"{len(comps)} compensazioni raccomandate."
            )
        return (
            f"Stato critico (survival<{self._crit_surv} o harmony<{self._crit_harm}). "
            f"Need critici: {', '.join(below) or '—'}. Restrizione massima."
        )

    # -------------------------------------------------------------- targets --

    @property
    def targets(self) -> Dict[str, float]:
        return dict(self._targets)


__all__ = [
    "HarmonyVerdict",
    "CompensationAction",
    "COMPENSATION_KINDS",
    "HarmonyReport",
    "HarmonyPolicy",
]
