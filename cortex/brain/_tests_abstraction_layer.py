"""
Tests — AbstractionLayer BRN-018
===================================
Run: python -m pytest cortex/brain/_tests_abstraction_layer.py -v
"""
import pytest
from cortex.brain.abstraction_layer import (
    Concept, ConceptRelation, ConceptualGraph, RelationType, AbstractionLevel,
    HierarchicalAbstractor, AnalogyEngine, ConceptualBlender,
    AbstractionLayer, create_abstraction_layer, create_abstraction_layer_with_concepts,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_animal_concept(cid, label, can_fly=0, has_legs=1, is_alive=1,
                         lays_eggs=0, domain="biology", level=2) -> Concept:
    return Concept(
        concept_id=cid, label=label, domain=domain,
        abstraction_level=level,
        features={"can_fly": float(can_fly), "has_legs": float(has_legs),
                  "is_alive": float(is_alive), "lays_eggs": float(lays_eggs),
                  "warm_blooded": 1.0},
        confidence=0.9,
    )


def make_vehicle_concept(cid, label, has_wheels=1, uses_fuel=1,
                          carries_passengers=1, domain="engineering") -> Concept:
    return Concept(
        concept_id=cid, label=label, domain=domain,
        abstraction_level=2,
        features={"has_wheels": float(has_wheels), "uses_fuel": float(uses_fuel),
                  "carries_passengers": float(carries_passengers),
                  "man_made": 1.0},
        confidence=0.85,
    )


# ─── TestConceptualGraph ───────────────────────────────────────────────────────

class TestConceptualGraph:

    def test_add_and_get(self):
        g = ConceptualGraph()
        c = make_animal_concept("cat", "cat")
        g.add_concept(c)
        assert g.get("cat") is c

    def test_get_by_label(self):
        g = ConceptualGraph()
        c = make_animal_concept("dog_1", "Dog")
        g.add_concept(c)
        found = g.get_by_label("dog")
        assert found is c

    def test_get_by_domain(self):
        g = ConceptualGraph()
        g.add_concept(make_animal_concept("cat", "cat", domain="biology"))
        g.add_concept(make_vehicle_concept("car", "car", domain="engineering"))
        bio = g.get_by_domain("biology")
        assert len(bio) == 1 and bio[0].concept_id == "cat"

    def test_get_by_level(self):
        g = ConceptualGraph()
        g.add_concept(make_animal_concept("cat", "cat", level=2))
        g.add_concept(make_animal_concept("animal", "animal", level=3))
        lvl2 = g.get_by_level(2)
        assert len(lvl2) == 1

    def test_cosine_similarity_identical(self):
        g = ConceptualGraph()
        c1 = make_animal_concept("c1", "cat1")
        c2 = make_animal_concept("c2", "cat2")   # same features
        g.add_concept(c1); g.add_concept(c2)
        sim = g.similarity("c1", "c2")
        assert sim > 0.95

    def test_cosine_similarity_orthogonal(self):
        g = ConceptualGraph()
        c1 = Concept("c1", "X", features={"a": 1.0, "b": 0.0})
        c2 = Concept("c2", "Y", features={"a": 0.0, "b": 1.0})
        g.add_concept(c1); g.add_concept(c2)
        sim = g.similarity("c1", "c2")
        assert sim < 0.1

    def test_get_similar_returns_ordered(self):
        g = ConceptualGraph()
        cat  = make_animal_concept("cat",  "cat",  can_fly=0, has_legs=1)
        dog  = make_animal_concept("dog",  "dog",  can_fly=0, has_legs=1)
        bird = make_animal_concept("bird", "bird", can_fly=1, has_legs=1)
        g.add_concept(cat); g.add_concept(dog); g.add_concept(bird)
        similar = g.get_similar("cat", top_k=2, min_sim=0.5)
        assert len(similar) >= 1
        # dog deve essere più simile a cat di bird
        ids = [s[0] for s in similar]
        if len(ids) >= 2:
            assert ids[0] == "dog"

    def test_similarity_no_common_features(self):
        g = ConceptualGraph()
        c1 = Concept("c1", "X", features={"a": 1.0})
        c2 = Concept("c2", "Y", features={"b": 1.0})
        g.add_concept(c1); g.add_concept(c2)
        assert g.similarity("c1", "c2") == 0.0


# ─── TestHierarchicalAbstractor ───────────────────────────────────────────────

class TestHierarchicalAbstractor:

    def test_abstract_creates_concept(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.5)
        concepts = [
            make_animal_concept("cat", "cat", can_fly=0),
            make_animal_concept("dog", "dog", can_fly=0),
            make_animal_concept("horse", "horse", can_fly=0),
        ]
        result = abs_.abstract(concepts, target_level=3, label="mammal")
        assert result is not None
        assert result.abstraction_level == 3
        assert result.source == "abstracted"

    def test_abstract_keeps_common_features(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.5)
        concepts = [
            make_animal_concept("c1", "cat"),
            make_animal_concept("c2", "dog"),
        ]
        result = abs_.abstract(concepts, target_level=3)
        assert result is not None
        # is_alive e warm_blooded sono comuni → devono apparire
        assert "is_alive" in result.features
        assert "warm_blooded" in result.features

    def test_abstract_adds_is_a_relations(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.5)
        c1 = make_animal_concept("c1", "cat")
        c2 = make_animal_concept("c2", "dog")
        result = abs_.abstract([c1, c2], target_level=3, label="mammal")
        assert result is not None
        c1_isa = [r.target_id for r in c1.get_relations(RelationType.IS_A)]
        assert result.concept_id in c1_isa

    def test_abstract_returns_none_no_features(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.9, max_feature_variance=0.01)
        concepts = [
            Concept("c1", "X", features={"a": 0.1}),
            Concept("c2", "Y", features={"a": 0.9}),   # alta varianza
        ]
        # La feature 'a' ha varianza alta → nessuna feature strutturale → None
        result = abs_.abstract(concepts, target_level=3)
        assert result is None

    def test_abstract_empty_input(self):
        abs_ = HierarchicalAbstractor()
        assert abs_.abstract([], target_level=3) is None

    def test_abstract_domain_preserved(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.5)
        concepts = [
            make_animal_concept("c1", "cat", domain="biology"),
            make_animal_concept("c2", "dog", domain="biology"),
        ]
        result = abs_.abstract(concepts, target_level=3)
        assert result is not None
        assert result.domain == "biology"

    def test_abstract_cross_domain_label(self):
        abs_ = HierarchicalAbstractor(min_feature_coverage=0.5)
        concepts = [
            make_animal_concept("c1", "cat", domain="biology"),
            make_vehicle_concept("c2", "car", domain="engineering"),
        ]
        result = abs_.abstract(concepts, target_level=3)
        # Poche features comuni → potrebbe essere None (ok)
        if result is not None:
            assert result.domain == "cross_domain"


# ─── TestAnalogyEngine ────────────────────────────────────────────────────────

class TestAnalogyEngine:

    def _make_pump_analogy(self):
        """Crea lo scenario cuore/pompa classico."""
        heart = Concept("heart", "heart", domain="biology",
                        features={"pumps_fluid": 1.0, "rhythmic": 1.0,
                                  "distributes_resource": 1.0, "essential": 1.0})
        pump  = Concept("pump",  "pump",  domain="engineering",
                        features={"pumps_fluid": 1.0, "rhythmic": 0.6,
                                  "distributes_resource": 1.0, "essential": 0.8})
        motor = Concept("motor", "motor", domain="engineering",
                        features={"rotates": 1.0, "uses_energy": 1.0,
                                  "distributes_resource": 0.3, "essential": 0.7})
        return heart, pump, motor

    def test_find_analogy_returns_best_match(self):
        eng = AnalogyEngine()
        heart, pump, motor = self._make_pump_analogy()
        result = eng.find_analogy(heart, [pump, motor])
        assert result is not None
        target, mapping, score = result
        assert target.concept_id == "pump"
        assert score > 0.3

    def test_find_analogy_empty_pool(self):
        eng = AnalogyEngine()
        heart, _, _ = self._make_pump_analogy()
        assert eng.find_analogy(heart, []) is None

    def test_find_analogy_no_overlap(self):
        eng = AnalogyEngine()
        src = Concept("s", "S", features={"a": 1.0, "b": 0.5})
        tgt = Concept("t", "T", features={"x": 1.0, "y": 0.5})
        assert eng.find_analogy(src, [tgt]) is None

    def test_project_analogy_creates_concept(self):
        eng = AnalogyEngine()
        heart, pump, _ = self._make_pump_analogy()
        common_feats = {"pumps_fluid", "distributes_resource"}
        mapping = {f: f for f in common_feats}
        projected = eng.project_analogy(heart, pump, mapping, "engineering")
        assert projected is not None
        assert projected.domain == "engineering"
        assert projected.source == "analogical"
        analogy_rels = [r.target_id for r in projected.get_relations(RelationType.ANALOGY_OF)]
        assert "heart" in analogy_rels

    def test_project_analogy_preserves_structure(self):
        eng = AnalogyEngine()
        src = Concept("s", "S", domain="A",
                      features={"pumps_fluid": 0.9, "rhythmic": 0.8})
        tgt = Concept("t", "T", domain="B",
                      features={"pumps_fluid": 0.7, "rhythmic": 0.5, "extra_b": 0.6})
        mapping = {"pumps_fluid": "pumps_fluid", "rhythmic": "rhythmic"}
        proj = eng.project_analogy(src, tgt, mapping, "B")
        assert "pumps_fluid" in proj.features
        assert "rhythmic" in proj.features


# ─── TestConceptualBlender ────────────────────────────────────────────────────

class TestConceptualBlender:

    def test_blend_creates_concept(self):
        blender = ConceptualBlender()
        virus = Concept("virus", "virus", domain="biology",
                        features={"self_replicating": 1.0, "harmful": 0.8,
                                  "infects_host": 1.0})
        software = Concept("soft", "software", domain="computing",
                           features={"runs_on_computer": 1.0, "executes_code": 1.0,
                                     "harmful": 0.2})
        result = blender.blend(virus, software, label="computer_virus")
        assert result is not None
        assert result.label == "computer_virus"
        assert result.source == "blended"

    def test_blend_contains_generic_space(self):
        blender = ConceptualBlender()
        c1 = Concept("c1", "A", features={"x": 0.8, "y": 0.7, "z": 1.0})
        c2 = Concept("c2", "B", features={"x": 0.9, "y": 0.6, "w": 0.5})
        result = blender.blend(c1, c2)
        # x e y sono compatibili (diff < 0.35) → devono essere nel blend
        assert "x" in result.features
        assert "y" in result.features

    def test_blend_has_blend_of_relations(self):
        blender = ConceptualBlender()
        c1 = Concept("c1", "A", features={"a": 0.5})
        c2 = Concept("c2", "B", features={"b": 0.5})
        result = blender.blend(c1, c2)
        blend_rels = [r.target_id for r in result.get_relations(RelationType.BLEND_OF)]
        assert "c1" in blend_rels
        assert "c2" in blend_rels

    def test_blend_level_at_least_max_input(self):
        blender = ConceptualBlender()
        c1 = Concept("c1", "A", features={"x": 0.5}, abstraction_level=2)
        c2 = Concept("c2", "B", features={"y": 0.5}, abstraction_level=4)
        result = blender.blend(c1, c2)
        assert result.abstraction_level >= 4

    def test_blend_cross_domain(self):
        blender = ConceptualBlender()
        c1 = Concept("c1", "A", domain="biology",   features={"a": 0.9})
        c2 = Concept("c2", "B", domain="computing", features={"b": 0.8})
        result = blender.blend(c1, c2)
        assert result.domain == "cross_domain"

    def test_blend_auto_label(self):
        blender = ConceptualBlender()
        c1 = Concept("c1", "Alpha", features={"x": 0.5})
        c2 = Concept("c2", "Beta",  features={"y": 0.5})
        result = blender.blend(c1, c2)
        assert "Alpha" in result.label and "Beta" in result.label


# ─── TestAbstractionLayer ─────────────────────────────────────────────────────

class TestAbstractionLayer:

    def test_init(self):
        al = create_abstraction_layer()
        status = al.get_full_status()
        assert status["status"] == "active"
        assert status["brn_id"] == "BRN-018"

    def test_add_concept(self):
        al = create_abstraction_layer()
        c  = make_animal_concept("cat", "cat")
        al.add_concept(c)
        assert al.graph.get("cat") is c

    def test_add_concept_updates_existing(self):
        al = create_abstraction_layer()
        c1 = Concept("x", "X", features={"a": 0.5})
        c2 = Concept("x", "X", features={"b": 0.7})
        al.add_concept(c1)
        al.add_concept(c2)
        # b deve essere stato aggiunto
        assert "b" in al.graph.get("x").features

    def test_add_concept_from_dict(self):
        al = create_abstraction_layer()
        c  = al.add_concept_from_dict("tree", {"height": 0.8, "photosynthesis": 1.0},
                                       domain="biology")
        assert al.graph.get(c.concept_id) is not None

    def test_process_runs_pipeline(self):
        al = create_abstraction_layer()
        concepts = [
            make_animal_concept("cat", "cat"),
            make_animal_concept("dog", "dog"),
        ]
        result = al.process(concepts)
        assert "cycle" in result
        assert "abstractions" in result
        assert result["cycle"] == 1

    def test_process_creates_abstraction(self):
        al = create_abstraction_layer()
        concepts = [
            make_animal_concept("cat", "cat"),
            make_animal_concept("dog", "dog"),
            make_animal_concept("fox", "fox"),
        ]
        result = al.process(concepts, run_blending=False, run_analogy=False)
        assert len(result["abstractions"]) >= 1

    def test_abstract_from_examples(self):
        al = create_abstraction_layer()
        al.add_concept(make_animal_concept("cat", "cat"))
        al.add_concept(make_animal_concept("dog", "dog"))
        result = al.abstract_from_examples(["cat", "dog"], target_level=3, label="mammal")
        assert result is not None
        assert al.graph.get(result.concept_id) is not None

    def test_abstract_from_examples_unknown_ids(self):
        al = create_abstraction_layer()
        result = al.abstract_from_examples(["nonexistent_1", "nonexistent_2"])
        assert result is None

    def test_find_analogy_cross_domain(self):
        al = create_abstraction_layer()
        al.add_concept(Concept("heart", "heart", domain="biology",
                               features={"pumps_fluid": 1.0, "distributes": 1.0,
                                         "rhythmic": 0.9, "essential": 1.0}))
        al.add_concept(Concept("pump", "pump", domain="engineering",
                               features={"pumps_fluid": 1.0, "distributes": 0.9,
                                         "rhythmic": 0.5, "essential": 0.8}))
        result = al.find_analogy("heart", "engineering")
        assert result is not None
        assert result.domain == "engineering"
        assert result.source == "analogical"

    def test_find_analogy_unknown_source(self):
        al = create_abstraction_layer()
        assert al.find_analogy("nonexistent", "engineering") is None

    def test_blend_two_concepts(self):
        al = create_abstraction_layer()
        al.add_concept(make_animal_concept("bird",  "bird",  can_fly=1))
        al.add_concept(make_vehicle_concept("plane", "plane", has_wheels=1))
        result = al.blend("bird", "plane")
        assert result is not None
        assert result.source == "blended"
        assert al.graph.get(result.concept_id) is not None

    def test_blend_unknown_id(self):
        al = create_abstraction_layer()
        al.add_concept(make_animal_concept("cat", "cat"))
        assert al.blend("cat", "nonexistent") is None

    def test_transfer_knowledge(self):
        al = create_abstraction_layer()
        # 3 concetti biologia con features strutturali
        for cid, lbl in [("c1","lion"),("c2","wolf"),("c3","shark")]:
            al.add_concept(Concept(cid, lbl, domain="biology",
                                   features={"predator": 1.0, "hunts": 1.0,
                                             "territorial": 0.8}))
        # Target domain: mercati finanziari
        al.add_concept(Concept("m1", "hedge_fund", domain="finance",
                               features={"predator": 0.9, "hunts": 0.8,
                                         "territorial": 0.7, "profit_driven": 1.0}))
        transferred = al.transfer_knowledge("biology", "finance")
        # Deve aver trasferito almeno un concetto
        assert len(transferred) >= 1
        for t in transferred:
            assert t.domain == "finance"

    def test_suggest_learning_strategy_empty_domain(self):
        al = create_abstraction_layer()
        strategy = al.suggest_learning_strategy("unknown_domain")
        assert strategy == "CURIOSITY_DRIVEN"

    def test_suggest_learning_strategy_analogical(self):
        al = create_abstraction_layer()
        # Pochi concetti nel target domain, ma molti in source
        al.add_concept(make_animal_concept("cat", "cat", domain="biology"))
        al.add_concept(make_animal_concept("dog", "dog", domain="biology"))
        al.add_concept(make_vehicle_concept("car", "car", domain="engineering"))
        strategy = al.suggest_learning_strategy("engineering")
        assert strategy in ("ANALOGICAL", "EPISODIC_REPLAY", "CURIOSITY_DRIVEN", "GRADIENT_BASED")

    def test_suggest_learning_strategy_gradient_based(self):
        al = create_abstraction_layer()
        for i in range(25):
            al.add_concept(make_animal_concept(f"c{i}", f"animal_{i}", domain="biology"))
        strategy = al.suggest_learning_strategy("biology")
        assert strategy == "GRADIENT_BASED"

    def test_import_from_knowledge_graph(self):
        al = create_abstraction_layer()

        class MockRel:
            def __init__(self, t): self.rel = "similar_to"; self.target = t; self.weight = 0.8

        class MockEntity:
            def __init__(self, eid, etype, props, rels):
                self.id = eid; self.entity_type = etype
                self.properties = props; self.relations = rels

        class MockKG:
            def __init__(self):
                self._entities = {
                    "carbon_dioxide": MockEntity("carbon_dioxide", "CONCEPT",
                        {"concentration": 0.8, "toxic_threshold": 0.6},
                        [MockRel("methane")]),
                    "methane": MockEntity("methane", "CONCEPT",
                        {"concentration": 0.4}, []),
                }

        n = al.import_from_knowledge_graph(MockKG())
        assert n == 2
        assert al.graph.get("kg_carbon_dioxide") is not None

    def test_observe_causal_structure(self):
        al = create_abstraction_layer()
        from cortex.brain.causal_reasoning import create_causal_reasoner, CausalEdge
        cr = create_causal_reasoner()
        cr.add_causal_link("co2", "temp", strength=0.8, domain="climate")
        cr.add_causal_link("temp", "ice_melt", strength=0.7, domain="climate")
        n = al.observe_causal_structure(cr)
        assert n >= 2
        # co2 deve avere feature causale
        c = al.graph.get("causal_co2")
        assert c is not None
        assert "causal_out_degree" in c.features

    def test_status_tracks_activity(self):
        al = create_abstraction_layer()
        al.add_concept(make_animal_concept("cat", "cat"))
        al.add_concept(make_animal_concept("dog", "dog"))
        al.process([make_animal_concept("bird", "bird"),
                    make_animal_concept("fox",  "fox")])
        status = al.get_full_status()
        assert status["graph"]["total_concepts"] >= 4

    def test_factory_with_concepts(self):
        al = create_abstraction_layer_with_concepts([
            {"label": "tree",  "features": {"height": 0.7}, "domain": "biology"},
            {"label": "shrub", "features": {"height": 0.3}, "domain": "biology"},
        ])
        assert len(al.graph) == 2

    def test_process_cycle_increments(self):
        al = create_abstraction_layer()
        c  = [make_animal_concept("c1", "cat"), make_animal_concept("c2", "dog")]
       