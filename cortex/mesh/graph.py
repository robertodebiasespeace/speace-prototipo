"""
SPEACE Cortex Mesh — Typed Adaptive DAG (M4.5)

Implementa `MeshGraph`, il grafo tipizzato adattivo di neuroni della Continuous
Neural Mesh (CNM). Concetto centrale del contratto M4-CNM.

Caratteristiche:
  - Nodi = neuroni (identificati per nome; contratto validato via contract.py)
  - Archi = connessioni tipizzate (output_type di src compatibile con
           input_type di dst, secondo OLC.is_compatible_with)
  - Invariante DAG: il grafo è aciclico (rifiuto all'insert di edges che
                    chiuderebbero un ciclo)
  - Adattivo: add/remove di neuroni e archi è ammesso a runtime (thread-safe)
  - Viste derivate: per livello (L1..L5), per bisogno (harmony/survival/…),
                    per tipo OLC (producers/consumers)
  - Algoritmi: topological sort (Kahn), cycle probe (DFS), path finding
               (BFS bounded)
  - Export: snapshot JSON-safe e formato DOT (GraphViz)
  - Edge metadata: peso sinaptico (M5 plasticity), heartbeat_last_used,
                   success/failure counters

Violazioni (tassonomia estesa rispetto a contract.ContractViolationCode):
  - GRAPH_NEURON_NOT_FOUND
  - GRAPH_DUPLICATE_NEURON
  - GRAPH_EDGE_TYPE_MISMATCH
  - GRAPH_CYCLE_DETECTED
  - GRAPH_DUPLICATE_EDGE
  - GRAPH_SELF_LOOP
  - GRAPH_CONTRACT_VIOLATION (bubble-up da validate_contract)

Milestone: M4.5 (PROP-CORTEX-NEURAL-MESH-M4)
Riferimento canonico: cortex/mesh/SPEC_NEURON_CONTRACT.md §3 (DAG)
"""

from __future__ import annotations
import dataclasses
import datetime
import enum
import logging
import threading
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from cortex.mesh.olc import OLCBase, NEEDS_CATALOG
from cortex.mesh.contract import (
    Neuron,
    NeuronRegistry,
    ContractViolation,
    ContractViolationCode,
    Phase,
    LEVELS,
    validate_contract,
    registry as default_neuron_registry,
    emit_event,
)

_log = logging.getLogger("speace.mesh.graph")

GRAPH_VERSION = "1.0"


# ================================================================================
# Violazioni graph-level
# ================================================================================

class GraphViolationCode(str, enum.Enum):
    GRAPH_NEURON_NOT_FOUND = "GRAPH_NEURON_NOT_FOUND"
    GRAPH_DUPLICATE_NEURON = "GRAPH_DUPLICATE_NEURON"
    GRAPH_EDGE_TYPE_MISMATCH = "GRAPH_EDGE_TYPE_MISMATCH"
    GRAPH_CYCLE_DETECTED = "GRAPH_CYCLE_DETECTED"
    GRAPH_DUPLICATE_EDGE = "GRAPH_DUPLICATE_EDGE"
    GRAPH_SELF_LOOP = "GRAPH_SELF_LOOP"
    GRAPH_CONTRACT_VIOLATION = "GRAPH_CONTRACT_VIOLATION"


@dataclasses.dataclass(frozen=True)
class GraphViolation:
    code: GraphViolationCode
    message: str
    src: str = ""
    dst: str = ""
    wrapped: Optional[ContractViolation] = None

    def __str__(self) -> str:  # pragma: no cover
        edge = f" [{self.src} → {self.dst}]" if self.src or self.dst else ""
        return f"{self.code.value}{edge}: {self.message}"


# ================================================================================
# Edge metadata
# ================================================================================

@dataclasses.dataclass
class EdgeMeta:
    """
    Metadati dell'arco. M4.5 li inizializza con valori neutri;
    M5 (plasticity) li aggiorna in base a successi/fallimenti e heartbeat.
    """
    weight: float = 1.0                      # peso sinaptico [0..∞)
    successes: int = 0
    failures: int = 0
    last_used_ts: Optional[str] = None       # ISO-8601
    created_ts: str = ""

    def record_success(self) -> None:
        self.successes += 1
        self.last_used_ts = _iso_now()

    def record_failure(self) -> None:
        self.failures += 1
        self.last_used_ts = _iso_now()

    def activation_ratio(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0


def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


# ================================================================================
# MeshGraph — DAG principale
# ================================================================================

class MeshGraph:
    """
    Grafo tipizzato adattivo dei neuroni CNM.

    Thread-safety: un solo RLock globale protegge strutture dati.
    Le letture pesanti (topological_order, snapshot) copiano gli output
    sotto lock, poi rilasciano.

    Integrazione con NeuronRegistry:
      - `attach_from_registry(reg)` aggiunge tutti i neuroni attualmente
        registrati senza errori di contratto
      - oppure `add_neuron(n)` one-by-one (ritorna violazioni aggregate)

    Il grafo NON duplica i Neuron objects: li referenzia per nome dal registry
    (o tramite reference diretto se aggiunti con add_neuron). Per questo
    `lookup(name)` ritorna sempre l'oggetto vivo.
    """

    def __init__(self, neuron_registry: Optional[NeuronRegistry] = None) -> None:
        self._lock = threading.RLock()
        self._neurons: Dict[str, Neuron] = {}          # name → Neuron
        self._succ: Dict[str, Set[str]] = defaultdict(set)  # src → {dst}
        self._pred: Dict[str, Set[str]] = defaultdict(set)  # dst → {src}
        self._edge_meta: Dict[Tuple[str, str], EdgeMeta] = {}
        # Indici derivati (aggiornati su add/remove)
        self._by_level: Dict[int, Set[str]] = defaultdict(set)
        self._by_need: Dict[str, Set[str]] = defaultdict(set)
        self._by_input_type: Dict[str, Set[str]] = defaultdict(set)   # olc_name → {neuron_name}
        self._by_output_type: Dict[str, Set[str]] = defaultdict(set)
        # Registry di riferimento (usato per validate_contract quando add_neuron registra)
        self._registry = neuron_registry or default_neuron_registry()

    # ---------------------------------------------------------------- nodes --

    def add_neuron(
        self,
        neuron: Neuron,
        *,
        register_in_neuron_registry: bool = True,
        skip_contract: bool = False,
    ) -> List[GraphViolation]:
        """
        Aggiunge un neurone al grafo.

        Ritorna lista di violazioni (vuota = OK).

        Per default esegue `validate_contract(neuron)` e bolle-up eventuali
        violazioni come `GRAPH_CONTRACT_VIOLATION`. Se `skip_contract=True`
        salta il check (usato dal loader di `attach_from_registry` quando
        si sa che il neurone è già validato).

        Se `register_in_neuron_registry=True` (default) registra il neurone
        nel NeuronRegistry di riferimento; eventuale DUPLICATE_NAME è riportato
        come violazione del grafo.
        """
        violations: List[GraphViolation] = []
        name = neuron.name

        if not skip_contract:
            for cv in validate_contract(neuron):
                violations.append(GraphViolation(
                    code=GraphViolationCode.GRAPH_CONTRACT_VIOLATION,
                    message=str(cv),
                    src=name,
                    wrapped=cv,
                ))
            if violations:
                return violations

        with self._lock:
            if name in self._neurons:
                if self._neurons[name] is neuron:
                    # idempotente
                    return []
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_DUPLICATE_NEURON,
                    message=f"neurone '{name}' già presente nel grafo",
                    src=name,
                )]

            if register_in_neuron_registry:
                reg_vs = self._registry.register(neuron)
                if reg_vs:
                    return [GraphViolation(
                        code=GraphViolationCode.GRAPH_CONTRACT_VIOLATION,
                        message=str(reg_vs[0]),
                        src=name,
                        wrapped=reg_vs[0],
                    )]

            self._neurons[name] = neuron
            self._succ.setdefault(name, set())
            self._pred.setdefault(name, set())
            self._by_level[neuron.level].add(name)
            for need in neuron.needs_served or []:
                self._by_need[need].add(name)
            if neuron.input_type is not None:
                self._by_input_type[neuron.input_type._OLC_NAME].add(name)
            if neuron.output_type is not None:
                self._by_output_type[neuron.output_type._OLC_NAME].add(name)

        emit_event(name, "GRAPH_NEURON_ADDED", level=neuron.level)
        return []

    def remove_neuron(self, name: str) -> bool:
        """
        Rimuove il neurone e TUTTI gli archi che lo toccano.
        Ritorna True se il neurone esisteva.
        """
        with self._lock:
            if name not in self._neurons:
                return False
            neuron = self._neurons[name]
            # rimuovi archi uscenti
            for dst in list(self._succ.get(name, set())):
                self._pred[dst].discard(name)
                self._edge_meta.pop((name, dst), None)
            # rimuovi archi entranti
            for src in list(self._pred.get(name, set())):
                self._succ[src].discard(name)
                self._edge_meta.pop((src, name), None)
            self._succ.pop(name, None)
            self._pred.pop(name, None)
            # indici
            self._by_level[neuron.level].discard(name)
            for need in neuron.needs_served or []:
                self._by_need[need].discard(name)
            if neuron.input_type is not None:
                self._by_input_type[neuron.input_type._OLC_NAME].discard(name)
            if neuron.output_type is not None:
                self._by_output_type[neuron.output_type._OLC_NAME].discard(name)
            del self._neurons[name]
        emit_event(name, "GRAPH_NEURON_REMOVED")
        return True

    def lookup(self, name: str) -> Optional[Neuron]:
        with self._lock:
            return self._neurons.get(name)

    def has_neuron(self, name: str) -> bool:
        with self._lock:
            return name in self._neurons

    def nodes(self) -> List[str]:
        with self._lock:
            return sorted(self._neurons.keys())

    def all_neurons(self) -> List[Neuron]:
        with self._lock:
            return list(self._neurons.values())

    # ---------------------------------------------------------------- edges --

    def add_edge(self, src: str, dst: str, *, weight: float = 1.0) -> List[GraphViolation]:
        """
        Aggiunge un arco tipizzato src → dst.

        Controlli:
          1. entrambi i neuroni esistono                 → GRAPH_NEURON_NOT_FOUND
          2. self-loop vietato                           → GRAPH_SELF_LOOP
          3. arco già esistente                          → GRAPH_DUPLICATE_EDGE
          4. compatibilità tipi OLC                      → GRAPH_EDGE_TYPE_MISMATCH
                src.output_type.is_compatible_with(dst.input_type)
          5. aciclicità: non deve esistere path dst → src → GRAPH_CYCLE_DETECTED

        Se validi, l'arco viene creato con EdgeMeta(weight, created_ts=now).
        """
        if src == dst:
            return [GraphViolation(
                code=GraphViolationCode.GRAPH_SELF_LOOP,
                message=f"self-loop non ammesso su '{src}'",
                src=src, dst=dst,
            )]

        with self._lock:
            if src not in self._neurons:
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_NEURON_NOT_FOUND,
                    message=f"src='{src}' non registrato nel grafo",
                    src=src, dst=dst,
                )]
            if dst not in self._neurons:
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_NEURON_NOT_FOUND,
                    message=f"dst='{dst}' non registrato nel grafo",
                    src=src, dst=dst,
                )]
            if dst in self._succ[src]:
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_DUPLICATE_EDGE,
                    message=f"arco già presente: {src} → {dst}",
                    src=src, dst=dst,
                )]

            # (4) compatibilità tipi
            sn = self._neurons[src]
            dn = self._neurons[dst]
            compat_ok = False
            if sn.output_type is not None and dn.input_type is not None:
                try:
                    compat_ok = sn.output_type.is_compatible_with(dn.input_type)
                except Exception as e:  # pragma: no cover
                    compat_ok = False
                    _log.warning("is_compatible_with raised: %s", e)
            if not compat_ok:
                so = sn.output_type._OLC_NAME if sn.output_type else "<none>"
                di = dn.input_type._OLC_NAME if dn.input_type else "<none>"
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_EDGE_TYPE_MISMATCH,
                    message=(
                        f"type mismatch: {src}.output_type='{so}' non compatibile "
                        f"con {dst}.input_type='{di}'"
                    ),
                    src=src, dst=dst,
                )]

            # (5) aciclicità — cerca path dst → src nello stato CORRENTE
            if self._reachable_unlocked(dst, src):
                return [GraphViolation(
                    code=GraphViolationCode.GRAPH_CYCLE_DETECTED,
                    message=f"aggiungere {src} → {dst} chiuderebbe un ciclo",
                    src=src, dst=dst,
                )]

            # Commit
            self._succ[src].add(dst)
            self._pred[dst].add(src)
            self._edge_meta[(src, dst)] = EdgeMeta(
                weight=float(weight),
                created_ts=_iso_now(),
            )

        emit_event(src, "GRAPH_EDGE_ADDED", dst=dst, weight=weight)
        return []

    def remove_edge(self, src: str, dst: str) -> bool:
        with self._lock:
            if dst not in self._succ.get(src, set()):
                return False
            self._succ[src].discard(dst)
            self._pred[dst].discard(src)
            self._edge_meta.pop((src, dst), None)
        emit_event(src, "GRAPH_EDGE_REMOVED", dst=dst)
        return True

    def has_edge(self, src: str, dst: str) -> bool:
        with self._lock:
            return dst in self._succ.get(src, set())

    def edges(self) -> List[Tuple[str, str]]:
        """Snapshot ordinata degli archi (src, dst)."""
        with self._lock:
            out: List[Tuple[str, str]] = []
            for s in sorted(self._succ.keys()):
                for d in sorted(self._succ[s]):
                    out.append((s, d))
            return out

    def edge_meta(self, src: str, dst: str) -> Optional[EdgeMeta]:
        with self._lock:
            return self._edge_meta.get((src, dst))

    # ------------------------------------------------------- neighbors/views --

    def successors(self, name: str) -> List[str]:
        with self._lock:
            return sorted(self._succ.get(name, set()))

    def predecessors(self, name: str) -> List[str]:
        with self._lock:
            return sorted(self._pred.get(name, set()))

    def neurons_by_level(self, level: int) -> List[Neuron]:
        with self._lock:
            return [self._neurons[n] for n in sorted(self._by_level.get(level, set()))]

    def neurons_by_need(self, need: str) -> List[Neuron]:
        if need not in NEEDS_CATALOG:
            return []
        with self._lock:
            return [self._neurons[n] for n in sorted(self._by_need.get(need, set()))]

    def producers_of(self, olc_name: str) -> List[str]:
        """Neuroni il cui output_type._OLC_NAME == olc_name."""
        with self._lock:
            return sorted(self._by_output_type.get(olc_name, set()))

    def consumers_of(self, olc_name: str) -> List[str]:
        """Neuroni il cui input_type._OLC_NAME == olc_name."""
        with self._lock:
            return sorted(self._by_input_type.get(olc_name, set()))

    def roots(self) -> List[str]:
        """Neuroni senza predecessori."""
        with self._lock:
            return sorted(n for n in self._neurons if not self._pred.get(n))

    def sinks(self) -> List[str]:
        """Neuroni senza successori."""
        with self._lock:
            return sorted(n for n in self._neurons if not self._succ.get(n))

    # ---------------------------------------------------- algoritmi di base --

    def _reachable_unlocked(self, src: str, target: str) -> bool:
        """DFS interna (richiede lock già acquisito)."""
        if src == target:
            return True
        stack = [src]
        visited: Set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in self._succ.get(cur, set()):
                if nxt == target:
                    return True
                if nxt not in visited:
                    stack.append(nxt)
        return False

    def is_reachable(self, src: str, dst: str) -> bool:
        with self._lock:
            if src not in self._neurons or dst not in self._neurons:
                return False
            return self._reachable_unlocked(src, dst)

    def has_cycle(self) -> bool:
        """
        Verifica indipendente invariante DAG. Dovrebbe sempre ritornare False
        se add_edge è l'unico modo di creare archi (protezione difensiva).
        """
        with self._lock:
            in_deg: Dict[str, int] = {n: len(self._pred.get(n, set())) for n in self._neurons}
            q = deque([n for n, d in in_deg.items() if d == 0])
            visited = 0
            while q:
                cur = q.popleft()
                visited += 1
                for nxt in self._succ.get(cur, set()):
                    in_deg[nxt] -= 1
                    if in_deg[nxt] == 0:
                        q.append(nxt)
            return visited != len(self._neurons)

    def topological_order(self) -> List[str]:
        """
        Ritorna un ordinamento topologico (Kahn). Solleva RuntimeError se
        `has_cycle()` è True (invariante violato — non dovrebbe mai accadere).
        L'ordinamento tra pari è deterministico (alfabetico) per riproducibilità.
        """
        with self._lock:
            in_deg: Dict[str, int] = {n: len(self._pred.get(n, set())) for n in self._neurons}
            # min-heap emulato con sort crescente su ogni estrazione batch
            ready = sorted(n for n, d in in_deg.items() if d == 0)
            out: List[str] = []
            while ready:
                cur = ready.pop(0)
                out.append(cur)
                newly = []
                for nxt in sorted(self._succ.get(cur, set())):
                    in_deg[nxt] -= 1
                    if in_deg[nxt] == 0:
                        newly.append(nxt)
                ready = sorted(ready + newly)
            if len(out) != len(self._neurons):
                raise RuntimeError("topological_order: grafo contiene cicli (invariante DAG violato)")
            return out

    def layers(self) -> List[List[str]]:
        """
        Partizionamento in "strati" per esecuzione parallela:
        ogni strato contiene nodi senza dipendenze residue rispetto ai precedenti.
        (Kahn a livelli — utile al runtime M4.6 per schedulare batch paralleli.)
        """
        with self._lock:
            in_deg: Dict[str, int] = {n: len(self._pred.get(n, set())) for n in self._neurons}
            current = sorted(n for n, d in in_deg.items() if d == 0)
            layers: List[List[str]] = []
            seen = 0
            while current:
                layers.append(current)
                seen += len(current)
                nxt_layer: List[str] = []
                for cur in current:
                    for nxt in self._succ.get(cur, set()):
                        in_deg[nxt] -= 1
                        if in_deg[nxt] == 0:
                            nxt_layer.append(nxt)
                current = sorted(nxt_layer)
            if seen != len(self._neurons):
                raise RuntimeError("layers: grafo contiene cicli (invariante DAG violato)")
            return layers

    def find_paths(
        self,
        src: str,
        dst: str,
        *,
        max_hops: int = 8,
        max_paths: int = 32,
    ) -> List[List[str]]:
        """
        BFS bounded per trovare fino a `max_paths` cammini da src a dst
        (escluso path vuoto, lunghezza ≤ max_hops archi). Utile al
        task_generator M4.11 per esplorare routing alternativi.
        """
        with self._lock:
            if src not in self._neurons or dst not in self._neurons:
                return []
            paths: List[List[str]] = []
            queue: deque = deque([[src]])
            while queue and len(paths) < max_paths:
                path = queue.popleft()
                if len(path) > max_hops + 1:
                    continue
                last = path[-1]
                if last == dst and len(path) > 1:
                    paths.append(path)
                    continue
                for nxt in sorted(self._succ.get(last, set())):
                    if nxt in path:
                        continue  # evita cicli in paths (DAG garantisce comunque)
                    queue.append(path + [nxt])
            return paths

    # ---------------------------------------------------------- bulk/attach --

    def attach_from_registry(
        self,
        reg: Optional[NeuronRegistry] = None,
        *,
        skip_contract: bool = False,
    ) -> Dict[str, List[GraphViolation]]:
        """
        Importa tutti i neuroni dal NeuronRegistry (default = _REGISTRY di
        contract.py). Ritorna {name: [violations]} solo per quelli falliti.
        """
        reg = reg or self._registry
        report: Dict[str, List[GraphViolation]] = {}
        for n in reg.all():
            vs = self.add_neuron(
                n,
                register_in_neuron_registry=False,  # già in registry
                skip_contract=skip_contract,
            )
            if vs:
                report[n.name] = vs
        return report

    def auto_wire(
        self,
        *,
        dry_run: bool = False,
    ) -> List[Tuple[str, str]]:
        """
        Heuristic automatic wiring: per ogni tipo OLC, collega ogni producer
        a ogni consumer compatibile, saltando:
          - self-loop
          - edge già presente
          - edge che chiuderebbe un ciclo (gestito da add_edge)

        In `dry_run=True` ritorna solo la lista proposta senza mutare.

        Utile al bootstrap: M4.8 (adapter neuroni) istanzia 30+ neuroni,
        `auto_wire()` genera la topologia di default rispettosa dei tipi.
        """
        proposed: List[Tuple[str, str]] = []
        with self._lock:
            for olc_name, producers in list(self._by_output_type.items()):
                consumers = self._by_input_type.get(olc_name, set())
                for s in sorted(producers):
                    for d in sorted(consumers):
                        if s == d:
                            continue
                        if d in self._succ.get(s, set()):
                            continue
                        proposed.append((s, d))

        created: List[Tuple[str, str]] = []
        if not dry_run:
            for s, d in proposed:
                vs = self.add_edge(s, d)
                if not vs:
                    created.append((s, d))
            return created
        return proposed

    # -------------------------------------------------------- snapshot/export --

    def snapshot(self) -> Dict[str, Any]:
        """Snapshot JSON-safe per telemetry (M4.13) e debug."""
        with self._lock:
            return {
                "version": GRAPH_VERSION,
                "ts": _iso_now(),
                "nodes": [
                    {
                        "name": n.name,
                        "level": n.level,
                        "needs": list(n.needs_served),
                        "input_type": n.input_type._OLC_NAME if n.input_type else None,
                        "output_type": n.output_type._OLC_NAME if n.output_type else None,
                        "version": n.version,
                    }
                    for n in sorted(self._neurons.values(), key=lambda x: x.name)
                ],
                "edges": [
                    {
                        "src": s,
                        "dst": d,
                        "weight": self._edge_meta[(s, d)].weight,
                        "successes": self._edge_meta[(s, d)].successes,
                        "failures": self._edge_meta[(s, d)].failures,
                    }
                    for (s, d) in self.edges()
                ],
                "stats": {
                    "nodes": len(self._neurons),
                    "edges": sum(len(v) for v in self._succ.values()),
                    "roots": len(self.roots()),
                    "sinks": len(self.sinks()),
                    "levels": {str(L): len(self._by_level.get(L, set())) for L in LEVELS},
                    "needs": {k: len(self._by_need.get(k, set())) for k in NEEDS_CATALOG},
                },
            }

    def to_dot(self, *, title: str = "SPEACE CNM Mesh") -> str:
        """Export DOT (GraphViz) per rendering visuale."""
        lines: List[str] = [f'digraph "{title}" {{', '  rankdir=LR;', '  node [shape=box];']
        colors = {1: "#fce4ec", 2: "#e1f5fe", 3: "#fff9c4", 4: "#e8f5e9", 5: "#f3e5f5"}
        with self._lock:
            for n in sorted(self._neurons.values(), key=lambda x: x.name):
                color = colors.get(n.level, "#eeeeee")
                label = f"{n.name}\\nL{n.level} · {'/'.join(n.needs_served or ['—'])}"
                lines.append(f'  "{n.name}" [label="{label}", style=filled, fillcolor="{color}"];')
            for (s, d) in self.edges():
                m = self._edge_meta.get((s, d))
                w = f" ({m.weight:.2f})" if m else ""
                lines.append(f'  "{s}" -> "{d}" [label="{w.strip()}"];')
        lines.append("}")
        return "\n".join(lines)

    # --------------------------------------------------------------- utility --

    def clear(self) -> None:
        """Svuota completamente il grafo (NON tocca il NeuronRegistry)."""
        with self._lock:
            self._neurons.clear()
            self._succ.clear()
            self._pred.clear()
            self._edge_meta.clear()
            self._by_level.clear()
            self._by_need.clear()
            self._by_input_type.clear()
            self._by_output_type.clear()

    def __len__(self) -> int:
        return len(self._neurons)

    def __repr__(self) -> str:  # pragma: no cover
        with self._lock:
            return (
                f"<MeshGraph nodes={len(self._neurons)} "
                f"edges={sum(len(v) for v in self._succ.values())}>"
            )


# ================================================================================
# Factory di default: singleton (opzionale, simile a NeuronRegistry)
# ================================================================================

_DEFAULT_GRAPH: Optional[MeshGraph] = None
_DEFAULT_GRAPH_LOCK = threading.Lock()


def default_graph() -> MeshGraph:
    """Ritorna un singleton MeshGraph attaccato al default NeuronRegistry."""
    global _DEFAULT_GRAPH
    if _DEFAULT_GRAPH is None:
        with _DEFAULT_GRAPH_LOCK:
            if _DEFAULT_GRAPH is None:
                _DEFAULT_GRAPH = MeshGraph()
    return _DEFAULT_GRAPH


def _reset_default_graph() -> None:
    """Solo per testing."""
    global _DEFAULT_GRAPH
    with _DEFAULT_GRAPH_LOCK:
        _DEFAULT_GRAPH = None


# ================================================================================
# __main__ demo (runnable come `python -m cortex.mesh.graph`)
# ================================================================================

def _demo() -> int:  # pragma: no cover
    from cortex.mesh.contract import neuron
    from cortex.mesh.olc import (
        SensoryFrame, InterpretationFrame, DecisionFrame, ActionResult,
    )

    @neuron(
        name="demo.perceiver",
        input_type=SensoryFrame,
        output_type=InterpretationFrame,
        level=2, needs_served=["integration"],
        resource_budget={"max_ms": 100, "max_mb": 16},
        side_effects=[], version="1.0.0",
        description="demo perceiver",
    )
    def perceiver(inp: SensoryFrame) -> InterpretationFrame:
        return InterpretationFrame(intent="see", confidence=0.9, source=inp.source)

    @neuron(
        name="demo.planner",
        input_type=InterpretationFrame,
        output_type=DecisionFrame,
        level=1, needs_served=["harmony"],
        resource_budget={"max_ms": 200, "max_mb": 16},
        side_effects=[], version="1.0.0",
        description="demo planner",
    )
    def planner(inp: InterpretationFrame) -> DecisionFrame:
        return DecisionFrame(action="wait", rationale=f"saw {inp.intent}", confidence=inp.confidence)

    @neuron(
        name="demo.actor",
        input_type=DecisionFrame,
        output_type=ActionResult,
        level=4, needs_served=["survival"],
        resource_budget={"max_ms": 300, "max_mb": 32},
        side_effects=[], version="1.0.0",
        description="demo actor",
    )
    def actor(inp: DecisionFrame) -> ActionResult:
        return ActionResult(ok=True, details=f"did {inp.action}")

    g = MeshGraph()
    for wrapper in (perceiver, planner, actor):
        vs = g.add_neuron(wrapper.instance())
        assert not vs, f"add_neuron failed: {vs}"

    created = g.auto_wire()
    print(f"Auto-wired edges: {created}")
    print(f"Topo order: {g.topological_order()}")
    print(f"Layers: {g.layers()}")
    print(f"Snapshot stats: {g.snapshot()['stats']}")
    print()
    print(g.to_dot())
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_demo())
