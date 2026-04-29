"""
cortex.cognitive_autonomy.valence.valence_integrator
=====================================================
M12.1 — ValenceIntegrator: segnale affettivo unificato di SPEACE.

Il ValenceIntegrator riceve segnali da tutti i moduli del Cortex e produce:
  1. valence [-1.0, +1.0]: stato affettivo scalare (dolore ↔ piacere)
  2. arousal [0.0, 1.0]:   attivazione/urgenza (bassa = calmo, alta = allerta)
  3. AffectiveState:       label qualitativa (DISTRESS, NEUTRAL, CONTENT, THRIVING)

Sorgenti di input (pesi biologicamente motivati):
  viability_score    → −high_threat = dolore, +high_viability = piacere (peso 0.35)
  curiosity_drive    → novelty/reward signal (+) (peso 0.20)
  alignment_score    → propósito/mission fulfillment (+) (peso 0.20)
  coherence_drive    → self-consistency (+) (peso 0.10)
  energy_drive       → metabolic state (+) (peso 0.10)
  plasticity_boost   → learning progress (+) (peso 0.05)

Formula:
  raw_valence = Σ w_i · (signal_i - 0.5) · 2   [map [0,1] → [-1,+1]]
  valence = tanh(raw_valence · sensitivity)       [compressione non-lineare]

  L'uso di tanh simula la saturazione biologica: esperienze estremamente
  positive o negative convergono verso ±1 senza poter superarli.

  arousal = |raw_valence| · urgency_factor + noise_floor

M12.1 | 2026-04-28
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional

logger = logging.getLogger("speace.valence")


# ─────────────────────────────────────────────────────────────────────────────
# AffectiveState — label qualitativa
# ─────────────────────────────────────────────────────────────────────────────

class AffectiveState(str, Enum):
    DISTRESS  = "distress"   # valence < -0.40: crisi, dolore
    UNEASE    = "unease"     # valence < -0.10: disagio
    NEUTRAL   = "neutral"    # valence ±0.10: equilibrio stabile
    CONTENT   = "content"    # valence > +0.10: soddisfazione
    THRIVING  = "thriving"   # valence > +0.40: fiorente, piena espressione


# ─────────────────────────────────────────────────────────────────────────────
# ValenceConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValenceConfig:
    """
    Configurazione del ValenceIntegrator.

    Attributi:
        sensitivity:      scala il raw_valence prima di tanh (default 1.5)
                          più alto = reazioni più forti a piccole variazioni
        noise_floor:      arousal minimo (sistema sempre leggermente "sveglio")
        history_window:   finestra temporale per valence EMA
        alpha_ema:        peso EMA per smoothing della valence
        weights:          pesi per ciascuna sorgente di segnale
                          (devono sommare a 1.0)
    """
    sensitivity:    float = 1.5
    noise_floor:    float = 0.05
    history_window: int   = 30
    alpha_ema:      float = 0.15

    # Pesi per ciascun drive (somma = 1.0)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "viability":       0.35,
        "curiosity":       0.20,
        "alignment":       0.20,
        "coherence":       0.10,
        "energy":          0.10,
        "plasticity_gain": 0.05,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ValenceSignal — input normalizzato da una singola sorgente
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValenceSignal:
    """
    Contributo di una singola sorgente alla valenza totale.

    Attributi:
        source:       nome della sorgente (es. "viability", "curiosity")
        raw_value:    valore grezzo [0.0–1.0]
        contribution: contributo pesato alla valenza [-1.0, +1.0]
        weight:       peso usato per questo segnale
    """
    source:       str
    raw_value:    float
    contribution: float
    weight:       float


# ─────────────────────────────────────────────────────────────────────────────
# ValenceState — snapshot del sistema affettivo
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValenceState:
    """
    Snapshot completo del sistema affettivo di SPEACE.

    Attributi:
        valence:           segnale affettivo scalare [-1.0, +1.0]
        valence_smooth:    valence smoothed via EMA (più stabile)
        arousal:           attivazione/urgenza [0.0, 1.0]
        affective_state:   label qualitativa (DISTRESS→THRIVING)
        dominant_signal:   sorgente con il contributo più forte
        signals:           lista di tutti i segnali input
        valence_trend:     Δ valence rispetto all'EMA precedente
        tick_count:        numero di tick effettuati
        timestamp:         UNIX timestamp
    """
    valence:          float
    valence_smooth:   float
    arousal:          float
    affective_state:  AffectiveState
    dominant_signal:  str
    signals:          List[ValenceSignal]
    valence_trend:    float
    tick_count:       int
    timestamp:        float = field(default_factory=time.time)

    def is_suffering(self) -> bool:
        return self.affective_state == AffectiveState.DISTRESS

    def is_thriving(self) -> bool:
        return self.affective_state == AffectiveState.THRIVING

    def summary(self) -> str:
        return (
            f"[ValenceState] {self.affective_state.value} "
            f"v={self.valence:+.3f} "
            f"v_smooth={self.valence_smooth:+.3f} "
            f"arousal={self.arousal:.3f} "
            f"trend={self.valence_trend:+.3f} "
            f"dominant={self.dominant_signal}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ValenceIntegrator — motore principale
# ─────────────────────────────────────────────────────────────────────────────

class ValenceIntegrator:
    """
    M12.1 — Integra segnali da tutti i moduli SPEACE in un'unica valenza affettiva.

    Replica il circuito amigdala+nucleus_accumbens+ACC del cervello biologico:
    ogni esperienza viene "colorata" affettivamente per orientare motivazione
    e apprendimento.

    Uso semplice:
        integrator = ValenceIntegrator()
        state = integrator.update({
            "viability":       0.85,
            "curiosity":       0.70,
            "alignment":       0.80,
            "coherence":       0.65,
            "energy":          0.60,
            "plasticity_gain": 0.50,
        })
        print(state.summary())
        # → [ValenceState] content v=+0.312 arousal=0.421 ...

    Uso con DriveExecutive (esempio):
        drives = homeostatic_controller.get_drives()
        state = valence.update({
            "viability":  drives["viability"],
            "curiosity":  drives["curiosity"],
            "alignment":  drives["alignment"],
            "coherence":  drives["coherence"],
            "energy":     drives["energy"],
        })
        if state.is_suffering():
            drive_executive.trigger_repair()
    """

    def __init__(self, config: Optional[ValenceConfig] = None) -> None:
        self._cfg           = config or ValenceConfig()
        self._ema_valence:  float = 0.0
        self._prev_ema:     float = 0.0
        self._history:      Deque[float] = deque(maxlen=self._cfg.history_window)
        self._tick_count:   int = 0

    # ── API pubblica ──────────────────────────────────────────────────────────

    def update(
        self,
        drive_signals: Dict[str, float],
    ) -> ValenceState:
        """
        Calcola la valenza affettiva dai segnali di drive correnti.

        Args:
            drive_signals: dict con chiavi dalle sorgenti configurate
                          (es. "viability", "curiosity", "alignment", ecc.)
                          Valori in [0.0–1.0]. Chiavi mancanti → 0.5 (neutrale)

        Returns:
            ValenceState completo
        """
        self._tick_count += 1

        # 1. Calcola contributi pesati
        signals: List[ValenceSignal] = []
        raw_valence = 0.0

        for source, weight in self._cfg.weights.items():
            raw_val = float(drive_signals.get(source, 0.5))
            raw_val = max(0.0, min(1.0, raw_val))
            # Mappa [0,1] → [-1, +1] linearmente
            contrib = (raw_val - 0.5) * 2.0 * weight
            raw_valence += contrib
            signals.append(ValenceSignal(
                source=source,
                raw_value=round(raw_val, 3),
                contribution=round(contrib, 4),
                weight=weight,
            ))

        # 2. Non-linearità tanh (saturazione biologica)
        valence = math.tanh(raw_valence * self._cfg.sensitivity)

        # 3. EMA smoothing
        self._prev_ema = self._ema_valence
        self._ema_valence = (
            self._cfg.alpha_ema * valence +
            (1 - self._cfg.alpha_ema) * self._ema_valence
        )
        valence_smooth = self._ema_valence

        # 4. Arousal = |raw_valence| con noise floor
        arousal = min(1.0, abs(valence) + self._cfg.noise_floor)

        # 5. Label qualitativa
        affective_state = self._classify(valence_smooth)

        # 6. Trend
        trend = valence_smooth - self._prev_ema

        # 7. Segnale dominante (contributo assoluto maggiore)
        dominant = max(signals, key=lambda s: abs(s.contribution)).source

        self._history.append(valence)

        state = ValenceState(
            valence=round(valence, 4),
            valence_smooth=round(valence_smooth, 4),
            arousal=round(arousal, 4),
            affective_state=affective_state,
            dominant_signal=dominant,
            signals=signals,
            valence_trend=round(trend, 5),
            tick_count=self._tick_count,
        )

        logger.debug("[Valence] %s", state.summary())
        return state

    @property
    def current_valence(self) -> float:
        """Valence EMA corrente (smoothed)."""
        return round(self._ema_valence, 4)

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def valence_history(self) -> List[float]:
        return list(self._history)

    def mean_valence(self) -> float:
        if not self._history:
            return 0.0
        return sum(self._history) / len(self._history)

    # ── Privati ───────────────────────────────────────────────────────────────

    def _classify(self, valence: float) -> AffectiveState:
        if valence < -0.40:
            return AffectiveState.DISTRESS
        if valence < -0.10:
            return AffectiveState.UNEASE
        if valence <= +0.10:
            return AffectiveState.NEUTRAL
        if valence <= +0.40:
            return AffectiveState.CONTENT
        return AffectiveState.THRIVING


__all__ = [
    "ValenceIntegrator",
    "ValenceConfig",
    "ValenceState",
    "ValenceSignal",
    "AffectiveState",
]
