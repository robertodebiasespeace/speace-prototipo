"""
AttentionGating — M5.11 (Cognitive Autonomy)

Implementa il layer di Attention Gating per SPEACE Cortex.
Il gating decide quante risorse cognitive allocare a ciascuno stream
di input (neuroni/moduli) prima che arrivino ai processi decisionali.

Architettura a 3 livelli:

  L1 — Policy uniforme (M5.11, questo file):
       Tutti gli stream ricevono peso 1/N. Baseline senza bias.
       Utile come lower bound e per test di regressione.

  L2 — Policy salience-based (M5.11 esteso):
       Peso proporzionale alla "salience" dello stream
       (fitness delta, novelty, urgency drive).
       Formula: w_i = salience_i / Σ salience_j (softmax-free).

  L3 — Policy RL-driven (M5.12):
       Reward = ΔΦ(t) (aumento del C-index).
       UCB1 bandit: UCB_i = avg_r_i + C*sqrt(ln(t)/n_i).

Interfaccia unificata:
    gate = AttentionGating(policy="uniform")  # o "salience"
    weights = gate.compute(streams)           # dict stream_id → weight
    gate.update_reward(stream_id, reward)     # feedback per M5.12

Milestone: M5.11 + M5.12
Versione: 1.1 | 2026-04-26
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.attention.gating")


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class AttentionPolicy(str, Enum):
    UNIFORM  = "uniform"    # M5.11 — baseline: pesi identici
    SALIENCE = "salience"   # M5.11 — pesi proporzionali a salience
    RL       = "rl"         # M5.12 — RL-driven (UCB1 / ε-greedy), TODO


@dataclass
class AttentionStream:
    """
    Uno stream di input per il gating.

    id:       identificatore univoco (es. "safety_receptor", "smfoi_push")
    salience: valore [0, 1] indicante l'importanza dello stream
              (fitness delta, novelty, urgency). Usato dalla policy SALIENCE.
    value:    payload opzionale dello stream (non usato dal gating, passthrough)
    """
    id:       str
    salience: float = 0.5
    value:    Any   = None

    def __post_init__(self):
        self.salience = float(np.clip(self.salience, 0.0, 1.0))


@dataclass
class GatingResult:
    """Risultato del calcolo attention weights per un set di stream."""
    weights:    Dict[str, float]   # stream_id → peso normalizzato [0,1]
    policy:     AttentionPolicy
    n_streams:  int
    entropy:    float              # Shannon entropy dei pesi (bit)
    max_weight: float
    min_weight: float
    # Per M5.12: stream scelto come "focus" (peso massimo)
    focus_stream: Optional[str] = None


# ---------------------------------------------------------------------------
# AttentionGating
# ---------------------------------------------------------------------------

class AttentionGating:
    """
    Layer di Attention Gating per SPEACE Cortex.

    Gestisce l'allocazione dell'attenzione tra stream cognitivi.
    Policy uniforme (M5.11) come baseline; interfaccia pronta per
    policy RL-driven (M5.12).

    Usage:
        gate = AttentionGating(policy="uniform")
        streams = [AttentionStream("safety", salience=0.9),
                   AttentionStream("energy", salience=0.4)]
        result = gate.compute(streams)
        print(result.weights)  # {"safety": 0.5, "energy": 0.5}

        gate = AttentionGating(policy="salience")
        result = gate.compute(streams)
        # {"safety": 0.69, "energy": 0.31}  ← salience-weighted
    """

    # UCB1 exploration constant (per M5.12)
    _UCB_C: float = 1.414  # √2

    def __init__(
        self,
        policy:             AttentionPolicy | str = AttentionPolicy.UNIFORM,
        temperature:        float = 1.0,   # per softmax salience (riserva M5.12)
        min_weight:         float = 0.01,  # peso minimo garantito a ogni stream
        history_size:       int   = 100,   # ring buffer per statistiche
        diversity_threshold: float = 1.0,  # bit — soglia M5.13
    ) -> None:
        if isinstance(policy, str):
            policy = AttentionPolicy(policy)
        self.policy              = policy
        self.temperature         = temperature
        self.min_weight          = min_weight
        self.diversity_threshold = diversity_threshold

        # History per analytics
        self._weight_history: deque[Dict[str, float]] = deque(maxlen=history_size)
        self._entropy_history: deque[float]           = deque(maxlen=history_size)
        self._call_count = 0

        # M5.12 placeholder: reward accumulators per UCB1
        self._reward_sum:   Dict[str, float] = {}
        self._reward_count: Dict[str, int]   = {}

        logger.info("AttentionGating init: policy=%s min_w=%.2f", policy.value, min_weight)

    # ------------------------------------------------------------------ #
    # Core: compute weights
    # ------------------------------------------------------------------ #

    def compute(
        self,
        streams: Sequence[AttentionStream],
    ) -> GatingResult:
        """
        Calcola i pesi di attenzione per la sequenza di stream fornita.

        Args:
            streams: sequenza di AttentionStream da pesare.
                     L'ordine non influenza il risultato.

        Returns:
            GatingResult con weights normalizzati (sommano a 1.0).
        """
        if not streams:
            return GatingResult(
                weights={}, policy=self.policy, n_streams=0,
                entropy=0.0, max_weight=0.0, min_weight=0.0,
            )

        n = len(streams)
        ids = [s.id for s in streams]

        if self.policy == AttentionPolicy.UNIFORM:
            raw_weights = self._uniform(n)
        elif self.policy == AttentionPolicy.SALIENCE:
            raw_weights = self._salience_weighted(streams)
        elif self.policy == AttentionPolicy.RL:
            raw_weights = self._rl_ucb1(streams)
        else:
            raw_weights = self._uniform(n)

        # Applica min_weight floor e ri-normalizza
        floored = [max(w, self.min_weight) for w in raw_weights]
        total   = sum(floored)
        normed  = [w / total for w in floored]

        weights_dict = dict(zip(ids, normed))
        entropy      = self._shannon_entropy(normed)
        focus        = max(weights_dict, key=weights_dict.__getitem__)

        result = GatingResult(
            weights=weights_dict,
            policy=self.policy,
            n_streams=n,
            entropy=entropy,
            max_weight=max(normed),
            min_weight=min(normed),
            focus_stream=focus,
        )

        self._weight_history.append(weights_dict)
        self._entropy_history.append(entropy)
        self._call_count += 1

        logger.debug("Gating[%s] n=%d entropy=%.3f focus=%s",
                     self.policy.value, n, entropy, focus)
        return result

    # ------------------------------------------------------------------ #
    # Policy implementations
    # ------------------------------------------------------------------ #

    def _uniform(self, n: int) -> List[float]:
        """M5.11 — Policy uniforme: tutti i pesi = 1/N."""
        return [1.0 / n] * n

    def _salience_weighted(self, streams: Sequence[AttentionStream]) -> List[float]:
        """
        M5.11 — Policy salience: pesi proporzionali a salience_i.

        Formula: w_i = salience_i / Σ salience_j
        Gestisce il caso tutti-zero con fallback uniforme.
        """
        sal = [s.salience for s in streams]
        total = sum(sal)
        if total < 1e-9:
            return self._uniform(len(streams))
        return [s / total for s in sal]

    def _rl_ucb1(self, streams: Sequence[AttentionStream]) -> List[float]:
        """
        M5.12 — UCB1 bandit per attention allocation.

        Formula UCB1 per ogni stream i al passo t:
            UCB_i = avg_reward_i + C * sqrt(ln(t) / n_i)

        dove:
            avg_reward_i = media reward storico dello stream
            C            = UCB exploration constant (default √2)
            t            = numero totale di pull
            n_i          = numero di volte che stream i è stato scelto

        Stream non ancora selezionati ricevono UCB = +inf (esplorazione forzata).
        I pesi sono proporzionali ai valori UCB normalizzati su [0,1].

        Se nessuno stream ha reward storico → fallback uniforme.
        """
        n = len(streams)
        total_pulls = sum(self._reward_count.get(s.id, 0) for s in streams)

        if total_pulls == 0:
            # Prima esplorazione: pesi uniformi
            return self._uniform(n)

        ucb_values = []
        for s in streams:
            count = self._reward_count.get(s.id, 0)
            if count == 0:
                # Stream mai esplorato → esplorazione forzata
                ucb_values.append(float('inf'))
            else:
                avg_r = self._reward_sum.get(s.id, 0.0) / count
                # Normalizza avg_r da [-1,1] a [0,1] per UCB positivo
                avg_r_norm = (avg_r + 1.0) / 2.0
                explore    = self._UCB_C * math.sqrt(math.log(total_pulls + 1) / count)
                ucb_values.append(avg_r_norm + explore)

        # Gestisci inf: se tutti sono inf, uniforme
        finite = [v for v in ucb_values if math.isfinite(v)]
        if not finite:
            return self._uniform(n)

        # Sostituisci inf con max_finite * 2 per softmax-safe normalizzazione
        max_finite = max(finite)
        ucb_clipped = [v if math.isfinite(v) else max_finite * 2.0 for v in ucb_values]

        # Normalizza a pesi sommanti a 1
        total = sum(ucb_clipped)
        if total < 1e-12:
            return self._uniform(n)
        return [v / total for v in ucb_clipped]

    # ------------------------------------------------------------------ #
    # M5.12 interface: reward feedback
    # ------------------------------------------------------------------ #

    def update_reward(self, stream_id: str, reward: float) -> None:
        """
        M5.12 — Registra il reward per uno stream dopo l'esecuzione.
        Reward = ΔΦ(t) (aumento del C-index) o altro segnale scalare.
        In M5.11 accumula ma non aggiorna i pesi (UCB1 non attivo).
        """
        reward = float(np.clip(reward, -1.0, 1.0))
        if stream_id not in self._reward_sum:
            self._reward_sum[stream_id]   = 0.0
            self._reward_count[stream_id] = 0
        self._reward_sum[stream_id]   += reward
        self._reward_count[stream_id] += 1

    def get_reward_stats(self) -> Dict[str, Dict[str, float]]:
        """Statistiche reward accumulate (per diagnostica M5.12)."""
        stats = {}
        for sid in self._reward_sum:
            n   = max(1, self._reward_count[sid])
            avg = self._reward_sum[sid] / n
            stats[sid] = {"total": self._reward_sum[sid],
                          "count": float(n), "avg": avg}
        return stats

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #

    @staticmethod
    def _shannon_entropy(weights: List[float]) -> float:
        """Shannon entropy in bit dei pesi di attenzione."""
        h = 0.0
        for w in weights:
            if w > 1e-12:
                h -= w * math.log2(w)
        return round(h, 4)

    def diversity_ok(self) -> bool:
        """
        M5.13 — Verifica che l'entropia media sia ≥ diversity_threshold (bit).
        True se il gating non è troppo concentrato su un unico stream.
        """
        if not self._entropy_history:
            return True
        avg_entropy = float(np.mean(list(self._entropy_history)))
        return avg_entropy >= self.diversity_threshold

    def get_stats(self) -> Dict[str, Any]:
        """Statistiche globali del gating layer."""
        h_list = list(self._entropy_history)
        return {
            "policy":          self.policy.value,
            "call_count":      self._call_count,
            "avg_entropy":     round(float(np.mean(h_list)), 4) if h_list else 0.0,
            "min_entropy":     round(float(np.min(h_list)), 4) if h_list else 0.0,
            "diversity_ok":    self.diversity_ok(),
            "diversity_threshold": self.diversity_threshold,
            "n_stream_rewards": len(self._reward_sum),
        }

    def reset_history(self) -> None:
        """Reset ring buffer statistiche (non tocca reward accumulati)."""
        self._weight_history.clear()
        self._entropy_history.clear()
        self._call_count = 0

    def __repr__(self) -> str:
        s = self.get_stats()
        return (f"AttentionGating(policy={s['policy']}, "
                f"calls={s['call_count']}, "
                f"avg_entropy={s['avg_entropy']:.3f}, "
                f"diversity_ok={s['diversity_ok']})")


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_uniform_gating(min_weight: float = 0.01) -> AttentionGating:
    """Crea un gating con policy uniforme (M5.11 baseline)."""
    return AttentionGating(policy=AttentionPolicy.UNIFORM, min_weight=min_weight)


def create_salience_gating(min_weight: float = 0.01) -> AttentionGating:
    """Crea un gating con policy salience-weighted (M5.11 esteso)."""
    return AttentionGating(policy=AttentionPolicy.SALIENCE, min_weight=min_weight)


__all__ = [
    "AttentionPolicy",
    "AttentionStream",
    "GatingResult",
    "AttentionGating",
    "create_uniform_gating",
    "create_salience_gating",
]
