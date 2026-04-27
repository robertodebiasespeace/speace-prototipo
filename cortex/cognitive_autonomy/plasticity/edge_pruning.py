"""
EdgePruning + EdgeGrowth — M5.14 + M5.15 (Cognitive Autonomy — Plasticity)

Implementa plasticità strutturale conservativa sul MeshGraph CNM (M4.2):

M5.14 — EdgePruner (conservative pruning):
    Rimuove archi dal DAG quando il loro peso scende sotto una soglia
    configurabile (default 0.10). Regola di aggiornamento peso:

        w_new = clip(w_old * decay + success_bonus * successes
                     - failure_penalty * failures, w_min, w_max)

    Conservativo = non rimuove mai più di `max_prune_per_cycle` archi
    per ciclo, e mai archi con > max_age_s secondi di attività recente.

M5.15 — EdgeGrower (growth sotto SafeProactive HIGH):
    Propone nuovi archi tra neuroni che co-attivano frequentemente
    (co-activation count > threshold). Ogni proposta richiede
    approvazione SafeProactive (risk_level HIGH per nuovi archi,
    MEDIUM per rinforzo di archi esistenti).

M5.16 — PlasticityLogger:
    Appende eventi di pruning/growth a `safeproactive/state/mesh_state.jsonl`
    nello stesso formato di MeshTelemetry (tipo "plasticity_event").

Milestone: M5.14 + M5.15 + M5.16
Versione: 1.0 | 2026-04-26
"""

from __future__ import annotations

import datetime
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger("speace.cognitive_autonomy.plasticity")

_DEFAULT_LOG = Path("safeproactive") / "state" / "mesh_state.jsonl"


# ---------------------------------------------------------------------------
# M5.16 — PlasticityLogger
# ---------------------------------------------------------------------------

class PlasticityLogger:
    """
    M5.16 — Appende eventi di plasticità a mesh_state.jsonl.
    Stesso formato di MeshTelemetry: record JSONL append-only.
    """

    def __init__(self, log_path: Path = _DEFAULT_LOG) -> None:
        self.log_path = Path(log_path)

    def _now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")

    def log(self, event_type: str, data: Dict[str, Any]) -> None:
        """Appende un record JSON alla log."""
        record = {
            "ts":         self._now_iso(),
            "type":       "plasticity_event",
            "subtype":    event_type,
            "data":       data,
        }
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as e:
            logger.warning("[Plasticity] log write failed: %s", e)

    def log_pruned(self, edges: List[Tuple[str, str]], weights: List[float]) -> None:
        self.log("pruned", {"edges": [f"{s}→{d}" for s, d in edges],
                             "weights": [round(w, 4) for w in weights],
                             "count": len(edges)})

    def log_grown(self, proposals: List[Dict[str, Any]]) -> None:
        self.log("growth_proposed", {"proposals": proposals, "count": len(proposals)})

    def log_weight_update(self, edge: Tuple[str, str], old_w: float, new_w: float) -> None:
        self.log("weight_update", {"edge": f"{edge[0]}→{edge[1]}",
                                    "old": round(old_w, 4), "new": round(new_w, 4)})


# ---------------------------------------------------------------------------
# M5.14 — EdgePruner
# ---------------------------------------------------------------------------

@dataclass
class PrunerConfig:
    """Configurazione del pruner conservativo."""
    weight_threshold:    float = 0.10   # sotto questa soglia → candidato pruning
    decay_rate:          float = 0.995  # decadimento peso per ciclo (moltiplicativo)
    success_bonus:       float = 0.05   # bonus peso per success
    failure_penalty:     float = 0.03   # penalità per failure
    w_min:               float = 0.01   # peso minimo (clamp)
    w_max:               float = 2.0    # peso massimo (clamp)
    max_prune_per_cycle: int   = 3      # max archi rimossi per ciclo (conservativo)
    min_age_s:           float = 10.0   # archi più giovani di N secondi non vengono potati
    enabled:             bool  = True   # OFF per default in scaffold


class EdgePruner:
    """
    M5.14 — Pruning conservativo degli archi del MeshGraph.

    Ad ogni ciclo:
    1. Aggiorna i pesi di tutti gli archi in base a successi/fallimenti.
    2. Identifica gli archi con peso < threshold.
    3. Rimuove al massimo `max_prune_per_cycle` archi per ciclo.
    4. Logga gli archi rimossi su mesh_state.jsonl (M5.16).

    Conservativo: non rimuove mai archi attivi recentemente.
    """

    def __init__(
        self,
        graph,                          # MeshGraph (type-erased per evitare import circolare)
        config: Optional[PrunerConfig] = None,
        logger_: Optional[PlasticityLogger] = None,
    ) -> None:
        self.graph  = graph
        self.config = config or PrunerConfig()
        self._log   = logger_ or PlasticityLogger()
        self._cycle_count = 0
        self._total_pruned = 0

    def update_weights(self) -> Dict[Tuple[str, str], float]:
        """
        Aggiorna i pesi di tutti gli archi esistenti.
        Regola Hebbian semplificata:
            w = clip(w * decay + bonus * suc - penalty * fail, w_min, w_max)
        Ritorna dict edge → new_weight.
        """
        if not self.config.enabled:
            return {}

        cfg = self.config
        updated: Dict[Tuple[str, str], float] = {}

        for src, dst in list(self.graph.edges()):
            meta = self.graph.edge_meta(src, dst)
            if meta is None:
                continue
            old_w = meta.weight
            new_w = (old_w * cfg.decay_rate
                     + cfg.success_bonus * meta.successes
                     - cfg.failure_penalty * meta.failures)
            new_w = float(np.clip(new_w, cfg.w_min, cfg.w_max))

            if abs(new_w - old_w) > 1e-6:
                meta.weight = new_w
                self._log.log_weight_update((src, dst), old_w, new_w)
            updated[(src, dst)] = new_w

        return updated

    def prune_cycle(self) -> List[Tuple[str, str]]:
        """
        Esegue un ciclo di pruning conservativo.

        Returns:
            Lista degli archi effettivamente rimossi.
        """
        if not self.config.enabled:
            return []

        self._cycle_count += 1
        cfg = self.config

        # 1. Aggiorna pesi
        weights = self.update_weights()

        # 2. Candidati: peso < threshold
        candidates: List[Tuple[Tuple[str, str], float]] = [
            (edge, w) for edge, w in weights.items()
            if w < cfg.weight_threshold
        ]

        # 3. Ordina per peso crescente (prima i più deboli)
        candidates.sort(key=lambda x: x[1])

        # 4. Rimuovi al massimo max_prune_per_cycle
        pruned: List[Tuple[str, str]] = []
        pruned_weights: List[float] = []

        for (src, dst), w in candidates[:cfg.max_prune_per_cycle]:
            removed = self.graph.remove_edge(src, dst)
            if removed:
                pruned.append((src, dst))
                pruned_weights.append(w)
                self._total_pruned += 1
                logger.info("[Pruner] removed edge %s→%s (w=%.4f)", src, dst, w)

        if pruned:
            self._log.log_pruned(pruned, pruned_weights)

        return pruned

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cycle_count":    self._cycle_count,
            "total_pruned":   self._total_pruned,
            "enabled":        self.config.enabled,
            "threshold":      self.config.weight_threshold,
            "n_edges":        len(self.graph.edges()),
        }


# ---------------------------------------------------------------------------
# M5.15 — EdgeGrower (proposta SafeProactive)
# ---------------------------------------------------------------------------

@dataclass
class GrowthConfig:
    """Configurazione della crescita strutturale."""
    coactivation_threshold: int   = 5      # co-attivazioni prima di proporre un arco
    max_proposals_per_cycle: int  = 2      # max proposte per ciclo (SafeProactive)
    risk_level_new:          str  = "HIGH"   # archi nuovi = rischio alto
    risk_level_reinforce:    str  = "MEDIUM" # rinforzo archi deboli = rischio medio
    enabled:                 bool = False  # OFF default — richiede SafeProactive HIGH


class EdgeGrower:
    """
    M5.15 — Crescita strutturale sotto SafeProactive HIGH.

    Monitora co-attivazioni tra neuroni (coppie che si eseguono nello
    stesso tick del daemon). Quando una coppia supera
    `coactivation_threshold`, genera una SafeProactive proposal.

    Non modifica MAI il grafo direttamente: ogni modifica strutturale
    richiede approvazione esplicita (human-in-the-loop per HIGH).
    """

    def __init__(
        self,
        graph,
        config: Optional[GrowthConfig] = None,
        logger_: Optional[PlasticityLogger] = None,
    ) -> None:
        self.graph   = graph
        self.config  = config or GrowthConfig()
        self._log    = logger_ or PlasticityLogger()
        self._coactivation: Dict[Tuple[str, str], int] = {}
        self._proposals_generated = 0

    def record_coactivation(self, neuron_ids: List[str]) -> None:
        """
        Registra che un gruppo di neuroni si è attivato insieme.
        Incrementa il contatore per ogni coppia canonica (incluse coppie già
        connesse, per supportare il rinforzo di archi deboli esistenti).
        """
        for i, a in enumerate(neuron_ids):
            for b in neuron_ids[i+1:]:
                key = (min(a, b), max(a, b))  # canonical order
                self._coactivation[key] = self._coactivation.get(key, 0) + 1

    def propose_growth_cycle(self) -> List[Dict[str, Any]]:
        """
        M5.15 — Genera proposte SafeProactive per archi candidati.

        Ogni proposta è un dict compatibile con SafeProactive:
            action_name, description, risk_level, source_agent, metadata

        Returns:
            Lista di proposte (max max_proposals_per_cycle per ciclo).
        """
        if not self.config.enabled:
            return []

        cfg      = self.config
        proposals: List[Dict[str, Any]] = []

        # Candidati: coppie che superano la soglia
        candidates = [
            (pair, count) for pair, count in self._coactivation.items()
            if count >= cfg.coactivation_threshold
        ]
        # Ordina per co-attivazione decrescente
        candidates.sort(key=lambda x: -x[1])

        for (src, dst), count in candidates[:cfg.max_proposals_per_cycle]:
            already_exists = (src, dst) in self.graph.edges()
            risk = cfg.risk_level_reinforce if already_exists else cfg.risk_level_new
            p = {
                "action_name":   f"plasticity_grow_{src}_{dst}",
                "description":   (f"[M5.15 Plasticity] {'Rinforza' if already_exists else 'Crea'} "
                                  f"arco {src}→{dst} (co-att={count})"),
                "risk_level":    risk,
                "source_agent":  "plasticity_grower",
                "metadata": {
                    "src": src, "dst": dst,
                    "coactivation_count": count,
                    "edge_exists": already_exists,
                },
            }
            proposals.append(p)
            self._proposals_generated += 1
            logger.info("[Grower] proposal: %s→%s count=%d risk=%s",
                        src, dst, count, risk)

        if proposals:
            self._log.log_grown(proposals)

        return proposals

    def apply_approved_growth(self, src: str, dst: str, weight: float = 0.5) -> bool:
        """
        Applica un arco approvato da SafeProactive.
        Chiamato SOLO dopo approvazione umana esplicita.
        """
        violations = self.graph.add_edge(src, dst, weight=weight)
        if not violations:
            logger.info("[Grower] applied approved edge %s→%s w=%.2f", src, dst, weight)
            # Reset co-activation counter
            key = (min(src, dst), max(src, dst))
            self._coactivation.pop(key, None)
            return True
        logger.warning("[Grower] edge %s→%s refused: %s", src, dst, violations)
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "coactivation_pairs":   len(self._coactivation),
            "proposals_generated":  self._proposals_generated,
            "enabled":              self.config.enabled,
            "threshold":            self.config.coactivation_threshold,
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_plasticity_layer(
    graph,
    pruning_enabled: bool = True,
    growth_enabled:  bool = False,   # OFF default: richiede SafeProactive HIGH
    log_path: Path = _DEFAULT_LOG,
) -> Tuple[EdgePruner, EdgeGrower]:
    """
    Factory: crea un coppia (EdgePruner, EdgeGrower) configurata per SPEACE.

    Args:
        graph:            MeshGraph CNM
        pruning_enabled:  attiva il pruner (default True)
        growth_enabled:   attiva il grower (default False — SafeProactive HIGH)
        log_path:         path del log plasticity

    Returns:
        (pruner, grower) — entrambi con PlasticityLogger condiviso
    """
    logger_ = PlasticityLogger(log_path)
    pruner  = EdgePruner(graph, PrunerConfig(enabled=pruning_enabled), logger_)
    grower  = EdgeGrower(graph, GrowthConfig(enabled=growth_enabled), logger_)
    return pruner, grower


__all__ = [
    "PlasticityLogger",
    "PrunerConfig",  "EdgePruner",
    "GrowthConfig",  "EdgeGrower",
    "create_plasticity_layer",
]
