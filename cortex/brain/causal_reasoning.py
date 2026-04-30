"""
SPEACE Causal Reasoning – BRN-017
===================================
Pearl's Causal Hierarchy: Association → Intervention → Counterfactual.

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import copy
import logging
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CausalLevel(Enum):
    ASSOCIATION     = 1
    INTERVENTION    = 2
    COUNTERFACTUAL  = 3


class EdgeMechanism(Enum):
    LINEAR      = "linear"
    THRESHOLD   = "threshold"
    INHIBITORY  = "inhibitory"
    MODULATORY  = "modulatory"
    UNKNOWN     = "unknown"


@dataclass
class CausalNode:
    node_id:  str
    name:     str
    value:    Optional[float] = None
    noise:    float = 0.0
    domain:   str   = "unknown"
    observed: bool  = False

    def set_value(self, v: float) -> None:
        self.value = v
        self.observed = True


@dataclass
class CausalEdge:
    source:     str
    target:     str
    strength:   float = 0.5
    mechanism:  EdgeMechanism = EdgeMechanism.LINEAR
    lag:        float = 0.0
    confidence: float = 1.0
    learned:    bool  = False

    def compute_effect(self, parent_value: float) -> float:
        if self.mechanism == EdgeMechanism.LINEAR:
            return self.strength * parent_value
        elif self.mechanism == EdgeMechanism.THRESHOLD:
            return self.strength if parent_value > 0.5 else 0.0
        elif self.mechanism == EdgeMechanism.INHIBITORY:
            return -self.strength * parent_value
        elif self.mechanism == EdgeMechanism.MODULATORY:
            return parent_value ** (1.0 + self.strength * 0.5)
        return self.strength * parent_value


class CausalGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge]      = []
        self._adj:  Dict[str, List[str]]  = defaultdict(list)
        self._radj: Dict[str, List[str]]  = defaultdict(list)

    def add_node(self, node: CausalNode) -> None:
        self.nodes[node.node_id] = node

    def ensure_node(self, node_id: str, name: Optional[str] = None,
                    domain: str = "unknown") -> CausalNode:
        if node_id not in self.nodes:
            self.nodes[node_id] = CausalNode(
                node_id=node_id, name=name or node_id, domain=domain)
        return self.nodes[node_id]

    def add_edge(self, edge: CausalEdge) -> None:
        for e in self.edges:
            if e.source == edge.source and e.target == edge.target:
                e.strength   = edge.strength
                e.confidence = edge.confidence
                return
        self.edges.append(edge)
        self._adj[edge.source].append(edge.target)
        self._radj[edge.target].append(edge.source)

    def remove_edge(self, source: str, target: str) -> bool:
        before = len(self.edges)
        self.edges = [e for e in self.edges
                      if not (e.source == source and e.target == target)]
        self._adj[source]  = [t for t in self._adj[source]  if t != target]
        self._radj[target] = [s for s in self._radj[target] if s != source]
        return len(self.edges) < before

    def parents(self, node_id: str) -> List[str]:
        return list(self._radj.get(node_id, []))

    def children(self, node_id: str) -> List[str]:
        return list(self._adj.get(node_id, []))

    def ancestors(self, node_id: str) -> Set[str]:
        result: Set[str] = set()
        queue  = deque(self.parents(node_id))
        while queue:
            n = queue.popleft()
            if n not in result:
                result.add(n)
                queue.extend(self.parents(n))
        return result

    def descendants(self, node_id: str) -> Set[str]:
        result: Set[str] = set()
        queue  = deque(self.children(node_id))
        while queue:
            n = queue.popleft()
            if n not in result:
                result.add(n)
                queue.extend(self.children(n))
        return result

    def topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {n: 0 for n in self.nodes}
        for e in self.edges:
            in_degree[e.target] = in_degree.get(e.target, 0) + 1
        queue = deque(n for n, d in in_degree.items() if d == 0)
        order: List[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for child in self.children(n):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return order if len(order) == len(self.nodes) else []

    def is_dag(self) -> bool:
        return len(self.topological_sort()) == len(self.nodes)

    def propagate(self, root: Optional[str] = None) -> Dict[str, float]:
        order = self.topological_sort()
        if not order:
            logger.warning("[CausalGraph] Ciclo rilevato, propagazione impossibile")
            return {}
        results: Dict[str, float] = {}
        edge_map: Dict[Tuple[str, str], CausalEdge] = {
            (e.source, e.target): e for e in self.edges
        }
        for nid in order:
            node = self.nodes[nid]
            if node.observed:
                results[nid] = node.value or 0.0
                continue
            contrib = node.noise
            for parent_id in self.parents(nid):
                edge = edge_map.get((parent_id, nid))
                if edge and parent_id in results:
                    contrib += edge.compute_effect(results[parent_id])
            node.value = 1.0 / (1.0 + math.exp(-contrib + 0.5))
            results[nid] = node.value
        return results

    def do_operator(self, node_id: str, value: float) -> "CausalGraph":
        """
        Applica l'intervento do(node_id = value) — Pearl do-calculus.
        1. Crea copia del grafo
        2. Rimuove tutti gli archi entranti nel nodo (taglia backdoor path)
        3. Fissa il valore del nodo
        Ritorna grafo mutilato (originale non modificato).
        """
        g = copy.deepcopy(self)
        if node_id not in g.nodes:
            logger.warning(f"[do_operator] nodo '{node_id}' non trovato")
            return g
        for parent_id in list(g.parents(node_id)):
            g.remove_edge(parent_id, node_id)
        g.nodes[node_id].set_value(value)
        logger.debug(f"[do_operator] do({node_id}={value:.3f})")
        return g

    def copy(self) -> "CausalGraph":
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: {"name": n.name, "value": n.value, "domain": n.domain}
                      for nid, n in self.nodes.items()},
            "edges": [{"source": e.source, "target": e.target,
                       "strength": round(e.strength, 4),
                       "mechanism": e.mechanism.value,
                       "confidence": round(e.confidence, 4)}
                      for e in self.edges],
        }


class CausalLearner:
    """
    Apprende struttura causale da dati osservazionali (algoritmo PC semplificato).
    Inferisce direzione causale tramite Granger causality (lag-1 cross-correlation).
    """

    def __init__(self, min_samples: int = 10, min_correlation: float = 0.3) -> None:
        self._observations: deque = deque(maxlen=500)
        self._time_series:  Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.min_samples   = min_samples
        self.min_corr      = min_correlation
        self._proposal_log: List[Dict] = []

    def observe(self, variables: Dict[str, float],
                timestamp: Optional[float] = None) -> None:
        ts = timestamp or time.time()
        self._observations.append({"ts": ts, "vars": dict(variables)})
        for var_id, val in variables.items():
            self._time_series[var_id].append((ts, val))

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mx, my = sum(x) / n, sum(y) / n
        num  = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dex  = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dey  = math.sqrt(sum((yi - my) ** 2 for yi in y))
        if dex < 1e-9 or dey < 1e-9:
            return 0.0
        return num / (dex * dey)

    def _granger_direction(self, var_a: str, var_b: str) -> Optional[Tuple[str, str]]:
        ts_a = list(self._time_series[var_a])
        ts_b = list(self._time_series[var_b])
        if len(ts_a) < 5 or len(ts_b) < 5:
            return None
        times = sorted(set(t for t, _ in ts_a) & set(t for t, _ in ts_b))
        if len(times) < 5:
            return None
        map_a = {t: v for t, v in ts_a}
        map_b = {t: v for t, v in ts_b}
        vals_a = [map_a[t] for t in times]
        vals_b = [map_b[t] for t in times]
        corr_ab = abs(self._pearson_correlation(vals_a[:-1], vals_b[1:]))
        corr_ba = abs(self._pearson_correlation(vals_b[:-1], vals_a[1:]))
        if corr_ab > corr_ba + 0.05:
            return (var_a, var_b)
        elif corr_ba > corr_ab + 0.05:
            return (var_b, var_a)
        return None

    def learn_structure(self, graph: CausalGraph) -> List[CausalEdge]:
        if len(self._observations) < self.min_samples:
            return []
        proposed: List[CausalEdge] = []
        var_ids = list(self._time_series.keys())
        for i, var_a in enumerate(var_ids):
            for var_b in var_ids[i + 1:]:
                obs_with_both = [
                    o for o in self._observations
                    if var_a in o["vars"] and var_b in o["vars"]
                ]
                if len(obs_with_both) < self.min_samples:
                    continue
                vals_a = [o["vars"][var_a] for o in obs_with_both]
                vals_b = [o["vars"][var_b] for o in obs_with_both]
                corr = abs(self._pearson_correlation(vals_a, vals_b))
                if corr < self.min_corr:
                    continue
                direction = self._granger_direction(var_a, var_b)
                if direction is None:
                    continue
                src, tgt = direction
                if any(e.source == src and e.target == tgt for e in graph.edges):
                    continue
                edge = CausalEdge(
                    source=src, target=tgt,
                    strength=min(1.0, corr),
                    confidence=corr,
                    learned=True,
                )
                proposed.append(edge)
                self._proposal_log.append({
                    "ts": time.time(), "src": src, "tgt": tgt, "corr": round(corr, 3)
                })
                logger.info(f"[CausalLearner] Proposto arco: {src} -> {tgt} "
                            f"(corr={corr:.3f})")
        return proposed


class InterventionSimulator:
    """
    Simula gli effetti di interventi multipli do(X1=v1, X2=v2, ...).
    Implementa Pearl Level 2 (Intervention).
    """

    def simulate(
        self,
        graph: CausalGraph,
        interventions: Dict[str, float],
        steps: int = 1,
    ) -> Dict[str, Any]:
        # Baseline senza interventi
        baseline_graph = graph.copy()
        baseline = baseline_graph.propagate()

        # Applica do() per ogni variabile
        mutilated = graph.copy()
        for node_id, value in interventions.items():
            mutilated = mutilated.do_operator(node_id, value)

        effects: Dict[str, float] = {}
        for _ in range(steps):
            effects = mutilated.propagate()

        delta = {
            nid: round(effects.get(nid, 0.0) - baseline.get(nid, 0.0), 4)
            for nid in graph.nodes
        }

        affected_nodes = set()
        for node_id in interventions:
            affected_nodes.update(mutilated.descendants(node_id))
        affected_edges = [
            e for e in graph.edges
            if e.source in affected_nodes or e.target in affected_nodes
        ]
        avg_conf = (sum(e.confidence for e in affected_edges) / len(affected_edges)
                    if affected_edges else 0.5)

        return {
            "interventions": interventions,
            "baseline":      {k: round(v, 4) for k, v in baseline.items()},
            "effects":       {k: round(v, 4) for k, v in effects.items()},
            "delta":         delta,
            "affected_nodes": list(affected_nodes),
            "confidence":    round(avg_conf, 4),
            "causal_level":  CausalLevel.INTERVENTION.name,
        }


class CounterfactualEngine:
    """
    Ragionamento controfattuale: "cosa sarebbe successo se?"
    Algoritmo 3-step di Pearl: Abduction -> Action -> Prediction.
    """

    def query(
        self,
        graph: CausalGraph,
        observed: Dict[str, float],
        intervention: Dict[str, float],
        query_nodes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        # Step 1: Abduction — inferisci rumore esogeno U
        factual_graph = graph.copy()
        for nid, val in observed.items():
            if nid in factual_graph.nodes:
                factual_graph.nodes[nid].set_value(val)
        predicted = factual_graph.propagate()
        for nid, node in factual_graph.nodes.items():
            obs_val  = observed.get(nid)
            pred_val = predicted.get(nid, 0.5)
            if obs_val is not None:
                node.noise = obs_val - pred_val

        # Step 2: Action — applica intervento controfattuale
        cf_graph = factual_graph.copy()
        for node_id, value in intervention.items():
            cf_graph = cf_graph.do_operator(node_id, value)

        # Step 3: Prediction — propaga con i noise inferiti
        cf_effects = cf_graph.propagate()

        targets = query_nodes or list(graph.nodes.keys())
        factual_vals      = {n: round(observed.get(n, predicted.get(n, 0.0)), 4) for n in targets}
        counterfactual_vals = {n: round(cf_effects.get(n, 0.0), 4) for n in targets}
        delta_vals          = {n: round(counterfactual_vals[n] - factual_vals[n], 4) for n in targets}

        return {
            "factual":        factual_vals,
            "counterfactual": counterfactual_vals,
            "delta":          delta_vals,
            "query_nodes":    targets,
            "intervention":   intervention,
            "causal_level":   CausalLevel.COUNTERFACTUAL.name,
        }


class CausalReasoner:
    """
    SPEACE Causal Reasoning Module (BRN-017) — FULL IMPLEMENTATION.

    Pearl's Causal Hierarchy completa:
      Level 1 (Association)    : infer_cause()
      Level 2 (Intervention)   : simulate_intervention()
      Level 3 (Counterfactual) : counterfactual()

    Integrazioni:
      - BRN-015 PredictiveCoding : detect_surprise() — PredictionError -> discovery
      - WorldModel KnowledgeGraph: import_from_knowledge_graph() — prior causale
    """

    def __init__(self) -> None:
        self.graph     = CausalGraph()
        self.learner   = CausalLearner()
        self.simulator = InterventionSimulator()
        self.cfengine  = CounterfactualEngine()

        self._cycle        = 0
        self._surprises:   List[Dict] = []
        self._inferences:  List[Dict] = []
        self._auto_learn   = True

        logger.info("CausalReasoner BRN-017 inizializzato (Level 1-2-3 attivi)")

    def observe(self, variables: Dict[str, float],
                timestamp: Optional[float] = None) -> None:
        for var_id, val in variables.items():
            node = self.graph.ensure_node(var_id)
            node.value = val
        self.learner.observe(variables, timestamp)
        if self._auto_learn and len(self.learner._observations) % 20 == 0:
            proposed_edges = self.learner.learn_structure(self.graph)
            for edge in proposed_edges:
                self.graph.ensure_node(edge.source)
                self.graph.ensure_node(edge.target)
                self.graph.add_edge(edge)

    def add_causal_link(self, source: str, target: str,
                        strength: float = 0.5,
                        mechanism: EdgeMechanism = EdgeMechanism.LINEAR,
                        domain: str = "unknown") -> None:
        self.graph.ensure_node(source, domain=domain)
        self.graph.ensure_node(target, domain=domain)
        self.graph.add_edge(CausalEdge(
            source=source, target=target,
            strength=strength, mechanism=mechanism,
            confidence=1.0, learned=False,
        ))

    def infer_cause(self, observation: Dict[str, float]) -> Dict[str, Any]:
        """Level 1 — Association: identifica causa più probabile per l'osservazione."""
        self._cycle += 1
        self.observe(observation)

        candidates: List[Dict] = []
        for effect_id, effect_val in observation.items():
            if abs(effect_val - 0.5) <= 0.2:
                continue
            for parent_id in self.graph.parents(effect_id):
                parent_node = self.graph.nodes.get(parent_id)
                if parent_node is None or parent_node.value is None:
                    continue
                edge = next(
                    (e for e in self.graph.edges
                     if e.source == parent_id and e.target == effect_id), None
                )
                if edge is None:
                    continue
                expected_contrib = abs(edge.compute_effect(parent_node.value))
                score = expected_contrib * edge.confidence
                candidates.append({
                    "cause":     parent_id,
                    "effect":    effect_id,
                    "score":     round(score, 4),
                    "mechanism": edge.mechanism.value,
                    "strength":  round(edge.strength, 4),
                    "level":     CausalLevel.ASSOCIATION.name,
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        top = candidates[0] if candidates else None

        result = {
            "cause":      top["cause"]  if top else None,
            "effect":     top["effect"] if top else None,
            "level":      CausalLevel.ASSOCIATION.name,
            "confidence": top["score"]  if top else 0.0,
            "candidates": candidates[:5],
            "cycle":      self._cycle,
        }
        self._inferences.append(result)
        return result

    def simulate_intervention(self, do_ops: Dict[str, float],
                               steps: int = 2) -> Dict[str, Any]:
        """Level 2 — Intervention: simula effetti di do(X=x)."""
        return self.simulator.simulate(self.graph, do_ops, steps=steps)

    def counterfactual(self, observed: Dict[str, float],
                       intervention: Dict[str, float],
                       query_nodes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Level 3 — Counterfactual: risponde a 'cosa sarebbe successo se...'"""
        return self.cfengine.query(self.graph, observed, intervention, query_nodes)

    def detect_surprise(self, prediction_error: Any) -> Optional[Dict]:
        """Integrazione BRN-015: PredictionError sorprendente -> trigger discovery."""
        if not getattr(prediction_error, "is_surprising", False):
            return None
        source_id = getattr(prediction_error, "source_id", "unknown")
        error_mag = getattr(prediction_error, "error_magnitude", 0.0)
        level_name = getattr(
            getattr(prediction_error, "level", None), "name", "L3_CONCEPTUAL"
        )
        self._surprises.append({
            "ts": time.time(), "source": source_id,
            "error": round(error_mag, 4), "level": level_name,
        })
        self.graph.ensure_node(source_id, name=source_id, domain=level_name)
        logger.info(f"[CausalReasoner] Sorpresa BRN-015: source={source_id}, "
                    f"error={error_mag:.3f} -> avvia discovery causale")
        return {
            "trigger":   "prediction_error_surprise",
            "source_id": source_id,
            "error":     error_mag,
            "action":    "increase_observation_weight",
        }

    def import_from_knowledge_graph(
        self, kg: Any,
        causal_relations: Optional[List[str]] = None,
    ) -> int:
        """Importa relazioni semantiche dal KnowledgeGraph come prior causale."""
        causal_rels = causal_relations or [
            "causes", "feeds", "depends_on", "influences",
            "triggers", "required_by", "monitors",
        ]
        imported = 0
        try:
            for eid, entity in getattr(kg, "_entities", {}).items():
                for rel in getattr(entity, "relations", []):
                    if rel.rel in causal_rels:
                        self.graph.ensure_node(
                            eid, name=eid,
                            domain=getattr(entity, "entity_type", "unknown"))
                        self.graph.ensure_node(rel.target, name=rel.target)
                        self.graph.add_edge(CausalEdge(
                            source=eid, target=rel.target,
                            strength=rel.weight, mechanism=EdgeMechanism.UNKNOWN,
                            confidence=0.7, learned=False,
                        ))
                        imported += 1
        except Exception as exc:
            logger.warning(f"[CausalReasoner] import_from_knowledge_graph: {exc}")
        logger.info(f"[CausalReasoner] Importati {imported} archi dal KnowledgeGraph")
        return imported

    def get_full_status(self) -> Dict[str, Any]:
        return {
            "module":  "CausalReasoner",
            "brn_id":  "BRN-017",
            "status":  "active",
            "cycle":   self._cycle,
            "graph": {
                "nodes":   len(self.graph.nodes),
                "edges":   len(self.graph.edges),
                "is_dag":  self.graph.is_dag(),
                "domains": list({n.domain for n in self.graph.nodes.values()}),
            },
            "learner": {
                "observations":   len(self.learner._observations),
                "proposals_made": len(self.learner._proposal_log)