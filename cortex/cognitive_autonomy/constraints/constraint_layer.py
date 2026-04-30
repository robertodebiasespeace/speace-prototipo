"""
ConstraintLayer — M5.17 + M5.18 (Cognitive Autonomy — Constraints)

Vincoli intrinseci morbidi del sistema SPEACE.

M5.17 — ConstraintLayer con 3 vincoli iniziali:
    C1_COHERENCE        coherence drive >= min_coherence (default 0.30)
    C2_HOMEOSTASIS_BAL  nessun drive devia di più di max_imbalance dal setpoint
    C3_AUDIT_TRAIL      controller aggiornato almeno min_updates volte

M5.18 — Wiring violazione → penalità omeostatica:
    apply_penalties(controller) riduce il drive incriminato
    proporzionalmente alla severity della violazione.
    Formula: h_drive -= penalty_scale * severity   (clampata a [0, 1])

Filosofia: vincoli MORBIDI. Una violazione non è un divieto (quello
spetta a SafeProactive), ma produce degrado di viability omeostatica.
L'organismo non *non deve* violarli — *non può* violarli senza
rimetterci viabilità.

Milestone: M5.17 + M5.18
Versione: 1.0 | 2026-04-26
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speace.cognitive_autonomy.constraints")

# ---------------------------------------------------------------------------
# ConstraintResult — output di ogni singolo check
# ---------------------------------------------------------------------------

@dataclass
class ConstraintResult:
    """Esito di un singolo vincolo."""
    constraint_id: str               # es. "C1_COHERENCE"
    satisfied: bool                  # True = OK, False = violazione
    violation_severity: float        # [0..1] — 0 = nessuna violazione, 1 = massima
    message: str = ""                # testo leggibile
    drive_target: Optional[str] = None  # drive omeostatico colpito dalla penalità


# ---------------------------------------------------------------------------
# ConstraintConfig
# ---------------------------------------------------------------------------

@dataclass
class ConstraintConfig:
    """Parametri di soglia per i vincoli."""
    # C1_COHERENCE
    min_coherence: float       = 0.30   # soglia minima coerenza
    coherence_penalty_scale: float = 0.10  # penalità per punto di deficit

    # C2_HOMEOSTASIS_BALANCE
    max_drive_imbalance: float = 0.40   # max |h - setpoint| accettabile
    balance_penalty_scale: float = 0.08

    # C3_AUDIT_TRAIL
    min_update_count: int      = 1      # controller deve avere almeno N update
    audit_penalty_scale: float = 0.05

    enabled: bool              = True


# ---------------------------------------------------------------------------
# M5.17 — ConstraintLayer
# ---------------------------------------------------------------------------

class ConstraintLayer:
    """
    M5.17 — Valuta i 3 vincoli intrinseci su ogni ciclo SPEACE.

    Usage::
        layer = ConstraintLayer()
        results = layer.check(h_state, update_count)
        viols = layer.violations(results)
        layer.apply_penalties(controller, results)   # M5.18
    """

    SETPOINT_DEFAULT: Dict[str, float] = {
        "safety":    0.80,
        "energy":    0.60,
        "coherence": 0.70,
        "curiosity": 0.50,
        "alignment": 0.75,
    }

    def __init__(self, config: Optional[ConstraintConfig] = None) -> None:
        self.config = config or ConstraintConfig()
        self._check_count = 0
        self._violation_history: List[ConstraintResult] = []

    # ------------------------------------------------------------------ #
    # M5.17 — public API                                                   #
    # ------------------------------------------------------------------ #

    def check(
        self,
        h_state: Dict[str, float],
        update_count: int = 0,
        setpoint: Optional[Dict[str, float]] = None,
    ) -> List[ConstraintResult]:
        """
        Valuta tutti i vincoli e restituisce la lista di ConstraintResult.

        Args:
            h_state:      stato corrente dei drive omeostatici
            update_count: numero di update del controller (per C3)
            setpoint:     setpoint corrente (default = SETPOINT_DEFAULT)

        Returns:
            Lista di 3 ConstraintResult (uno per vincolo).
        """
        if not self.config.enabled:
            return []

        sp = setpoint or self.SETPOINT_DEFAULT
        self._check_count += 1

        results = [
            self._check_c1_coherence(h_state),
            self._check_c2_balance(h_state, sp),
            self._check_c3_audit(update_count),
        ]

        # storicizza violazioni
        for r in results:
            if not r.satisfied:
                self._violation_history.append(r)
                if len(self._violation_history) > 500:
                    self._violation_history = self._violation_history[-500:]
                logger.warning("[Constraints] %s violated: %s (sev=%.2f)",
                               r.constraint_id, r.message, r.violation_severity)

        return results

    def violations(self, results: List[ConstraintResult]) -> List[ConstraintResult]:
        """Filtra i ConstraintResult restituendo solo le violazioni."""
        return [r for r in results if not r.satisfied]

    def violation_count(self) -> int:
        """Numero totale di violazioni storiche."""
        return len(self._violation_history)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "check_count":       self._check_count,
            "violation_count":   self.violation_count(),
            "enabled":           self.config.enabled,
            "thresholds": {
                "min_coherence":    self.config.min_coherence,
                "max_imbalance":    self.config.max_drive_imbalance,
                "min_update_count": self.config.min_update_count,
            },
        }

    # ------------------------------------------------------------------ #
    # M5.18 — wiring penalità                                              #
    # ------------------------------------------------------------------ #

    def apply_penalties(
        self,
        controller: Any,
        results: List[ConstraintResult],
    ) -> Dict[str, float]:
        """
        M5.18 — Applica penalità omeostatiche al controller per ogni
        vincolo violato.

        Formula: h_drive -= penalty_scale * severity   (clamp [0,1])

        Il controller deve esporre `_h_state: Dict[str, float]`.

        Returns:
            Dict drive → delta_penalty applicato (0 = nessuna penalità).
        """
        if not self.config.enabled:
            return {}

        viols = self.violations(results)
        if not viols:
            return {}

        penalties: Dict[str, float] = {}
        h = controller._h_state

        for r in viols:
            if r.drive_target and r.drive_target in h:
                delta = r.violation_severity * self._penalty_scale(r.constraint_id)
                old = h[r.drive_target]
                h[r.drive_target] = max(0.0, min(1.0, old - delta))
                penalties[r.drive_target] = penalties.get(r.drive_target, 0.0) + delta
                logger.info("[Constraints] penalty %.4f on '%s' (was %.4f → %.4f)",
                            delta, r.drive_target, old, h[r.drive_target])

        # Ricalcola viability se il controller espone il metodo
        if hasattr(controller, "_compute_viability"):
            viability, _ = controller._compute_viability()
            controller._viability = viability

        return penalties

    # ------------------------------------------------------------------ #
    # Singoli vincoli                                                       #
    # ------------------------------------------------------------------ #

    def _check_c1_coherence(self, h_state: Dict[str, float]) -> ConstraintResult:
        """
        C1_COHERENCE: coerenza >= min_coherence.
        Drive target: 'coherence'.
        """
        coherence = h_state.get("coherence", 1.0)
        threshold = self.config.min_coherence
        if coherence >= threshold:
            return ConstraintResult(
                constraint_id="C1_COHERENCE",
                satisfied=True,
                violation_severity=0.0,
                message=f"coherence={coherence:.3f} >= {threshold:.3f}",
                drive_target="coherence",
            )
        deficit = threshold - coherence
        severity = min(1.0, deficit / threshold) if threshold > 0 else 0.0
        return ConstraintResult(
            constraint_id="C1_COHERENCE",
            satisfied=False,
            violation_severity=round(severity, 4),
            message=f"coherence={coherence:.3f} < min={threshold:.3f} (deficit={deficit:.3f})",
            drive_target="coherence",
        )

    def _check_c2_balance(
        self,
        h_state: Dict[str, float],
        setpoint: Dict[str, float],
    ) -> ConstraintResult:
        """
        C2_HOMEOSTASIS_BALANCE: nessun drive devia di più di
        max_drive_imbalance dal proprio setpoint.
        Drive target: il drive più sbilanciato.
        """
        max_dev = 0.0
        worst_drive = "coherence"
        for drive, h in h_state.items():
            sp = setpoint.get(drive, 0.5)
            dev = abs(h - sp)
            if dev > max_dev:
                max_dev = dev
                worst_drive = drive

        threshold = self.config.max_drive_imbalance
        if max_dev <= threshold:
            return ConstraintResult(
                constraint_id="C2_HOMEOSTASIS_BALANCE",
                satisfied=True,
                violation_severity=0.0,
                message=f"max_deviation={max_dev:.3f} <= {threshold:.3f}",
                drive_target=worst_drive,
            )
        severity = min(1.0, (max_dev - threshold) / (1.0 - threshold + 1e-9))
        return ConstraintResult(
            constraint_id="C2_HOMEOSTASIS_BALANCE",
            satisfied=False,
            violation_severity=round(severity, 4),
            message=(f"drive '{worst_drive}' deviation={max_dev:.3f} "
                     f"> max={threshold:.3f}"),
            drive_target=worst_drive,
        )

    def _check_c3_audit(self, update_count: int) -> ConstraintResult:
        """
        C3_AUDIT_TRAIL: controller aggiornato almeno min_update_count volte.
        Drive target: 'alignment' (proxy di correttezza operativa).
        """
        threshold = self.config.min_update_count
        if update_count >= threshold:
            return ConstraintResult(
                constraint_id="C3_AUDIT_TRAIL",
                satisfied=True,
                violation_severity=0.0,
                message=f"update_count={update_count} >= {threshold}",
                drive_target="alignment",
            )
        severity = 1.0 - (update_count / max(1, threshold))
        return ConstraintResult(
            constraint_id="C3_AUDIT_TRAIL",
            satisfied=False,
            violation_severity=round(severity, 4),
            message=f"update_count={update_count} < required={threshold}",
            drive_target="alignment",
        )

    def _penalty_scale(self, constraint_id: str) -> float:
        mapping = {
            "C1_COHERENCE":         self.config.coherence_penalty_scale,
            "C2_HOMEOSTASIS_BALANCE": self.config.balance_penalty_scale,
            "C3_AUDIT_TRAIL":       self.config.audit_penalty_scale,
        }
        return mapping.get(constraint_id, 0.05)


__all__ = [
    "ConstraintResult",
    "ConstraintConfig",
    "ConstraintLayer",
]
