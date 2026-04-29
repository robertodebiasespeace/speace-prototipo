"""
cortex.cognitive_autonomy.plasticity.homeostatic_plasticity
=============================================================
M12.1 — HomeostaticPlasticityRegulator: synaptic scaling per SPEACE.

Principio biologico:
  La "Hebbian plasticity" (Long-Term Potentiation) ha un problema fondamentale:
  è instabile. Se ogni esperienza positiva rafforza le sinapsi, il sistema
  tende all'ipereccitabilità o alla saturazione (runaway potentiation).

  La soluzione biologica è la "homeostatic plasticity" o "synaptic scaling"
  (Turrigiano & Nelson, 2000):
    → Se un neurone è TROPPO attivo per troppo tempo:
      scala VERSO IL BASSO tutte le sue sinapsi proporzionalmente
    → Se un neurone è TROPPO silenzioso per troppo tempo:
      scala VERSO L'ALTO tutte le sue sinapsi proporzionalmente

  Questo meccanismo mantiene il neurone in una "finestra di attività ottimale"
  — né iper-eccitato né silenzioso — preservando la capacità di apprendere.

  "Neurons talk to each other, but they also listen to themselves.
   Synaptic scaling allows neurons to adjust their own excitability
   to maintain stable firing rates over long time scales."
   — Turrigiano, 2008

  Proprietà chiave:
    1. GLOBALE: agisce su TUTTE le sinapsi di un neurone, non solo le attive
    2. MOLTIPLICATIVA: scala per un fattore, non aggiunge/sottrae una costante
    3. LENTA: si attiva in ore/giorni, non in secondi (complemento a LTP)
    4. TARGET-DRIVEN: mira a un firing rate target, non a una soglia fissa

Analogia SPEACE:
  HomeostaticPlasticityRegulator monitora la `plasticity_rate` media del
  sistema nel tempo:
    - Se plasticity_rate è CRONICAMENTE ALTA → synaptic_scale_down (fattore < 1)
    - Se plasticity_rate è CRONICAMENTE BASSA → synaptic_scale_up (fattore > 1)
  Il fattore di scaling è applicato alla `learning_rate` in `epigenome.yaml`
  (e ai moduli di apprendimento che lo leggono).

M12.1 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, List, Optional, Tuple

logger = logging.getLogger("speace.plasticity.homeostatic")


# ─────────────────────────────────────────────────────────────────────────────
# ScalingDirection — direzione del synaptic scaling
# ─────────────────────────────────────────────────────────────────────────────

class ScalingDirection(str, Enum):
    STABLE     = "stable"      # attività nel range ottimale
    SCALE_DOWN = "scale_down"  # troppa attività → riduce sinapsi
    SCALE_UP   = "scale_up"    # troppa poca attività → amplifica sinapsi


# ─────────────────────────────────────────────────────────────────────────────
# HomeostaticConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HomeostaticConfig:
    """
    Configurazione del regolatore omeostatico della plasticità.

    Attributi:
        target_activity:      firing rate target (0.0–1.0). Default: 0.55
                              (biologico: ~55% del massimo firing rate)
        high_activity_thresh: soglia ALTA — se media > target+thresh → scale_down
        low_activity_thresh:  soglia BASSA — se media < target-thresh → scale_up
        history_window:       numero di campioni per la media mobile
        scale_factor_max:     fattore massimo di scaling (es. 1.30 = +30%)
        scale_factor_min:     fattore minimo di scaling (es. 0.70 = -30%)
        scaling_speed:        velocità con cui il fattore si sposta verso il target
                              (biologico: lento, 0.01–0.05 per ciclo)
        min_samples_to_act:   campioni minimi prima di applicare scaling
    """
    target_activity:      float = 0.55
    high_activity_thresh: float = 0.15   # > 0.70 → scale_down
    low_activity_thresh:  float = 0.20   # < 0.35 → scale_up
    history_window:       int   = 20     # finestra mobile
    scale_factor_max:     float = 1.30
    scale_factor_min:     float = 0.70
    scaling_speed:        float = 0.02
    min_samples_to_act:   int   = 5


# ─────────────────────────────────────────────────────────────────────────────
# HomeostaticState — snapshot del regolatore
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HomeostaticState:
    """
    Snapshot del regolatore omeostatico della plasticità.

    Attributi:
        scale_factor:      fattore di scaling corrente [0.70–1.30]
        mean_activity:     media mobile dell'attività di plasticità
        direction:         direzione corrente dello scaling
        consecutive_high:  campioni consecutivi sopra la soglia alta
        consecutive_low:   campioni consecutivi sotto la soglia bassa
        history_size:      dimensione della finestra mobile corrente
        scaled_learning_rate: learning_rate * scale_factor
        timestamp:         UNIX timestamp
    """
    scale_factor:         float
    mean_activity:        float
    direction:            ScalingDirection
    consecutive_high:     int
    consecutive_low:      int
    history_size:         int
    scaled_learning_rate: float
    timestamp:            float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"[HomeostaticPlasticity] "
            f"scale={self.scale_factor:.3f} "
            f"mean_activity={self.mean_activity:.3f} "
            f"direction={self.direction.value} "
            f"lr_scaled={self.scaled_learning_rate:.4f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# HomeostaticPlasticityRegulator
# ─────────────────────────────────────────────────────────────────────────────

class HomeostaticPlasticityRegulator:
    """
    M12.1 — Previene runaway potentiation tramite synaptic scaling.

    Monitora l'attività di plasticità nel tempo e applica un fattore
    di scaling moltiplicativo per mantenere il sistema in una zona
    di apprendimento ottimale.

    Uso:
        regulator = HomeostaticPlasticityRegulator()
        base_lr = 0.05  # learning_rate dall'epigenome

        # Ogni ciclo: registra l'attività corrente e ottieni lr scalata
        state = regulator.update(
            current_activity=0.85,  # es. numero neuroni attivi / totale
            base_learning_rate=base_lr,
        )
        effective_lr = state.scaled_learning_rate
        print(state.summary())

        # Se scale_down: il sistema sta imparando troppo velocemente
        # Se scale_up:   il sistema è quasi spento, stimolarlo
    """

    def __init__(self, config: Optional[HomeostaticConfig] = None) -> None:
        self._cfg           = config or HomeostaticConfig()
        self._history:      Deque[float]  = deque(maxlen=self._cfg.history_window)
        self._scale_factor: float         = 1.0
        self._consec_high:  int           = 0
        self._consec_low:   int           = 0
        self._tick_count:   int           = 0

    # ── API pubblica ──────────────────────────────────────────────────────────

    def update(
        self,
        current_activity:    float,
        base_learning_rate:  float = 0.05,
    ) -> HomeostaticState:
        """
        Registra l'attività corrente e aggiorna il fattore di scaling.

        Args:
            current_activity:   livello di attività plastica [0.0–1.0]
                                (es. plasticity_boost / max_boost, oppure
                                     n_synapses_updated / n_total)
            base_learning_rate: learning_rate base (dall'epigenome)

        Returns:
            HomeostaticState con scale_factor e scaled_learning_rate
        """
        self._tick_count += 1
        self._history.append(max(0.0, min(1.0, current_activity)))

        direction = ScalingDirection.STABLE

        if len(self._history) >= self._cfg.min_samples_to_act:
            mean_act = sum(self._history) / len(self._history)
            high_th  = self._cfg.target_activity + self._cfg.high_activity_thresh
            low_th   = self._cfg.target_activity - self._cfg.low_activity_thresh

            if mean_act > high_th:
                # Troppa attività → scale down
                self._consec_high += 1
                self._consec_low   = 0
                direction          = ScalingDirection.SCALE_DOWN
                self._scale_factor = max(
                    self._cfg.scale_factor_min,
                    self._scale_factor - self._cfg.scaling_speed
                )
            elif mean_act < low_th:
                # Troppa poca attività → scale up
                self._consec_low  += 1
                self._consec_high  = 0
                direction          = ScalingDirection.SCALE_UP
                self._scale_factor = min(
                    self._cfg.scale_factor_max,
                    self._scale_factor + self._cfg.scaling_speed
                )
            else:
                # Zona ottimale → rilassa il fattore verso 1.0
                self._consec_high = 0
                self._consec_low  = 0
                direction         = ScalingDirection.STABLE
                if self._scale_factor > 1.0:
                    self._scale_factor = max(1.0, self._scale_factor - self._cfg.scaling_speed * 0.5)
                elif self._scale_factor < 1.0:
                    self._scale_factor = min(1.0, self._scale_factor + self._cfg.scaling_speed * 0.5)
        else:
            mean_act = sum(self._history) / max(len(self._history), 1)

        scaled_lr = base_learning_rate * self._scale_factor

        state = HomeostaticState(
            scale_factor=round(self._scale_factor, 4),
            mean_activity=round(mean_act, 4),
            direction=direction,
            consecutive_high=self._consec_high,
            consecutive_low=self._consec_low,
            history_size=len(self._history),
            scaled_learning_rate=round(scaled_lr, 6),
        )

        if direction != ScalingDirection.STABLE:
            logger.debug("[HomeostaticPlasticity] %s", state.summary())

        return state

    def reset_scale(self) -> None:
        """Ripristina il fattore di scaling a 1.0 (es. dopo reset del sistema)."""
        self._scale_factor = 1.0
        self._history.clear()
        self._consec_high = 0
        self._consec_low  = 0

    @property
    def scale_factor(self) -> float:
        return self._scale_factor

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def activity_history(self) -> List[float]:
        return list(self._history)


__all__ = [
    "HomeostaticPlasticityRegulator",
    "HomeostaticConfig",
    "HomeostaticState",
    "ScalingDirection",
]
