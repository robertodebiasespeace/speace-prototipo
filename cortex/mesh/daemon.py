"""
cortex.mesh.daemon — Mesh Daemon (M4.14)

Daemon orchestratore della Continuous Neural Mesh. Esegue cicli periodici
componendo gli step osservativi della mesh:

    NeedsDriver.observe()
        → HarmonyPolicy.evaluate()
        → TaskGenerator.generate()
        → MeshTelemetry.record_cycle()

**Modalità di esecuzione:**

  - **manual / single-tick**    `daemon.tick()` → esegue un singolo ciclo
  - **auto (heartbeat)**        `daemon.start(interval_s=N)` → loop in background
  - **scheduled** (M4.14b)      `daemon.run_at_times([...])` → cron-like (TODO)

**Filosofia:**

  - Il daemon **non possiede** registry/graph: li riceve via DI (constructor
    injection). Questo permette al daemon di lavorare su mesh diverse (test,
    staging, prod) senza globals.
  - Tutti gli step sono **fail-soft**: un'eccezione in observe/harmony/gen
    viene catturata, registrata come evento `error` di telemetria, e il loop
    continua.
  - **No SafeProactive write here**: il daemon produce `TaskProposal` ma la
    persistenza di proposte come PROPOSALS.md è responsabilità di un layer
    esterno (consume queue separata in M4.15).

**Side-effects dichiarati:**

  - `fs_write:safeproactive/state/mesh_state.jsonl` (telemetria)
  - Nessun side-effect cognitivo o di mutazione DNA.
"""

from __future__ import annotations

import datetime as _dt
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from cortex.mesh.contract import NeuronRegistry
from cortex.mesh.graph import MeshGraph
from cortex.mesh.needs_driver import NeedsDriver
from cortex.mesh.harmony import HarmonyPolicy
from cortex.mesh.task_generator import TaskGenerator
from cortex.mesh.telemetry import MeshTelemetry, DEFAULT_MESH_STATE_PATH
from cortex.mesh.olc import NeedsSnapshot, FeedbackFrame


# ---------------------------------------------------------------------------
# Tick result
# ---------------------------------------------------------------------------


@dataclass
class TickResult:
    """Esito di una singola esecuzione di `daemon.tick()`."""
    ok: bool
    cycle_id: str
    ts: str
    verdict: Optional[str] = None
    driving_need: Optional[str] = None
    proposals_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "cycle_id": self.cycle_id,
            "ts": self.ts,
            "verdict": self.verdict,
            "driving_need": self.driving_need,
            "proposals_count": self.proposals_count,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class MeshDaemon:
    """
    Daemon di esecuzione continua della mesh.

    Esempio:
        from cortex.mesh.contract import NeuronRegistry
        from cortex.mesh.registry import discover_neurons
        from cortex.mesh.graph import MeshGraph
        from cortex.mesh.daemon import MeshDaemon

        reg = NeuronRegistry()
        discover_neurons("cortex.mesh.adapters", registry=reg)
        g = MeshGraph(neuron_registry=reg); g.attach_from_registry(); g.auto_wire()

        d = MeshDaemon(registry=reg, graph=g)
        d.tick()                    # singolo ciclo
        d.start(interval_s=60.0)    # heartbeat ogni 60s
        ...
        d.stop()
    """

    def __init__(
        self,
        *,
        registry: NeuronRegistry,
        graph: MeshGraph,
        needs_driver: Optional[NeedsDriver] = None,
        harmony_policy: Optional[HarmonyPolicy] = None,
        task_generator: Optional[TaskGenerator] = None,
        telemetry: Optional[MeshTelemetry] = None,
        telemetry_path: str = DEFAULT_MESH_STATE_PATH,
        max_proposals: int = 5,
        fitness_history_size: int = 32,
        proposal_listener: Optional[Callable[[List[Any]], None]] = None,
    ) -> None:
        self._reg = registry
        self._graph = graph

        self._driver = needs_driver or NeedsDriver()
        self._policy = harmony_policy or HarmonyPolicy(targets=self._driver.targets)
        self._gen = task_generator or TaskGenerator(
            policy=self._policy, max_proposals=max_proposals
        )
        self._tlm = telemetry or MeshTelemetry(telemetry_path)

        # Storia fitness — il daemon stesso non produce fitness; viene fornita
        # esternamente via `record_fitness()`. Anello di feedback chiuso in M4.15.
        self._fitness_window: List[FeedbackFrame] = []
        self._fitness_max = max(1, int(fitness_history_size))

        # Listener opzionale: invocato dopo ogni tick con la lista di proposte
        # generate (es. per scrivere su PROPOSALS.md).
        self._listener = proposal_listener

        # Background thread state
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_tick: Optional[TickResult] = None
        self._tick_count = 0

    # ------------------------------------------------------------ API --

    @property
    def telemetry(self) -> MeshTelemetry:
        return self._tlm

    @property
    def driver(self) -> NeedsDriver:
        return self._driver

    @property
    def policy(self) -> HarmonyPolicy:
        return self._policy

    def last_tick(self) -> Optional[TickResult]:
        with self._lock:
            return self._last_tick

    def tick_count(self) -> int:
        with self._lock:
            return self._tick_count

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------ fitness feedback --

    def record_fitness(self, frame: FeedbackFrame) -> None:
        """Inserisce un FeedbackFrame nella finestra di osservazione."""
        with self._lock:
            self._fitness_window.append(frame)
            if len(self._fitness_window) > self._fitness_max:
                self._fitness_window = self._fitness_window[-self._fitness_max:]

    # ------------------------------------------------------------ tick --

    def tick(self, *, runtime_snapshot: Optional[Dict[str, Any]] = None) -> TickResult:
        """
        Esegue un singolo ciclo della mesh:
          observe → evaluate → generate → telemetry → listener (opt).

        Mai solleva. In caso di errore restituisce un TickResult con `ok=False`.
        """
        ts = _iso_now()
        try:
            graph_snap = self._graph.snapshot()
            with self._lock:
                fitness_window = list(self._fitness_window)
            risk_proposals = self._inspect_risk_queue()
            needs_snap = self._driver.observe(
                graph_snapshot=graph_snap,
                runtime_snapshot=runtime_snapshot,
                registry=self._reg,
                fitness_history=fitness_window,
                risk_proposals=risk_proposals,
            )
            harmony_rep = self._policy.evaluate(needs_snap)
            proposals = self._gen.generate(needs_snap, harmony_report=harmony_rep)

            # Registry summary (count + quarantined)
            try:
                names = list(self._reg.names())
                registry_summary = {
                    "total": len(names),
                    "quarantined": sum(1 for n in names if self._reg.is_quarantined(n)),
                }
            except Exception:
                registry_summary = {"total": 0, "quarantined": 0}

            event = self._tlm.record_cycle(
                needs_snapshot=needs_snap,
                harmony_report=harmony_rep,
                graph_snapshot=graph_snap,
                runtime_snapshot=runtime_snapshot,
                registry_summary=registry_summary,
                proposals=proposals,
            )

            # Listener (best-effort)
            if self._listener and proposals:
                try:
                    self._listener(list(proposals))
                except Exception:
                    pass  # non blocca il loop

            res = TickResult(
                ok=True,
                cycle_id=event["cycle_id"],
                ts=event["ts"],
                verdict=event.get("verdict"),
                driving_need=event.get("driving_need"),
                proposals_count=len(proposals),
                error=None,
            )
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            # Registriamo l'errore come evento speciale
            try:
                event = self._tlm.record_event({
                    "ts": ts, "verdict": "error",
                    "extras": {"trace": traceback.format_exc().splitlines()[-3:]},
                    "error": err,
                })
                cyc = event.get("cycle_id", "err")
            except Exception:
                cyc = "err"
            res = TickResult(
                ok=False, cycle_id=cyc, ts=ts,
                verdict="error", error=err,
            )
        with self._lock:
            self._last_tick = res
            self._tick_count += 1
        return res

    def _inspect_risk_queue(self) -> Optional[Dict[str, int]]:
        """
        Stub: in futuro questa funzione interrogherà SafeProactive per
        contare le proposte aperte per livello di rischio. Per ora ritorna
        None → harmony non penalizza.
        """
        return None

    # ------------------------------------------------------------ run loop --

    def start(self, interval_s: float = 60.0) -> None:
        """Avvia il daemon in background con heartbeat ogni `interval_s` secondi."""
        if self.is_running():
            return
        self._stop_evt.clear()
        t = threading.Thread(
            target=self._loop, args=(float(interval_s),),
            name="MeshDaemon", daemon=True,
        )
        self._thread = t
        t.start()

    def _loop(self, interval_s: float) -> None:
        # Tick immediato all'avvio, poi heartbeat
        self.tick()
        while not self._stop_evt.is_set():
            # wait con timeout ci permette di rispondere a stop senza ritardo eccessivo
            if self._stop_evt.wait(timeout=interval_s):
                break
            try:
                self.tick()
            except Exception:
                # Difensivo: tick() gestisce già le sue eccezioni, ma blindiamo il loop
                pass

    def stop(self, timeout: float = 5.0) -> None:
        """Richiede stop pulito al loop background."""
        self._stop_evt.set()
        t = self._thread
        if t is not None:
            t.join(timeout=timeout)
        self._thread = None

    def run_n(self, n: int, *, sleep_s: float = 0.0) -> List[TickResult]:
        """Esegue N tick in foreground (utile per test/benchmark)."""
        if n < 1:
            return []
        out: List[TickResult] = []
        for _ in range(int(n)):
            out.append(self.tick())
            if sleep_s > 0:
                time.sleep(sleep_s)
        return out


__all__ = [
    "MeshDaemon",
    "TickResult",
]
