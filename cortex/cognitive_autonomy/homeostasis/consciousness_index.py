"""
ConsciousnessIndex — M5.3 (Cognitive Autonomy)

Port da speaceorganismocibernetico/SPEACE_Cortex/adaptive_consciousness/consciousness_index.py
Esteso con:
  - integrazione BrainIntegration (BRN-001→015) come sorgente Φ
  - emergenza setpoint omeostatici (HomeostaticController aggiorna COHERENCE
    e ALIGNMENT dal C-index storico)
  - wiring bidirezionale con SystemReceptors.read_coherence()

Formula:
    C-index = α * Φ_norm + β * W_activation + γ * A_complexity

dove:
    Φ_norm     = sigmoid(0.5 * (phi - 1.0))      — Integrated Information (IIT)
    W_activation = occupancy Global Workspace     — GWT
    A_complexity  = metacognition + self-model    — Adaptive complexity

Setpoint emergenti (M5.3):
    coherence_setpoint = EMA(C-index, tau=20) — il sistema impara il proprio
    livello di riposo invece di usare un valore statico.

Milestone: M5.3 + M5.6
Versione: 1.1 | 2026-04-26
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.consciousness_index")

# ---------------------------------------------------------------------------
# M5.6 — Φ(t) 3-component structure
# ---------------------------------------------------------------------------

@dataclass
class PhiComponents:
    """
    M5.6 — Tre componenti di Φ(t) per il C-index.

    Φ_integration:      misura quanto le parti del sistema lavorano insieme
                        (coerenza globale, IIT classica). Proxy: mean pairwise
                        coherence tra i moduli BRN attivi.
    Φ_differentiation:  varietà degli stati interni (diversità cognitiva).
                        Proxy: entropia normalizzata degli activation levels.
    Φ_global_workspace: accesso al Global Workspace (broadcasting GWT).
                        Proxy: n_broadcast_items / GWT_capacity.

    Il Φ_composite usato nel C-index è una media pesata:
        Φ_composite = w_i*Φ_integration + w_d*Φ_differentiation + w_g*Φ_global_workspace
    con pesi default: 0.45 / 0.30 / 0.25 (integration è il più importante).
    """
    integration:      float = 0.5   # [0, 1]
    differentiation:  float = 0.5   # [0, 1]
    global_workspace: float = 0.5   # [0, 1]
    # pesi composizione
    w_integration:      float = 0.45
    w_differentiation:  float = 0.30
    w_global_workspace: float = 0.25

    def composite(self) -> float:
        """Φ composito pesato ∈ [0, 1]."""
        return float(np.clip(
            self.w_integration      * self.integration
            + self.w_differentiation  * self.differentiation
            + self.w_global_workspace * self.global_workspace,
            0.0, 1.0,
        ))

    @classmethod
    def from_scalar(cls, phi: float) -> "PhiComponents":
        """
        Fallback: scalare → PhiComponents omogenei.
        Usato quando il brain non espone i 3 sotto-componenti.
        """
        v = float(np.clip(phi, 0.0, 1.0))
        return cls(integration=v, differentiation=v, global_workspace=v)

    @classmethod
    def from_brain_state(cls, brain_state: dict) -> "PhiComponents":
        """
        M5.6 — Estrae i 3 componenti Φ dal brain_state di BrainIntegration.

        Mappatura:
          integration      ← consciousness_index (IIT proxy da BRN-010)
          differentiation  ← entropia degli attention_weights (se presenti),
                             altrimenti proxy da cycle_count variability
          global_workspace ← working_memory.total_items / WM_CAPACITY
        """
        WM_CAPACITY = 7.0

        phi_int  = float(brain_state.get("consciousness_index", 0.5))
        phi_int  = float(np.clip(phi_int, 0.0, 1.0))

        # Differenziazione: usa i layer di attention se disponibili,
        # altrimenti stima da dopamina (proxy varietà stati)
        attention_weights = brain_state.get("attention_weights", None)
        if attention_weights is not None:
            aw = np.array(attention_weights, dtype=float)
            aw = aw / (aw.sum() + 1e-12)
            entropy = float(-np.sum(aw * np.log(aw + 1e-12)))
            max_entropy = float(np.log(len(aw) + 1e-12))
            phi_diff = float(np.clip(entropy / (max_entropy + 1e-12), 0.0, 1.0))
        else:
            # Proxy: variabilità da dopamina e cicli
            da = float(brain_state.get("dopamine_level", 0.5))
            phi_diff = float(np.clip(0.5 + (da - 0.5) * 0.6, 0.0, 1.0))

        # Global workspace
        wm_items = brain_state.get("working_memory", {}).get("total_items", 0)
        phi_gws  = float(np.clip(wm_items / WM_CAPACITY, 0.0, 1.0))

        return cls(
            integration=phi_int,
            differentiation=phi_diff,
            global_workspace=phi_gws,
        )



# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

@dataclass
class CIndexComponents:
    """Componenti del C-index."""
    phi: float = 0.0            # Integrated Information (IIT)
    w_activation: float = 0.0  # Global Workspace activation (GWT)
    a_complexity: float = 0.0  # Adaptive Metacognition
    alpha: float = 0.35         # peso Φ    (SPEACE-aligned)
    beta:  float = 0.35         # peso W    (SPEACE-aligned)
    gamma: float = 0.30         # peso A    (SPEACE-aligned)


@dataclass
class CIndexResult:
    """Risultato di un calcolo C-index."""
    c_index: float
    phi_norm: float
    w_activation: float
    a_complexity: float
    phi_contribution: float
    w_contribution: float
    a_contribution: float
    trend: str = "unknown"
    stability: float = 1.0
    emergent_coherence_setpoint: Optional[float] = None
    # M5.6: 3-component Φ breakdown (None se non calcolato)
    phi_components: Optional["PhiComponents"] = None


# ---------------------------------------------------------------------------
# ConsciousnessIndex
# ---------------------------------------------------------------------------

class ConsciousnessIndex:
    """
    Calcolatore composito del C-index (Consciousness Index).

    Combina:
    - IIT: Integrated Information Theory (Φ)
    - GWT: Global Workspace Theory (W-activation)
    - Adaptive Metacognition (A-complexity)

    M5.3: feed automatico da BrainIntegration; setpoint emergenti via EMA.
    """

    def __init__(
        self,
        alpha: float = 0.35,
        beta:  float = 0.35,
        gamma: float = 0.30,
        ema_tau: int = 20,
        history_size: int = 200,
    ) -> None:
        total = alpha + beta + gamma
        if abs(total - 1.0) > 1e-4:
            alpha, beta, gamma = alpha/total, beta/total, gamma/total
        self.alpha = alpha
        self.beta  = beta
        self.gamma = gamma
        self.ema_tau = ema_tau

        self._history: deque[float] = deque(maxlen=history_size)
        self._component_history: deque[Dict] = deque(maxlen=history_size)
        self._emergent_setpoint: Optional[float] = None  # EMA del C-index
        self._ema: Optional[float] = None

        logger.info("ConsciousnessIndex init: α=%.2f β=%.2f γ=%.2f tau=%d",
                    alpha, beta, gamma, ema_tau)

    # ------------------------------------------------------------------ #
    # Core calculation
    # ------------------------------------------------------------------ #

    def _normalize_phi(self, phi: float) -> float:
        """Sigmoid normalization: phi→[0,1]."""
        return 1.0 / (1.0 + math.exp(-0.5 * (phi - 1.0)))

    def calculate(
        self,
        phi: float,
        w_activation: float,
        a_complexity: float,
    ) -> CIndexResult:
        """
        Calcola C-index da componenti esplicite.

        Args:
            phi:          IIT phi value (qualsiasi scala reale)
            w_activation: GWT workspace activation [0, 1]
            a_complexity: Adaptive metacognition complexity [0, 1]
        """
        phi_n   = self._normalize_phi(phi)
        phi_c   = self.alpha * phi_n
        w_c     = self.beta  * np.clip(w_activation, 0.0, 1.0)
        a_c     = self.gamma * np.clip(a_complexity, 0.0, 1.0)
        c_index = float(np.clip(phi_c + w_c + a_c, 0.0, 1.0))

        # Aggiorna history e EMA
        self._history.append(c_index)
        self._component_history.append(dict(phi=phi, w=w_activation, a=a_complexity))
        self._update_ema(c_index)

        # Trend
        trend, stability = self._analyze_trend(window=10)

        result = CIndexResult(
            c_index=c_index,
            phi_norm=phi_n,
            w_activation=float(w_activation),
            a_complexity=float(a_complexity),
            phi_contribution=phi_c,
            w_contribution=w_c,
            a_contribution=a_c,
            trend=trend,
            stability=stability,
            emergent_coherence_setpoint=self._emergent_setpoint,
        )
        return result

    def calculate_from_components(self, comp: CIndexComponents) -> CIndexResult:
        return self.calculate(comp.phi, comp.w_activation, comp.a_complexity)

    # ------------------------------------------------------------------ #
    # M5.6: 3-component Φ
    # ------------------------------------------------------------------ #

    def calculate_from_phi3(
        self,
        phi_components: "PhiComponents",
        w_activation: float,
        a_complexity: float,
    ) -> CIndexResult:
        """
        M5.6 — Calcola C-index usando PhiComponents (Φ a 3 componenti).

        Φ_composite = w_i*Φ_int + w_d*Φ_diff + w_g*Φ_gws
        C = α * normalize(Φ_composite) + β * W + γ * A
        """
        phi_composite = phi_components.composite()
        result = self.calculate(
            phi=phi_composite * 2.0,   # rimappa [0,1]→[0,2] per sigmoid centrata su 1
            w_activation=w_activation,
            a_complexity=a_complexity,
        )
        # Inietta il breakdown 3-component nel result
        result.phi_components = phi_components
        return result

    # ------------------------------------------------------------------ #
    # M5.3+M5.6: feed da BrainIntegration
    # ------------------------------------------------------------------ #

    def calculate_from_brain(self, brain_state: Dict[str, Any]) -> CIndexResult:
        """
        M5.3+M5.6 — Calcola C-index da BrainIntegration.get_system_state().

        M5.6: estrae PhiComponents a 3 componenti dal brain_state.
        Fallback automatico a scalare se il brain non espone attention_weights.

        Mappatura:
            PhiComponents   ← from_brain_state() (M5.6)
            w_activation    ← working_memory.total_items / WM_CAPACITY
            a_complexity    ← dopamine_level (proxy self-regulation)
        """
        WM_CAPACITY = 7.0
        phi_comp = PhiComponents.from_brain_state(brain_state)
        wm_items = brain_state.get("working_memory", {}).get("total_items", 0)
        w_act    = float(np.clip(wm_items / WM_CAPACITY, 0.0, 1.0))
        da       = float(np.clip(brain_state.get("dopamine_level", 0.5), 0.0, 1.0))
        return self.calculate_from_phi3(phi_comp, w_activation=w_act, a_complexity=da)

    # ------------------------------------------------------------------ #
    # M5.3: setpoint emergenti
    # ------------------------------------------------------------------ #

    def _update_ema(self, c_index: float) -> None:
        """EMA del C-index → setpoint emergente per COHERENCE."""
        alpha_ema = 2.0 / (self.ema_tau + 1)
        if self._ema is None:
            self._ema = c_index
        else:
            self._ema = alpha_ema * c_index + (1 - alpha_ema) * self._ema
        # Il setpoint emergente è l'EMA con un margine ottimistico +0.05
        self._emergent_setpoint = float(np.clip(self._ema + 0.05, 0.1, 0.95))

    @property
    def emergent_coherence_setpoint(self) -> Optional[float]:
        """Setpoint emergente per il drive COHERENCE (EMA C-index + 0.05)."""
        return self._emergent_setpoint

    def apply_emergent_setpoints(self, controller_config) -> Dict[str, float]:
        """
        Aggiorna h_setpoint_static del HomeostaticController con valori emergenti.
        Solo COHERENCE viene aggiornato (gli altri restano statici fino a M5.6+).

        Returns: dict dei setpoint aggiornati.
        """
        updated = dict(controller_config.h_setpoint_static)
        if self._emergent_setpoint is not None:
            updated["coherence"] = self._emergent_setpoint
        return updated

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #

    def _analyze_trend(self, window: int = 10) -> Tuple[str, float]:
        h = list(self._history)[-window:]
        if len(h) < 2:
            return "unknown", 1.0
        diff = np.diff(h)
        direction = float(np.mean(diff))
        stability = float(max(0.0, 1.0 - np.std(h)))
        if direction > 0.02:
            trend = "increasing"
        elif direction < -0.02:
            trend = "decreasing"
        else:
            trend = "stable"
        return trend, stability

    def get_stats(self) -> Dict[str, Any]:
        if not self._history:
            return {"count": 0, "mean": 0.0, "max": 0.0, "min": 0.0, "last": 0.0}
        h = list(self._history)
        return {
            "count": len(h),
            "mean":  round(float(np.mean(h)), 4),
            "max":   round(float(np.max(h)), 4),
            "min":   round(float(np.min(h)), 4),
            "std":   round(float(np.std(h)), 4),
            "last":  round(h[-1], 4),
            "emergent_setpoint": self._emergent_setpoint,
        }

    def reset(self) -> None:
        self._history.clear()
        self._component_history.clear()
        self._ema = None
        self._emergent_setpoint = None

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (f"ConsciousnessIndex(last={stats['last']:.3f}, "
                f"mean={stats['mean']:.3f}, "
                f"emergent_sp={self._emergent_setpoint})")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class CIndexCalculator:
    @staticmethod
    def create_speace_aligned() -> ConsciousnessIndex:
        return ConsciousnessIndex(alpha=0.35, beta=0.35, gamma=0.30)

    @staticmethod
    def create_balanced() -> ConsciousnessIndex:
        return ConsciousnessIndex(alpha=0.40, beta=0.35, gamma=0.25)

    @staticmethod
    def create_phi_focused() -> ConsciousnessIndex:
        return ConsciousnessIndex(alpha=0.50, beta=0.30, gamma=0.20)


def calculate_speace_c_index(
    phi: float, w_activation: float, a_complexity: float
) -> Tuple[float, Dict[str, float]]:
    """Helper: calcola C-index SPEACE-aligned con breakdown componenti."""
    calc = CIndexCalculator.create_speace_aligned()
    r = calc.calculate(phi, w_activation, a_complexity)
    return r.c_index, {
        "phi_contribution": r.phi_contribution,
        "w_contribution":   r.w_contribution,
        "a_contribution":   r.a_contribution,
    }


__all__ = [
    "PhiComponents", "CIndexComponents", "CIndexResult", "ConsciousnessIndex",
    "CIndexCalculator", "calculate_speace_c_index",
]
