"""
cortex.homeostasis.kinetic_flow
================================
M14.5 — Homeodyna + Kinetica: flusso energetico inter-lobo.

Modella la dinamica energetica tra i lobi cerebrali di SPEACE usando
principi ispirati alla diffusione termica e alla trasmissione sinaptica:

  Homeodyna  — ogni lobo tende verso il proprio set_point con τ di rilassamento
  Kinetica   — energia cinetica di ogni lobo = (dE/dt)² (energia del cambiamento)
  Flow       — l'energia fluisce tra lobi connessi proporzionalmente al gradiente

Integrazione con EnergyBudget (M9):
  kf = KineticFlow()
  result = kf.tick(dt=1.0)
  # result.total_kinetic → iniettare in EnergyBudget o DriveExecutive

Uso standalone:
  kf = KineticFlow()
  kf.inject("Frontale", 0.3)       # stimolazione esterna
  result = kf.tick(dt=1.0)
  print(result.total_kinetic)       # energia complessiva di cambiamento
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Configurazione ────────────────────────────────────────────────────────────

@dataclass
class KineticFlowConfig:
    """Parametri del modello Homeodyna+Kinetica."""
    # Costante di rilassamento omeostatico (τ in secondi simulati)
    # Più basso = ritorno più veloce al set_point
    relaxation_tau: float = 5.0

    # Coefficiente di diffusione inter-lobo (0.0 = nessun flusso, 1.0 = max)
    diffusion_coeff: float = 0.25

    # Clamp energia [0, 1]
    energy_min: float = 0.0
    energy_max: float = 1.0

    # Soglia kinetic per "stato di eccitazione alta"
    high_kinetic_threshold: float = 0.15

    # Decadimento inerzia (smorzamento) per evitare oscillazioni permanenti
    damping: float = 0.05

    # Numero massimo di tick memorizzati nello storico rolling
    history_max: int = 50


# ── Stato dei lobi ────────────────────────────────────────────────────────────

# Topologia default ispirata alla BioCore (Grok SPEACE v2.6)
DEFAULT_LOBES: Dict[str, float] = {
    "Frontale":  0.82,   # set_point = activation iniziale
    "Temporale": 0.78,
    "Parietale": 0.71,
    "Occipitale":0.65,
    "Cingulate": 0.85,
}

# Connessioni inter-lobo: (src, tgt, peso_connessione)
DEFAULT_CONNECTIONS: List[Tuple[str, str, float]] = [
    ("Frontale",  "Temporale",  0.82),
    ("Frontale",  "Parietale",  0.75),
    ("Frontale",  "Cingulate",  0.89),
    ("Temporale", "Parietale",  0.71),
    ("Temporale", "Occipitale", 0.68),
    ("Parietale", "Occipitale", 0.64),
    ("Cingulate", "Frontale",   0.91),   # feedback loop
]


@dataclass
class LobeState:
    """Stato energetico istantaneo di un singolo lobo."""
    name: str
    energy: float       # livello energetico corrente [0, 1]
    set_point: float    # target omeostatico [0, 1]
    velocity: float = 0.0   # dE/dt dell'ultimo tick (inerzia)
    kinetic: float = 0.0    # energia cinetica = velocity²

    def clamp(self, lo: float = 0.0, hi: float = 1.0) -> None:
        self.energy = max(lo, min(hi, self.energy))
        self.kinetic = self.velocity ** 2


# ── Risultato tick ────────────────────────────────────────────────────────────

@dataclass
class KineticFlowResult:
    """Output di un singolo passo di simulazione."""
    timestamp:     float
    dt:            float
    lobes:         Dict[str, LobeState]
    total_kinetic: float    # Σ K_i — iniettabile in EnergyBudget
    mean_energy:   float    # media attivazione lobi
    high_kinetic:  bool     # total_kinetic > threshold (stato eccitato)
    flow_map:      Dict[str, float]   # flusso netto per lobo (positivo = guadagno)

    def to_dict(self) -> dict:
        return {
            "timestamp":     self.timestamp,
            "dt":            self.dt,
            "total_kinetic": round(self.total_kinetic, 6),
            "mean_energy":   round(self.mean_energy, 4),
            "high_kinetic":  self.high_kinetic,
            "lobes": {
                name: {
                    "energy":    round(s.energy, 4),
                    "set_point": round(s.set_point, 4),
                    "velocity":  round(s.velocity, 6),
                    "kinetic":   round(s.kinetic, 6),
                }
                for name, s in self.lobes.items()
            },
            "flow_map": {k: round(v, 6) for k, v in self.flow_map.items()},
        }


# ── KineticFlow ───────────────────────────────────────────────────────────────

class KineticFlow:
    """
    Simulatore di flusso energetico inter-lobo.

    Fisicamente modella:
      dE_i/dt = Homeodyna_i + Kinetica_i + Σ_j Flow_ji

    Dove:
      Homeodyna_i = (set_point_i - E_i) / τ          (rilassamento omeostatico)
      Kinetica_i  = -damping * velocity_i              (smorzamento inerzia)
      Flow_ji     = diffusion * w_ji * (E_j - E_i)    (diffusione pesata)

    Il total_kinetic = Σ velocity_i² rappresenta l'"attività di cambiamento"
    globale del sistema — alto quando il sistema è in transizione energetica.
    """

    def __init__(
        self,
        lobes: Optional[Dict[str, float]] = None,
        connections: Optional[List[Tuple[str, str, float]]] = None,
        config: Optional[KineticFlowConfig] = None,
    ):
        self.config = config or KineticFlowConfig()
        _lobes = lobes or DEFAULT_LOBES
        _conns = connections or DEFAULT_CONNECTIONS

        # Inizializza stati
        self._states: Dict[str, LobeState] = {
            name: LobeState(name=name, energy=ep, set_point=ep)
            for name, ep in _lobes.items()
        }

        # Tabella di adiacenza pesata: adj[i][j] = peso_connessione
        self._adj: Dict[str, Dict[str, float]] = {n: {} for n in self._states}
        for src, tgt, w in _conns:
            if src in self._adj and tgt in self._states:
                self._adj[src][tgt] = w

        self._history: List[KineticFlowResult] = []
        self._tick_count: int = 0
        self._last_result: Optional[KineticFlowResult] = None

    # ── Stimolazione esterna ─────────────────────────────────────────────────

    def inject(self, lobe: str, amount: float) -> bool:
        """
        Inietta energia in un lobo (es. da stimolazione sensoriale o task).
        amount > 0 eccita, amount < 0 inibisce.
        Ritorna False se il lobo non esiste.
        """
        if lobe not in self._states:
            return False
        s = self._states[lobe]
        s.energy = max(self.config.energy_min,
                       min(self.config.energy_max, s.energy + amount))
        return True

    def set_setpoint(self, lobe: str, set_point: float) -> bool:
        """Aggiorna il set_point omeostatico di un lobo."""
        if lobe not in self._states:
            return False
        self._states[lobe].set_point = max(0.0, min(1.0, set_point))
        return True

    # ── Tick principale ──────────────────────────────────────────────────────

    def tick(self, dt: float = 1.0) -> KineticFlowResult:
        """
        Avanza la simulazione di dt secondi simulati.
        Calcola: Homeodyna + Kinetica + flusso inter-lobo.
        Ritorna KineticFlowResult con total_kinetic e stato di ogni lobo.
        """
        cfg = self.config
        flow_map: Dict[str, float] = {n: 0.0 for n in self._states}

        # 1. Calcola flusso netto per ogni lobo (da vicini)
        for src, neighbors in self._adj.items():
            for tgt, w in neighbors.items():
                e_src = self._states[src].energy
                e_tgt = self._states[tgt].energy
                flow = cfg.diffusion_coeff * w * (e_src - e_tgt) * dt
                flow_map[src] -= flow   # src perde energia
                flow_map[tgt] += flow   # tgt guadagna energia

        # 2. Aggiorna ogni lobo: Homeodyna + smorzamento + flusso
        for name, state in self._states.items():
            # Forza omeostatica: tende al set_point
            homeodyna = ((state.set_point - state.energy) / cfg.relaxation_tau) * dt

            # Smorzamento inerzia
            damping_force = -cfg.damping * state.velocity * dt

            # Variazione totale
            delta = homeodyna + damping_force + flow_map[name]

            # Aggiorna velocity (= dE/dt approssimato)
            state.velocity = delta / dt if dt > 0 else 0.0

            # Aggiorna energia
            state.energy += delta
            state.clamp(cfg.energy_min, cfg.energy_max)

        # 3. Calcola metriche aggregate
        total_kinetic = sum(s.kinetic for s in self._states.values())
        mean_energy   = sum(s.energy for s in self._states.values()) / len(self._states)
        high_kinetic  = total_kinetic > cfg.high_kinetic_threshold

        result = KineticFlowResult(
            timestamp     = time.time(),
            dt            = dt,
            lobes         = dict(self._states),
            total_kinetic = total_kinetic,
            mean_energy   = mean_energy,
            high_kinetic  = high_kinetic,
            flow_map      = flow_map,
        )

        # Rolling history
        self._history.append(result)
        if len(self._history) > cfg.history_max:
            self._history.pop(0)

        self._last_result = result
        self._tick_count += 1
        return result

    # ── Integrazione EnergyBudget ─────────────────────────────────────────────

    def energy_budget_feed(self, budget) -> float:
        """
        Integrazione con EnergyBudget (M9):
          - Se total_kinetic alto → sistema eccitato → attiva un "kinetic_flow" neuron
          - Ritorna il total_kinetic per uso esterno

        Usage:
          from cortex.cognitive_autonomy.energy.budget import EnergyBudget
          budget = EnergyBudget()
          kf.energy_budget_feed(budget)
        """
        if self._last_result is None:
            self.tick()
        tk = self._last_result.total_kinetic
        if self._last_result.high_kinetic:
            if hasattr(budget, "activate"):
                budget.activate("kinetic_flow_active")
        else:
            if hasattr(budget, "deactivate"):
                budget.deactivate("kinetic_flow_active")
        return tk

    # ── Statistiche ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Stato compatto per SMFOI Step 1 (Self-Location)."""
        if self._last_result is None:
            return {"tick_count": 0, "total_kinetic": 0.0, "mean_energy": 0.0}
        lr = self._last_result
        return {
            "tick_count":   self._tick_count,
            "total_kinetic": round(lr.total_kinetic, 6),
            "mean_energy":  round(lr.mean_energy, 4),
            "high_kinetic": lr.high_kinetic,
            "lobes": {
                n: {"energy": round(s.energy, 4), "kinetic": round(s.kinetic, 6)}
                for n, s in lr.lobes.items()
            },
        }

    def kinetic_trend(self) -> str:
        """
        Analizza la tendenza recente della total_kinetic.
        Ritorna: 'rising' | 'falling' | 'stable'
        """
        if len(self._history) < 3:
            return "stable"
        recent = [r.total_kinetic for r in self._history[-5:]]
        deltas = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        avg_delta = sum(deltas) / len(deltas)
        if avg_delta > 0.001:
            return "rising"
        elif avg_delta < -0.001:
            return "falling"
        return "stable"
