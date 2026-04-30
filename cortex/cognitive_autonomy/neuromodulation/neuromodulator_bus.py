"""
cortex.cognitive_autonomy.neuromodulation.neuromodulator_bus
=============================================================
M15.2 — NeuromodulatorBus: sistema di neuromodulazione globale.

Principio biologico:
  4 neurotrasmettitori principali modulano GLOBALMENTE tutti i sistemi cerebrali:
  - Dopamina (DA)   → apprendimento, ricompensa, motivazione, curiosità
  - Serotonina (5HT) → stabilità, umore, regolazione impulsi, consol. memoria
  - Noradrenalina (NE) → arousal, attenzione, stress response, plasticità
  - Acetilcolina (ACh) → plasticità sinaptica, attenzione, memoria lavoro

  Questi NON sono segnali locali: vengono trasmessi broadcast a TUTTI i moduli.
  Ogni modulo ha recettori con sensibilità diversa per ogni neurotrasmettitore.

Implementazione SPEACE:
  Il NeuromodulatorBus calcola i livelli dei 4 neurotrasmettitori da:
    - Viability (homeostasi) → dopamina + serotonina
    - Curiosity (drive) → dopamina + noradrenalina
    - Emergence score → acetilcolina (plasticità apprendimento)
    - Valence (emozione) → serotonina + noradrenalina

  Poi li broadcast a tutti i moduli registrati come modificatori.

Effetti:
  Dopamina alta  → learning_rate +, exploration +, reward sensitivity +
  Serotonina alta → stability +, consolidation +, risk_aversion +
  Noradrenalina alta → attention_gain +, arousal +, signal_noise_ratio +
  Acetilcolina alta → plasticity +, working_memory_capacity +, STDP gain +
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Livelli neurotrasmettitori ────────────────────────────────────────────────

@dataclass
class NeuromodulatorLevels:
    """Livelli correnti dei 4 neurotrasmettitori principali [0, 1]."""
    dopamine:       float = 0.5    # DA — ricompensa, motivazione
    serotonin:      float = 0.5    # 5HT — stabilità, umore
    norepinephrine: float = 0.5    # NE — arousal, attenzione
    acetylcholine:  float = 0.5    # ACh — plasticità, working memory

    def to_dict(self) -> dict:
        return {
            "dopamine":       round(self.dopamine, 4),
            "serotonin":      round(self.serotonin, 4),
            "norepinephrine": round(self.norepinephrine, 4),
            "acetylcholine":  round(self.acetylcholine, 4),
        }

    def clamp(self) -> None:
        self.dopamine       = max(0.0, min(1.0, self.dopamine))
        self.serotonin      = max(0.0, min(1.0, self.serotonin))
        self.norepinephrine = max(0.0, min(1.0, self.norepinephrine))
        self.acetylcholine  = max(0.0, min(1.0, self.acetylcholine))


# ── Effetti modulatori ────────────────────────────────────────────────────────

@dataclass
class ModulatoryEffect:
    """
    Effetto computato per un modulo dopo broadcast neuromodulatorio.
    Ogni campo è un moltiplicatore [0.5, 2.0] da applicare al modulo.
    """
    learning_rate_mult:   float = 1.0    # DA
    exploration_mult:     float = 1.0    # DA + NE
    stability_mult:       float = 1.0    # 5HT
    consolidation_mult:   float = 1.0    # 5HT
    attention_gain:       float = 1.0    # NE
    arousal_mult:         float = 1.0    # NE
    plasticity_mult:      float = 1.0    # ACh
    working_mem_capacity: float = 1.0    # ACh

    def to_dict(self) -> dict:
        return {
            "learning_rate":     round(self.learning_rate_mult, 4),
            "exploration":       round(self.exploration_mult, 4),
            "stability":         round(self.stability_mult, 4),
            "consolidation":     round(self.consolidation_mult, 4),
            "attention_gain":    round(self.attention_gain, 4),
            "arousal":           round(self.arousal_mult, 4),
            "plasticity":        round(self.plasticity_mult, 4),
            "working_memory":    round(self.working_mem_capacity, 4),
        }


# ── Recettore modulo ──────────────────────────────────────────────────────────

@dataclass
class ModuleReceptor:
    """Sensibilità di un modulo ai 4 neurotrasmettitori."""
    name: str
    da_sensitivity:  float = 1.0   # dopamina
    ht_sensitivity:  float = 1.0   # serotonina
    ne_sensitivity:  float = 1.0   # noradrenalina
    ach_sensitivity: float = 1.0   # acetilcolina
    # Callback opzionale: chiamata con ModulatoryEffect ad ogni broadcast
    on_modulate: Optional[Callable[[ModulatoryEffect], None]] = None


# ── Configurazione bus ────────────────────────────────────────────────────────

@dataclass
class NeuromodulatorConfig:
    """Parametri del neuromodulator bus."""
    ema_alpha: float = 0.20          # smoothing EMA dei livelli
    baseline: float  = 0.50          # livello a riposo
    max_delta: float = 0.30          # variazione massima per ciclo
    history_max: int = 100           # storico rolling


# ── NeuromodulatorBus ─────────────────────────────────────────────────────────

class NeuromodulatorBus:
    """
    Bus globale di neuromodulazione per SPEACE Cortex.

    Ogni ciclo cognitivo:
      1. update(state_dict) → aggiorna i livelli DA/5HT/NE/ACh
         dallo stato cognitivo corrente (viability, curiosity, valence, ecc.)
      2. broadcast() → invia ModulatoryEffect a tutti i moduli registrati
      3. get_effect(module) → ritorna l'effetto per un modulo specifico

    Mapping biologico stato → neurotrasmettitore:
      viability (alto) → 5HT ↑ (sistema stabile, no stress)
      viability (basso) → NE ↑ (alert, stress response)
      curiosity (alto) → DA ↑ (reward anticipation) + NE ↑
      emergence_score → ACh ↑ (più si apprende → più plasticità)
      valence (positiva) → DA ↑ + 5HT ↑
      valence (negativa) → NE ↑ + DA ↓
    """

    def __init__(self, config: Optional[NeuromodulatorConfig] = None):
        self.config   = config or NeuromodulatorConfig()
        self._levels  = NeuromodulatorLevels()
        self._modules: Dict[str, ModuleReceptor] = {}
        self._cycle   = 0
        self._history: List[NeuromodulatorLevels] = []
        self._last_effect: Dict[str, ModulatoryEffect] = {}

    # ── Registrazione moduli ─────────────────────────────────────────────────

    def register(
        self,
        name: str,
        da_sensitivity: float = 1.0,
        ht_sensitivity: float = 1.0,
        ne_sensitivity: float = 1.0,
        ach_sensitivity: float = 1.0,
        on_modulate: Optional[Callable] = None,
    ) -> bool:
        if name in self._modules:
            return False
        self._modules[name] = ModuleReceptor(
            name=name,
            da_sensitivity=da_sensitivity,
            ht_sensitivity=ht_sensitivity,
            ne_sensitivity=ne_sensitivity,
            ach_sensitivity=ach_sensitivity,
            on_modulate=on_modulate,
        )
        return True

    # ── Aggiornamento livelli ────────────────────────────────────────────────

    def update(self, state: Dict[str, float]) -> NeuromodulatorLevels:
        """
        Aggiorna i livelli neuromodulatori dallo stato cognitivo.

        state keys (tutti opzionali, default=0.5):
          viability, curiosity, valence, emergence_score,
          energy_level, alignment_score, stress
        """
        cfg = self.config
        α   = cfg.ema_alpha
        b   = cfg.baseline
        d   = cfg.max_delta

        viability      = state.get("viability", 0.5)
        curiosity      = state.get("curiosity", 0.5)
        valence        = state.get("valence", 0.0)       # [-1, 1]
        emergence      = state.get("emergence_score", 0.5)
        energy         = state.get("energy_level", 0.5)
        alignment      = state.get("alignment_score", 0.5)

        # Normalizza valence [-1,1] → [0,1]
        valence_norm = (valence + 1.0) / 2.0

        # ── Calcola target per ogni neurotrasmettitore ──────────────────────
        # Dopamina: curiosity + valence positiva + alignment alto
        da_target = b + d * (
            0.40 * curiosity +
            0.35 * valence_norm +
            0.25 * alignment
        ) - d * 0.5

        # Serotonina: viability alta + basso stress + energia buona
        ht_target = b + d * (
            0.50 * viability +
            0.30 * energy +
            0.20 * (1.0 - curiosity)  # troppa curiosità abbassa 5HT (impulsività)
        ) - d * 0.3

        # Noradrenalina: bassa viability + alta curiosità + bassa energia
        ne_stress = 1.0 - viability
        ne_target = b + d * (
            0.45 * ne_stress +
            0.30 * curiosity +
            0.25 * (1.0 - energy)
        ) - d * 0.2

        # Acetilcolina: emergence score + viability media (ottimo apprendimento)
        ach_target = b + d * (
            0.60 * emergence +
            0.40 * min(viability, 1.0 - viability) * 2  # picco a viability=0.5
        ) - d * 0.1

        # ── EMA smoothing ───────────────────────────────────────────────────
        self._levels.dopamine       = (1 - α) * self._levels.dopamine       + α * da_target
        self._levels.serotonin      = (1 - α) * self._levels.serotonin      + α * ht_target
        self._levels.norepinephrine = (1 - α) * self._levels.norepinephrine + α * ne_target
        self._levels.acetylcholine  = (1 - α) * self._levels.acetylcholine  + α * ach_target
        self._levels.clamp()

        # Storico
        import copy
        self._history.append(copy.copy(self._levels))
        if len(self._history) > cfg.history_max:
            self._history.pop(0)

        return self._levels

    # ── Broadcast ────────────────────────────────────────────────────────────

    def broadcast(self) -> Dict[str, ModulatoryEffect]:
        """
        Invia gli effetti modulatori a tutti i moduli registrati.
        Ritorna dict {module_name: ModulatoryEffect}.
        """
        self._cycle += 1
        effects: Dict[str, ModulatoryEffect] = {}
        lv = self._levels

        for name, receptor in self._modules.items():
            # Scala i livelli per la sensibilità del modulo
            da  = lv.dopamine       * receptor.da_sensitivity
            ht  = lv.serotonin      * receptor.ht_sensitivity
            ne  = lv.norepinephrine * receptor.ne_sensitivity
            ach = lv.acetylcholine  * receptor.ach_sensitivity

            # Calcola moltiplicatori [0.5, 2.0] (1.0 = nessun effetto)
            effect = ModulatoryEffect(
                learning_rate_mult   = 0.5 + da * 1.5,        # DA: 0.5→2.0
                exploration_mult     = 0.5 + (da + ne)/2,     # DA+NE
                stability_mult       = 0.5 + ht * 1.5,        # 5HT: 0.5→2.0
                consolidation_mult   = 0.5 + ht,              # 5HT: 0.5→1.5
                attention_gain       = 0.5 + ne * 1.5,        # NE: 0.5→2.0
                arousal_mult         = 0.5 + ne,              # NE: 0.5→1.5
                plasticity_mult      = 0.5 + ach * 1.5,       # ACh: 0.5→2.0
                working_mem_capacity = 0.5 + ach,             # ACh: 0.5→1.5
            )
            effects[name] = effect
            self._last_effect[name] = effect

            # Callback
            if receptor.on_modulate is not None:
                try:
                    receptor.on_modulate(effect)
                except Exception as e:
                    logger.warning(f"[NeuromodBus] callback errore {name}: {e}")

        return effects

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_levels(self) -> NeuromodulatorLevels:
        return self._levels

    def get_effect(self, module_name: str) -> Optional[ModulatoryEffect]:
        return self._last_effect.get(module_name)

    def get_dominant_neuromodulator(self) -> str:
        lv = self._levels
        best = max(
            [("dopamine", lv.dopamine), ("serotonin", lv.serotonin),
             ("norepinephrine", lv.norepinephrine), ("acetylcholine", lv.acetylcholine)],
            key=lambda x: x[1]
        )
        return best[0]

    def get_stats(self) -> dict:
        return {
            "cycle":        self._cycle,
            "n_modules":    len(self._modules),
            "levels":       self._levels.to_dict(),
            "dominant":     self.get_dominant_neuromodulator(),
            "last_effects": {n: e.to_dict() for n, e in self._last_effect.items()},
        }
