"""
Tests M5.14 + M5.15 + M5.16 — Plasticity Layer
EdgePruner, EdgeGrower, PlasticityLogger

Copertura:
  PL-01 to PL-06  PlasticityLogger (M5.16)
  PR-07 to PR-17  EdgePruner — weight update + pruning (M5.14)
  GR-18 to GR-25  EdgeGrower — co-activation + proposals (M5.15)
  FAC-26 to FAC-28 Factory create_plasticity_layer
  INT-29 to INT-30 Integration tests

Run:
    cd SPEACE-prototipo
    python -m pytest cortex/cognitive_autonomy/plasticity/_tests_plasticity.py -v

Milestone: M5.14 + M5.15 + M5.16
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# path bootstrap
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE
for _ in range(6):
    if (_ROOT / "cortex").is_dir() or (_ROOT / "dashboard").is_dir():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

from cortex.cognitive_autonomy.plasticity.edge_pruning import (
    PlasticityLogger,
    PrunerConfig, EdgePruner,
    GrowthConfig, EdgeGrower,
    create_plasticity_layer,
)
from cortex.mesh.graph import MeshGraph
from cortex.mesh.contract import Neuron, NeuronRegistry
from cortex.mesh.olc.types import SensoryFrame, InterpretationFrame, FeedbackFrame, ActionResult


# =============================================================================
# Neuron fixtures
# =============================================================================

class NeuronA(Neuron):
    name = "na"; input_type = SensoryFrame; output_type = InterpretationFrame
    level = 1; version = "1.0"; needs_served = []; resource_budget = {}
    side_effects = []; description = "test A"
    def execute(self, inp): return InterpretationFrame(intent="x", confidence=0.9)

class NeuronB(Neuron):
    name = "nb"; input_type = InterpretationFrame; output_type = FeedbackFrame
    level = 2; version = "1.0"; needs_served = []; resource_budget = {}
    side_effects = []; description = "test B"
    def execute(self, inp): return FeedbackFrame(cycle_id="c1", latency_ms=1.0, errors=0, fitness_delta=0.1)

class NeuronC(Neuron):
    name = "nc"; input_type = FeedbackFrame; output_type = ActionResult
    level = 3; version = "1.0"; needs_served = []; resource_budget = {}
    side_effects = []; description = "test C"
    def execute(self, inp): return ActionResult(ok=True, output={})

class NeuronD(Neuron):
    name = "nd"; input_type = InterpretationFrame; output_type = FeedbackFrame
    level = 2; version = "1.0"; needs_served = []; resource_budget = {}
    side_effects = []; description = "test D"
    def execute(self, inp): return FeedbackFrame(cycle_id="c2", latency_ms=2.0, errors=0, fitness_delta=0.0)


def _make_graph(*neuron_cls) -> MeshGraph:
    """Build isolated MeshGraph (fresh registry, no global state pollution)."""
    g = MeshGraph(neuron_registry=NeuronRegistry())
    for cls in neuron_cls:
        # register_in_neuron_registry=False avoids duplicate-name errors across tests
        viols = g.add_neuron(cls(), skip_contract=True, register_in_neuron_registry=False)
        assert viols == [], f"add_neuron {cls.name} viols: {viols}"
    return g


def _add_edge(g: MeshGraph, src: str, dst: str, weight: float = 0.5) -> None:
    viols = g.add_edge(src, dst, weight=weight)
    assert viols == [], f"add_edge {src}->{dst} viols: {viols}"


# =============================================================================
# PL — PlasticityLogger (M5.16)
# =============================================================================

class TestPlasticityLogger:

    def test_pl01_log_creates_file(self, tmp_path):
        """PL-01: log() crea il file jsonl."""
        p = tmp_path / "sub" / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        logger.log("test_event", {"key": "value"})
        assert p.exists()

    def test_pl02_log_valid_json(self, tmp_path):
        """PL-02: ogni riga e JSON valido con campi ts/type/subtype/data."""
        p = tmp_path / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        logger.log("my_event", {"x": 42})
        line = p.read_text().strip()
        record = json.loads(line)
        assert record["type"] == "plasticity_event"
        assert record["subtype"] == "my_event"
        assert record["data"]["x"] == 42
        assert "ts" in record

    def test_pl03_log_appends(self, tmp_path):
        """PL-03: chiamate multiple appendono righe."""
        p = tmp_path / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        for i in range(5):
            logger.log("ev", {"i": i})
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 5

    def test_pl04_log_pruned(self, tmp_path):
        """PL-04: log_pruned() scrive subtype=pruned con edges/count."""
        p = tmp_path / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        logger.log_pruned([("na", "nb"), ("nb", "nc")], [0.05, 0.08])
        rec = json.loads(p.read_text().strip())
        assert rec["subtype"] == "pruned"
        assert rec["data"]["count"] == 2
        assert "na->nb" in rec["data"]["edges"] or "na→nb" in rec["data"]["edges"]

    def test_pl05_log_grown(self, tmp_path):
        """PL-05: log_grown() scrive subtype=growth_proposed con count."""
        p = tmp_path / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        proposals = [{"src": "na", "dst": "nc", "risk_level": "HIGH"}]
        logger.log_grown(proposals)
        rec = json.loads(p.read_text().strip())
        assert rec["subtype"] == "growth_proposed"
        assert rec["data"]["count"] == 1

    def test_pl06_log_weight_update(self, tmp_path):
        """PL-06: log_weight_update() scrive edge/old/new."""
        p = tmp_path / "mesh_state.jsonl"
        logger = PlasticityLogger(p)
        logger.log_weight_update(("na", "nb"), 0.50, 0.48)
        rec = json.loads(p.read_text().strip())
        assert rec["subtype"] == "weight_update"
        assert "na" in rec["data"]["edge"]
        assert "nb" in rec["data"]["edge"]
        assert abs(rec["data"]["old"] - 0.50) < 1e-3
        assert abs(rec["data"]["new"] - 0.48) < 1e-3


# =============================================================================
# PR — EdgePruner (M5.14)
# =============================================================================

class TestEdgePruner:

    def _pruner(self, graph, tmp_path, **cfg_kwargs):
        cfg = PrunerConfig(min_age_s=0.0, **cfg_kwargs)
        log = PlasticityLogger(tmp_path / "mesh_state.jsonl")
        return EdgePruner(graph, cfg, log)

    def test_pr07_update_weights_returns_dict(self, tmp_path):
        """PR-07: update_weights() ritorna dict {(src,dst): weight}."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.5)
        pruner = self._pruner(g, tmp_path)
        updated = pruner.update_weights()
        assert ("na", "nb") in updated
        assert isinstance(updated[("na", "nb")], float)

    def test_pr08_decay_reduces_weight(self, tmp_path):
        """PR-08: decay senza successi riduce il peso ogni ciclo."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.5)
        pruner = self._pruner(g, tmp_path, decay_rate=0.9, success_bonus=0.0, failure_penalty=0.0)
        w0 = g.edge_meta("na", "nb").weight
        pruner.update_weights()
        w1 = g.edge_meta("na", "nb").weight
        assert w1 < w0, f"Peso non decresciuto: {w0} -> {w1}"
        assert abs(w1 - w0 * 0.9) < 1e-5

    def test_pr09_success_bonus_increases_weight(self, tmp_path):
        """PR-09: successes aumentano il peso."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.5)
        meta = g.edge_meta("na", "nb")
        meta.successes = 10
        pruner = self._pruner(g, tmp_path, decay_rate=1.0, success_bonus=0.05, failure_penalty=0.0)
        pruner.update_weights()
        w1 = g.edge_meta("na", "nb").weight
        assert w1 > 0.5, f"Success bonus non applicato: w={w1}"

    def test_pr10_failure_penalty_decreases_weight(self, tmp_path):
        """PR-10: failures riducono il peso."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.5)
        meta = g.edge_meta("na", "nb")
        meta.failures = 5
        pruner = self._pruner(g, tmp_path, decay_rate=1.0, success_bonus=0.0, failure_penalty=0.1)
        pruner.update_weights()
        w1 = g.edge_meta("na", "nb").weight
        assert w1 < 0.5

    def test_pr11_weight_clamps_to_wmin(self, tmp_path):
        """PR-11: peso non scende sotto w_min."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.01)
        meta = g.edge_meta("na", "nb")
        meta.failures = 100
        pruner = self._pruner(g, tmp_path, w_min=0.01, failure_penalty=0.5)
        pruner.update_weights()
        w1 = g.edge_meta("na", "nb").weight
        assert w1 >= 0.01

    def test_pr12_prune_below_threshold(self, tmp_path):
        """PR-12: arco con peso sotto threshold viene rimosso."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.05)
        pruner = self._pruner(g, tmp_path, decay_rate=1.0,
                              success_bonus=0.0, failure_penalty=0.0,
                              weight_threshold=0.10)
        pruned = pruner.prune_cycle()
        assert ("na", "nb") in pruned
        assert not g.has_edge("na", "nb")

    def test_pr13_strong_edge_not_pruned(self, tmp_path):
        """PR-13: arco con peso sopra threshold non viene rimosso."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.9)
        pruner = self._pruner(g, tmp_path, decay_rate=1.0,
                              success_bonus=0.0, failure_penalty=0.0)
        pruned = pruner.prune_cycle()
        assert len(pruned) == 0
        assert g.has_edge("na", "nb")

    def test_pr14_max_prune_per_cycle_respected(self, tmp_path):
        """PR-14: max_prune_per_cycle limita rimozioni per ciclo."""
        g = _make_graph(NeuronA, NeuronB, NeuronC, NeuronD)
        _add_edge(g, "na", "nb", weight=0.01)
        _add_edge(g, "na", "nd", weight=0.01)
        _add_edge(g, "nb", "nc", weight=0.01)
        pruner = self._pruner(g, tmp_path, decay_rate=1.0,
                              success_bonus=0.0, failure_penalty=0.0,
                              max_prune_per_cycle=2)
        pruned = pruner.prune_cycle()
        assert len(pruned) <= 2

    def test_pr15_disabled_pruner_does_nothing(self, tmp_path):
        """PR-15: pruner disabilitato non tocca il grafo."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.01)
        pruner = self._pruner(g, tmp_path, enabled=False)
        pruned = pruner.prune_cycle()
        assert pruned == []
        assert g.has_edge("na", "nb")

    def test_pr16_stats_cycle_count(self, tmp_path):
        """PR-16: get_stats() incrementa cycle_count ad ogni prune_cycle."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.9)
        pruner = self._pruner(g, tmp_path)
        for _ in range(4):
            pruner.prune_cycle()
        stats = pruner.get_stats()
        assert stats["cycle_count"] == 4

    def test_pr17_stats_total_pruned(self, tmp_path):
        """PR-17: get_stats() total_pruned conta gli archi rimossi cumulativi."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.05)
        pruner = self._pruner(g, tmp_path, decay_rate=1.0,
                              success_bonus=0.0, failure_penalty=0.0)
        pruner.prune_cycle()
        stats = pruner.get_stats()
        assert stats["total_pruned"] == 1


# =============================================================================
# GR — EdgeGrower (M5.15)
# =============================================================================

class TestEdgeGrower:

    def _grower(self, graph, tmp_path, **cfg_kwargs):
        cfg = GrowthConfig(enabled=True, **cfg_kwargs)
        log = PlasticityLogger(tmp_path / "mesh_state.jsonl")
        return EdgeGrower(graph, cfg, log)

    def test_gr18_disabled_grower_no_proposals(self, tmp_path):
        """GR-18: grower disabilitato non genera proposte."""
        g = _make_graph(NeuronA, NeuronB)
        cfg = GrowthConfig(enabled=False)
        grower = EdgeGrower(g, cfg)
        for _ in range(10):
            grower.record_coactivation(["na", "nb"])
        proposals = grower.propose_growth_cycle()
        assert proposals == []

    def test_gr19_coactivation_below_threshold_no_proposal(self, tmp_path):
        """GR-19: co-attivazioni sotto soglia non generano proposte."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        grower = self._grower(g, tmp_path, coactivation_threshold=5)
        for _ in range(3):
            grower.record_coactivation(["na", "nc"])
        proposals = grower.propose_growth_cycle()
        assert len(proposals) == 0

    def test_gr20_coactivation_above_threshold_generates_proposal(self, tmp_path):
        """GR-20: co-attivazioni sopra soglia -> proposta generata."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        grower = self._grower(g, tmp_path, coactivation_threshold=5)
        for _ in range(6):
            grower.record_coactivation(["na", "nc"])
        proposals = grower.propose_growth_cycle()
        assert len(proposals) >= 1
        p = proposals[0]
        assert "plasticity_grow" in p["action_name"]
        assert p["risk_level"] == "HIGH"
        assert p["metadata"]["coactivation_count"] >= 5

    def test_gr21_max_proposals_per_cycle(self, tmp_path):
        """GR-21: max_proposals_per_cycle limita le proposte."""
        g = _make_graph(NeuronA, NeuronB, NeuronC, NeuronD)
        grower = self._grower(g, tmp_path, coactivation_threshold=3, max_proposals_per_cycle=1)
        for _ in range(5):
            grower.record_coactivation(["na", "nc"])
            grower.record_coactivation(["na", "nd"])
        proposals = grower.propose_growth_cycle()
        assert len(proposals) <= 1

    def test_gr22_already_connected_risk_medium(self, tmp_path):
        """GR-22: coppia gia connessa ottiene risk=MEDIUM (rinforzo)."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.3)
        grower = self._grower(g, tmp_path, coactivation_threshold=3,
                              risk_level_reinforce="MEDIUM", risk_level_new="HIGH")
        for _ in range(5):
            grower.record_coactivation(["na", "nb"])
        proposals = grower.propose_growth_cycle()
        assert any(p["risk_level"] == "MEDIUM" for p in proposals)

    def test_gr23_apply_approved_growth(self, tmp_path):
        """GR-23: apply_approved_growth() crea l'arco nel grafo."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        grower = self._grower(g, tmp_path)
        result = grower.apply_approved_growth("nb", "nc", weight=0.6)
        assert result is True
        assert g.has_edge("nb", "nc")
        meta = g.edge_meta("nb", "nc")
        assert abs(meta.weight - 0.6) < 1e-5

    def test_gr24_apply_approved_clears_coactivation(self, tmp_path):
        """GR-24: dopo apply_approved_growth il contatore co-att viene azzerato."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        grower = self._grower(g, tmp_path, coactivation_threshold=3)
        for _ in range(5):
            grower.record_coactivation(["nb", "nc"])
        key = ("nb", "nc")
        assert grower._coactivation.get(key, 0) >= 5
        grower.apply_approved_growth("nb", "nc", weight=0.4)
        assert grower._coactivation.get(key, 0) == 0

    def test_gr25_stats_proposals_generated(self, tmp_path):
        """GR-25: get_stats() proposals_generated conta le proposte totali."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        grower = self._grower(g, tmp_path, coactivation_threshold=2)
        for _ in range(5):
            grower.record_coactivation(["na", "nc"])
        grower.propose_growth_cycle()
        grower.propose_growth_cycle()
        stats = grower.get_stats()
        assert stats["proposals_generated"] >= 1


# =============================================================================
# FAC — create_plasticity_layer factory
# =============================================================================

class TestFactory:

    def test_fac26_factory_returns_tuple(self, tmp_path):
        """FAC-26: create_plasticity_layer ritorna (EdgePruner, EdgeGrower)."""
        g = _make_graph(NeuronA, NeuronB)
        pruner, grower = create_plasticity_layer(g, log_path=tmp_path / "mesh_state.jsonl")
        assert isinstance(pruner, EdgePruner)
        assert isinstance(grower, EdgeGrower)

    def test_fac27_pruning_enabled_growth_disabled_default(self, tmp_path):
        """FAC-27: default pruner ON, grower OFF."""
        g = _make_graph(NeuronA, NeuronB)
        pruner, grower = create_plasticity_layer(g, log_path=tmp_path / "mesh_state.jsonl")
        assert pruner.config.enabled is True
        assert grower.config.enabled is False

    def test_fac28_shared_logger_writes_to_same_file(self, tmp_path):
        """FAC-28: pruner e grower condividono lo stesso log path."""
        g = _make_graph(NeuronA, NeuronB)
        log_path = tmp_path / "mesh_state.jsonl"
        pruner, grower = create_plasticity_layer(g, pruning_enabled=True,
                                                  growth_enabled=True,
                                                  log_path=log_path)
        _add_edge(g, "na", "nb", weight=0.05)
        pruner.config.min_age_s = 0.0
        pruner.config.decay_rate = 1.0
        pruner.config.success_bonus = 0.0
        pruner.config.failure_penalty = 0.0
        pruner.prune_cycle()
        for _ in range(10):
            grower.record_coactivation(["na", "nb"])
        grower.propose_growth_cycle()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) >= 2
        subtypes = {json.loads(l)["subtype"] for l in lines if l}
        assert "growth_proposed" in subtypes


# =============================================================================
# Integration smoke
# =============================================================================

class TestPlasticityIntegration:

    def test_int29_prune_and_grow_cycle(self, tmp_path):
        """INT-29: ciclo completo prune + grow su stesso grafo."""
        g = _make_graph(NeuronA, NeuronB, NeuronC)
        _add_edge(g, "na", "nb", weight=0.8)
        _add_edge(g, "nb", "nc", weight=0.03)

        log_path = tmp_path / "mesh_state.jsonl"
        pruner, grower = create_plasticity_layer(g, pruning_enabled=True,
                                                  growth_enabled=True,
                                                  log_path=log_path)
        pruner.config = PrunerConfig(enabled=True, weight_threshold=0.10,
                                     decay_rate=1.0, success_bonus=0.0,
                                     failure_penalty=0.0, min_age_s=0.0)
        grower.config = GrowthConfig(enabled=True, coactivation_threshold=3)

        for _ in range(5):
            grower.record_coactivation(["nb", "nc"])

        pruned = pruner.prune_cycle()
        proposals = grower.propose_growth_cycle()

        assert ("nb", "nc") in pruned
        assert g.has_edge("na", "nb")
        assert len(proposals) >= 1

    def test_int30_log_file_coherence(self, tmp_path):
        """INT-30: dopo prune+grow il log contiene record validi."""
        g = _make_graph(NeuronA, NeuronB)
        _add_edge(g, "na", "nb", weight=0.05)
        log_path = tmp_path / "mesh_state.jsonl"
        pruner = EdgePruner(g, PrunerConfig(enabled=True, weight_threshold=0.10,
                                             decay_rate=1.0, success_bonus=0.0,
                                             failure_penalty=0.0, min_age_s=0.0),
                            PlasticityLogger(log_path))
        pruner.prune_cycle()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) >= 1
        for line in lines:
            rec = json.loads(line)
            assert rec["type"] == "plasticity_event"
            assert "ts" in rec
            assert "subtype" in rec
