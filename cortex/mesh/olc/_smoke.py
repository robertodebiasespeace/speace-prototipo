"""
Smoke test locale per OLC (M4.3).
Esegue:
  1. Import → registry popolato con 12 tipi
  2. validate() su istanze valide (deve ritornare [])
  3. validate() su istanze invalide (deve ritornare violazioni coerenti)
  4. to_dict() / from_dict() round-trip
  5. is_compatible_with() exact e non-compat
  6. registry.check_compatibility() via nomi
Esecuzione: python -m cortex.mesh.olc._smoke
"""

from __future__ import annotations
import json
import sys
import traceback

from cortex.mesh.olc import (
    ALL_TYPES,
    SensoryFrame,
    InterpretationFrame,
    DecisionFrame,
    SafetyVerdict,
    NeedsSnapshot,
    TaskProposal,
    all_types,
    names,
    check_compatibility,
    snapshot,
    NEEDS_CATALOG,
    OLCValidationError,
)


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    failures = []

    # ------------------------------------------------------------------
    # 1. Registry popolato
    # ------------------------------------------------------------------
    try:
        reg_names = set(names())
        expected = {t._OLC_NAME for t in ALL_TYPES}
        _assert(reg_names == expected, f"registry names mismatch: got {reg_names}, exp {expected}")
        _assert(len(all_types()) == 12, f"atteso 12 tipi registrati, trovati {len(all_types())}")
        print(f"[1/6] registry OK — {len(all_types())} tipi: {sorted(reg_names)}")
    except Exception as e:
        failures.append(("registry populate", e))
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 2. validate() su istanze valide → []
    # ------------------------------------------------------------------
    try:
        sf = SensoryFrame(source="user_input", payload={"q": "ciao"}, modality="text", confidence=0.9)
        _assert(sf.validate() == [], f"SensoryFrame valido ha violazioni: {sf.validate()}")

        intf = InterpretationFrame(intent="greeting", confidence=0.85, entities=["user"])
        _assert(intf.validate() == [], f"InterpretationFrame valido ha violazioni: {intf.validate()}")

        ns = NeedsSnapshot(
            needs={k: 0.5 for k in NEEDS_CATALOG},
            gap={k: 0.1 for k in NEEDS_CATALOG},
        )
        _assert(ns.validate() == [], f"NeedsSnapshot valido ha violazioni: {ns.validate()}")

        tp = TaskProposal(title="bilanciare carico", driving_need="harmony", priority=0.7)
        _assert(tp.validate() == [], f"TaskProposal valido ha violazioni: {tp.validate()}")

        print("[2/6] validate() su istanze valide OK (4 tipi campionati)")
    except Exception as e:
        failures.append(("validate valid", e))
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 3. validate() cattura violazioni note
    # ------------------------------------------------------------------
    try:
        # SensoryFrame con confidence fuori range
        sf_bad = SensoryFrame(source="", payload={}, confidence=1.5)
        violations = sf_bad.validate()
        _assert(any("source" in x for x in violations), "atteso violazione su source vuoto")
        _assert(any("confidence" in x for x in violations), "atteso violazione su confidence")
        # DecisionFrame con risk_level non valido
        df_bad = DecisionFrame(action="x", args={}, risk_level="CRITICAL", risk=2.0)
        violations = df_bad.validate()
        _assert(any("risk_level" in x for x in violations), "atteso violazione risk_level")
        _assert(any("risk" in x for x in violations), "atteso violazione risk numerico")
        # SafetyVerdict blocked=True senza reasons
        sv_bad = SafetyVerdict(blocked=True, risk_level="high", reasons=[])
        violations = sv_bad.validate()
        _assert(any("reasons" in x for x in violations), "atteso violazione reasons mancanti")
        # NeedsSnapshot con chiave extra
        ns_bad = NeedsSnapshot(
            needs={**{k: 0.5 for k in NEEDS_CATALOG}, "aliens": 0.9},
            gap={k: 0.0 for k in NEEDS_CATALOG},
        )
        violations = ns_bad.validate()
        _assert(any("aliens" in x or "extra" in x for x in violations), f"atteso violazione chiave extra, got {violations}")
        print("[3/6] validate() cattura violazioni OK")
    except Exception as e:
        failures.append(("validate invalid", e))
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 4. Round-trip to_dict/from_dict
    # ------------------------------------------------------------------
    try:
        sf = SensoryFrame(source="noaa", payload={"t": 14.5}, modality="numeric", confidence=0.88)
        d = sf.to_dict()
        _assert("_olc" in d and d["_olc"]["name"] == "olc.sensory_frame", "missing _olc meta")
        # JSON serializable
        js = json.dumps(d)
        back = SensoryFrame.from_dict(json.loads(js))
        _assert(back == sf, "round-trip non simmetrico su SensoryFrame")

        ns = NeedsSnapshot(
            needs={k: round(i / 10, 2) for i, k in enumerate(NEEDS_CATALOG)},
            gap={k: 0.0 for k in NEEDS_CATALOG},
        )
        back = NeedsSnapshot.from_dict(ns.to_dict())
        _assert(back.needs == ns.needs, "round-trip NeedsSnapshot")

        # Mismatch OLC name → errore
        try:
            SensoryFrame.from_dict({"_olc": {"name": "olc.wrong"}, "source": "x", "payload": {}})
            raise RuntimeError("atteso errore su mismatch _olc.name ma non sollevato")
        except OLCValidationError:
            pass
        print("[4/6] round-trip to_dict/from_dict OK (con JSON + mismatch check)")
    except Exception as e:
        failures.append(("round-trip", e))
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 5. is_compatible_with — exact + incompat
    # ------------------------------------------------------------------
    try:
        _assert(SensoryFrame.is_compatible_with(SensoryFrame), "exact compat con se stesso deve essere True")
        _assert(not SensoryFrame.is_compatible_with(InterpretationFrame), "SensoryFrame !→ InterpretationFrame")
        _assert(not DecisionFrame.is_compatible_with(SafetyVerdict), "DecisionFrame !→ SafetyVerdict")
        print("[5/6] is_compatible_with() exact + incompat OK")
    except Exception as e:
        failures.append(("compat", e))
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 6. registry.check_compatibility() via nomi
    # ------------------------------------------------------------------
    try:
        _assert(check_compatibility("olc.sensory_frame", "olc.sensory_frame"), "name-based exact compat")
        _assert(not check_compatibility("olc.sensory_frame", "olc.interpretation_frame"),
                "name-based cross-type incompat")
        try:
            check_compatibility("olc.does_not_exist", "olc.sensory_frame")
            raise RuntimeError("atteso OLCValidationError per nome sconosciuto")
        except OLCValidationError:
            pass
        snap = snapshot()
        _assert(len(snap) == 12, f"snapshot atteso 12 entry, trovate {len(snap)}")
        _assert("olc.sensory_frame" in snap, "snapshot deve contenere sensory_frame")
        print(f"[6/6] registry compat + snapshot OK (12 tipi, esempio snapshot[sensory_frame]={snap['olc.sensory_frame']})")
    except Exception as e:
        failures.append(("registry compat", e))
        traceback.print_exc()

    if failures:
        print(f"\n❌ FAILURES: {len(failures)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    print("\n✅ TUTTI I SMOKE TEST OLC PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
