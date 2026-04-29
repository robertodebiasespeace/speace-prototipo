"""
cortex.cognitive_autonomy.criticality.criticality_controller
=============================================================
M13.0 — CriticalityController: Self-Organized Criticality (SOC).

Il cervello biologico opera vicino al punto critico tra ordine e caos —
una zona di metastabilità che massimizza la capacità di trasmissione
dell'informazione, la sensibilità agli stimoli e la flessibilità cognitiva.
(Beggs & Plenz 2003, Science; Shew & Plenz 2013, Neuroscientist)

Concetto centrale:
  order_score = coherence * 0.6 + (1 - novelty) * 0.4

  OVER-ORDERED (order_score > 0.75): sistema troppo rigido, prevedibile.
    → boost novelty, abbassa temperatura generazione
  OVER-CHAOTIC (order_score < 0.35): sistema incoerente, instabile.
    → boost coherence, alza struttura
  CRITICAL (0.35 ≤ order_score ≤ 0.75): zona ottimale — metastabilità.
    → mantieni, piccoli aggiustamenti per restare nella zona

Wiring SPEACE:
  SMFOI_v3.py step 6 (Outcome Evaluation) →
    CriticalityController.assess(emergence, coherence, novelty) →
    CriticalityState con zone + modulation_suggestion →
    DriveExecutive legge modulation per mutation_gate e exploration_bonus

M13.0 | 2026-04-29
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, List, Optional

logger = logging.getLogger("speace.criticality")


# ─────────────────────────────────────────────────────────────────────────────
# CriticalityZone — classificazione della zona corrente
# ─────────────────────────────────────────────────────────────────────────────

class CriticalityZone(str, Enum):
    OVER_ORDERED = "OVER-ORDERED"   # rigido, ripetitivo — troppo ordine
    CRITICAL     = "CRITICAL"       # zona ottimale — metastabilità
    OVER_CHAOTIC = "OVER-CHAOTIC"   # incoerente, instabile — troppo caos


# ─────────────────────────────────────────────────────────────────────────────
# CriticalityConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CriticalityConfig:
    """
    Configurazione del CriticalityController.

    Attributi:
        order_threshold:    soglia superiore ordine (> → OVER-ORDERED)
        chaos_threshold:    soglia inferiore ordine (< → OVER-CHAOTIC)
        coherence_weight:   peso della coherence nel calcolo order_score
        novelty_weight:     peso della (1-novelty) nel calcolo order_score
        temperature_boost:  Δtemperature suggerito in OVER-ORDERED
        novelty_boost:      Δexploration_bonus suggerito in OVER-ORDERED
        temperature_cut:    Δtemperature suggerito in OVER-CHAOTIC (negativo)
        coherence_boost:    Δcoherence_boost suggerito in OVER-CHAOTIC
        history_window:     finestra di tick per media mobile order_score
        alpha_ema:          peso EMA per smoothing order_score
    """
    order_threshold:  float = 0.75
    chaos_threshold:  float = 0.35
    coherence_weight: float = 0.60
    novelty_weight:   float = 0.40

    # Suggerimenti modulazione
    temperature_boost:  float = +0.15
    novelty_boost:      float = +0.20
    temperature_cut:    float = -0.15
    coherence_boost:    float = +0.20

    history_window: int   = 20
    alpha_ema:      float = 0.20


# ─────────────────────────────────────────────────────────────────────────────
# ModulationSuggestion — suggerimento di regolazione
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModulationSuggestion:
    """
    Suggerimento di modulazione emesso dal CriticalityController.

    Attributi:
        temperature_delta:   Δtemperatura LLM (+boost curiosità, -boost struttura)
        exploration_bonus:   Δexploration_bonus DriveExecutive
        coherence_boost:     Δpriorità di coerenza
        mutation_gate_open:  se True: zona critica → mutazioni consentite
        maintain:            True se zona già ottimale (no intervento)
    """
    temperature_delta:  float = 0.0
    exploration_bonus:  float = 0.0
    coherence_boost:    float = 0.0
    mutation_gate_open: bool  = True
    maintain:           bool  = False

    def summary(self) -> str:
        if self.maintain:
            return "maintain (in critical zone)"
        parts = []
        if self.temperature_delta != 0.0:
            parts.append(f"temp_delta={self.temperature_delta:+.2f}")
        if self.exploration_bonus != 0.0:
            parts.append(f"exploration={self.exploration_bonus:+.2f}")
        if self.coherence_boost != 0.0:
            parts.append(f"coherence={self.coherence_boost:+.2f}")
        parts.append(f"mutation_gate={'OPEN' if self.mutation_gate_open else 'CLOSED'}")
        return " | ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# CriticalityState — snapshot del sistema critico
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CriticalityState:
    """
    Snapshot completo dello stato di criticità di SPEACE.

    Attributi:
        zone:              zona corrente (OVER-ORDERED / CRITICAL / OVER-CHAOTIC)
        order_score:       score ordine grezzo [0, 1]
        order_score_ema:   score ordine smoothed via EMA
        coherence:         coherence input
        novelty:           novelty input
        emergence:         emergence input
        in_target_zone:    True se nella zona critica ottimale
        recommendation:    stringa descrittiva azione raccomandata
        modulation:        ModulationSuggestion da applicare
        tick_count:        numero di tick effettuati
        timestamp:         UNIX timestamp
    """
    zone:             CriticalityZone
    order_score:      float
    order_score_ema:  float
    coherence:        float
    novelty:          float
    emergence:        float
    in_target_zone:   bool
    recommendation:   str
    modulation:       ModulationSuggestion
    tick_count:       int
    timestamp:        float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"[Criticality] {self.zone.value} "
            f"order={self.order_score:.3f} "
            f"ema={self.order_score_ema:.3f} "
            f"coherence={self.coherence:.3f} "
            f"novelty={self.novelty:.3f} "
            f"→ {self.modulation.summary()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CriticalityController — motore principale
# ─────────────────────────────────────────────────────────────────────────────

class CriticalityController:
    """
    M13.0 — Monitora e regola la criticità di SPEACE.

    Mantiene il sistema nella zona ottimale di metastabilità tra ordine e caos,
    dove la capacità cognitiva è massima (sensibilità, flessibilità, trasmissione).

    Uso semplice:
        ctrl = CriticalityController()
        state = ctrl.assess(emergence=0.72, coherence=0.85, novelty=0.20)
        print(state.summary())
        # → [Criticality] OVER-ORDERED order=0.748 ... → temp_delta=+0.15 | exploration=+0.20

    Wiring con DriveExecutive:
        crit = ctrl.assess(emergence, coherence, novelty)
        if not crit.modulation.mutation_gate_open:
            drive_executive.behavioral_state.mutation_gate_open = False
        drive_executive.behavioral_state.exploration_bonus += crit.modulation.exploration_bonus
    """

    def __init__(self, config: Optional[CriticalityConfig] = None) -> None:
        self._cfg        = config or CriticalityConfig()
        self._ema:       float = 0.5          # valore iniziale neutro
        self._history:   Deque[float] = deque(maxlen=self._cfg.history_window)
        self._tick:      int = 0
        self._zone_history: Deque[CriticalityZone] = deque(maxlen=self._cfg.history_window)

    # ── API pubblica ──────────────────────────────────────────────────────────

    def assess(
        self,
        emergence: float,
        coherence: float,
        novelty:   float,
    ) -> CriticalityState:
        """
        Valuta la criticità corrente e suggerisce modulazione.

        Args:
            emergence: score di emergenza globale [0, 1]
            coherence: score di coerenza cognitiva [0, 1]
            novelty:   score di novità/esplorazione [0, 1]

        Returns:
            CriticalityState con zone, order_score, modulation_suggestion
        """
        self._tick += 1

        # Clamp input
        emergence = max(0.0, min(1.0, float(emergence)))
        coherence = max(0.0, min(1.0, float(coherence)))
        novelty   = max(0.0, min(1.0, float(novelty)))

        # 1. Calcola order_score
        order_score = (
            self._cfg.coherence_weight * coherence +
            self._cfg.novelty_weight   * (1.0 - novelty)
        )
        order_score = max(0.0, min(1.0, order_score))

        # 2. EMA smoothing
        self._ema = (
            self._cfg.alpha_ema * order_score +
            (1.0 - self._cfg.alpha_ema) * self._ema
        )

        # 3. Classifica zona (usa EMA per stabilità)
        zone = self._classify(self._ema)

        # 4. Genera modulazione
        modulation, recommendation = self._modulate(zone)

        # 5. mutation_gate: aperto solo se in zona critica o quasi
        modulation.mutation_gate_open = (zone == CriticalityZone.CRITICAL)

        # 6. Registra storia
        self._history.append(order_score)
        self._zone_history.append(zone)

        state = CriticalityState(
            zone=zone,
            order_score=round(order_score, 4),
            order_score_ema=round(self._ema, 4),
            coherence=round(coherence, 4),
            novelty=round(novelty, 4),
            emergence=round(emergence, 4),
            in_target_zone=(zone == CriticalityZone.CRITICAL),
            recommendation=recommendation,
            modulation=modulation,
            tick_count=self._tick,
        )

        logger.debug("[Criticality] %s", state.summary())
        return state

    @property
    def current_zone(self) -> Optional[CriticalityZone]:
        """Zona critica corrente (None se nessun tick effettuato)."""
        if not self._zone_history:
            return None
        return self._zone_history[-1]

    @property
    def order_score_ema(self) -> float:
        """EMA corrente dell'order_score."""
        return round(self._ema, 4)

    def zone_stability(self) -> float:
        """
        Frazione di tick recenti nella stessa zona dell'ultimo tick.
        1.0 = sistema stabile nella zona corrente.
        """
        if len(self._zone_history) < 2:
            return 1.0
        current = self._zone_history[-1]
        return sum(1 for z in self._zone_history if z == current) / len(self._zone_history)

    def mean_order_score(self) -> float:
        """Media dell'order_score nella finestra temporale."""
        if not self._history:
            return 0.5
        return round(sum(self._history) / len(self._history), 4)

    def is_critical(self) -> bool:
        """True se il sistema è attualmente nella zona critica ottimale."""
        return self.current_zone == CriticalityZone.CRITICAL

    # ── Privati ───────────────────────────────────────────────────────────────

    def _classify(self, ema: float) -> CriticalityZone:
        if ema > self._cfg.order_threshold:
            return CriticalityZone.OVER_ORDERED
        if ema < self._cfg.chaos_threshold:
            return CriticalityZone.OVER_CHAOTIC
        return CriticalityZone.CRITICAL

    def _modulate(self, zone: CriticalityZone):
        """Produce ModulationSuggestion e stringa recommendation."""
        cfg = self._cfg

        if zone == CriticalityZone.OVER_ORDERED:
            mod = ModulationSuggestion(
                temperature_delta  = cfg.temperature_boost,
                exploration_bonus  = cfg.novelty_boost,
                coherence_boost    = 0.0,
                mutation_gate_open = False,   # troppo rigido — non mutare ora
                maintain           = False,
            )
            rec = (
                "Sistema OVER-ORDERED: aumenta divergenza e novità. "
                "Boost temperature generazione, attiva esplorazione spontanea."
            )

        elif zone == CriticalityZone.OVER_CHAOTIC:
            mod = ModulationSuggestion(
                temperature_delta  = cfg.temperature_cut,
                exploration_bonus  = 0.0,
                coherence_boost    = cfg.coherence_boost,
                mutation_gate_open = False,   # troppo caotico — non mutare ora
                maintain           = False,
            )
            rec = (
                "Sistema OVER-CHAOTIC: aumenta struttura e coerenza. "
                "Riduci temperatura, prioritizza consolidamento memoria."
            )

        else:  # CRITICAL
            mod = ModulationSuggestion(
                temperature_delta  = 0.0,
                exploration_bonus  = 0.0,
                coherence_boost    = 0.0,
                mutation_gate_open = True,    # zona ottimale — mutazioni consentite
                maintain           = True,
            )
            rec = "Sistema CRITICAL (zona ottimale): mantieni equilibrio corrente."

        return mod, rec


__all__ = [
    "CriticalityController",
    "CriticalityConfig",
    "CriticalityState",
    "CriticalityZone",
    "ModulationSuggestion",
]
