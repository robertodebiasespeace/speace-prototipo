"""
cortex.cognitive_autonomy.predictive.predictive_processor
==========================================================
M10.1 — Implementazione del Predictive Coding per SPEACE.

Architettura:

  Input reale (segnali dal mondo / dai receptor)
       ↓
  PredictionModel.predict()  ← genera previsione dello stato atteso
       ↓
  PredictionError.compute()  ← calcola |reale - atteso|
       ↓
  Classificazione errore: SUPPRESSED / LOW / MEDIUM / HIGH / CRITICAL
       ↓
  SUPPRESSED → scartato (già previsto, nessun aggiornamento)
  LOW        → aggiorna solo il modello interno (apprendimento silenzioso)
  MEDIUM     → passa al Cortex con priorità normale
  HIGH       → passa al Cortex con priorità alta
  CRITICAL   → attiva immediatamente HomeostaticController + alert

  Dopo ogni ciclo: PredictionModel aggiorna i pesi in base all'errore
  (online learning, simile alla plasticità sinaptica Hebbiana).

Metriche chiave:
  suppression_rate: % segnali non trasmessi (obiettivo: > 60% in stato stabile)
  mean_prediction_error: errore medio (basso = modello ben calibrato)
  surprise_index: quanto spesso emergono HIGH/CRITICAL errors

M10.1 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.predictive")


# ─────────────────────────────────────────────────────────────────────────────
# PredictionErrorLevel — classificazione dell'errore
# ─────────────────────────────────────────────────────────────────────────────

class PredictionErrorLevel(str, Enum):
    SUPPRESSED = "suppressed"   # |error| < low_threshold  → segnale non trasmesso
    LOW        = "low"          # |error| < mid_threshold  → solo apprendimento
    MEDIUM     = "medium"       # |error| < high_threshold → Cortex, priorità normale
    HIGH       = "high"         # |error| < crit_threshold → Cortex, priorità alta
    CRITICAL   = "critical"     # |error| ≥ crit_threshold → alert immediato


# ─────────────────────────────────────────────────────────────────────────────
# PredictionError — risultato dell'elaborazione predittiva
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PredictionError:
    """
    Risultato del confronto previsione vs. realtà per una singola metrica.

    Attributi:
        key:        nome della metrica (es. "viability", "curiosity")
        predicted:  valore previsto dal PredictionModel
        actual:     valore reale osservato
        error:      |actual - predicted| (errore assoluto)
        signed_error: actual - predicted (errore con segno — indica direzione)
        level:      classificazione dell'errore
        timestamp:  timestamp UNIX
        should_transmit: True se il segnale deve essere trasmesso al Cortex
    """
    key:           str
    predicted:     float
    actual:        float
    error:         float
    signed_error:  float
    level:         PredictionErrorLevel
    timestamp:     float
    should_transmit: bool

    def to_dict(self) -> dict:
        return {
            "key":           self.key,
            "predicted":     round(self.predicted, 4),
            "actual":        round(self.actual, 4),
            "error":         round(self.error, 4),
            "signed_error":  round(self.signed_error, 4),
            "level":         self.level.value,
            "should_transmit": self.should_transmit,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PredictionModel — modello interno dello stato atteso
# ─────────────────────────────────────────────────────────────────────────────

class PredictionModel:
    """
    M10.1 — Modello predittivo interno di SPEACE.

    Mantiene una media mobile esponenziale (EMA) per ogni metrica osservata.
    La previsione per il ciclo successivo è l'EMA corrente + trend stimato.

    Aggiornamento online (Hebbian-like):
      EMA_new = alpha * actual + (1 - alpha) * EMA_old
      trend   = beta * (actual - prev_actual) + (1 - beta) * trend_old

    Parametri:
        alpha:          peso dell'osservazione corrente nell'EMA (default 0.15)
                        Basso alpha → previsioni stabili ma lente ad adattarsi
                        Alto alpha → previsioni reattive ma rumorose
        beta:           peso del trend (default 0.10)
        window:         finestra storica per calcolo varianza (default 30)
    """

    def __init__(
        self,
        alpha: float = 0.15,
        beta:  float = 0.10,
        window: int  = 30,
    ) -> None:
        self.alpha  = alpha
        self.beta   = beta
        self.window = window

        self._ema:     Dict[str, float] = {}   # media mobile per metrica
        self._trend:   Dict[str, float] = {}   # trend stimato
        self._prev:    Dict[str, float] = {}   # valore precedente
        self._history: Dict[str, Deque[float]] = {}  # storia per varianza
        self._n_updates = 0

    def predict(self, key: str) -> Optional[float]:
        """
        Genera la previsione per la prossima osservazione della metrica `key`.
        Ritorna None se la metrica non è ancora stata osservata.

        Previsione = EMA + trend * 0.5
        (trend smorzato: il cervello non extrapola a piena velocità)
        """
        if key not in self._ema:
            return None
        trend_component = self._trend.get(key, 0.0) * 0.5
        prediction = self._ema[key] + trend_component
        return float(np.clip(prediction, 0.0, 1.0))

    def update(self, key: str, actual: float) -> None:
        """
        Aggiorna il modello con un'osservazione reale.
        Questo è l'equivalente del "synaptic update" dopo un prediction error.
        """
        actual = float(np.clip(actual, 0.0, 1.0))

        if key not in self._ema:
            # Prima osservazione: inizializza
            self._ema[key]   = actual
            self._trend[key] = 0.0
            self._prev[key]  = actual
            self._history[key] = deque(maxlen=self.window)
        else:
            # Aggiorna trend
            delta = actual - self._prev[key]
            self._trend[key] = (self.beta * delta +
                                (1.0 - self.beta) * self._trend[key])
            # Aggiorna EMA
            self._ema[key] = (self.alpha * actual +
                              (1.0 - self.alpha) * self._ema[key])
            self._prev[key] = actual

        self._history[key].append(actual)
        self._n_updates += 1

    def get_variance(self, key: str) -> float:
        """Varianza storica della metrica — misura di stabilità."""
        hist = self._history.get(key)
        if not hist or len(hist) < 3:
            return 0.5  # incertezza massima se pochi dati
        return float(np.var(list(hist)))

    def is_calibrated(self, key: str, min_observations: int = 5) -> bool:
        """True se il modello ha abbastanza osservazioni per questa metrica."""
        hist = self._history.get(key)
        return hist is not None and len(hist) >= min_observations

    def get_status(self) -> dict:
        return {
            "tracked_metrics": list(self._ema.keys()),
            "n_updates":       self._n_updates,
            "ema":             {k: round(v, 4) for k, v in self._ema.items()},
            "trends":          {k: round(v, 4) for k, v in self._trend.items()},
        }


# ─────────────────────────────────────────────────────────────────────────────
# PredictiveProcessor — filtro predittivo in ingresso al Cortex
# ─────────────────────────────────────────────────────────────────────────────

class PredictiveProcessor:
    """
    M10.1 — Filtro predittivo principale di SPEACE.

    Riceve osservazioni dallo stato del sistema (receptor readings,
    homeostasis output, world_model snapshot) e decide per ognuna:
      - SUPPRESSED: già prevista, non trasmettere (risparmio computazionale)
      - LOW: aggiorna modello silenziosamente
      - MEDIUM/HIGH/CRITICAL: trasmetti al Cortex con priorità appropriata

    Soglie di errore (configurabili):
      suppressed: |error| < 0.03
      low:        |error| < 0.08
      medium:     |error| < 0.15
      high:       |error| < 0.30
      critical:   |error| ≥ 0.30

    Uso:
        proc = PredictiveProcessor()
        errors = proc.process({"viability": 0.72, "curiosity": 0.65, ...})
        to_transmit = [e for e in errors if e.should_transmit]

        # In DEEP_SLEEP o IDLE: soglie più rigide (meno segnali passano)
        proc.set_sensitivity(WakeState.IDLE)
    """

    # Soglie di errore per stato AWAKE (normali)
    THRESHOLDS_AWAKE = {
        "suppressed": 0.03,
        "low":        0.08,
        "medium":     0.15,
        "high":       0.30,
    }
    # In IDLE: soglie più alte → meno segnali passano (risparmio energetico)
    THRESHOLDS_IDLE = {
        "suppressed": 0.06,
        "low":        0.12,
        "medium":     0.20,
        "high":       0.35,
    }
    # In DEEP_SLEEP: solo errori enormi passano (solo safety)
    THRESHOLDS_SLEEP = {
        "suppressed": 0.15,
        "low":        0.20,
        "medium":     0.30,
        "high":       0.45,
    }

    def __init__(
        self,
        model:  Optional[PredictionModel] = None,
        alpha:  float = 0.15,
        beta:   float = 0.10,
    ) -> None:
        self.model = model or PredictionModel(alpha=alpha, beta=beta)
        self._thresholds = self.THRESHOLDS_AWAKE.copy()

        # Metriche
        self._total_processed    = 0
        self._total_suppressed   = 0
        self._total_transmitted  = 0
        self._error_history: Deque[float] = deque(maxlen=200)

    # ── Interfaccia principale ────────────────────────────────────────────────

    def process(
        self,
        observations: Dict[str, float],
        force_transmit: bool = False,
    ) -> List[PredictionError]:
        """
        Processa un batch di osservazioni.

        Args:
            observations:   dict {metrica → valore_reale [0,1]}
            force_transmit: se True, trasmette tutto (bypass filtro — es. in repair mode)

        Returns:
            Lista di PredictionError, uno per ogni metrica osservata.
        """
        results = []
        ts = time.time()

        for key, actual in observations.items():
            actual = float(np.clip(actual, 0.0, 1.0))

            # Previsione del modello
            predicted = self.model.predict(key)
            if predicted is None or not self.model.is_calibrated(key):
                # Prima osservazione: passa sempre (non abbiamo previsione)
                self.model.update(key, actual)
                pe = PredictionError(
                    key=key, predicted=actual, actual=actual,
                    error=0.0, signed_error=0.0,
                    level=PredictionErrorLevel.MEDIUM,
                    timestamp=ts, should_transmit=True,
                )
                results.append(pe)
                self._total_transmitted += 1
                self._total_processed += 1
                continue

            # Calcola errore
            signed_err = actual - predicted
            abs_err    = abs(signed_err)
            self._error_history.append(abs_err)

            # Classifica e decide
            level = self._classify(abs_err)
            transmit = force_transmit or level not in (
                PredictionErrorLevel.SUPPRESSED, PredictionErrorLevel.LOW
            )

            pe = PredictionError(
                key=key, predicted=predicted, actual=actual,
                error=round(abs_err, 5), signed_error=round(signed_err, 5),
                level=level, timestamp=ts, should_transmit=transmit,
            )
            results.append(pe)

            # Aggiorna modello (apprendimento continuo)
            self.model.update(key, actual)

            # Metriche
            self._total_processed += 1
            if transmit:
                self._total_transmitted += 1
            else:
                self._total_suppressed += 1

            if level in (PredictionErrorLevel.HIGH, PredictionErrorLevel.CRITICAL):
                logger.info(
                    "[PredictiveProcessor] %s error=%s: predicted=%.3f actual=%.3f (%s)",
                    key, level.value, predicted, actual, level.value
                )

        return results

    def process_single(self, key: str, actual: float) -> PredictionError:
        """Processa una singola metrica. Convenienza per testing."""
        results = self.process({key: actual})
        return results[0]

    # ── Adattamento sensibilità in base allo stato sonno-veglia ──────────────

    def set_sensitivity(self, wake_state_value: str) -> None:
        """
        Adatta le soglie in base allo stato sonno-veglia.
        In IDLE/DEEP_SLEEP: soglie più alte → meno segnali trasmessi.
        """
        if wake_state_value == "awake":
            self._thresholds = self.THRESHOLDS_AWAKE.copy()
        elif wake_state_value == "idle":
            self._thresholds = self.THRESHOLDS_IDLE.copy()
        elif wake_state_value == "deep_sleep":
            self._thresholds = self.THRESHOLDS_SLEEP.copy()

    # ── Logica di classificazione ────────────────────────────────────────────

    def _classify(self, abs_error: float) -> PredictionErrorLevel:
        t = self._thresholds
        if abs_error < t["suppressed"]:
            return PredictionErrorLevel.SUPPRESSED
        elif abs_error < t["low"]:
            return PredictionErrorLevel.LOW
        elif abs_error < t["medium"]:
            return PredictionErrorLevel.MEDIUM
        elif abs_error < t["high"]:
            return PredictionErrorLevel.HIGH
        else:
            return PredictionErrorLevel.CRITICAL

    # ── Metriche ─────────────────────────────────────────────────────────────

    @property
    def suppression_rate(self) -> float:
        """Frazione di segnali non trasmessi (obiettivo: > 0.60 in stato stabile)."""
        if self._total_processed == 0:
            return 0.0
        return self._total_suppressed / self._total_processed

    @property
    def mean_prediction_error(self) -> float:
        """Errore medio di previsione (basso = modello ben calibrato)."""
        if not self._error_history:
            return 0.5
        return float(np.mean(self._error_history))

    @property
    def surprise_index(self) -> float:
        """
        Indice di sorpresa: quanto spesso emergono errori HIGH/CRITICAL.
        Alto surprise_index = sistema in transizione o sotto stress.
        """
        if not self._error_history:
            return 0.0
        high_threshold = self._thresholds["high"]
        high_count = sum(1 for e in self._error_history if e >= high_threshold)
        return high_count / len(self._error_history)

    def get_metrics(self) -> dict:
        return {
            "total_processed":   self._total_processed,
            "total_suppressed":  self._total_suppressed,
            "total_transmitted": self._total_transmitted,
            "suppression_rate":  round(self.suppression_rate, 4),
            "mean_error":        round(self.mean_prediction_error, 4),
            "surprise_index":    round(self.surprise_index, 4),
            "model":             self.model.get_status(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# BehavioralPredictor — predizione comportamentale di alto livello (M13.2)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BehavioralPrediction:
    """
    Predizione del prossimo comportamento/azione di SPEACE.

    Attributi:
        likely_next_action: etichetta azione prevista (es. "recall", "explore", "repair")
        expected_energy:    domanda energetica attesa [0, 1]
        confidence:         confidenza nella predizione [0, 1]
        based_on_n:         numero di osservazioni usate
        history_pattern:    descrizione del pattern rilevato
    """
    likely_next_action: str
    expected_energy:    float
    confidence:         float
    based_on_n:         int
    history_pattern:    str = ""

    def to_dict(self) -> dict:
        return {
            "likely_next_action": self.likely_next_action,
            "expected_energy":    round(self.expected_energy, 3),
            "confidence":         round(self.confidence, 3),
            "based_on_n":         self.based_on_n,
            "history_pattern":    self.history_pattern,
        }


class BehavioralPredictor:
    """
    M13.2 — Predizione comportamentale di alto livello per SPEACE.

    Opera sopra il PredictiveProcessor (segnali) per produrre predizioni
    su quale azione/comportamento SPEACE eseguirà probabilmente nel prossimo
    ciclo, basandosi sulla storia recente degli input e dello stato biologico.

    Ispirato a Grok SPEACE v4.2 PredictiveEngine, ma integrato con
    BehavioralState e DriveExecutive di SPEACE-prototipo.

    Uso:
        predictor = BehavioralPredictor()
        pred = predictor.predict_next_state(
            current_input="analizza ecosistema marino",
            bio_state={"energy": 0.8, "curiosity": 0.7, "viability": 0.9}
        )
        # → BehavioralPrediction(likely_next_action="explore", confidence=0.72, ...)

        # Dopo il ciclo:
        error = predictor.get_prediction_error(actual_action="explore")
        predictor.update_history({"input": current_input, "action": "explore"})
    """

    # Parole-chiave per classificazione azione
    _RECALL_KEYWORDS = frozenset([
        "ricorda", "memoria", "codice", "remember", "recall",
        "passato", "storia", "precedente",
    ])
    _REPAIR_KEYWORDS = frozenset([
        "errore", "problema", "fix", "ripara", "broken",
        "fallito", "critico", "emergenza",
    ])
    _EXPLORE_KEYWORDS = frozenset([
        "esplora", "scopri", "nuovo", "creativo", "analizza",
        "studia", "ricerca", "innovativo", "diverge",
    ])
    _PLAN_KEYWORDS = frozenset([
        "pianifica", "obiettivo", "goal", "step", "strategia",
        "roadmap", "progetta", "organizza",
    ])

    def __init__(self, memory_size: int = 20) -> None:
        self._memory_size = memory_size
        self._history: Deque[Dict[str, Any]] = deque(maxlen=memory_size)
        self._last_prediction: Optional[BehavioralPrediction] = None
        self._n_predictions = 0
        self._n_errors = 0
        self._cumulative_error = 0.0

    def predict_next_state(
        self,
        current_input: str,
        bio_state: Dict[str, float],
    ) -> BehavioralPrediction:
        """
        Predice il prossimo stato comportamentale.

        Args:
            current_input: input testuale corrente (query, task, messaggio)
            bio_state:     stato biologico corrente {drive → valore [0,1]}
                           Chiavi attese: energy, curiosity, viability, coherence, alignment

        Returns:
            BehavioralPrediction con azione prevista e confidenza
        """
        self._n_predictions += 1
        n_hist = len(self._history)

        # Livelli drive (con default neutro)
        energy    = float(bio_state.get("energy",    0.5))
        curiosity = float(bio_state.get("curiosity", 0.5))
        viability = float(bio_state.get("viability", 0.8))

        # Pattern matching input corrente
        inp_lower = current_input.lower()
        action_from_input = self._classify_input(inp_lower)

        # Pattern matching storia recente (ultimi 3 input)
        if n_hist >= 3:
            recent_inputs = [
                h.get("input", "") for h in list(self._history)[-3:]
            ]
            history_action = self._classify_pattern(recent_inputs)
        else:
            history_action = None

        # Calcolo domanda energetica attesa
        expected_energy = round(energy * 0.9, 3)

        # Regole comportamentali basate su drive
        if viability < 0.4:
            final_action   = "repair"
            confidence     = 0.88
            pattern_desc   = f"viability={viability:.2f} < 0.4 → self_repair_mode"
        elif curiosity > 0.7 and action_from_input == "explore":
            final_action   = "explore"
            confidence     = 0.80
            pattern_desc   = f"curiosity={curiosity:.2f} > 0.7 + input→explore"
        elif action_from_input is not None:
            final_action   = action_from_input
            confidence     = 0.70 if n_hist >= 3 else 0.50
            pattern_desc   = f"input pattern → {action_from_input}"
        elif history_action is not None:
            final_action   = history_action
            confidence     = 0.60
            pattern_desc   = f"history pattern → {history_action}"
        else:
            final_action   = "general"
            confidence     = 0.40
            pattern_desc   = "no dominant pattern"

        # Boost confidenza se storia conferma
        if history_action == final_action and n_hist >= 3:
            confidence = min(0.95, confidence + 0.10)

        pred = BehavioralPrediction(
            likely_next_action = final_action,
            expected_energy    = expected_energy,
            confidence         = round(confidence, 3),
            based_on_n         = n_hist,
            history_pattern    = pattern_desc,
        )
        self._last_prediction = pred

        logger.debug(
            "[BehavioralPredictor] predicted=%s confidence=%.2f pattern='%s'",
            final_action, confidence, pattern_desc,
        )
        return pred

    def get_prediction_error(self, actual_action: str) -> float:
        """
        Calcola l'errore della predizione precedente rispetto all'azione reale.

        Returns:
            0.0 se predizione corretta, 1.0 se completamente errata.
            Valore intermedio se azione semanticamente parzialmente correlata.
        """
        if self._last_prediction is None:
            return 0.5   # nessuna predizione precedente
        predicted = self._last_prediction.likely_next_action
        if predicted == actual_action:
            error = 0.0
        elif self._are_related(predicted, actual_action):
            error = 0.3
        else:
            error = 1.0

        self._n_errors += 1
        self._cumulative_error += error
        return error

    def update_history(self, state: Dict[str, Any]) -> None:
        """
        Aggiorna la storia con lo stato del ciclo appena completato.

        Args:
            state: dict con chiavi "input" e opzionalmente "action", "output"
        """
        self._history.append({
            "timestamp":  time.time(),
            **state,
        })

    @property
    def mean_error(self) -> float:
        """Errore medio di predizione comportamentale."""
        if self._n_errors == 0:
            return 0.5
        return round(self._cumulative_error / self._n_errors, 4)

    @property
    def n_predictions(self) -> int:
        return self._n_predictions

    def get_status(self) -> dict:
        return {
            "n_predictions":    self._n_predictions,
            "n_history":        len(self._history),
            "mean_error":       self.mean_error,
            "last_prediction":  self._last_prediction.to_dict() if self._last_prediction else None,
        }

    # ── Privati ───────────────────────────────────────────────────────────────

    def _classify_input(self, inp: str) -> Optional[str]:
        words = set(inp.split())
        if words & self._REPAIR_KEYWORDS:
            return "repair"
        if words & self._RECALL_KEYWORDS:
            return "recall"
        if words & self._EXPLORE_KEYWORDS:
            return "explore"
        if words & self._PLAN_KEYWORDS:
            return "plan"
        return None

    def _classify_pattern(self, recent_inputs: List[str]) -> Optional[str]:
        """Classifica il pattern degli ultimi N input."""
        counts: Dict[str, int] = {}
        for inp in recent_inputs:
            action = self._classify_input(inp.lower())
            if action:
                counts[action] = counts.get(action, 0) + 1
        if not counts:
            return None
        return max(counts, key=lambda k: counts[k])

    @staticmethod
    def _are_related(a: str, b: str) -> bool:
        """True se le due azioni sono semanticamente correlate."""
        related_groups = [
            {"explore", "plan"},
            {"recall", "repair"},
        ]
        for group in related_groups:
            if a in group and b in group:
                return True
        return False


__all__ = [
    "PredictionModel",
    "PredictionError",
    "PredictionErrorLevel",
    "PredictiveProcessor",
    "BehavioralPredictor",
    "BehavioralPrediction",
]
