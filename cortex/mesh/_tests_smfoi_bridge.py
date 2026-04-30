"""
Test suite per cortex.mesh.smfoi_bridge (M4.15)

Copre:
  AC-B1   is_enabled rispetta default OFF se epigenome senza blocco mesh
  AC-B2   is_enabled True solo con `epigenome.mesh.enabled: true`
  AC-B3   bridge OFF → result.enabled=False, push invariato, no daemon build
  AC-B4   bridge ON con healthy → enabled=True, promoted=False, push invariato
  AC-B5   bridge ON con verdict watch/alert/critical → priority lifted
  AC-B6   push originale "none" → type rinominato in mesh_<verdict>
  AC-B7   bridge cattura errori interni in `error` senza sollevare
  AC-B8   step3bis_needs_check function-style funziona end-to-end
  AC-B9   reset_global_bridge consente nuova istanza (ricarica daemon)
  AC-B10  daemon è cachato (1 build, N tick)

Esecuzione: python -m cortex.mesh._tests_smfoi_bridge
"""

from __future__ import annotations

import os
import tempfile
import traceback
from typing import Any, Dict, List, Tuple

from cortex.mesh.smfoi_bridge import (
    MeshNeedsCheck,
    NeedsCheckResult,
    is_enabled,
    step3bis_needs_check,
    reset_global_bridge,
)
from cortex.mesh.olc import NeedsSnapshot
from cortex.mesh.olc.base import NEEDS_CATALOG
from cortex.mesh.harmony import HarmonyVerdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmpfile(suffix: str = ".jsonl") -> str:
    fd, path = tempfile.mkstemp(prefix="mesh_bridge_test_", suffix=suffix)
    os.close(fd)
    os.unlink(path)
    return path


def _epi(enabled: bool) -> Dict[str, Any]:
    return {"mesh": {"enabled": enabled}}


def _bridge_with_forced_verdict(verdict: HarmonyVerdict, telemetry_path: str) -> MeshNeedsCheck:
    """Bridge che intercetta il daemon e lo sostituisce con un fake che ritorna
    un TickResult con il verdict richiesto."""
    from cortex.mesh.daemon import TickResult

    class _FakeDaemon:
        def __init__(self, v):
            self._v = v
            self._tick_calls = 0

        def tick(self, runtime_snapshot=None):
            self._tick_calls += 1
            return TickResult(
                ok=True,
                cycle_id=f"fake-cyc-{self._tick_calls:04d}",
                ts="2026-04-25T10:00:00Z",
                verdict=str(self._v.value),
                driving_need="harmony" if self._v != HarmonyVerdict.HEALTHY else None,
                proposals_count=2 if self._v != HarmonyVerdict.HEALTHY else 0,
                error=None,
            )

    bridge = MeshNeedsCheck(telemetry_path=telemetry_path)
    bridge._daemon = _FakeDaemon(verdict)  # type: ignore[attr-defined]
    return bridge


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def case_ac_b1_is_enabled_default_off():
    assert is_enabled(None) is False
    assert is_enabled({}) is False
    assert is_enabled({"flags": {"x": True}}) is False
    assert is_enabled({"mesh": {}}) is False
    return "AC-B1 default OFF su epigenome vuoto/missing"


def case_ac_b2_is_enabled_true_only_explicit():
    assert is_enabled({"mesh": {"enabled": True}}) is True
    assert is_enabled({"mesh": {"enabled": False}}) is False
    assert is_enabled({"mesh": {"enabled": "yes"}}) is True  # truthy
    return "AC-B2 enabled True solo con flag esplicito"


def case_ac_b3_bridge_off_passthrough():
    bridge = MeshNeedsCheck()
    push_in = {"type": "user", "priority": 1, "content": {"x": 1}, "source": "ext"}
    res = bridge.run(push=push_in, epigenome=_epi(False))
    assert isinstance(res, NeedsCheckResult)
    assert res.enabled is False
    assert res.promoted is False
    assert res.push == push_in
    # Daemon NON deve essere costruito
    assert bridge._daemon is None  # type: ignore[attr-defined]
    return "AC-B3 OFF → passthrough, no daemon build"


def case_ac_b4_bridge_on_healthy_no_promote():
    path = _tmpfile()
    try:
        bridge = _bridge_with_forced_verdict(HarmonyVerdict.HEALTHY, path)
        push_in = {"type": "user", "priority": 1, "content": None, "source": "ext"}
        res = bridge.run(push=push_in, epigenome=_epi(True))
        assert res.enabled is True
        assert res.verdict == "healthy"
        assert res.promoted is False
        # Push intatto
        assert res.push["type"] == "user"
        assert res.push["priority"] == 1
        return "AC-B4 ON + healthy → no promotion, push intatto"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_b5_bridge_promotes_on_alerts():
    path = _tmpfile()
    try:
        # WATCH lift +1
        b1 = _bridge_with_forced_verdict(HarmonyVerdict.WATCH, path)
        r1 = b1.run(push={"type": "user", "priority": 0}, epigenome=_epi(True))
        assert r1.promoted is True
        assert r1.push["priority"] >= 1, r1.push

        # ALERT lift +2
        b2 = _bridge_with_forced_verdict(HarmonyVerdict.ALERT, path)
        r2 = b2.run(push={"type": "user", "priority": 1}, epigenome=_epi(True))
        assert r2.promoted is True
        assert r2.push["priority"] >= 2, r2.push

        # CRITICAL lift +3
        b3 = _bridge_with_forced_verdict(HarmonyVerdict.CRITICAL, path)
        r3 = b3.run(push={"type": "user", "priority": 0}, epigenome=_epi(True))
        assert r3.promoted is True
        assert r3.push["priority"] >= 3, r3.push

        return f"AC-B5 lift WATCH/ALERT/CRITICAL → priorities ({r1.push['priority']},{r2.push['priority']},{r3.push['priority']})"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_b6_push_none_renamed():
    path = _tmpfile()
    try:
        bridge = _bridge_with_forced_verdict(HarmonyVerdict.WATCH, path)
        res = bridge.run(
            push={"type": "none", "priority": 0, "content": None, "source": "internal"},
            epigenome=_epi(True),
        )
        assert res.push["type"] == "mesh_watch", res.push
        assert res.push["source"] == "cnm"
        assert isinstance(res.push.get("content"), dict)
        assert res.push["content"].get("verdict") == "watch"
        return "AC-B6 push 'none' rinominato a mesh_watch + content arricchito"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_b7_error_caught_in_result():
    """Daemon che solleva durante tick → result.error popolato, nessuna eccezione."""
    path = _tmpfile()
    try:
        class _BoomDaemon:
            def tick(self, runtime_snapshot=None):
                raise RuntimeError("boom-tick")

        bridge = MeshNeedsCheck(telemetry_path=path)
        bridge._daemon = _BoomDaemon()  # type: ignore[attr-defined]
        # _build_error rimane None, quindi _get_daemon ritorna il mock
        res = bridge.run(push={"type": "x", "priority": 0}, epigenome=_epi(True))
        assert res.enabled is True
        assert res.error and "RuntimeError" in res.error
        # Push intatto su errore
        assert res.promoted is False
        return f"AC-B7 errore tick catturato in result.error ({res.error[:30]}...)"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_b8_function_entry_end_to_end():
    """Chiama la function entry point con epigenome reale; mesh canonica deve
    costruirsi e tick produrre un verdict valido."""
    reset_global_bridge()
    res = step3bis_needs_check(
        push={"type": "user", "priority": 0},
        epigenome=_epi(True),
    )
    # In una mesh sana il verdict tipico è 'watch' (bisogni inizialmente bassi)
    # ma accettiamo qualunque valore valido — l'importante è che funzioni
    assert res.enabled is True, res.error
    assert res.verdict in ("healthy", "watch", "alert", "critical"), (res.verdict, res.error)
    assert res.cycle_id, res.cycle_id
    return f"AC-B8 function entry → verdict={res.verdict}, props={res.proposals_count}"


def case_ac_b9_reset_global():
    reset_global_bridge()
    # Prima chiamata costruisce il singleton
    res1 = step3bis_needs_check(push={"type": "x", "priority": 0}, epigenome=_epi(True))
    from cortex.mesh.smfoi_bridge import _GLOBAL_BRIDGE as G1  # type: ignore
    assert G1 is not None
    reset_global_bridge()
    from cortex.mesh.smfoi_bridge import _GLOBAL_BRIDGE as G2  # type: ignore
    assert G2 is None
    # Seconda chiamata ricostruisce
    res2 = step3bis_needs_check(push={"type": "x", "priority": 0}, epigenome=_epi(True))
    assert res1.enabled and res2.enabled
    return "AC-B9 reset_global_bridge azzera singleton"


def case_ac_b11_non_dict_content_preserved():
    """Push originale con content stringa (es. external_push={'content':'hello'})
    deve essere preservato sotto _original senza sollevare ValueError."""
    path = _tmpfile()
    try:
        bridge = _bridge_with_forced_verdict(HarmonyVerdict.WATCH, path)
        res = bridge.run(
            push={"type": "user", "priority": 0, "content": "hello", "source": "ext"},
            epigenome=_epi(True),
        )
        assert res.error is None, res.error
        assert res.promoted is True
        assert isinstance(res.push.get("content"), dict)
        assert res.push["content"].get("_original") == "hello"
        assert res.push["content"].get("verdict") == "watch"
        return "AC-B11 content non-dict preservato sotto _original"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def case_ac_b10_daemon_cached():
    """Più chiamate consecutive → un solo build di daemon."""
    bridge = MeshNeedsCheck()
    # Prima chiamata costruisce
    r1 = bridge.run(push={"type": "x", "priority": 0}, epigenome=_epi(True))
    d1 = bridge._daemon  # type: ignore[attr-defined]
    assert d1 is not None
    assert r1.enabled

    # Seconda e terza chiamata devono riutilizzare la stessa istanza
    r2 = bridge.run(push={"type": "y", "priority": 0}, epigenome=_epi(True))
    r3 = bridge.run(push={"type": "z", "priority": 0}, epigenome=_epi(True))
    assert bridge._daemon is d1  # type: ignore[attr-defined]

    # Tre tick → tick_count del daemon = 3
    assert d1.tick_count() == 3, d1.tick_count()
    return "AC-B10 daemon cachato (1 build, 3 tick)"


CASES = [
    case_ac_b1_is_enabled_default_off,
    case_ac_b2_is_enabled_true_only_explicit,
    case_ac_b3_bridge_off_passthrough,
    case_ac_b4_bridge_on_healthy_no_promote,
    case_ac_b5_bridge_promotes_on_alerts,
    case_ac_b6_push_none_renamed,
    case_ac_b7_error_caught_in_result,
    case_ac_b8_function_entry_end_to_end,
    case_ac_b9_reset_global,
    case_ac_b10_daemon_cached,
    case_ac_b11_non_dict_content_preserved,
]


def run_all() -> Tuple[int, int, List[str]]:
    passed = 0
    failed = 0
    lines: List[str] = []
    for case in CASES:
        name = case.__name__
        try:
            desc = case()
            passed += 1
            lines.append(f"  [PASS] {name}: {desc}")
        except AssertionError as e:
            failed += 1
            lines.append(f"  [FAIL] {name}: {e}")
        except Exception as e:
            failed += 1
            lines.append(
                f"  [ERROR] {name}: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
    return passed, failed, lines


def main() -> int:
    p, f, lines = run_all()
    print(f"cortex.mesh._tests_smfoi_bridge — {p}/{p+f} passed")
    for l in lines:
        print(l)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
