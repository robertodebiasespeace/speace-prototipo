"""
cortex.mesh.smfoi_bridge — Bridge CNM ↔ SMFOI-KERNEL (M4.15)

Definisce lo **Step 3.bis "Needs Check"** che il kernel SMFOI v0.3 esegue
fra Step 3 (Push Detection) e Step 4 (Survival & Evolution Stack).

**Contratto di integrazione:**

  - L'attivazione è **opt-in** controllata da `epigenome.mesh.enabled`.
    Default OFF → comportamento del kernel invariato (retrocompatibilità).
  - Quando attivo, il bridge:
      1. costruisce (o riusa) una mesh canonica via discovery,
      2. esegue `MeshDaemon.tick()` (osserva → harmony → genera proposte),
      3. **promuove a push-signal** verdetti non-healthy e bisogni con gap
         significativo, **mergendo** con il push esistente.
  - **Fail-soft assoluto**: qualunque errore in costruzione mesh, tick o
    serializzazione **NON deve** rompere il ciclo SMFOI. In caso di errore
    il bridge ritorna l'input invariato + un campo `mesh_error`.
  - **No side-effect cognitivi diretti**: il bridge non chiama LLM, non muta
    DNA, non scrive su PROPOSALS.md. Le proposte mesh restano nella
    telemetria (`mesh_state.jsonl`) e raggiungono SafeProactive solo tramite
    consume queue separata (M4.x successiva).

Side-effect dichiarati (ereditati dal MeshDaemon):
  - `fs_write:safeproactive/state/mesh_state.jsonl`
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cortex.mesh.smfoi_bridge")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class NeedsCheckResult:
    """Esito dello Step 3.bis."""
    enabled: bool
    push: Dict[str, Any]              # push originale, possibilmente arricchito
    promoted: bool                    # True se il bridge ha alzato la priority
    verdict: Optional[str] = None     # HarmonyVerdict (healthy/watch/alert/critical)
    driving_need: Optional[str] = None
    proposals_count: int = 0
    cycle_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "promoted": self.promoted,
            "verdict": self.verdict,
            "driving_need": self.driving_need,
            "proposals_count": self.proposals_count,
            "cycle_id": self.cycle_id,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Helpers su epigenome
# ---------------------------------------------------------------------------


def _read_mesh_block(epigenome: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Estrae il blocco `mesh:` dall'epigenome con default conservativi."""
    if not isinstance(epigenome, dict):
        return {"enabled": False}
    block = epigenome.get("mesh") or {}
    if not isinstance(block, dict):
        return {"enabled": False}
    return block


def is_enabled(epigenome: Optional[Dict[str, Any]]) -> bool:
    """`epigenome.mesh.enabled` con default OFF (retrocompatibile)."""
    block = _read_mesh_block(epigenome)
    return bool(block.get("enabled", False))


def _verdict_priority_lift(verdict: Optional[str]) -> int:
    """Mappa harmony verdict → boost di priority del push."""
    if verdict is None:
        return 0
    v = str(verdict).lower()
    return {"healthy": 0, "watch": 1, "alert": 2, "critical": 3}.get(v, 0)


# ---------------------------------------------------------------------------
# Mesh bridge
# ---------------------------------------------------------------------------


class MeshNeedsCheck:
    """
    Helper integrato nel kernel SMFOI per lo Step 3.bis.

    Mantiene una cache lazy della mesh canonica + del daemon, così il primo
    ciclo paga discovery+wiring ma quelli successivi sono O(1) sul singolo tick.

    Uso (dentro SMFOI._step3bis_needs_check):
        bridge = MeshNeedsCheck()  # singleton di kernel-instance
        result = bridge.run(push=push, epigenome=self.epigenome)
        push = result.push  # forward downstream (Step 4)
    """

    def __init__(self, telemetry_path: Optional[str] = None) -> None:
        self._telemetry_path = telemetry_path
        self._lock = threading.Lock()
        self._daemon: Optional[Any] = None  # MeshDaemon, lazy
        self._build_error: Optional[str] = None

    # --------------------------------------------------------------- daemon --

    def _build_daemon(self) -> Optional[Any]:
        """
        Costruisce (lazy) una mesh canonica + daemon. Fail-soft: in caso di
        errore segna `_build_error` e ritorna None.
        """
        try:
            from cortex.mesh.contract import NeuronRegistry
            from cortex.mesh.graph import MeshGraph
            from cortex.mesh.registry import discover_neurons
            from cortex.mesh.daemon import MeshDaemon
            from cortex.mesh.telemetry import DEFAULT_MESH_STATE_PATH

            reg = NeuronRegistry()
            discover_neurons("cortex.mesh.adapters", registry=reg)
            graph = MeshGraph(neuron_registry=reg)
            graph.attach_from_registry()
            graph.auto_wire()

            d = MeshDaemon(
                registry=reg,
                graph=graph,
                telemetry_path=self._telemetry_path or DEFAULT_MESH_STATE_PATH,
            )
            return d
        except Exception as exc:
            self._build_error = f"{type(exc).__name__}: {exc}"
            logger.warning("MeshNeedsCheck: build mesh fallita (%s)", self._build_error)
            return None

    def _get_daemon(self) -> Optional[Any]:
        with self._lock:
            if self._daemon is None and self._build_error is None:
                self._daemon = self._build_daemon()
            return self._daemon

    # ----------------------------------------------------------------- run --

    def run(
        self,
        *,
        push: Optional[Dict[str, Any]] = None,
        epigenome: Optional[Dict[str, Any]] = None,
        runtime_snapshot: Optional[Dict[str, Any]] = None,
    ) -> NeedsCheckResult:
        """
        Esegue lo Step 3.bis. Mai solleva.

        Politica di promozione (push merge):
          - verdict CRITICAL → push.priority lifted to max(current, 3),
            type="mesh_critical" se push originale era "none".
          - verdict ALERT    → push.priority lifted to max(current, 2),
            type="mesh_alert" se push originale era "none".
          - verdict WATCH    → push.priority lifted to max(current, 1),
            type="mesh_watch" se push originale era "none".
          - HEALTHY          → nessuna promozione.
        """
        original_push = dict(push or {"type": "none", "priority": 0,
                                       "content": None, "source": "internal"})

        # Default: pass-through
        result = NeedsCheckResult(
            enabled=False,
            push=original_push,
            promoted=False,
        )

        if not is_enabled(epigenome):
            return result

        result.enabled = True

        d = self._get_daemon()
        if d is None:
            result.error = self._build_error or "daemon_unavailable"
            return result

        # Tick fail-soft (il daemon stesso non solleva mai)
        try:
            tick = d.tick(runtime_snapshot=runtime_snapshot)
        except Exception as exc:  # difensivo
            result.error = f"{type(exc).__name__}: {exc}"
            return result

        result.cycle_id = tick.cycle_id
        if not tick.ok:
            result.error = tick.error or "tick_failed"
            return result

        result.verdict = tick.verdict
        result.driving_need = tick.driving_need
        result.proposals_count = int(tick.proposals_count or 0)

        # Merge: promuoviamo il push se il verdict lo richiede
        lift = _verdict_priority_lift(tick.verdict)
        if lift > 0:
            new_priority = max(int(original_push.get("priority") or 0), lift)
            new_push = dict(original_push)
            new_push["priority"] = new_priority
            # Se il push originale era "none" diamo un type informativo
            if (new_push.get("type") in (None, "", "none")):
                new_push["type"] = f"mesh_{tick.verdict}"
                new_push["source"] = "cnm"
            # Sempre arricchisci con metadata mesh (non distruttivo).
            # Se content originale non è dict (es. stringa "hello"),
            # lo preserviamo sotto la chiave "_original".
            raw_content = new_push.get("content")
            if isinstance(raw_content, dict):
                content = dict(raw_content)
            elif raw_content is None:
                content = {}
            else:
                content = {"_original": raw_content}
            content.setdefault("driving_need", tick.driving_need)
            content.setdefault("proposals_count", result.proposals_count)
            content.setdefault("verdict", tick.verdict)
            new_push["content"] = content
            result.push = new_push
            result.promoted = True

        return result


# ---------------------------------------------------------------------------
# Function-style entry (per callers che non vogliono istanziare il bridge)
# ---------------------------------------------------------------------------


_GLOBAL_BRIDGE: Optional[MeshNeedsCheck] = None
_GLOBAL_LOCK = threading.Lock()


def step3bis_needs_check(
    *,
    push: Optional[Dict[str, Any]] = None,
    epigenome: Optional[Dict[str, Any]] = None,
    runtime_snapshot: Optional[Dict[str, Any]] = None,
) -> NeedsCheckResult:
    """
    Entry-point funzionale (singleton). Pensato per uso dentro
    `SMFOIKernel.run_cycle()` come Step 3.bis.

    Esempio:
        from cortex.mesh.smfoi_bridge import step3bis_needs_check, is_enabled

        push = self._step3_push_detection(external_push)
        if is_enabled(self.epigenome):
            res = step3bis_needs_check(push=push, epigenome=self.epigenome)
            push = res.push
            context["mesh_step3bis"] = res.to_dict()
    """
    global _GLOBAL_BRIDGE
    with _GLOBAL_LOCK:
        if _GLOBAL_BRIDGE is None:
            _GLOBAL_BRIDGE = MeshNeedsCheck()
        bridge = _GLOBAL_BRIDGE
    return bridge.run(push=push, epigenome=epigenome, runtime_snapshot=runtime_snapshot)


def reset_global_bridge() -> None:
    """Per testing: dimentica il singleton (riforza ricostruzione mesh)."""
    global _GLOBAL_BRIDGE
    with _GLOBAL_LOCK:
        _GLOBAL_BRIDGE = None


__all__ = [
    "MeshNeedsCheck",
    "NeedsCheckResult",
    "is_enabled",
    "step3bis_needs_check",
    "reset_global_bridge",
]
