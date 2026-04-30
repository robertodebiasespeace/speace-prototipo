"""
Test minimo per i 4 nuovi comparti Cortex introdotti con M1.
Copre: istanziabilità, metodo self_report, e contratti principali.

Eseguibile con: pytest tests/test_cortex_compartments.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------------
# SAFETY MODULE
# ------------------------------------------------------------------

def test_safety_module_instantiable_and_reports():
    from cortex.comparti.safety_module import SafetyModule
    sm = SafetyModule()
    report = sm.self_report()
    assert report["module"] == "safety_module"
    assert isinstance(report["safe_mode"], bool)


def test_safety_module_classifies_risk():
    from cortex.comparti.safety_module import SafetyModule
    sm = SafetyModule()
    assert sm.evaluate_risk({"name": "read_log"}) == "low"
    assert sm.evaluate_risk({"name": "mutate_epigenome"}) == "medium"
    assert sm.evaluate_risk({"name": "replicate_to_cloud"}) == "high"
    assert sm.evaluate_risk({"name": "eu_ai_act_review"}) == "regulatory"


def test_safety_module_guard_blocks_medium_without_approval():
    from cortex.comparti.safety_module import SafetyModule
    sm = SafetyModule()
    result = sm.guard(lambda: "should_not_run",
                     {"name": "mutate_epigenome", "payload": {}})
    assert result["executed"] is False
    assert result["risk_level"] == "medium"


def test_safety_module_guard_allows_low():
    from cortex.comparti.safety_module import SafetyModule
    sm = SafetyModule()
    result = sm.guard(lambda: "ok", {"name": "read_log", "payload": {}})
    assert result["executed"] is True
    assert result["result"] == "ok"


# ------------------------------------------------------------------
# TEMPORAL LOBE
# ------------------------------------------------------------------

def test_temporal_lobe_analyzes_text():
    from cortex.comparti.temporal_lobe import TemporalLobe
    tl = TemporalLobe()
    out = tl.analyze_language("SPEACE mira alla pace e all'armonia globale")
    assert out["token_count"] > 0
    assert out["sentiment_placeholder"] in (-1, 0, 1)
    assert len(out["word_freq_top5"]) <= 5


def test_temporal_lobe_market_scan_is_disabled():
    from cortex.comparti.temporal_lobe import TemporalLobe
    tl = TemporalLobe()
    out = tl.market_scan("BTC")
    assert out["status"] == "disabled_phase1"


def test_temporal_lobe_extract_keywords():
    from cortex.comparti.temporal_lobe import TemporalLobe
    tl = TemporalLobe()
    kws = tl.extract_keywords("climate change climate policy harmony peace harmony")
    assert "climate" in kws or "harmony" in kws


# ------------------------------------------------------------------
# PARIETAL LOBE
# ------------------------------------------------------------------

def test_parietal_lobe_rejects_non_whitelisted():
    from cortex.comparti.parietal_lobe import ParietalLobe
    pl = ParietalLobe()
    out = pl.fetch_api("https://example.com")
    assert out["status"] == "rejected"
    assert out["reason"] == "domain_not_in_whitelist"


def test_parietal_lobe_rejects_invalid_scheme():
    from cortex.comparti.parietal_lobe import ParietalLobe
    pl = ParietalLobe()
    out = pl.fetch_api("ftp://rigeneproject.org")
    assert out["status"] == "rejected"
    assert out["reason"] == "invalid_url_scheme"


def test_parietal_lobe_iot_stub():
    from cortex.comparti.parietal_lobe import ParietalLobe
    pl = ParietalLobe()
    out = pl.iot_read("sensor_001")
    assert out["status"] == "no_iot_connected_phase1"


# ------------------------------------------------------------------
# CEREBELLUM
# ------------------------------------------------------------------

def test_cerebellum_rejects_out_of_whitelist():
    from cortex.comparti.cerebellum import Cerebellum
    cb = Cerebellum()
    out = cb.execute("rm_rf_slash", [])
    assert out["status"] == "rejected"
    assert out["reason"] == "command_not_in_whitelist"


def test_cerebellum_self_test_executes():
    from cortex.comparti.cerebellum import Cerebellum
    cb = Cerebellum()
    out = cb.execute("self_test", [])
    assert out["status"] == "executed"
    assert out["result"]["all_ok"] is True


def test_cerebellum_rollback_dry_run():
    from cortex.comparti.cerebellum import Cerebellum
    cb = Cerebellum()
    out = cb.execute("rollback_dry_run", [])
    assert out["status"] == "executed"
    assert out["result"]["dry_run"] is True
    assert isinstance(out["result"]["available_snapshots"], list)


# ------------------------------------------------------------------
# KERNEL DISPATCH
# ------------------------------------------------------------------

def test_kernel_lists_nine_compartments():
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="TEST", recursion_level=1)
    comps = k.list_compartments()
    assert len(comps) == 9
    for required in ("safety_module", "temporal_lobe", "parietal_lobe",
                     "cerebellum", "world_model", "prefrontal_cortex"):
        assert required in comps


def test_kernel_call_compartment_safety():
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="TEST", recursion_level=1)
    out = k.call_compartment("safety_module")
    assert out["status"] == "ok"
    assert out["result"]["module"] == "safety_module"


def test_kernel_call_compartment_unknown():
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="TEST", recursion_level=1)
    out = k.call_compartment("nonexistent_compartment")
    assert out["status"] == "unknown"
