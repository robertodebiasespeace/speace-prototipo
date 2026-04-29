"""
cortex.cognitive_autonomy.temporal.circadian_oscillator
=========================================================
M11.1 — CircadianOscillator: pacemaker bio-temporale di SPEACE.

Replica il nucleo soprachiasmatico (SCN):
  - Ritmo circadiano 24h modellato come somma di sinusoidi (Fourier biologico)
  - Ritmo ultradiano ~90min (ciclo attenzione-riposo, analogo REM/NREM)
  - Segnali ormonali simulati: cortisolo (mattino), adenosina (accumulo),
    melatonina (sera), BDNF (consolidamento notturno)
  - Vettore di modulatori [0.0–1.0] per curiosity/energy/plasticity/immune

Matematica:
  La fase circadiana è calcolata come angolo 0..2π in un giorno di 24h.
  La forma d'onda usa una sinusoide smorzata + armoniche secondarie per
  approssimare il profilo biologico reale (picco mattino, valle notturna).

  f_circadian(t) = 0.5 + 0.5·sin(2π·t/T_day - φ_peak)
  dove φ_peak sposta il picco alle 10:00 (fase cognitiva ottimale).

  f_ultradian(t) = 0.5 + 0.5·sin(2π·t/T_ultradian)
  dove T_ultradian = 5400s (90 min).

M11.1 | 2026-04-28
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger("speace.temporal.circadian")

# ── Costanti biologiche ────────────────────────────────────────────────────

_T_CIRCADIAN_S   = 86400.0   # 24h in secondi
_T_ULTRADIAN_S   = 5400.0    # 90 min in secondi
_PEAK_HOUR       = 10.0      # ora del picco cognitivo (10:00)
_VALLEY_HOUR     = 4.0       # ora del minimo (04:00)
_MELATONIN_START = 21.0      # inizio secrezione melatonina (21:00)
_CORTISOL_PEAK   = 8.5       # picco cortisolo (08:30)


# ─────────────────────────────────────────────────────────────────────────────
# CircadianPhase — fase del ciclo circadiano
# ─────────────────────────────────────────────────────────────────────────────

class CircadianPhase(str, Enum):
    MORNING_PEAK   = "morning_peak"    # 07:00–12:00 — alta curiosity, allerta
    AFTERNOON      = "afternoon"       # 12:00–17:00 — processing standard
    EVENING        = "evening"         # 17:00–21:00 — riduzione energy
    NIGHT_VALLEY   = "night_valley"    # 21:00–07:00 — consolidamento, repair
    ULTRADIAN_REST = "ultradian_rest"  # pausa ultradiana (5-10 min)


# ─────────────────────────────────────────────────────────────────────────────
# CircadianConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CircadianConfig:
    """
    Configurazione dell'oscillatore circadiano.

    Attributi:
        reference_hour:   ora di riferimento per la fase 0 (default 0.0 = mezzanotte).
                          Può essere impostata per "sincronizzare" SPEACE con l'ora
                          locale del sistema.
        circadian_amplitude: ampiezza della modulazione circadiana [0.0–1.0].
                          1.0 = piena modulazione (differenza giorno/notte massima).
                          0.0 = nessuna modulazione (flat).
        ultradian_amplitude: ampiezza del ritmo ultradiano [0.0–0.50].
        ultradian_rest_threshold: soglia sotto cui si attiva ULTRADIAN_REST [0.0–0.30].
        use_system_clock: se True, usa l'ora reale del sistema per calcolare la fase.
                          Se False, usa il timestamp UNIX fornito a tick().
        simulated_hour:   ora simulata [0.0–24.0] — usata solo se use_system_clock=False.
    """
    reference_hour:          float = 0.0    # mezzanotte = fase 0
    circadian_amplitude:     float = 0.70   # modulazione circadiana 70%
    ultradian_amplitude:     float = 0.20   # modulazione ultradiana 20%
    ultradian_rest_threshold: float = 0.15  # soglia pausa ultradiana
    use_system_clock:        bool  = True   # usa ora di sistema
    simulated_hour:          float = 9.0    # ora simulata (se use_system_clock=False)


# ─────────────────────────────────────────────────────────────────────────────
# UltradianCycle — stato del ciclo ultradiano
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UltradianCycle:
    """Stato del ciclo ultradiano corrente."""
    phase_rad:    float   # fase corrente in radianti [0, 2π]
    intensity:    float   # intensità [0.0–1.0]
    is_rest:      bool    # True se nella fase di riposo
    minutes_to_rest: float  # minuti al prossimo riposo ultradiano


# ─────────────────────────────────────────────────────────────────────────────
# CircadianState — snapshot completo dell'oscillatore
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CircadianState:
    """
    Snapshot completo dello stato dell'oscillatore circadiano.

    Attributi:
        phase:           fase corrente del ciclo circadiano
        hour_of_day:     ora del giorno [0.0–24.0]
        circadian_level: livello circadiano base [0.0–1.0]
        ultradian:       stato del ciclo ultradiano corrente
        modulators:      vettore di modulatori per i drive SPEACE
        hormones:        livelli ormonali simulati
    """
    phase:            CircadianPhase
    hour_of_day:      float
    circadian_level:  float
    ultradian:        UltradianCycle
    modulators:       Dict[str, float]
    hormones:         Dict[str, float]
    timestamp:        float = field(default_factory=time.time)

    def modulate(self, drive_name: str, base_value: float) -> float:
        """Applica la modulazione circadiana a un drive base."""
        mod = self.modulators.get(drive_name, 1.0)
        return max(0.0, min(1.0, base_value * mod))

    def summary(self) -> str:
        mods = " ".join(f"{k}={v:.2f}" for k, v in self.modulators.items())
        return (
            f"[CircadianState] {self.phase.value} "
            f"h={self.hour_of_day:.1f} "
            f"circ={self.circadian_level:.2f} "
            f"ultradian={'REST' if self.ultradian.is_rest else f'{self.ultradian.intensity:.2f}'} "
            f"| {mods}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CircadianOscillator — pacemaker principale
# ─────────────────────────────────────────────────────────────────────────────

class CircadianOscillator:
    """
    M11.1 — Pacemaker bio-temporale di SPEACE.

    Produce un vettore di modulatori [0.0–1.0] per ogni drive SPEACE
    in base alla fase del ciclo circadiano e ultradiano corrente.

    Modulatori prodotti:
        curiosity_mod    — alta al mattino (MORNING_PEAK), bassa di notte
        energy_mod       — segue cortisolo: picco mattino, calo sera
        plasticity_mod   — alta nel pomeriggio (window sinaptica biologica)
        immune_mod       — alta di notte (riparazione immunitaria notturna)
        consolidation_mod — alta di notte (NIGHT_VALLEY = consolidamento)
        exploration_mod  — alta al mattino, bassa di notte

    Uso base:
        osc = CircadianOscillator()
        state = osc.tick()
        # Ora modula i drive
        curiosity_modulated = state.modulate("curiosity", 0.65)

    Uso con ora simulata (test / ambiente headless):
        cfg = CircadianConfig(use_system_clock=False, simulated_hour=22.0)
        osc = CircadianOscillator(config=cfg)
        state = osc.tick()  # simula le 22:00 (sera)
    """

    def __init__(self, config: Optional[CircadianConfig] = None) -> None:
        self._cfg = config or CircadianConfig()
        self._ultradian_origin: float = time.time()
        self._tick_count: int = 0

    # ── API pubblica ──────────────────────────────────────────────────────────

    def tick(self, timestamp: Optional[float] = None) -> CircadianState:
        """
        Calcola lo stato circadiano corrente.

        Args:
            timestamp: UNIX timestamp opzionale. Se None e use_system_clock=True,
                       usa time.time(). Se use_system_clock=False, usa simulated_hour.
        """
        self._tick_count += 1
        now = timestamp or time.time()

        hour = self._compute_hour(now)
        circ_level = self._circadian_wave(hour)
        ultradian  = self._ultradian_state(now)
        phase      = self._classify_phase(hour, ultradian.is_rest)
        hormones   = self._compute_hormones(hour)
        modulators = self._compute_modulators(phase, circ_level, ultradian, hormones)

        state = CircadianState(
            phase=phase,
            hour_of_day=round(hour, 2),
            circadian_level=round(circ_level, 3),
            ultradian=ultradian,
            modulators=modulators,
            hormones=hormones,
            timestamp=now,
        )
        logger.debug("[Circadian] %s", state.summary())
        return state

    def set_simulated_hour(self, hour: float) -> None:
        """Imposta l'ora simulata (solo se use_system_clock=False)."""
        if not 0.0 <= hour < 24.0:
            raise ValueError(f"hour deve essere in [0, 24), got {hour}")
        self._cfg.simulated_hour = hour
        self._cfg.use_system_clock = False

    @property
    def tick_count(self) -> int:
        return self._tick_count

    # ── Calcolo ora ───────────────────────────────────────────────────────────

    def _compute_hour(self, now: float) -> float:
        """Calcola l'ora del giorno [0.0, 24.0)."""
        if self._cfg.use_system_clock:
            import datetime
            dt = datetime.datetime.fromtimestamp(now)
            return dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        return self._cfg.simulated_hour % 24.0

    # ── Onda circadiana ───────────────────────────────────────────────────────

    def _circadian_wave(self, hour: float) -> float:
        """
        Calcola il livello circadiano [0.0–1.0] per l'ora data.

        Formula bio-ispirata:
          f(h) = 0.5 + A·[0.7·sin(2π·h/24 - φ_peak) + 0.3·sin(4π·h/24 - φ2)]
          dove φ_peak sposta il picco alle 10h, φ2 aggiunge armonica secondaria.
        """
        A    = self._cfg.circadian_amplitude
        # Fase: 0=mezzanotte, picco a 10h
        phi1 = 2 * math.pi * (_PEAK_HOUR - self._cfg.reference_hour) / 24.0
        phi2 = 4 * math.pi * (_PEAK_HOUR - self._cfg.reference_hour) / 24.0

        rad_h = 2 * math.pi * hour / 24.0
        raw   = 0.7 * math.sin(rad_h - phi1) + 0.3 * math.sin(2 * rad_h - phi2)
        return max(0.0, min(1.0, 0.5 + A * 0.5 * raw))

    # ── Ciclo ultradiano ──────────────────────────────────────────────────────

    def _ultradian_state(self, now: float) -> UltradianCycle:
        """
        Calcola lo stato del ciclo ultradiano corrente.
        T_ultradian = 5400s (90 min). Riposo nelle valli basse.
        """
        elapsed   = (now - self._ultradian_origin) % _T_ULTRADIAN_S
        phase_rad = 2 * math.pi * elapsed / _T_ULTRADIAN_S
        intensity = 0.5 + 0.5 * math.sin(phase_rad)  # [0, 1]
        A_u       = self._cfg.ultradian_amplitude

        # La componente ultradiana modula l'intensità intorno a 1.0
        ultradian_mod = 1.0 - A_u + A_u * intensity

        is_rest = (intensity < self._cfg.ultradian_rest_threshold)
        time_to_rest_s = max(0.0,
            (_T_ULTRADIAN_S - elapsed) * (1 - self._cfg.ultradian_rest_threshold)
        )
        return UltradianCycle(
            phase_rad=round(phase_rad, 3),
            intensity=round(ultradian_mod, 3),
            is_rest=is_rest,
            minutes_to_rest=round(time_to_rest_s / 60.0, 1),
        )

    # ── Classificazione fase ──────────────────────────────────────────────────

    def _classify_phase(self, hour: float, ultradian_rest: bool) -> CircadianPhase:
        """Classifica la fase corrente del ciclo circadiano."""
        if ultradian_rest:
            return CircadianPhase.ULTRADIAN_REST
        if 7.0 <= hour < 12.0:
            return CircadianPhase.MORNING_PEAK
        if 12.0 <= hour < 17.0:
            return CircadianPhase.AFTERNOON
        if 17.0 <= hour < 21.0:
            return CircadianPhase.EVENING
        return CircadianPhase.NIGHT_VALLEY

    # ── Ormoni simulati ───────────────────────────────────────────────────────

    def _compute_hormones(self, hour: float) -> Dict[str, float]:
        """
        Simula i livelli ormonali principali [0.0–1.0].

        Cortisolo:   picco alle 8:30, decade durante il giorno
        Melatonina:  bassa di giorno, alta di notte (21:00–07:00)
        Adenosina:   accumulo durante la veglia, azzerata dal sonno
        BDNF:        picco notturno (consolida plasticità)
        """
        # Cortisolo: forma d'onda Gaussian centrata sull'ora del picco
        cortisol_sigma = 2.0
        cortisol = math.exp(-0.5 * ((hour - _CORTISOL_PEAK) / cortisol_sigma) ** 2)

        # Melatonina: alta di notte, bassa di giorno
        if hour >= _MELATONIN_START or hour < 7.0:
            melatonin = 0.8
        elif 7.0 <= hour < 9.0:
            melatonin = 0.8 * (9.0 - hour) / 2.0  # calo mattutino
        elif 17.0 <= hour < _MELATONIN_START:
            melatonin = 0.3 * (hour - 17.0) / 4.0  # salita serale
        else:
            melatonin = 0.05

        # Adenosina (pressione del sonno): accumulo lineare durante veglia
        # modellato come funzione dell'ora (assume veglia dalle 7:00)
        wake_h = max(0.0, (hour - 7.0) % 24.0)
        adenosine = min(1.0, wake_h / 16.0)  # satura dopo 16h di veglia

        # BDNF: alta consolidamento notturno (22:00–06:00)
        if hour >= 22.0 or hour < 6.0:
            bdnf = 0.85
        else:
            bdnf = 0.35

        return {
            "cortisol":  round(cortisol,  3),
            "melatonin": round(melatonin, 3),
            "adenosine": round(adenosine, 3),
            "bdnf":      round(bdnf,      3),
        }

    # ── Modulatori drive ──────────────────────────────────────────────────────

    def _compute_modulators(
        self,
        phase:      CircadianPhase,
        circ_level: float,
        ultradian:  UltradianCycle,
        hormones:   Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calcola il vettore di modulatori per i drive SPEACE.

        Ogni modulatore è un fattore moltiplicativo [0.5–1.5] che
        amplifica o attenua il drive base corrispondente.
        Mapping biologico:
          curiosity    ← cortisolo + fase MORNING_PEAK
          energy_drive ← cortisolo - adenosina (stanchezza)
          plasticity   ← BDNF + fase AFTERNOON (finestra sinaptica)
          immune       ← fase NIGHT + melatonina (riparazione)
          consolidation ← BDNF + fase NIGHT (replay ippocampale)
          exploration  ← circ_level + cortisolo
        """
        u = ultradian.intensity  # [0.8–1.2] circa

        # curiosity: alta al mattino (cortisolo + allerta)
        curiosity_mod = 0.7 + 0.6 * hormones["cortisol"] * (
            1.5 if phase == CircadianPhase.MORNING_PEAK else
            1.0 if phase == CircadianPhase.AFTERNOON else 0.7
        )

        # energy_drive: degradato dall'adenosina (stanchezza)
        energy_mod = max(0.5, circ_level * (1.0 - 0.5 * hormones["adenosine"]))

        # plasticity: finestra sinaptica pomeridiana + BDNF notturno
        if phase == CircadianPhase.AFTERNOON:
            plasticity_mod = 1.2 + 0.2 * hormones["bdnf"]
        elif phase == CircadianPhase.NIGHT_VALLEY:
            plasticity_mod = 0.9 + 0.3 * hormones["bdnf"]
        else:
            plasticity_mod = 0.8 + 0.2 * hormones["bdnf"]

        # immune: sistema immunitario forte di notte
        immune_mod = 0.6 + 0.8 * hormones["melatonin"]

        # consolidation: replay ippocampale notturno
        consolidation_mod = (
            1.4 if phase == CircadianPhase.NIGHT_VALLEY else
            0.9 if phase == CircadianPhase.EVENING else 0.6
        )
        consolidation_mod *= (0.8 + 0.4 * hormones["bdnf"])

        # exploration: alta al mattino, bassa di notte
        exploration_mod = circ_level * (1.0 - 0.5 * hormones["melatonin"])

        # Applica modulazione ultradiana (riduce tutti in ULTRADIAN_REST)
        rest_factor = 0.7 if ultradian.is_rest else u

        return {
            "curiosity_mod":     round(min(1.5, max(0.3, curiosity_mod    * rest_factor)), 3),
            "energy_mod":        round(min(1.5, max(0.3, energy_mod       * rest_factor)), 3),
            "plasticity_mod":    round(min(1.5, max(0.3, plasticity_mod   * rest_factor)), 3),
            "immune_mod":        round(min(1.5, max(0.3, immune_mod       * rest_factor)), 3),
            "consolidation_mod": round(min(1.5, max(0.3, consolidation_mod * rest_factor)), 3),
            "exploration_mod":   round(min(1.5, max(0.3, exploration_mod  * rest_factor)), 3),
        }


__all__ = [
    "CircadianOscillator",
    "CircadianConfig",
    "CircadianPhase",
    "CircadianState",
    "UltradianCycle",
]
