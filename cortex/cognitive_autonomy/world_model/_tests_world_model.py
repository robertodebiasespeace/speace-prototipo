"""
Test suite — M6.7: World Model / Knowledge Graph

Test IDs:
  WM-01→WM-08   WorldSnapshot store
  KG-09→KG-18   KnowledgeGraph
  FD-19→FD-24   Feed connectors (offline/fixture)
  INF-25→INF-32 InferenceEngine + scenarios
  MB-33→MB-36   MemoryBridge
  CX-37→CX-42   WorldModelCortex (facade)
  E2E-43→E2E-45 End-to-end integration

Total target: 45 tests

Milestone: M6.7
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cortex.cognitive_autonomy.world_model.snapshot       import WorldSnapshot
from cortex.cognitive_autonomy.world_model.knowledge_graph import (
    KnowledgeGraph, EntityType, Entity, Relation, _INVERSE_RELATIONS
)
from cortex.cognitive_autonomy.world_model.inference import (
    InferenceEngine, CausalRule, BUILTIN_RULES, _get, _set_path
)
from cortex.cognitive_autonomy.world_model.memory_bridge  import MemoryBridge
from cortex.cognitive_autonomy.world_model.feeds.base     import FeedConnector, FeedResult
from cortex.cognitive_autonomy.world_model.feeds.nasa     import NASADonkiFeed
from cortex.cognitive_autonomy.world_model.feeds.noaa     import NOAAClimateFeed
from cortex.cognitive_autonomy.world_model.feeds.un_sdg   import UNSDGFeed
from cortex.cognitive_autonomy.world_model.cortex         import WorldModelCortex


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def empty_snapshot():
    return WorldSnapshot(seed_path=None, db_path=None, auto_load=False)


@pytest.fixture
def snapshot():
    return WorldSnapshot(seed_path=None, db_path=None, auto_load=False)


@pytest.fixture
def kg():
    return KnowledgeGraph()


@pytest.fixture
def engine():
    return InferenceEngine(rules=list(BUILTIN_RULES))


@pytest.fixture
def cortex():
    wm = WorldModelCortex(seed_path=None, db_path=None)
    wm.initialize(seed_kg=True)
    return wm


# ===========================================================================
# WM-01→WM-08  WorldSnapshot
# ===========================================================================

class TestWorldSnapshot:

    def test_wm01_init_creates_default_structure(self, empty_snapshot):
        """WM-01: snapshot vuoto ha tutte le sezioni standard."""
        keys = empty_snapshot.keys()
        for k in ("meta", "speace_state", "planet_state", "technology_state",
                  "rigene_objectives", "knowledge_graph", "scenarios", "feed_cache"):
            assert k in keys, f"missing key: {k}"

    def test_wm02_get_root_returns_deep_copy(self, snapshot):
        """WM-02: get() ritorna deep copy (modifiche non propagano)."""
        d = snapshot.get()
        d["meta"]["version"] = "hacked"
        assert snapshot.get("meta.version") != "hacked"

    def test_wm03_patch_simple_value(self, snapshot):
        """WM-03: patch() aggiorna un valore scalare."""
        snapshot.patch("planet_state.climate.co2_ppm", 430.0, persist=False)
        assert snapshot.get("planet_state.climate.co2_ppm") == 430.0

    def test_wm04_patch_nested_creates_path(self, snapshot):
        """WM-04: patch() crea nodi intermedi se assenti."""
        snapshot.patch("new_section.deep.key", "value", persist=False)
        assert snapshot.get("new_section.deep.key") == "value"

    def test_wm05_patch_increments_update_count(self, snapshot):
        """WM-05: ogni patch incrementa meta.update_count."""
        count0 = snapshot.get("meta.update_count") or 0
        snapshot.patch("speace_state.phase", 2, persist=False)
        snapshot.patch("speace_state.phase", 3, persist=False)
        assert snapshot.get("meta.update_count") == count0 + 2

    def test_wm06_merge_section(self, snapshot):
        """WM-06: merge() aggiorna solo i campi forniti."""
        snapshot.merge("speace_state", {"fitness": 0.77, "phase": 2}, persist=False)
        assert snapshot.get("speace_state.fitness") == 0.77
        assert snapshot.get("speace_state.phase") == 2

    def test_wm07_feed_cache_update(self, snapshot):
        """WM-07: update_feed_cache scrive correttamente."""
        snapshot.update_feed_cache("nasa", {"flares": 3}, status="ok")
        fc = snapshot.get("feed_cache.nasa")
        assert fc["status"] == "ok"
        assert fc["data"]["flares"] == 3

    def test_wm08_to_json_is_valid(self, snapshot):
        """WM-08: to_json() produce JSON valido."""
        import json
        text = snapshot.to_json()
        d = json.loads(text)
        assert "meta" in d

    def test_wm09_get_default(self, snapshot):
        """WM-09: get() con path assente ritorna default."""
        val = snapshot.get("nonexistent.path", default="MISS")
        assert val == "MISS"

    def test_wm10_get_stats(self, snapshot):
        """WM-10: get_stats() ritorna struttura corretta."""
        stats = snapshot.get_stats()
        assert "update_count" in stats
        assert "kg_entities" in stats


# ===========================================================================
# KG-09→KG-18  KnowledgeGraph
# ===========================================================================

class TestKnowledgeGraph:

    def test_kg09_add_entity(self, kg):
        """KG-09: add_entity crea un'entità con tipo."""
        e = kg.add_entity("SPEACE", EntityType.AI_AGENT, {"phase": 1})
        assert e.id == "SPEACE"
        assert e.entity_type == EntityType.AI_AGENT
        assert e.properties["phase"] == 1

    def test_kg10_add_entity_idempotent(self, kg):
        """KG-10: add_entity sullo stesso id aggiorna le proprietà."""
        kg.add_entity("X", EntityType.CONCEPT, {"val": 1})
        kg.add_entity("X", EntityType.CONCEPT, {"val": 2})
        assert kg.count() == 1
        assert kg.get_entity("X").properties["val"] == 2

    def test_kg11_add_relation_creates_entities(self, kg):
        """KG-11: add_relation crea entità se non esistono."""
        kg.add_relation("A", "created_by", "B")
        assert kg.get_entity("A") is not None
        assert kg.get_entity("B") is not None

    def test_kg12_inverse_relation(self, kg):
        """KG-12: add_relation crea la relazione inversa automaticamente."""
        kg.add_relation("SPEACE", "created_by", "Roberto", add_inverse=True)
        assert "SPEACE" in kg.neighbors("Roberto", "creates")

    def test_kg13_find_by_type(self, kg):
        """KG-13: find_by_type ritorna le entità del tipo specificato."""
        kg.add_entity("Alice", EntityType.HUMAN, {"name": "Alice"})
        kg.add_entity("Bob",   EntityType.HUMAN, {"name": "Bob"})
        kg.add_entity("HAL",   EntityType.AI_AGENT)
        humans = kg.find_by_type(EntityType.HUMAN)
        assert len(humans) == 2

    def test_kg14_path_exists_direct(self, kg):
        """KG-14: path_exists rileva collegamento diretto."""
        kg.add_relation("X", "rel", "Y")
        assert kg.path_exists("X", "Y") is True

    def test_kg15_path_exists_indirect(self, kg):
        """KG-15: path_exists rileva collegamento indiretto (BFS)."""
        kg.add_relation("A", "r", "B")
        kg.add_relation("B", "r", "C")
        assert kg.path_exists("A", "C") is True

    def test_kg16_path_not_exists(self, kg):
        """KG-16: path_exists ritorna False se non esiste percorso."""
        kg.add_entity("Isolated")
        kg.add_entity("Other")
        assert kg.path_exists("Isolated", "Other") is False

    def test_kg17_seed_from_rigene(self, kg):
        """KG-17: seed_from_rigene popola entità e relazioni fondamentali."""
        kg.seed_from_rigene()
        assert kg.count() >= 8
        assert kg.get_entity("SPEACE") is not None
        assert kg.get_entity("Rigene_Project") is not None
        # Verifica relazione SPEACE → created_by → Roberto_De_Biase
        assert "Roberto_De_Biase" in kg.neighbors("SPEACE", "created_by")

    def test_kg18_export_import_roundtrip(self, kg):
        """KG-18: to_dict / load_dict roundtrip conserva entità e relazioni."""
        kg.add_entity("E1", EntityType.CONCEPT, {"v": 42})
        kg.add_relation("E1", "part_of", "E2")
        exported = kg.to_dict()
        kg2 = KnowledgeGraph()
        kg2.load_dict(exported)
        assert kg2.count() == kg.count()
        e1 = kg2.get_entity("E1")
        assert e1 is not None
        assert e1.properties.get("v") == 42


# ===========================================================================
# FD-19→FD-24  Feed connectors
# ===========================================================================

class TestFeedConnectors:

    def test_fd19_nasa_fixture_has_required_keys(self):
        """FD-19: NASADonkiFeed fixture ha struttura attesa."""
        feed = NASADonkiFeed()
        result = feed._fixture()
        assert "solar_flares_7d" in result
        assert "last_flares" in result
        assert isinstance(result["last_flares"], list)

    def test_fd20_noaa_fixture_has_co2(self):
        """FD-20: NOAAClimateFeed fixture ha co2_ppm valido."""
        feed = NOAAClimateFeed()
        result = feed._fixture()
        assert result["co2_ppm"] > 400
        assert "data_source" in result

    def test_fd21_un_sdg_fixture_has_17_goals(self):
        """FD-21: UNSDGFeed fixture ha 17 obiettivi SDG."""
        feed = UNSDGFeed()
        result = feed._fixture()
        assert result["goals_count"] == 17
        assert len(result["goals"]) == 17

    def test_fd22_feed_result_ok_property(self):
        """FD-22: FeedResult.ok è True per status ok e cached."""
        ok  = FeedResult("test", "ok",     data={})
        ca  = FeedResult("test", "cached", data={})
        off = FeedResult("test", "offline", data={})
        assert ok.ok is True
        assert ca.ok is True
        assert off.ok is False

    def test_fd23_rate_limit_returns_cached(self):
        """FD-23: second fetch entro rate limit ritorna cached."""
        feed = NOAAClimateFeed()
        feed.min_interval_s = 9999.0   # forza rate limit
        # Prima fetch (usa fixture perché HTTP non disponibile in test)
        r1 = feed.fetch()
        r2 = feed.fetch()
        assert r2.source == "cache"

    def test_fd24_force_bypasses_rate_limit(self):
        """FD-24: force=True bypassa il rate limit."""
        feed = NASADonkiFeed()
        feed.min_interval_s = 9999.0
        r1 = feed.fetch()
        r2 = feed.fetch(force=True)
        # Entrambe devono aver completato (anche se offline/fixture)
        assert r2 is not None
        assert r2.feed_name == "nasa"


# ===========================================================================
# INF-25→INF-32  InferenceEngine
# ===========================================================================

_SAMPLE_SNAP = {
    "speace_state": {"phase": 1, "fitness": 0.58, "m5_complete": True},
    "planet_state": {
        "climate": {"co2_ppm": 422.0, "status": "critical", "global_temp_anomaly_c": 1.2},
        "biodiversity": {"status": "declining", "species_at_risk_pct": 28.0},
        "social": {"sdg_progress": "insufficient"},
    },
    "technology_state": {"ai_capability_level": "narrow_general", "iot_connected_devices_bn": 16},
}


class TestInferenceEngine:

    def test_inf25_builtin_rules_loaded(self, engine):
        """INF-25: built-in rules sono caricate correttamente."""
        assert len(engine._rules) >= 5

    def test_inf26_apply_rules_returns_active(self, engine):
        """INF-26: apply_rules attiva le regole che soddisfano la condizione."""
        active = engine.apply_rules(_SAMPLE_SNAP)
        # R002 (climate critical → SDG) e R005 (M5 complete → fitness) devono attivarsi
        rule_ids = [r.rule_id for r in active]
        assert "R002" in rule_ids
        assert "R005" in rule_ids

    def test_inf27_apply_rules_domain_filter(self, engine):
        """INF-27: apply_rules con domain_filter esclude altri domini."""
        active = engine.apply_rules(_SAMPLE_SNAP, domain_filter="climate")
        domains = {r.domain for r in active}
        assert domains <= {"climate"}

    def test_inf28_simulate_returns_scenario(self, engine):
        """INF-28: simulate() ritorna Scenario con id e effects."""
        sc = engine.simulate(
            _SAMPLE_SNAP, name="Test CO2",
            interventions={"planet_state.climate.co2_ppm": 435.0}
        )
        assert sc.scenario_id.startswith("SC-")
        assert sc.name == "Test CO2"

    def test_inf29_simulate_triggers_rules(self, engine):
        """INF-29: scenario CO2 > 430 triggera R001."""
        sc = engine.simulate(
            _SAMPLE_SNAP, "High CO2",
            interventions={"planet_state.climate.co2_ppm": 435.0}
        )
        assert "R001" in sc.triggered_rules

    def test_inf30_scenario_plausibility_in_range(self, engine):
        """INF-30: plausibility è in [0..1]."""
        sc = engine.simulate(_SAMPLE_SNAP, "Test", interventions={})
        assert 0.0 <= sc.plausibility <= 1.0

    def test_inf31_scenario_rigene_score_in_range(self, engine):
        """INF-31: rigene_score è in [-1..+1]."""
        sc = engine.simulate(_SAMPLE_SNAP, "Test", interventions={})
        assert -1.0 <= sc.rigene_score <= 1.0

    def test_inf32_standard_scenarios_returns_three(self, engine):
        """INF-32: run_standard_scenarios ritorna esattamente 3 scenari."""
        scenarios = engine.run_standard_scenarios(_SAMPLE_SNAP)
        assert len(scenarios) == 3
        names = [s.name for s in scenarios]
        assert any("CO2" in n for n in names)
        assert any("Phase" in n for n in names)


# ===========================================================================
# MB-33→MB-36  MemoryBridge
# ===========================================================================

class _MockMemory:
    """Mock di AutobiographicalMemory per test."""
    def __init__(self):
        self._episodes = []

    def store_episode(self, content, context="", tags=None, metadata=None):
        ep = {"content": content, "context": context,
              "tags": tags or [], "metadata": metadata or {}}
        self._episodes.append(ep)
        return f"EP-{len(self._episodes):04d}"

    def retrieve_episodes(self, query="", limit=10):
        return self._episodes[-limit:]


class TestMemoryBridge:

    def test_mb33_init_without_memory(self):
        """MB-33: MemoryBridge funziona senza memoria connessa."""
        snap = WorldSnapshot(seed_path=None, db_path=None, auto_load=False)
        bridge = MemoryBridge(snap, None)
        result = bridge.snapshot_to_memory()
        assert result is None   # memory not connected → None

    def test_mb34_snapshot_to_memory_stores_episode(self):
        """MB-34: snapshot_to_memory() crea un episodio in memoria."""
        snap = WorldSnapshot(seed_path=None, db_path=None, auto_load=False)
        snap.patch("planet_state.climate.co2_ppm", 425.0, persist=False)
        mem = _MockMemory()
        bridge = MemoryBridge(snap, mem)
        ep_id = bridge.snapshot_to_memory()
        assert ep_id is not None
        assert len(mem._episodes) == 1
        assert "CO2" in mem._episodes[0]["content"] or "co2" in mem._episodes[0]["content"].lower()

    def test_mb35_memory_to_snapshot_extracts_stats(self):
        """MB-35: memory_to_snapshot() estrae statistiche dagli episodi."""
        snap = WorldSnapshot(seed_path=None, db_path=None, auto_load=False)
        mem = _MockMemory()
        # Prepopola memoria con episodi che hanno metadata
        mem._episodes = [
            {"content": "test", "metadata": {"co2_ppm": 420.0, "speace_phase": 1}},
            {"content": "test", "metadata": {"co2_ppm": 425.0, "speace_phase": 1}},
        ]
        bridge = MemoryBridge(snap, mem)
        stats = bridge.memory_to_snapshot()
        assert stats["episode_count"] == 2
        assert "avg_co2_ppm" in stats

    def test_mb36_bridge_stats(self):
        """MB-36: get_stats() ritorna struttura corretta."""
        snap = WorldSnapshot(seed_path=None, db_path=None, auto_load=False)
        bridge = MemoryBridge(snap)
        stats = bridge.get_stats()
        assert "bridge_events" in stats
        assert stats["snapshot_connected"] is True
        assert stats["memory_connected"] is False


# ===========================================================================
# CX-37→CX-42  WorldModelCortex
# ===========================================================================

class TestWorldModelCortex:

    def test_cx37_initialize_populates_kg(self, cortex):
        """CX-37: initialize() popola il KG con entità Rigene."""
        assert cortex.kg.count() >= 8

    def test_cx38_query_returns_value(self, cortex):
        """CX-38: query() legge correttamente dal snapshot."""
        phase = cortex.query("speace_state.phase")
        assert phase is not None

    def test_cx39_update_persists_in_snapshot(self, cortex):
        """CX-39: update() scrive nel snapshot."""
        cortex.update("speace_state.fitness", 0.80)
        assert cortex.query("speace_state.fitness") == 0.80

    def test_cx40_ask_returns_answers(self, cortex):
        """CX-40: ask() con keyword 'co2' ritorna il valore CO2."""
        result = cortex.ask("qual è il livello di co2?")
        assert "answers" in result
        assert len(result["answers"]) > 0

    def test_cx41_refresh_feeds_returns_statuses(self, cortex):
        """CX-41: refresh_feeds() ritorna dict con status per ogni feed."""
        statuses = cortex.refresh_feeds()
        assert "nasa" in statuses
        assert "noaa" in statuses
        assert "un_sdg" in statuses

    def test_cx42_get_stats_structure(self, cortex):
        """CX-42: get_stats() ritorna struttura completa."""
        stats = cortex.get_stats()
        assert "snapshot" in stats
        assert "knowledge_graph" in stats
        assert "inference" in stats
        assert "bridge" in stats
        assert stats["initialized"] is True


# ===========================================================================
# E2E-43→E2E-45  End-to-end integration
# ===========================================================================

class TestEndToEnd:

    def test_e2e43_run_inference_stores_scenarios(self, cortex):
        """E2E-43: run_inference() esegue scenari e li persiste nel snapshot."""
        cortex.run_inference()
        scenarios = cortex.query("scenarios")
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 3

    def test_e2e44_feed_refresh_updates_co2(self, cortex):
        """E2E-44: refresh_feeds() aggiorna co2_ppm se NOAA risponde."""
        cortex.refresh_feeds()
        # NOAA usa fixture offline → co2 deve essere presente
        co2 = cortex.query("planet_state.climate.co2_ppm")
        assert co2 is not None and co2 > 400

    def test_e2e45_full_cycle(self, cortex):
        """E2E-45: ciclo completo init → feed → inference → memory."""
        # Update state
        cortex.update("speace_state.fitness", 0.72)
        # Refresh feeds (offline)
        cortex.refresh_feeds()
        # Run inference
        scenarios = cortex.run_inference()
        assert len(scenarios) == 3
        # Check rigene scores exist
        for sc in scenarios:
            assert "rigene_score" in sc
        # KG integrity
        assert cortex.kg.path_exists("SPEACE", "Rigene_Project")
        assert cortex.kg.path_exists("SPEACE", "Earth")
        # Summary
        summary = cortex._build_summary()
        assert summary["speace_fitness"] == 0.72
        assert summary["kg_entities"] >= 8
