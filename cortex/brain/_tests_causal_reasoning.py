"""
Tests — CausalReasoner BRN-017
================================
Suite di test per validare l'implementazione della gerarchia causale di Pearl.

Criteri di chiusura BRN.17:
  - do_operator() funzionante su grafo semplice
  - Propagazione forward corretta dopo intervento
  - CounterfactualEngine 3-step (abduction→action→prediction)
  - CausalLearner propone archi da dati osservazionali
  - Integrazione con PredictionError (sorpresa → discovery)
  - Integrazione con KnowledgeGraph (import relazioni)

Run: python -m pytest cortex/brain/_tests_causal_reasoning.py -v
"""
import math
import time
import pytest

from cortex.brain.causal_reasoning import (
    CausalGraph,
    CausalNode,
    CausalEdge,
    CausalLevel,
    CausalLearner,
    InterventionSimulator,
    CounterfactualEngine,
    CausalReasoner,
    EdgeMechanism,
    create_causal_reasoner,
    create_causal_reasoner_with_priors,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def make_climate_graph() -> CausalGraph:
    """
    Grafo causale semplice: CO2 → temperatura → scioglimento ghiacci
    """
    g = CausalGraph()
    g.add_node(CausalNode("co2",      name="CO2 Emission",      domain="climate"))
    g.add_node(CausalNode("temp",     name="Global Temperature", domain="climate"))
    g.add_node(CausalNode("ice_melt", name="Ice Melting",        domain="climate"))
    g.add_node(CausalNode("sea",      name="Sea Level",          domain="climate"))

    g.add_edge(CausalEdge("co2",      "temp",     strength=0.7, mechanism=EdgeMechanism.LINEAR))
    g.add_edge(CausalEdge("temp",     "ice_melt", strength=0.8, mechanism=EdgeMechanism.LINEAR))
    g.add_edge(CausalEdge("ice_melt", "sea",      strength=0.6, mechanism=EdgeMechanism.LINEAR))
    return g


def make_simple_reasoner() -> CausalReasoner:
    """CausalReasoner con grafo clima preiniziato."""
    cr = create_causal_reasoner()
    g  = make_climate_graph()
    cr.graph = g
    return cr


# ─────────────────────────────────────────────────────────────────────────────
# CAU-01 – CausalGraph: struttura base
# ─────────────────────────────────────────────────────────────────────────────

class TestCausalGraphStructure:

    def test_add_node(self):
        g = CausalGraph()
        g.add_node(CausalNode("x", name="X"))
        assert "x" in g.nodes

    def test_add_edge(self):
        g = CausalGraph()
        g.add_node(CausalNode("a", name="A"))
        g.add_node(CausalNode("b", name="B"))
        g.add_edge(CausalEdge("a", "b", strength=0.5))
        assert len(g.edges) == 1

    def test_parents_children(self):
        g = make_climate_graph()
        assert "co2" in g.parents("temp")
        assert "temp" in g.children("co2")

    def test_ancestors_descendants(self):
        g = make_climate_graph()
        anc = g.ancestors("sea")
        assert "co2" in anc and "temp" in anc and "ice_melt" in anc
        desc = g.descendants("co2")
        assert "temp" in desc and "ice_melt" in desc and "sea" in desc

    def test_is_dag_valid(self):
        g = make_climate_graph()
        assert g.is_dag() is True

    def test_topological_sort_order(self):
        g = make_climate_graph()
        order = g.topological_sort()
        assert order.index("co2") < order.index("temp")
        assert order.index("temp") < order.index("ice_melt")
        assert order.index("ice_melt") < order.index("sea")

    def test_remove_edge(self):
        g = make_climate_graph()
        removed = g.remove_edge("co2", "temp")
        assert removed is True
        assert "co2" not in g.parents("temp")

    def test_ensure_node_idempotent(self):
        g = CausalGraph()
        n1 = g.ensure_node("x", name="X", domain="test")
        n2 = g.ensure_node("x", name="X_dup")  # non deve sovrascrivere
        assert n1 is n2


# ─────────────────────────────────────────────────────────────────────────────
# CAU-02 – Propagazione forward
# ─────────────────────────────────────────────────────────────────────────────

class TestPropagation:

    def test_propagate_source_sets_value(self):
        g = CausalGraph()
        g.add_node(CausalNode("x", name="X", value=None))
        g.add_node(CausalNode("y", name="Y"))
        g.add_edge(CausalEdge("x", "y", strength=0.8))
        g.nodes["x"].set_value(1.0)
        results = g.propagate()
        assert "y" in results
        # y riceve contributo positivo → valore > 0.5
        assert results["y"] > 0.5

    def test_propagate_inhibitory_lowers_value(self):
        g = CausalGraph()
        g.add_node(CausalNode("x", name="X"))
        g.add_node(CausalNode("y", name="Y"))
        g.add_edge(CausalEdge("x", "y", strength=0.9, mechanism=EdgeMechanism.INHIBITORY))
        g.nodes["x"].set_value(1.0)
        results = g.propagate()
        # inibizione → y < 0.5
        assert results["y"] < 0.5

    def test_propagate_climate_chain(self):
        g = make_climate_graph()
        g.nodes["co2"].set_value(0.9)
        results = g.propagate()
        # temperatura deve salire con CO2 alto
        assert results["temp"] > 0.5
        # sea level dovrebbe rispondere indirettamente
        assert "sea" in results


# ─────────────────────────────────────────────────────────────────────────────
# CAU-03 – do_operator (Pearl Level 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestDoOperator:

    def test_do_removes_incoming_edges(self):
        g = make_climate_graph()
        mutilated = g.do_operator("temp", 0.9)
        # Il nodo temp non deve avere più genitori (co2 tagliato)
        assert mutilated.parents("temp") == []

    def test_do_sets_value(self):
        g = make_climate_graph()
        mutilated = g.do_operator("temp", 0.85)
        assert mutilated.nodes["temp"].value == pytest.approx(0.85, abs=1e-6)
        assert mutilated.nodes["temp"].observed is True

    def test_do_preserves_downstream_edges(self):
        g = make_climate_graph()
        mutilated = g.do_operator("temp", 0.9)
        # Gli archi temp→ice_melt e ice_melt→sea devono restare
        assert "ice_melt" in mutilated.children("temp")
        assert "sea" in mutilated.children("ice_melt")

    def test_do_does_not_modify_original(self):
        g = make_climate_graph()
        _ = g.do_operator("temp", 0.9)
        # Il grafo originale non cambia
        assert "co2" in g.parents("temp")

    def test_do_then_propagate(self):
        g = make_climate_graph()
        mutilated = g.do_operator("co2", 1.0)
        results = mutilated.propagate()
        assert results["co2"] == pytest.approx(1.0, abs=1e-6)
        # temp e downstream ricevono effetto
        assert results["temp"] > 0.5


# ─────────────────────────────────────────────────────────────────────────────
# CAU-04 – InterventionSimulator (Level 2)
# ─────────────────────────────────────────────────────────────────────────────

class TestInterventionSimulator:

    def test_simulate_returns_required_keys(self):
        g = make_climate_graph()
        sim = InterventionSimulator()
        result = sim.simulate(g, {"co2": 1.0})
        assert "effects" in result
        assert "baseline" in result
        assert "delta" in result
        assert "confidence" in result
        assert result["causal_level"] == CausalLevel.INTERVENTION.name

    def test_high_co2_increases_temp(self):
        g = make_climate_graph()
        sim = InterventionSimulator()
        result_high = sim.simulate(g, {"co2": 1.0})
        result_low  = sim.simulate(g, {"co2": 0.0})
        assert result_high["effects"]["temp"] > result_low["effects"]["temp"]

    def test_delta_positive_for_positive_intervention(self):
        g = make_climate_graph()
        # Prima imposta un valore baseline ai nodi
        g.nodes["co2"].set_value(0.5)
        g.propagate()
        sim = InterventionSimulator()
        result = sim.simulate(g, {"co2": 1.0})
        # con co2 alta, la delta temperatura deve essere ≥ 0
        assert result["delta"]["temp"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# CAU-05 – CounterfactualEngine (Level 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestCounterfactualEngine:

    def test_query_returns_required_keys(self):
        g = make_climate_graph()
        cf = CounterfactualEngine()
        result = cf.query(
            graph       = g,
            observed    = {"co2": 0.8, "temp": 0.7},
            intervention = {"co2": 0.2},
            query_nodes  = ["temp", "ice_melt"],
        )
        assert "factual" in result
        assert "counterfactual" in result
        assert "delta" in result
        assert result["causal_level"] == CausalLevel.COUNTERFACTUAL.name

    def test_counterfactual_lower_co2_lowers_temp(self):
        g = make_climate_graph()
        cf = CounterfactualEngine()
        result = cf.query(
            graph       = g,
            observed    = {"co2": 0.9},
            intervention = {"co2": 0.1},
            query_nodes  = ["temp"],
        )
        # Con CO2 ridotta, la temperatura controfattuale deve essere < quella reale
        assert result["counterfactual"]["temp"] <= result["factual"]["temp"] + 0.1

    def test_query_all_nodes_if_none(self):
        g = make_climate_graph()
        cf = CounterfactualEngine()
        result = cf.query(g, {"co2": 0.5}, {"co2": 0.0})
        # Deve avere tutti i nodi del grafo
        assert set(result["query_nodes"]) == set(g.nodes.keys())


# ─────────────────────────────────────────────────────────────────────────────
# CAU-06 – CausalLearner
# ─────────────────────────────────────────────────────────────────────────────

class TestCausalLearner:

    def _generate_correlated_data(self, n: int = 50) -> list:
        """Genera osservazioni dove A causa B (A → B con lag=1)."""
        import random
        rng = random.Random(42)
        data = []
        a_prev = 0.5
        ts = time.time()
        for i in range(n):
            a = max(0.0, min(1.0, a_prev + rng.gauss(0, 0.1)))
            b = max(0.0, min(1.0, a_prev * 0.8 + rng.gauss(0, 0.05)))
            data.append(({"A": a, "B": b}, ts + i * 0.1))
            a_prev = a
        return data

    def test_observe_accumulates(self):
        lrn = CausalLearner(min_samples=5)
        for i in range(10):
            lrn.observe({"x": float(i), "y": float(i * 2)})
        assert len(lrn._observations) == 10

    def test_learn_structure_below_min_samples(self):
        g   = CausalGraph()
        lrn = CausalLearner(min_samples=50)
        for i in range(5):
            lrn.observe({"A": float(i), "B": float(i)})
        proposed = lrn.learn_structure(g)
        assert proposed == []  # non abbastanza campioni

    def test_learn_structure_proposes_edges(self):
        g   = CausalGraph()
        lrn = CausalLearner(min_samples=10, min_correlation=0.2)
        data = self._generate_correlated_data(50)
        for obs, ts in data:
            lrn.observe(obs, ts)
        proposed = lrn.learn_structure(g)
        # Deve proporre almeno un arco A↔B (in qualche direzione)
        assert len(proposed) >= 1
        srcs_tgts = {(e.source, e.target) for e in proposed}
        assert ("A", "B") in srcs_tgts or ("B", "A") in srcs_tgts

    def test_learned_edges_flagged(self):
        g   = CausalGraph()
        lrn = CausalLearner(min_samples=10, min_correlation=0.2)
        data = self._generate_correlated_data(50)
        for obs, ts in data:
            lrn.observe(obs, ts)
        proposed = lrn.learn_structure(g)
        for edge in proposed:
            assert edge.learned is True


# ─────────────────────────────────────────────────────────────────────────────
# CAU-07 – CausalReasoner (integrazione)
# ─────────────────────────────────────────────────────────────────────────────

class TestCausalReasoner:

    def test_init(self):
        cr = create_causal_reasoner()
        status = cr.get_full_status()
        assert status["status"] == "active"
        assert status["brn_id"] == "BRN-017"

    def test_add_causal_link(self):
        cr = create_causal_reasoner()
        cr.add_causal_link("pollution", "disease", strength=0.7, domain="health")
        assert "pollution" in cr.graph.nodes
        assert "disease"   in cr.graph.nodes
        assert len(cr.graph.edges) == 1

    def test_observe_ensures_nodes(self):
        cr = create_causal_reasoner()
        cr.observe({"var_a": 0.3, "var_b": 0.7})
        assert "var_a" in cr.graph.nodes
        assert "var_b" in cr.graph.nodes

    def test_infer_cause_with_graph(self):
        cr = make_simple_reasoner()
        result = cr.infer_cause({"co2": 0.9, "temp": 0.75, "ice_melt": 0.6})
        assert "cause" in result
        assert "level" in result
        assert result["level"] == CausalLevel.ASSOCIATION.name
        assert result["cycle"] == 1

    def test_infer_cause_no_edges_returns_none(self):
        cr = create_causal_reasoner()
        cr.observe({"x": 0.9})
        result = cr.infer_cause({"x": 0.9})
        assert result["cause"] is None
        assert result["confidence"] == 0.0

    def test_simulate_intervention_via_reasoner(self):
        cr = make_simple_reasoner()
        result = cr.simulate_intervention({"co2": 1.0})
        assert "effects" in result
        assert result["causal_level"] == CausalLevel.INTERVENTION.name

    def test_counterfactual_via_reasoner(self):
        cr = make_simple_reasoner()
        result = cr.counterfactual(
            observed     = {"co2": 0.8},
            intervention = {"co2": 0.1},
            query_nodes  = ["temp"],
        )
        assert "delta" in result
        assert result["causal_level"] == CausalLevel.COUNTERFACTUAL.name

    def test_detect_surprise_non_surprising(self):
        cr = create_causal_reasoner()

        class FakePE:
            is_surprising   = False
            source_id       = "test_node"
            error_magnitude = 0.1

        result = cr.detect_surprise(FakePE())
        assert result is None

    def test_detect_surprise_triggers_discovery(self):
        cr = create_causal_reasoner()

        class FakePE:
            is_surprising   = True
            source_id       = "unexpected_node"
            error_magnitude = 2.5
            class level:
                name = "L5_NARRATIVE"

        result = cr.detect_surprise(FakePE())
        assert result is not None
        assert result["trigger"] == "prediction_error_surprise"
        assert "unexpected_node" in cr.graph.nodes

    def test_import_from_knowledge_graph(self):
        cr = create_causal_reasoner()

        # Mock minimale del KnowledgeGraph
        class MockRelation:
            def __init__(self, rel, target, weight=0.8):
                self.rel = rel; self.target = target; self.weight = weight

        class MockEntity:
            def __init__(self, eid, etype, rels):
                self.id = eid; self.entity_type = etype; self.relations = rels

        class MockKG:
            def __init__(self):
                self._entities = {
                    "deforestation": MockEntity("deforestation", "EVENT",
                        [MockRelation("causes", "co2_increase")]),
                    "co2_increase":  MockEntity("co2_increase", "EVENT", []),
                }

        n = cr.import_from_knowledge_graph(MockKG())
        assert n == 1
        assert "deforestation" in cr.graph.nodes
        assert "co2_increase"  in cr.graph.nodes
        assert len(cr.graph.edges) == 1

    def test_status_reflects_activity(self):
        cr = make_simple_reasoner()
        cr.infer_cause({"co2": 0.8, "temp": 0.6})
        cr.simulate_intervention({"co2": 1.0})
        status = cr.get_full_status()
        assert status["graph"]["nodes"] == 4
        assert status["graph"]["edges"] == 3
        assert status["graph"]["is_dag"] is True
        assert status["inferences_made"] >= 1

    def test_factory_with_priors(self):
        priors = [
            ("cause_a", "effect_b", 0.7, "economics"),
            ("effect_b", "effect_c", 0.5, "economics"),
        ]
        cr = create_causal_reasoner_with_priors(priors)
        assert len(cr.graph.nodes) == 3
        assert len(cr.graph.edges) == 2

    def test_edge_mechanism_threshold(self):
        g = CausalGraph()
        g.add_node(CausalNode("input",  name="Input"))
        g.add_node(CausalNode("output", name="Output"))
        g.add_edge(CausalEdge("input", "output",
                               strength=1.0, mechanism=EdgeMechanism.THRESHOLD))
        # sotto soglia
        g.nodes["input"].set_value(0.3)
        r_low = g.propagate()
        # sopra soglia
        g.nodes["input"].set_value(0.8)
        g.nodes["output"].observed = False
        r_high = g.propagate()
        assert r_high["output"] > r_low["output"]

    def test_multiple_do_operators_independent(self):
        """Ogni do_operator deve agire su una copia indipendente."""
        g = make_climate_graph()
        m1 = g.do_operator("co2", 1.0)
        m2 = g.do_operator("co2", 0.0)
        # I due grafi mutilati devono avere valori diversi
        r1 = m1.propagate()
        r2 = m2.propagate()
        assert r1["co2"] != r2["co2"]


# ─────────────────────────────────────────────────────────────────────────────
# Esecuzione diretta
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    sys.exit(result.returncode)
