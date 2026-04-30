"""
HomeostaticController — M5.1 + M5.2 (Cognitive Autonomy)

Implementa il controllore omeostatico del decimo comparto Cortex.

Equazione fondamentale (per ogni drive d):
    dh_d/dt = -k_restore * (h_d - setpoint_d) + k_input * (receptor_d - h_d)

dove:
    h_d          = stato corrente del drive (valore in [0, 1])
    setpoint_d   = valore target (configurabile via epigenome)
    receptor_d   = lettura esterna dal sistema reale (M5.2)
    k_restore    = forza di ripristino verso setpoint (default 0.1)
    k_input      = peso dei receptor reading (default 0.3)

In forma discreta (heartbeat dt):
    h_d(t+dt) = h_d(t) + dt * dh_d/dt  (clamp [0,1])

Viability score:
    Per ogni drive: score_d = max(0, 1 - max(0, |h_d - sp_d| - tol) / (1 - tol))
    viability = mean(score_d)  ∈ [0, 1]

M5.2 — Receptors (lettura stato sistema):
    energy      ← psutil (1 - CPU%, 1 - RAM%)
    safety      ← SafeProactive veto rate (inverso)
    curiosity   ← NeedsDriver.observe().needs["self_improvement"]
    coherence   ← Φ placeholder (0.5 fino a M5.6)
    alignment   ← epigenome.tina_alignment.alignment_score

Milestone: M5.1 (dh/dt + setpoint statici) + M5.2 (receptor wiring)
Versione: 1.0 | 2026-04-26
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger("speace.cognitive_autonomy.homeostasis")

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class Drive(str, Enum):
    """Drive omeostatici fondamentali."""
    ENERGY = "energy"
    SAFETY = "safety"
    CURIOSITY = "curiosity"
    COHERENCE = "coherence"
    ALIGNMENT = "alignment"


@dataclass
class HomeostasisConfig:
    """Configurazione omeostasi — letta da epigenome.cognitive_autonomy.homeostasis."""

    enabled: bool = True   # GK-01: attivato (era False scaffold). 2026-04-27
    heartbeat_s: float = 30.0
    k_restore: float = 0.10   # forza ripristino verso setpoint
    k_input: float = 0.30     # peso receptor reading
    h_setpoint_static: Dict[str, float] = field(
        default_factory=lambda: {
            Drive.ENERGY.value:    0.75,
            Drive.SAFETY.value:    0.95,
            Drive.CURIOSITY.value: 0.50,
            Drive.COHERENCE.value: 0.70,
            Drive.ALIGNMENT.value: 0.80,
        }
    )
    tolerance: float = 0.15

    @classmethod
    def from_epigenome(cls, epigenome: Mapping[str, Any]) -> "HomeostasisConfig":
        node = (epigenome or {}).get("cognitive_autonomy", {}).get("homeostasis", {})
        inst = cls()
        return cls(
            enabled=bool(node.get("enabled", inst.enabled)),
            heartbeat_s=float(node.get("heartbeat_s", inst.heartbeat_s)),
            k_restore=float(node.get("k_restore", inst.k_restore)),
            k_input=float(node.get("k_input", inst.k_input)),
            h_setpoint_static=dict(
                node.get("h_setpoint_static", inst.h_setpoint_static)
            ),
            tolerance=float(node.get("tolerance", inst.tolerance)),
        )


# ---------------------------------------------------------------------------
# M5.2 — Receptor subsystem
# ---------------------------------------------------------------------------


class SystemReceptors:
    """
    M5.2 — Legge lo stato corrente dei drive dal sistema reale.

    Ogni metodo ritorna un float in [0, 1].
    Fallback sicuro: ritorna il setpoint statico se la lettura non è disponibile.
    """

    def __init__(self, config: HomeostasisConfig) -> None:
        self._cfg = config
        self._sp = config.h_setpoint_static

    # --- ENERGY ---
    def read_energy(self) -> float:
        """Energia = disponibilità compute. 1 - saturazione CPU/RAM."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None) / 100.0
            ram = psutil.virtual_memory().percent / 100.0
            # Energia = complemento medio di saturazione risorse
            return float(max(0.0, min(1.0, 1.0 - (cpu * 0.4 + ram * 0.6))))
        except Exception:
            return self._sp.get(Drive.ENERGY.value, 0.75)

    # --- SAFETY ---
    def read_safety(self) -> float:
        """Safety = tasso di approvazione SafeProactive (1 = tutto approvato)."""
        try:
            proposals_path = Path("safeproactive") / "PROPOSALS.md"
            if not proposals_path.exists():
                return self._sp.get(Drive.SAFETY.value, 0.95)
            text = proposals_path.read_text(errors="replace")
            approved = text.count("APPROVATA") + text.count("AUTO-APPROVE")
            rejected = text.count("RIFIUTATA") + text.count("REJECTED")
            total = approved + rejected
            if total == 0:
                return self._sp.get(Drive.SAFETY.value, 0.95)
            return float(max(0.0, min(1.0, approved / total)))
        except Exception:
            return self._sp.get(Drive.SAFETY.value, 0.95)

    # --- CURIOSITY ---
    def read_curiosity(self) -> float:
        """Curiosity = self_improvement need da NeedsDriver."""
        try:
            from cortex.mesh.needs_driver import NeedsDriver
            snap = NeedsDriver().observe()
            needs = getattr(snap, "needs", {})
            val = needs.get("self_improvement", None)
            if val is not None:
                return float(max(0.0, min(1.0, val)))
        except Exception:
            pass
        return self._sp.get(Drive.CURIOSITY.value, 0.50)

    # --- COHERENCE ---
    def read_coherence(self) -> float:
        """
        Coherence = C-index (M5.3).
        Legge il C-index da BrainIntegration se disponibile,
        altrimenti usa mesh_state.jsonl come proxy.
        """
        # Priorità 1: BrainIntegration (M5.3)
        try:
            from cortex.brain.brain_integration import create_brain
            from cortex.cognitive_autonomy.homeostasis.consciousness_index import CIndexCalculator
            # Usa singleton leggero: solo lettura stato, non crea istanza pesante
            # Accede al brain_state via SPEACE-main se già inizializzato
            import sys
            speace_brain = getattr(sys.modules.get("__main__"), "brain", None)
            if speace_brain is not None:
                state = speace_brain.get_system_state()
                calc = CIndexCalculator.create_speace_aligned()
                r = calc.calculate_from_brain(state)
                return float(max(0.0, min(1.0, r.c_index)))
        except Exception:
            pass
        # Priorità 2: mesh_state.jsonl fitness_delta proxy
        try:
            mesh_path = Path("safeproactive") / "state" / "mesh_state.jsonl"
            if mesh_path.exists():
                import json
                lines = mesh_path.read_text(errors="replace").strip().splitlines()
                if lines:
                    last = json.loads(lines[-1])
                    fd = last.get("fitness_delta", None)
                    if fd is not None:
                        return float(max(0.0, min(1.0, 0.5 + float(fd) * 0.2)))
        except Exception:
            pass
        return self._sp.get(Drive.COHERENCE.value, 0.70)

    # --- ALIGNMENT ---
    def read_alignment(self) -> float:
        """Alignment = TINA alignment score da epigenome."""
        try:
            import yaml
            ep_path = Path("digitaldna") / "epigenome.yaml"
            if ep_path.exists():
                data = yaml.safe_load(ep_path.read_text())
                score = (data or {}).get("tina_alignment", {}).get("alignment_score", None)
                if score is not None:
                    return float(max(0.0, min(1.0, score)))
        except Exception:
            pass
        return self._sp.get(Drive.ALIGNMENT.value, 0.80)

    def read_all(self) -> Dict[str, float]:
        """Legge tutti i drive e ritorna un dict drive→float."""
        return {
            Drive.ENERGY.value:    self.read_energy(),
            Drive.SAFETY.value:    self.read_safety(),
            Drive.CURIOSITY.value: self.read_curiosity(),
            Drive.COHERENCE.value: self.read_coherence(),
            Drive.ALIGNMENT.value: self.read_alignment(),
        }


# ---------------------------------------------------------------------------
# HomeostaticController — M5.1 implementation
# ---------------------------------------------------------------------------


@dataclass
class HomeostaticController:
    """
    Controller omeostatico del decimo comparto Cortex (M5.1 + M5.2).

    Gestisce 5 drive fondamentali con equazione dh/dt e receptor wiring.
    """

    config: HomeostasisConfig = field(default_factory=HomeostasisConfig)
    _h_state: Dict[str, float] = field(default_factory=dict, init=False)
    _dh_dt: Dict[str, float] = field(default_factory=dict, init=False)
    _last_update_ts: float = field(default_factory=time.time, init=False)
    _viability: float = field(default=1.0, init=False)
    _update_count: int = field(default=0, init=False)
    _alert_history: List[str] = field(default_factory=list, init=False)
    _receptors: Optional[SystemReceptors] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._h_state = dict(self.config.h_setpoint_static)
        self._dh_dt = {d: 0.0 for d in self._h_state}
        self._receptors = SystemReceptors(self.config)

    # ------------------------------------------------------------------ #
    # Core update — dh/dt equation
    # ------------------------------------------------------------------ #

    def update(
        self,
        receptor_readings: Optional[Dict[str, float]] = None,
        dt: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna stato omeostatico con equazione dh/dt.

        Args:
            receptor_readings: misure esterne dei drive (M5.2). Se None
                               vengono lette da SystemReceptors.
            dt: passo temporale in secondi. Se None usa tempo reale
                dall'ultimo update.

        Returns:
            dict con h_state, h_setpoint, dh_dt, viability_score, alerts.
        """
        # --- Stub path: disabled ---
        if not self.config.enabled:
            return {
                "h_state":        dict(self._h_state),
                "h_setpoint":     dict(self.config.h_setpoint_static),
                "dh_dt":          {d: 0.0 for d in self._h_state},
                "viability_score": 1.0,
                "alerts":         [],
                "scaffold":       True,
                "enabled":        False,
            }

        # --- dt reale ---
        now = time.time()
        if dt is None:
            dt = min(now - self._last_update_ts, 10.0)  # max 10s per stabilità
        self._last_update_ts = now

        # --- Lettura receptors (M5.2) ---
        if receptor_readings is None:
            receptor_readings = self._receptors.read_all()

        # --- Equazione dh/dt per ogni drive ---
        k_r = self.config.k_restore
        k_i = self.config.k_input
        sp = self.config.h_setpoint_static
        new_state: Dict[str, float] = {}
        new_dhdt: Dict[str, float] = {}

        for drive in self._h_state:
            h = self._h_state[drive]
            s = sp.get(drive, 0.5)
            r = receptor_readings.get(drive, h)  # fallback: stato corrente

            # dh/dt = -k_restore * (h - setpoint) + k_input * (receptor - h)
            dhdt = -k_r * (h - s) + k_i * (r - h)
            new_dhdt[drive] = dhdt

            # Integrazione Eulero: h(t+dt) = h(t) + dt * dh/dt
            h_new = h + dt * dhdt
            new_state[drive] = max(0.0, min(1.0, h_new))

        self._h_state = new_state
        self._dh_dt = new_dhdt

        # --- Viability score ---
        viability, drive_scores = self._compute_viability()
        self._viability = viability

        # --- Alerts ---
        alerts = self._check_alerts(drive_scores)
        self._alert_history.extend(alerts)
        if len(self._alert_history) > 200:
            self._alert_history = self._alert_history[-200:]

        self._update_count += 1

        result = {
            "h_state":        dict(self._h_state),
            "h_setpoint":     dict(sp),
            "dh_dt":          dict(self._dh_dt),
            "receptor_readings": dict(receptor_readings),
            "viability_score": viability,
            "drive_scores":   drive_scores,
            "alerts":         alerts,
            "dt_applied":     dt,
            "update_count":   self._update_count,
            "enabled":        True,
            "scaffold":       False,
        }
        if alerts:
            logger.warning("[Homeostasis] alerts: %s", alerts)
        return result

    # ------------------------------------------------------------------ #
    # Viability computation
    # ------------------------------------------------------------------ #

    def _compute_viability(self) -> Tuple[float, Dict[str, float]]:
        """
        Calcola viability_score ∈ [0, 1].

        Per ogni drive:
            excess = max(0, |h - setpoint| - tolerance)
            score_d = max(0, 1 - excess / (1 - tolerance))
        viability = mean(score_d)
        """
        sp = self.config.h_setpoint_static
        tol = self.config.tolerance
        scores: Dict[str, float] = {}
        for drive, h in self._h_state.items():
            s = sp.get(drive, 0.5)
            excess = max(0.0, abs(h - s) - tol)
            denom = max(1e-9, 1.0 - tol)
            score = max(0.0, 1.0 - excess / denom)
            scores[drive] = round(score, 4)
        viability = sum(scores.values()) / max(1, len(scores))
        return round(viability, 4), scores

    # ------------------------------------------------------------------ #
    # Alerts
    # ------------------------------------------------------------------ #

    def _check_alerts(self, drive_scores: Dict[str, float]) -> List[str]:
        alerts: List[str] = []
        tol = self.config.tolerance
        sp = self.config.h_setpoint_static
        for drive, h in self._h_state.items():
            s = sp.get(drive, 0.5)
            dev = abs(h - s)
            if dev > tol * 2:
                alerts.append(
                    f"CRITICAL:{drive} h={h:.3f} sp={s:.3f} dev={dev:.3f}"
                )
            elif dev > tol:
                alerts.append(
                    f"WATCH:{drive} h={h:.3f} sp={s:.3f} dev={dev:.3f}"
                )
        return alerts

    # ------------------------------------------------------------------ #
    # Penalize (M5.18 stub)
    # ------------------------------------------------------------------ #

    def penalize(self, amount: float, reason: str = "") -> None:
        """
        Riduce viability_score indirettamente perturbando il drive SAFETY.
        Implementazione piena in M5.18 (constraint wiring).
        """
        if not self.config.enabled:
            return
        current = self._h_state.get(Drive.SAFETY.value, 0.95)
        perturbed = max(0.0, current - abs(amount))
        self._h_state[Drive.SAFETY.value] = perturbed
        self._viability, _ = self._compute_viability()
        logger.info("[Homeostasis] penalize(%.3f): %s → safety=%.3f",
                    amount, reason, perturbed)

    # ------------------------------------------------------------------ #
    # Snapshot / restore
    # ------------------------------------------------------------------ #

    def snapshot(self) -> Dict[str, Any]:
        return {
            "h_state":      dict(self._h_state),
            "dh_dt":        dict(self._dh_dt),
            "viability":    self._viability,
            "update_count": self._update_count,
            "version":      "M5.1",
        }

    def restore(self, snap: Dict[str, Any]) -> None:
        self._h_state = dict(snap.get("h_state", self._h_state))
        self._dh_dt = dict(snap.get("dh_dt", self._dh_dt))
        self._viability = float(snap.get("viability", 1.0))
        self._update_count = int(snap.get("update_count", 0))
        logger.info("[Homeostasis] restored from snapshot (v=%s)", snap.get("version"))


    def persist_cognitive_state(
        self,
        path: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        M5.4 — Persiste lo stato cognitivo corrente in JSON per il dashboard.

        Scrive su `safeproactive/state/cognitive_state.json`:
            viability_score, h_state, alerts, update_count, ts.

        Il dashboard legge questo file per mostrare il KPI viability.
        Chiamare dopo ogni update() con un flag (es. ogni 5 aggiornamenti).
        """
        import datetime
        state_path = Path(path or "safeproactive/state/cognitive_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {
            "viability_score":  self.viability_score,
            "h_state":          dict(self._h_state),
            "h_setpoint":       dict(self.config.h_setpoint_static),
            "dh_dt":            dict(self._dh_dt),
            "update_count":     self._update_count,
            "enabled":          self.config.enabled,
            "ts":               datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        if extra:
            payload.update(extra)
        try:
            tmp = state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(state_path)
        except OSError as e:
            logger.warning("[Homeostasis] persist_cognitive_state failed: %s", e)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def viability_score(self) -> float:
        """Viability corrente [0, 1]. 1.0 se disabilitato."""
        return 1.0 if not self.config.enabled else self._viability

    @property
    def h_state(self) -> Dict[str, float]:
        return dict(self._h_state)

    @property
    def dh_dt(self) -> Dict[str, float]:
        return dict(self._dh_dt)

    def __repr__(self) -> str:
        return (
            f"HomeostaticController(enabled={self.config.enabled}, "
            f"viability={self.viability_score:.3f}, "
            f"updates={self._update_count})"
        )


__all__ = ["Drive", "HomeostasisConfig", "HomeostaticController", "SystemReceptors"]
