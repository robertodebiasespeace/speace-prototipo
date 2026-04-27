"""
SPEACE Cortex Mesh — Async Scheduler Runtime (M4.6)

Scheduler asincrono per la Continuous Neural Mesh. Integra:
  - `MeshGraph` (M4.5) per topologia e routing
  - `contract.wrap_execute` (M4.2) per type-check I/O + timeout + retry
  - `execution_rules.yaml` (M4.4) per ceiling concurrency, queue size, fail-safe
  - `NeuronRegistry` per lookup

Modello di esecuzione:
  - Thread pool dedicato (ThreadPoolExecutor con max_concurrent_neurons)
  - Queue FIFO thread-safe con submit_timeout_ms
  - Backpressure configurabile: reject_new | drop_oldest | block
  - Per-level semaphore (L1..L5) e per-need semaphore per limitare
    concorrenza cross-task
  - Heartbeat-based fail-safe: error_rate > threshold per ≥N heartbeat
    consecutivi → freeze_mesh + flip epigenome flag (SPEC §8.3)

Entry points:
  - `submit(name, input_obj) -> Future`       esecuzione singola
  - `propagate(root, input_obj) -> {name: Future}`  esecuzione a cascata
                                                    lungo il DAG secondo layers
  - `heartbeat()` aggiorna metriche error rate e valuta fail-safe trip
  - `status()` snapshot dello stato runtime

Stato runtime:
  IDLE → RUNNING → FROZEN (fail-safe trip) | STOPPED (shutdown)

Milestone: M4.6 (PROP-CORTEX-NEURAL-MESH-M4)
Riferimento canonico: cortex/mesh/SPEC_NEURON_CONTRACT.md §5 (Runtime) e §8.3 (Fail-safe)
"""

from __future__ import annotations
import dataclasses
import datetime
import enum
import logging
import queue
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from cortex.mesh import execution_rules as _er
from cortex.mesh.contract import (
    Neuron, NeuronRegistry,
    ContractViolation, ContractViolationCode, Phase,
    wrap_execute, activate, retire, emit_event,
    registry as default_neuron_registry,
)
from cortex.mesh.graph import MeshGraph, default_graph

_log = logging.getLogger("speace.mesh.runtime")

RUNTIME_VERSION = "1.0"


# ================================================================================
# Stato runtime & configurazione
# ================================================================================

class RuntimeState(str, enum.Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FROZEN = "FROZEN"      # fail-safe trip; necessita reset manuale
    STOPPED = "STOPPED"


@dataclasses.dataclass
class TaskRequest:
    """Richiesta di esecuzione accodata."""
    neuron_name: str
    input_obj: Any
    submitted_ts: float
    future: Future
    retries_left: int = 0
    correlation_id: Optional[str] = None


@dataclasses.dataclass
class TaskResult:
    neuron_name: str
    ok: bool
    output: Any
    violations: List[ContractViolation]
    elapsed_ms: float
    ts: str


# ================================================================================
# Error rate tracker (fail-safe)
# ================================================================================

class _ErrorRateWindow:
    """
    Traccia error rate su finestra heartbeat. Ogni heartbeat valuta il
    rapporto fallimenti/totali del bucket corrente, sposta il bucket.
    Trip quando ≥ window_size heartbeat consecutivi superano la soglia.
    """

    def __init__(self, threshold: float, window: int) -> None:
        self._lock = threading.Lock()
        self._threshold = threshold
        self._window = max(1, int(window))
        self._buckets: Deque[Tuple[int, int]] = deque(maxlen=self._window)  # (ok, err)
        self._current_ok = 0
        self._current_err = 0

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._current_ok += 1
            else:
                self._current_err += 1

    def tick_heartbeat(self) -> Tuple[float, bool]:
        """Chiude il bucket corrente, apre un nuovo bucket. Ritorna (rate, tripped)."""
        with self._lock:
            bucket = (self._current_ok, self._current_err)
            self._buckets.append(bucket)
            self._current_ok = 0
            self._current_err = 0
            if len(self._buckets) < self._window:
                return 0.0, False
            tripped = True
            last_rate = 0.0
            for ok, err in self._buckets:
                total = ok + err
                rate = err / total if total > 0 else 0.0
                last_rate = rate
                if rate <= self._threshold:
                    tripped = False
                    break
            return last_rate, tripped

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._current_ok = 0
            self._current_err = 0


# ================================================================================
# Semafori per cap concorrenza (per livello / per bisogno)
# ================================================================================

class _CapsMap:
    """
    Wrapper thread-safe di BoundedSemaphore per chiave (livello o need).
    Acquire con timeout ritorna False se occupato.
    """

    def __init__(self, caps: Dict[str, int]) -> None:
        self._sems: Dict[str, threading.BoundedSemaphore] = {
            k: threading.BoundedSemaphore(v) for k, v in caps.items() if v > 0
        }

    def try_acquire(self, key: str, timeout_s: float = 0) -> bool:
        sem = self._sems.get(key)
        if sem is None:
            return True  # nessun cap → permetti
        return sem.acquire(timeout=timeout_s) if timeout_s > 0 else sem.acquire(blocking=False)

    def release(self, key: str) -> None:
        sem = self._sems.get(key)
        if sem is not None:
            try:
                sem.release()
            except ValueError:
                pass  # semaforo già al massimo — ignore

    def snapshot(self) -> Dict[str, int]:
        return {k: v._initial_value if hasattr(v, "_initial_value") else 0  # type: ignore[attr-defined]
                for k, v in self._sems.items()}


# ================================================================================
# MeshRuntime
# ================================================================================

class MeshRuntime:
    """
    Scheduler principale della mesh. Uso tipico:

        g = default_graph()
        rt = MeshRuntime(g)
        rt.start()
        future = rt.submit("neuron.x", input_obj)
        result = future.result(timeout=30)
        rt.stop()

    oppure per cascata DAG:
        futures = rt.propagate("neuron.root", input_obj)
    """

    def __init__(
        self,
        graph: Optional[MeshGraph] = None,
        *,
        max_concurrent_neurons: Optional[int] = None,
        queue_size: Optional[int] = None,
        submit_timeout_ms: Optional[int] = None,
        backpressure_strategy: Optional[str] = None,
        fail_safe_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._graph: MeshGraph = graph or default_graph()

        # Carica config dal YAML (con override parametri)
        conc = _er.get_concurrency_config()
        self._max_workers = int(max_concurrent_neurons or conc.get("max_concurrent_neurons", 8))
        self._queue_size = int(queue_size or conc.get("queue_size", 64))
        self._submit_timeout_s = float(
            submit_timeout_ms or conc.get("submit_timeout_ms", 1000)
        ) / 1000.0
        self._backpressure = backpressure_strategy or conc.get(
            "backpressure_strategy", "reject_new"
        )

        # Cap per livello e per need
        self._level_caps = _CapsMap({f"L{k}" if isinstance(k, int) else k: v
                                     for k, v in (conc.get("per_level_caps") or {}).items()})
        self._need_caps = _CapsMap(conc.get("per_need_caps") or {})

        # Fail-safe
        fs = _er.get_fail_safe_policy()
        self._fs_threshold = float(fs.get("error_rate_threshold", 0.50))
        self._fs_window = int(fs.get("error_rate_window_heartbeats", 2))
        self._fs_action = fs.get("action_on_trip", "freeze_mesh")
        self._fs_auto_flip = bool(fs.get("auto_flip_epigenome_enabled", True))
        self._fs_callback = fail_safe_callback
        self._error_window = _ErrorRateWindow(self._fs_threshold, self._fs_window)

        # Stato
        self._state: RuntimeState = RuntimeState.IDLE
        self._state_lock = threading.RLock()
        self._queue: "queue.Queue[TaskRequest]" = queue.Queue(maxsize=self._queue_size)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._dispatcher: Optional[threading.Thread] = None
        self._shutdown_evt = threading.Event()

        # Metriche cumulative
        self._counters_lock = threading.Lock()
        self._submitted = 0
        self._dispatched = 0
        self._completed = 0
        self._errored = 0
        self._rejected = 0
        self._skipped_quarantine = 0
        self._skipped_cap = 0

    # ----------------------------------------------------------- lifecycle --

    def start(self) -> None:
        with self._state_lock:
            if self._state in (RuntimeState.RUNNING, RuntimeState.FROZEN):
                return
            self._shutdown_evt.clear()
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="mesh-worker",
            )
            self._dispatcher = threading.Thread(
                target=self._dispatch_loop,
                name="mesh-dispatcher",
                daemon=True,
            )
            self._dispatcher.start()
            self._state = RuntimeState.RUNNING
            emit_event("<runtime>", "RUNTIME_STARTED",
                       max_workers=self._max_workers,
                       queue_size=self._queue_size,
                       backpressure=self._backpressure)

    def stop(self, *, graceful_timeout_s: float = 30.0) -> None:
        with self._state_lock:
            if self._state == RuntimeState.STOPPED:
                return
            self._shutdown_evt.set()
            self._state = RuntimeState.STOPPED
            # sveglia il dispatcher con sentinel no-op
            try:
                self._queue.put_nowait(TaskRequest(
                    neuron_name="<sentinel>",
                    input_obj=None,
                    submitted_ts=time.time(),
                    future=Future(),
                ))
            except queue.Full:
                pass

        if self._dispatcher is not None:
            self._dispatcher.join(timeout=graceful_timeout_s)
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
        emit_event("<runtime>", "RUNTIME_STOPPED")

    def freeze(self, reason: str = "manual_freeze") -> None:
        """Congela lo scheduler (mantiene thread pool ma rifiuta nuove submit)."""
        with self._state_lock:
            if self._state == RuntimeState.STOPPED:
                return
            self._state = RuntimeState.FROZEN
        emit_event("<runtime>", "MESH_FROZEN", reason=reason)
        if self._fs_callback is not None:
            try:
                self._fs_callback(reason)  # type: ignore[arg-type]
            except Exception as e:  # pragma: no cover
                _log.warning("fail_safe_callback raised: %s", e)

    def resume(self) -> None:
        """Ri-attiva dopo freeze (usage: post-intervento umano/PROP-MESH-RESUME)."""
        with self._state_lock:
            if self._state != RuntimeState.FROZEN:
                return
            self._state = RuntimeState.RUNNING
            self._error_window.reset()
        emit_event("<runtime>", "MESH_RESUMED")

    # -------------------------------------------------------------- submit --

    def submit(
        self,
        neuron_name: str,
        input_obj: Any,
        *,
        retries: int = 0,
        correlation_id: Optional[str] = None,
    ) -> Future:
        """Sottomette un task. Ritorna Future che risolverà in TaskResult."""
        fut: Future = Future()
        state = self._state
        if state != RuntimeState.RUNNING:
            fut.set_exception(RuntimeError(f"runtime not running (state={state.value})"))
            with self._counters_lock:
                self._rejected += 1
            return fut

        req = TaskRequest(
            neuron_name=neuron_name,
            input_obj=input_obj,
            submitted_ts=time.time(),
            future=fut,
            retries_left=max(0, int(retries)),
            correlation_id=correlation_id,
        )

        try:
            if self._backpressure == "block":
                self._queue.put(req, timeout=self._submit_timeout_s)
            elif self._backpressure == "drop_oldest":
                self._drop_oldest_if_full(req)
            else:  # reject_new (default)
                self._queue.put(req, timeout=self._submit_timeout_s)
        except queue.Full:
            with self._counters_lock:
                self._rejected += 1
            fut.set_exception(RuntimeError(
                f"queue full (size={self._queue_size}, strategy={self._backpressure})"
            ))
            emit_event(neuron_name, "TASK_REJECTED",
                       reason="queue_full", strategy=self._backpressure)
            return fut

        with self._counters_lock:
            self._submitted += 1
        return fut

    def _drop_oldest_if_full(self, req: TaskRequest) -> None:
        try:
            self._queue.put_nowait(req)
        except queue.Full:
            try:
                dropped = self._queue.get_nowait()
                dropped.future.set_exception(RuntimeError("dropped by backpressure=drop_oldest"))
                emit_event(dropped.neuron_name, "TASK_DROPPED", reason="drop_oldest")
                with self._counters_lock:
                    self._rejected += 1
                self._queue.put_nowait(req)
            except queue.Empty:  # pragma: no cover
                self._queue.put(req, timeout=self._submit_timeout_s)

    # ---------------------------------------------------------- propagate --

    def propagate(
        self,
        root_name: str,
        input_obj: Any,
        *,
        timeout_s: float = 30.0,
    ) -> Dict[str, TaskResult]:
        """
        Esegue la cascata da `root_name` lungo il DAG, livello per livello.
        Output di ogni neurone è passato come input ai suoi successori.
        Fan-in: se un nodo ha più predecessori, viene invocato una sola volta
        con l'output del primo predecessore COMPLETED nel BFS (policy MVP;
        M5 userà reducer custom).

        Ritorna {name: TaskResult} per ogni neurone eseguito.
        """
        results: Dict[str, TaskResult] = {}
        if not self._graph.has_neuron(root_name):
            raise ValueError(f"neurone '{root_name}' non presente nel grafo")

        # Esegui il root
        fut = self.submit(root_name, input_obj)
        root_res = fut.result(timeout=timeout_s)
        results[root_name] = root_res
        if not root_res.ok:
            return results

        # BFS a livelli dalla propagazione del root
        from collections import deque as _dq
        frontier: "_dq[Tuple[str, Any]]" = _dq()
        for succ in self._graph.successors(root_name):
            frontier.append((succ, root_res.output))

        seen: set = {root_name}
        while frontier:
            name, inp = frontier.popleft()
            if name in seen:
                continue
            seen.add(name)
            fut = self.submit(name, inp)
            try:
                res = fut.result(timeout=timeout_s)
            except Exception as e:
                res = TaskResult(
                    neuron_name=name, ok=False, output=None,
                    violations=[], elapsed_ms=0.0,
                    ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
                )
                _log.warning("propagate: future raised for %s: %s", name, e)
            results[name] = res
            if res.ok:
                for nxt in self._graph.successors(name):
                    if nxt not in seen:
                        frontier.append((nxt, res.output))
        return results

    # ------------------------------------------------------ dispatch loop --

    def _dispatch_loop(self) -> None:
        while not self._shutdown_evt.is_set():
            try:
                req = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if req.neuron_name == "<sentinel>":
                continue
            if self._state != RuntimeState.RUNNING:
                req.future.set_exception(RuntimeError(f"runtime not running (state={self._state.value})"))
                continue
            # Lookup
            neuron = self._graph.lookup(req.neuron_name)
            if neuron is None:
                req.future.set_exception(ValueError(f"neurone '{req.neuron_name}' non presente nel grafo"))
                emit_event(req.neuron_name, "TASK_LOOKUP_FAILED")
                continue
            # Quarantine check
            from cortex.mesh.contract import _REGISTRY as _NREG
            if _NREG.is_quarantined(req.neuron_name):
                with self._counters_lock:
                    self._skipped_quarantine += 1
                # Un neurone in quarantena che continua a ricevere submit è un
                # problema attivo: conta come errore nella error-rate window
                # per non mascherare la situazione al fail-safe.
                self._error_window.record(False)
                req.future.set_result(TaskResult(
                    neuron_name=req.neuron_name, ok=False, output=None,
                    violations=[], elapsed_ms=0.0,
                    ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
                ))
                emit_event(req.neuron_name, "SKIPPED_QUARANTINE")
                continue
            # Cap per livello e per need — se saturi, re-enqueue (backpressure naturale).
            # Il task non fallisce: attende il prossimo slot disponibile.
            level_key = f"L{neuron.level}"
            needs = list(neuron.needs_served or [])
            if not self._level_caps.try_acquire(level_key):
                try:
                    self._queue.put_nowait(req)
                    with self._counters_lock:
                        self._skipped_cap += 1
                    emit_event(req.neuron_name, "REQUEUED_LEVEL_CAP", level=level_key)
                    time.sleep(0.002)
                    continue
                except queue.Full:
                    req.future.set_exception(RuntimeError(
                        f"level cap {level_key} saturato + queue piena"))
                    with self._counters_lock:
                        self._rejected += 1
                    continue
            need_acquired: List[str] = []
            cap_fail = False
            for need in needs:
                if self._need_caps.try_acquire(need):
                    need_acquired.append(need)
                else:
                    cap_fail = True
                    break
            if cap_fail:
                for n in need_acquired:
                    self._need_caps.release(n)
                self._level_caps.release(level_key)
                try:
                    self._queue.put_nowait(req)
                    with self._counters_lock:
                        self._skipped_cap += 1
                    emit_event(req.neuron_name, "REQUEUED_NEED_CAP", needs=needs)
                    time.sleep(0.002)
                    continue
                except queue.Full:
                    req.future.set_exception(RuntimeError(
                        "need cap saturato + queue piena"))
                    with self._counters_lock:
                        self._rejected += 1
                    continue

            # Sottometti al pool
            with self._counters_lock:
                self._dispatched += 1

            assert self._executor is not None
            self._executor.submit(
                self._run_task, req, neuron, level_key, need_acquired,
            )

    def _run_task(
        self,
        req: TaskRequest,
        neuron: Neuron,
        level_key: str,
        need_acquired: List[str],
    ) -> None:
        t0 = time.perf_counter()
        try:
            runner = wrap_execute(neuron)
            output, violations = runner(req.input_obj)
            ok = not violations
            elapsed = (time.perf_counter() - t0) * 1000.0
            # Retry su timeout
            if not ok and req.retries_left > 0 and any(
                v.code == ContractViolationCode.BUDGET_EXCEEDED_TIMEOUT
                for v in violations
            ):
                req.retries_left -= 1
                emit_event(req.neuron_name, "RETRY_SCHEDULED",
                           retries_left=req.retries_left)
                # re-enqueue (fire-and-forget — stessa Future)
                try:
                    self._queue.put_nowait(req)
                    return
                except queue.Full:
                    pass  # fallback: fallisce qui
            # Strike su errore (aumenta strike counter in registry)
            if not ok:
                from cortex.mesh.contract import _REGISTRY as _NREG
                count, quarantined = _NREG.strike(req.neuron_name)
                emit_event(req.neuron_name, "STRIKE_RECORDED",
                           strikes=count, quarantined=quarantined)
            # Metriche
            with self._counters_lock:
                if ok:
                    self._completed += 1
                else:
                    self._errored += 1
            self._error_window.record(ok)
            # Risultato
            req.future.set_result(TaskResult(
                neuron_name=req.neuron_name,
                ok=ok, output=output,
                violations=violations,
                elapsed_ms=elapsed,
                ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
            ))
        except Exception as e:  # pragma: no cover
            elapsed = (time.perf_counter() - t0) * 1000.0
            _log.exception("unhandled in _run_task for %s", req.neuron_name)
            req.future.set_exception(e)
            with self._counters_lock:
                self._errored += 1
            self._error_window.record(False)
        finally:
            self._level_caps.release(level_key)
            for need in need_acquired:
                self._need_caps.release(need)

    # ----------------------------------------------------------- heartbeat --

    def heartbeat(self) -> Dict[str, Any]:
        """
        Chiamare ogni N secondi (es. ogni epigenome.mesh.heartbeat_s).
        Chiude la finestra di error rate corrente; se trip → freeze mesh.
        """
        rate, tripped = self._error_window.tick_heartbeat()
        info = {
            "state": self._state.value,
            "error_rate_last_window": rate,
            "tripped": tripped,
        }
        if tripped and self._state == RuntimeState.RUNNING:
            emit_event("<runtime>", "FAIL_SAFE_TRIP",
                       rate=rate, threshold=self._fs_threshold,
                       action=self._fs_action)
            if self._fs_action == "freeze_mesh":
                self.freeze(reason=f"error_rate={rate:.2%} > {self._fs_threshold:.2%}")
                if self._fs_auto_flip:
                    self._flip_epigenome_flag_best_effort()
        return info

    def _flip_epigenome_flag_best_effort(self) -> None:
        """Prova a flippare epigenome.mesh.enabled → false. Non-fatal."""
        try:
            from pathlib import Path
            import yaml
            epipath = Path(__file__).resolve().parents[2] / "digitaldna" / "epigenome.yaml"
            if not epipath.exists():
                _log.info("epigenome.yaml non trovato a %s — flag non flippato", epipath)
                return
            with open(epipath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            mesh = data.setdefault("mesh", {})
            if mesh.get("enabled", False) is True:
                mesh["enabled"] = False
                mesh["_last_freeze_ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                with open(epipath, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
                emit_event("<runtime>", "EPIGENOME_MESH_DISABLED")
        except Exception as e:  # pragma: no cover
            _log.warning("impossibile flippare epigenome: %s", e)

    # -------------------------------------------------------------- status --

    def status(self) -> Dict[str, Any]:
        with self._counters_lock:
            counters = {
                "submitted": self._submitted,
                "dispatched": self._dispatched,
                "completed": self._completed,
                "errored": self._errored,
                "rejected": self._rejected,
                "skipped_quarantine": self._skipped_quarantine,
                "skipped_cap": self._skipped_cap,
            }
        return {
            "version": RUNTIME_VERSION,
            "state": self._state.value,
            "queue_depth": self._queue.qsize(),
            "queue_max": self._queue_size,
            "max_workers": self._max_workers,
            "backpressure": self._backpressure,
            "fail_safe": {
                "threshold": self._fs_threshold,
                "window": self._fs_window,
                "action": self._fs_action,
            },
            "counters": counters,
        }


# ================================================================================
# __main__ demo
# ================================================================================

def _demo() -> int:  # pragma: no cover
    from cortex.mesh.contract import neuron
    from cortex.mesh.olc import SensoryFrame, InterpretationFrame, DecisionFrame, ActionResult

    @neuron(
        name="demo.rt.perceive",
        input_type=SensoryFrame, output_type=InterpretationFrame,
        level=2, needs_served=["integration"],
        resource_budget={"max_ms": 200, "max_mb": 16},
        side_effects=[], version="1.0.0",
        description="demo runtime perceive",
    )
    def perceive(inp: SensoryFrame) -> InterpretationFrame:
        return InterpretationFrame(intent="observed", confidence=0.8, source=inp.source)
    # --- plan & act defined below ---

    @neuron(
        name="demo.rt.plan",
        input_type=InterpretationFrame, output_type=DecisionFrame,
        level=1, needs_served=["harmony"],
        resource_budget={"max_ms": 200, "max_mb": 16},
        side_effects=[], version="1.0.0",
        description="demo runtime plan",
    )
    def plan(inp: InterpretationFrame) -> DecisionFrame:
        return DecisionFrame(action="engage", args={}, rationale=inp.intent, risk=0.1)

    @neuron(
        name="demo.rt.act",
        input_type=DecisionFrame, output_type=ActionResult,
        level=4, needs_served=["survival"],
        resource_budget={"max_ms": 200, "max_mb": 16},
        side_effects=[], version="1.0.0",
        description="demo runtime act",
    )
    def act(inp: DecisionFrame) -> ActionResult:
        return ActionResult(ok=True, output={"action": inp.action}, latency_ms=1.0, action=inp.action)

    g = MeshGraph()
    for w in (perceive, plan, act):
        g.add_neuron(w.instance())
    g.auto_wire()

    rt = MeshRuntime(g)
    rt.start()
    try:
        sf = SensoryFrame(source="cam", modality="image",
                          payload={"frame": 1}, confidence=0.9)
        results = rt.propagate("demo.rt.perceive", sf, timeout_s=5.0)
        for name, res in results.items():
            print(f"  {name}: ok={res.ok} elapsed={res.elapsed_ms:.2f}ms output={res.output}")
        print()
        print("STATUS:", rt.status())
        rt.heartbeat()
    finally:
        rt.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_demo())
