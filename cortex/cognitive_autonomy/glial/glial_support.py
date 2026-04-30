"""
cortex.cognitive_autonomy.glial.glial_support
===============================================
M11.2 — GlialSupport: ponte tra AstrocyteNetwork e il pipeline cognitivo.

Funzioni principali:
  1. plasticity_boost  — onde di calcio → potenziamento plasticità sinaptica
  2. metabolic_supply  — lactate shuttle → carburante per neuroni attivi
  3. cleanup_rate      — sistema glinfatico → clearance metaboliti (fase SLEEP)
  4. coherence_bridge  — propagazione onde Ca²⁺ → sincronizzazione compartments

Architettura:
  GlialSupport istanzia una AstrocyteNetwork con astrociti per ognuno
  dei 9+1 comparti SPEACE Cortex (prefrontal, hippocampus, safety, temporal,
  parietal, cerebellum, default_mode, curiosity, world_model, swarm).
  Le calcium waves propagano coerenza tra comparti.

  La WakeState del SleepWakeCycle modula il cleanup rate (biologico:
  il sistema glinfatico è 10× più attivo durante il sonno profondo).

M11.2 | 2026-04-28
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speace.glial")


# ─────────────────────────────────────────────────────────────────────────────
# GlialConfig
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GlialConfig:
    """
    Configurazione del supporto gliale.

    Attributi:
        plasticity_boost_max:  boost massimo applicato alla plasticità [0.0–1.0]
        calcium_threshold:     soglia segnale calcio per attivare plasticity boost
        cleanup_awake_rate:    tasso clearance in stato AWAKE (basso, come biologico)
        cleanup_sleep_rate:    tasso clearance in DEEP_SLEEP (alto: glymphatica attiva)
        metabolic_regen_rate:  velocità rigenerazione metabolic_reserve degli astrociti
        coherence_propagation: se True, propaga coerenza via calcium wave tra comparti
    """
    plasticity_boost_max:  float = 0.30
    calcium_threshold:     float = 0.40
    cleanup_awake_rate:    float = 0.05   # 5% clearance per tick in veglia
    cleanup_sleep_rate:    float = 0.40   # 40% clearance per tick in sleep
    metabolic_regen_rate:  float = 0.10
    coherence_propagation: bool  = True


# ─────────────────────────────────────────────────────────────────────────────
# GlialEffect — effetto modulatorio del supporto gliale
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GlialEffect:
    """
    Effetto modulatorio prodotto dal supporto gliale in un singolo tick.

    Attributi:
        plasticity_boost:  moltiplicatore plasticità [1.0–1.3]
        metabolic_supply:  carburante disponibile per neuroni [0.0–1.0]
        cleanup_rate:      tasso clearance metaboliti attuale [0.0–1.0]
        coherence_gain:    guadagno di coerenza da calcium waves [0.0–0.20]
        calcium_level:     livello calcio medio nella rete [0.0–1.0]
        active_astrocytes: numero astrociti attivi (calcium > threshold)
    """
    plasticity_boost:  float
    metabolic_supply:  float
    cleanup_rate:      float
    coherence_gain:    float
    calcium_level:     float
    active_astrocytes: int

    def summary(self) -> str:
        return (
            f"plasticity_boost={self.plasticity_boost:.2f} "
            f"metabolic={self.metabolic_supply:.2f} "
            f"cleanup={self.cleanup_rate:.2f} "
            f"coherence_gain={self.coherence_gain:.3f} "
            f"calcium={self.calcium_level:.2f} "
            f"active_astro={self.active_astrocytes}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GlialState — snapshot completo
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GlialState:
    """
    Snapshot completo del supporto gliale in un tick.

    Attributi:
        effect:           effetti modulatori calcolati
        network_health:   salute della rete astrocitaria [0.0–1.0]
        metabolic_crisis: True se metabolic_reserve media < 0.20
        glymphatic_active: True se cleanup_rate > 0.20 (glymphatica attiva)
        tick_count:       numero tick effettuati
        timestamp:        UNIX timestamp
    """
    effect:            GlialEffect
    network_health:    float
    metabolic_crisis:  bool
    glymphatic_active: bool
    tick_count:        int
    timestamp:         float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"[GlialState] health={self.network_health:.2f} "
            f"{'⚠CRISIS' if self.metabolic_crisis else 'OK'} "
            f"{'GLYMPHATIC' if self.glymphatic_active else ''} "
            f"| {self.effect.summary()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GlialSupport — motore principale
# ─────────────────────────────────────────────────────────────────────────────

# Comparti SPEACE Cortex (10+1 astrociti)
_SPEACE_REGIONS = [
    "prefrontal_cortex",
    "hippocampus",
    "safety_module",
    "temporal_lobe",
    "parietal_lobe",
    "cerebellum",
    "default_mode_network",
    "curiosity_module",
    "world_model",
    "swarm_orchestrator",
    "energy_monitor",
]

# Topologia di connessione (ispirata alla connettività funzionale cerebrale)
_CONNECTIVITY = [
    ("prefrontal_cortex",  "hippocampus"),
    ("prefrontal_cortex",  "default_mode_network"),
    ("prefrontal_cortex",  "world_model"),
    ("hippocampus",        "default_mode_network"),
    ("hippocampus",        "curiosity_module"),
    ("safety_module",      "prefrontal_cortex"),
    ("safety_module",      "energy_monitor"),
    ("temporal_lobe",      "hippocampus"),
    ("parietal_lobe",      "temporal_lobe"),
    ("parietal_lobe",      "world_model"),
    ("cerebellum",         "parietal_lobe"),
    ("world_model",        "swarm_orchestrator"),
    ("curiosity_module",   "swarm_orchestrator"),
    ("energy_monitor",     "cerebellum"),
]


class GlialSupport:
    """
    M11.2 — Integra AstrocyteNetwork come modulatore del pipeline cognitivo.

    Usa la rete astrocitaria già presente in cortex/astrocyte_network.py
    per produrre effetti modulatori bio-ispirati: plasticity boost,
    metabolic supply, glymphatic cleanup, e coherence propagation.

    Standalone (senza AstrocyteNetwork disponibile):
        GlialSupport può funzionare in modalità fallback con un network
        interno minimo, per garantire graceful degradation.

    Uso base:
        glial = GlialSupport()

        # In fase AWAKE con attività media
        effect = glial.tick(
            activity_level=0.7,   # 0=idle, 1=massima attività
            wake_state="awake",   # "awake" | "idle" | "deep_sleep"
            phi=0.5,              # Φ (integrazione informativa corrente)
        )
        print(effect.summary())

        # Applica plasticity boost
        new_plasticity = base_plasticity * effect.plasticity_boost
    """

    def __init__(
        self,
        config:  Optional[GlialConfig] = None,
        bus:     Any = None,
    ) -> None:
        self._cfg  = config or GlialConfig()
        self._bus  = bus
        self._tick_count = 0
        self._network = self._build_network()

    # ── API pubblica ──────────────────────────────────────────────────────────

    def tick(
        self,
        activity_level: float = 0.5,
        wake_state: str = "awake",
        phi: float = 0.5,
    ) -> GlialState:
        """
        Aggiorna la rete astrocitaria e calcola gli effetti gliali.

        Args:
            activity_level: attività cognitiva corrente [0.0–1.0]
                           (es. n_active_neurons/max_neurons)
            wake_state:    "awake" | "idle" | "deep_sleep"
            phi:           livello di integrazione informativa Φ corrente

        Returns:
            GlialState con tutti gli effetti modulatori
        """
        self._tick_count += 1

        # 1. Attiva astrociti proporzionalmente all'attività
        self._activate_astrocytes(activity_level)

        # 2. Propaga onde di calcio se Φ è elevato
        calcium_avg = self._propagate_if_high_phi(phi)

        # 3. Calcola plasticity boost da calcium wave
        plasticity_boost = self._compute_plasticity_boost(calcium_avg)

        # 4. Metabolic supply: rigenera riserve in base al wake_state
        metabolic_avg = self._update_metabolic(wake_state, activity_level)

        # 5. Glymphatic cleanup: molto più attivo in deep_sleep
        cleanup_rate = self._compute_cleanup_rate(wake_state)

        # 6. Coherence gain da calcium propagation
        coherence_gain = self._compute_coherence_gain(calcium_avg, phi)

        # 7. Conta astrociti attivi
        active = sum(
            1 for a in self._network.values()
            if a["calcium"] >= self._cfg.calcium_threshold
        )

        effect = GlialEffect(
            plasticity_boost=round(plasticity_boost, 3),
            metabolic_supply=round(metabolic_avg, 3),
            cleanup_rate=round(cleanup_rate, 3),
            coherence_gain=round(coherence_gain, 4),
            calcium_level=round(calcium_avg, 3),
            active_astrocytes=active,
        )

        metabolic_vals = [a["metabolic_reserve"] for a in self._network.values()]
        health = sum(metabolic_vals) / max(len(metabolic_vals), 1)
        crisis = health < 0.20

        state = GlialState(
            effect=effect,
            network_health=round(health, 3),
            metabolic_crisis=crisis,
            glymphatic_active=cleanup_rate >= 0.20,
            tick_count=self._tick_count,
        )

        logger.debug("[Glial] %s", state.summary())

        # Emetti evento se crisi metabolica
        if crisis:
            self._maybe_emit_repair()

        return state

    def stimulate(self, region: str, strength: float = 0.5) -> None:
        """Stimola direttamente un astrocita (simula attività in una regione)."""
        if region in self._network:
            node = self._network[region]
            node["calcium"] = min(1.0, node["calcium"] + strength)

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def network_status(self) -> Dict[str, Dict]:
        """Snapshot dello stato della rete astrocitaria."""
        return {
            region: {
                "calcium": round(node["calcium"], 3),
                "metabolic_reserve": round(node["metabolic_reserve"], 3),
            }
            for region, node in self._network.items()
        }

    # ── Metodi privati ────────────────────────────────────────────────────────

    def _build_network(self) -> Dict[str, Dict]:
        """
        Costruisce la rete astrocitaria interna.
        Fallback leggero se AstrocyteNetwork non è importabile.
        """
        network = {}
        for region in _SPEACE_REGIONS:
            network[region] = {
                "calcium":          0.0,
                "metabolic_reserve": 1.0,
                "connections":      [],
            }
        # Applica topologia
        for src, tgt in _CONNECTIVITY:
            if src in network and tgt in network:
                network[src]["connections"].append(tgt)
                network[tgt]["connections"].append(src)

        # Tenta di usare AstrocyteNetwork reale (optional)
        try:
            from cortex.astrocyte_network import AstrocyteNetwork, Astrocyte
            self._astro_net = AstrocyteNetwork("speace_glial", "long_range")
            for region in _SPEACE_REGIONS:
                self._astro_net.add_astrocyte(region, region)
            for src, tgt in _CONNECTIVITY:
                self._astro_net.connect(src, tgt)
            logger.info("[Glial] AstrocyteNetwork reale caricata (%d nodi)", len(_SPEACE_REGIONS))
        except Exception as e:
            self._astro_net = None
            logger.debug("[Glial] AstrocyteNetwork fallback (lightweight): %s", e)

        return network

    def _activate_astrocytes(self, activity: float) -> None:
        """Attiva gli astrociti in base all'attività cognitiva."""
        activation = activity * 0.3  # boost proporzionale (biologico: ~0.3)
        decay      = 0.05            # decadimento naturale del segnale Ca²⁺

        for node in self._network.values():
            node["calcium"] = max(0.0, node["calcium"] * (1 - decay) + activation)

    def _propagate_if_high_phi(self, phi: float) -> float:
        """
        Se Φ è alto (alta integrazione), propaga onde Ca²⁺ nella rete.
        Ritorna il livello di calcio medio dopo propagazione.
        """
        if phi > 0.5 and self._cfg.coherence_propagation:
            # Propagazione BFS-like: ogni nodo trasmette al 50% ai vicini
            for region, node in self._network.items():
                if node["calcium"] > self._cfg.calcium_threshold:
                    for neighbor in node["connections"]:
                        if neighbor in self._network:
                            self._network[neighbor]["calcium"] = min(
                                1.0,
                                self._network[neighbor]["calcium"] + node["calcium"] * 0.4
                            )

        calcium_vals = [n["calcium"] for n in self._network.values()]
        return sum(calcium_vals) / max(len(calcium_vals), 1)

    def _compute_plasticity_boost(self, calcium_avg: float) -> float:
        """
        Calcola il boost plasticità da segnale calcio.
        Biologico: Ca²⁺ → CAMKII → LTP (potenziamento a lungo termine).
        """
        if calcium_avg < self._cfg.calcium_threshold:
            return 1.0  # nessun boost
        # Boost lineare da soglia a max
        excess = (calcium_avg - self._cfg.calcium_threshold) / (1.0 - self._cfg.calcium_threshold)
        return 1.0 + self._cfg.plasticity_boost_max * excess

    def _update_metabolic(self, wake_state: str, activity: float) -> float:
        """
        Aggiorna la riserva metabolica degli astrociti.
        Biologico: lattato shuttle — astrociti forniscono lattato ai neuroni.
        In veglia: consumo proporzionale all'attività.
        In sleep: rigenerazione (astrociti restituiscono riserve).
        """
        regen  = self._cfg.metabolic_regen_rate
        consume = activity * 0.15  # consumo per alta attività

        for node in self._network.values():
            if wake_state in ("awake", "idle"):
                # Consumo + rigenerazione parziale
                node["metabolic_reserve"] = max(0.0, min(1.0,
                    node["metabolic_reserve"] - consume + regen * 0.3
                ))
            else:  # deep_sleep: rigenerazione piena
                node["metabolic_reserve"] = min(1.0,
                    node["metabolic_reserve"] + regen
                )

        reserves = [n["metabolic_reserve"] for n in self._network.values()]
        return sum(reserves) / max(len(reserves), 1)

    def _compute_cleanup_rate(self, wake_state: str) -> float:
        """
        Sistema glinfatico: clearance dei metaboliti tossici.
        Biologico: 10× più attivo in NREM sleep (deep sleep).
        """
        if wake_state == "deep_sleep":
            return self._cfg.cleanup_sleep_rate
        if wake_state == "idle":
            return self._cfg.cleanup_awake_rate * 2.0
        return self._cfg.cleanup_awake_rate

    def _compute_coherence_gain(self, calcium_avg: float, phi: float) -> float:
        """
        Guadagno di coerenza da calcium waves.
        Le onde Ca²⁺ sincronizzano compartimenti → Φ aumenta leggermente.
        """
        if calcium_avg < self._cfg.calcium_threshold:
            return 0.0
        # Guadagno massimo 0.05–0.15 Φ per onda forte
        base_gain = calcium_avg * 0.10
        phi_synergy = phi * 0.5  # più Φ c'è, più la sincronia è efficace
        return min(0.20, base_gain + phi_synergy * base_gain)

    def _maybe_emit_repair(self) -> None:
        """Emette REPAIR_STARTED su EventBus se crisi metabolica."""
        if self._bus is None:
            return
        try:
            from cortex.events import EventType, SPEACEEvent
            ev = SPEACEEvent(
                event_type=EventType.REPAIR_STARTED,
                source="glial_support",
                payload={"reason": "metabolic_crisis", "tick": self._tick_count},
                priority=2,
            )
            self._bus.publish(ev)
        except Exception as e:
            logger.debug("[Glial] EventBus emit failed: %s", e)


__all__ = [
    "GlialSupport",
    "GlialConfig",
    "GlialState",
    "GlialEffect",
]
