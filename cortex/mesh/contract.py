"""
SPEACE Cortex Mesh — Neuron Contract Validator (M4.2)

Implementazione di:
  - `Neuron` classe base con lifecycle a 5 fasi
  - `@neuron(...)` decoratore per dichiarare neuroni da funzioni
  - `ContractViolation` + `ContractViolationCode` (enum, tassonomia §8.1)
  - `validate_contract(obj)` validazione statica (boot-time)
  - `check_types_in_olc(obj)` interrogazione OLC registry (AC-4)
  - `wrap_execute(neuron)` hook runtime con type-check I/O + timeout (AC-5)
  - Telemetry stub con buffer in-memory (M4.13 lo sostituirà con mesh_state.jsonl)
  - Strike counter + quarantena (AC-2/§8.2)

Milestone: M4.2 (PROP-CORTEX-NEURAL-MESH-M4)
Riferimento canonico: cortex/mesh/SPEC_NEURON_CONTRACT.md

Esempio d'uso (runnable come `python -m cortex.mesh.contract`):

    from cortex.mesh.contract import neuron, validate_contract
    from cortex.mesh.olc import SensoryFrame, InterpretationFrame

    @neuron(
        name="neuron.example.echo",
        input_type=SensoryFrame,
        output_type=InterpretationFrame,
        level=2,
        needs_served=["integration"],
        resource_budget={"max_ms": 200, "max_mb": 32},
        side_effects=[],
        version="1.0.0",
        description="Echo neurone di esempio",
    )
    def echo(inp):
        return InterpretationFrame(intent="echo", confidence=1.0, source=inp.source)

    instance = echo.instance()
    assert validate_contract(instance) == []
"""

from __future__ import annotations
import concurrent.futures
import dataclasses
import datetime
import enum
import inspect
import logging
import re
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from cortex.mesh.olc import (
    OLCBase,
    OLCValidationError,
    NEEDS_CATALOG,
    lookup as olc_lookup,
)

CONTRACT_VERSION = "1.0"
_log = logging.getLogger("speace.mesh.contract")

# ================================================================================
# Costanti / Regex
# ================================================================================

NAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")
SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+(?:[-+][a-zA-Z0-9.-]+)?$")

# Pattern dei side-effect kind: <kind>:<arg>
SIDE_EFFECT_KINDS = {
    "fs_read",
    "fs_write",
    "net",
    "llm",
    "proposal",
    "shell",
    "kv",
    "state_bus",
}
_SIDE_EFFECT_PATTERN = re.compile(r"^([a-z_]+):(.+)$")
_RISK_LEVELS = {"low", "medium", "high"}

LEVELS = (1, 2, 3, 4, 5)

# Hard ceilings — sovrascritti da execution_rules.yaml (M4.4) con fallback costanti.
DEFAULT_MAX_MS_CEILING = 30_000
DEFAULT_MAX_MB_CEILING = 512
DEFAULT_MAX_RETRIES_CEILING = 3
DEFAULT_PRIORITY_BOOST_RANGE = (-2, 2)
DEFAULT_QUARANTINE_THRESHOLD = 3

MAX_DESCRIPTION_CHARS = 200


def _ceilings_from_rules() -> Dict[str, Any]:
    """Carica i ceiling da execution_rules.yaml; fallback a costanti se indisponibile."""
    try:
        from cortex.mesh import execution_rules as _er
        bc = _er.get_budget_ceilings()
        qp = _er.get_quarantine_policy()
        return {
            "max_ms": int(bc.get("max_ms", DEFAULT_MAX_MS_CEILING)),
            "max_mb": int(bc.get("max_mb", DEFAULT_MAX_MB_CEILING)),
            "max_retries": int(bc.get("max_retries", DEFAULT_MAX_RETRIES_CEILING)),
            "priority_boost_min": int(bc.get("priority_boost_min", DEFAULT_PRIORITY_BOOST_RANGE[0])),
            "priority_boost_max": int(bc.get("priority_boost_max", DEFAULT_PRIORITY_BOOST_RANGE[1])),
            "quarantine_threshold": int(qp.get("strike_threshold", DEFAULT_QUARANTINE_THRESHOLD)),
        }
    except Exception as e:  # pragma: no cover
        _log.warning("execution_rules load failed (%s) — using hard-coded fallback", e)
        return {
            "max_ms": DEFAULT_MAX_MS_CEILING,
            "max_mb": DEFAULT_MAX_MB_CEILING,
            "max_retries": DEFAULT_MAX_RETRIES_CEILING,
            "priority_boost_min": DEFAULT_PRIORITY_BOOST_RANGE[0],
            "priority_boost_max": DEFAULT_PRIORITY_BOOST_RANGE[1],
            "quarantine_threshold": DEFAULT_QUARANTINE_THRESHOLD,
        }


def current_ceilings() -> Dict[str, int]:
    """Snapshot dei ceiling correnti (per debug/telemetria)."""
    return _ceilings_from_rules()


# ================================================================================
# Enum & dataclass — tassonomia violazioni e fasi
# ================================================================================

class Phase(str, enum.Enum):
    REGISTERED = "REGISTERED"
    ACTIVATED = "ACTIVATED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ERRORED = "ERRORED"
    SKIPPED = "SKIPPED"
    RETIRED = "RETIRED"


class ContractViolationCode(str, enum.Enum):
    # Registration / boot-time
    REGISTRATION_DUPLICATE_NAME = "REGISTRATION_DUPLICATE_NAME"
    REGISTRATION_MISSING_METADATA = "REGISTRATION_MISSING_METADATA"
    REGISTRATION_UNKNOWN_TYPE = "REGISTRATION_UNKNOWN_TYPE"
    REGISTRATION_INVALID_LEVEL = "REGISTRATION_INVALID_LEVEL"
    REGISTRATION_INVALID_NAME = "REGISTRATION_INVALID_NAME"
    REGISTRATION_INVALID_VERSION = "REGISTRATION_INVALID_VERSION"
    REGISTRATION_INVALID_NEEDS = "REGISTRATION_INVALID_NEEDS"
    REGISTRATION_INVALID_BUDGET = "REGISTRATION_INVALID_BUDGET"
    REGISTRATION_INVALID_SIDE_EFFECT = "REGISTRATION_INVALID_SIDE_EFFECT"
    REGISTRATION_DESCRIPTION_TOO_LONG = "REGISTRATION_DESCRIPTION_TOO_LONG"
    REGISTRATION_PROPOSAL_HIGH_NO_APPROVER = "REGISTRATION_PROPOSAL_HIGH_NO_APPROVER"
    # Runtime
    ACTIVATION_FAILED = "ACTIVATION_FAILED"
    INPUT_INVALID = "INPUT_INVALID"
    OUTPUT_INVALID = "OUTPUT_INVALID"
    UNDECLARED_SIDE_EFFECT = "UNDECLARED_SIDE_EFFECT"
    BUDGET_EXCEEDED_TIMEOUT = "BUDGET_EXCEEDED_TIMEOUT"
    BUDGET_EXCEEDED_OOM = "BUDGET_EXCEEDED_OOM"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    CLEANUP_FAILED = "CLEANUP_FAILED"


@dataclasses.dataclass(frozen=True)
class ContractViolation:
    code: ContractViolationCode
    message: str
    neuron_name: str = ""
    phase: Optional[Phase] = None

    def __str__(self) -> str:  # pragma: no cover (utility)
        ph = f" [{self.phase.value}]" if self.phase else ""
        return f"{self.code.value}{ph} neuron='{self.neuron_name}': {self.message}"


# ================================================================================
# Telemetry stub (sostituito da telemetry.py M4.13)
# ================================================================================

_TELEMETRY_BUFFER: List[Dict[str, Any]] = []
_TELEMETRY_LOCK = threading.Lock()


def emit_event(neuron_name: str, event: str, **fields: Any) -> None:
    """Appende un evento lifecycle al buffer in-memory. M4.13 collegherà a mesh_state.jsonl."""
    ev = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
        "neuron": neuron_name,
        "event": event,
        **fields,
    }
    with _TELEMETRY_LOCK:
        _TELEMETRY_BUFFER.append(ev)


def drain_events() -> List[Dict[str, Any]]:
    with _TELEMETRY_LOCK:
        out = list(_TELEMETRY_BUFFER)
        _TELEMETRY_BUFFER.clear()
    return out


def peek_events() -> List[Dict[str, Any]]:
    with _TELEMETRY_LOCK:
        return list(_TELEMETRY_BUFFER)


# ================================================================================
# Neuron Registry (mesh-level, separato dall'OLC)
# ================================================================================

class NeuronRegistry:
    """
    Registry dei neuroni dichiarati nella mesh. M4.7 lo estenderà con
    auto-discovery via decoratore @neuron su import paths. In M4.2
    lo esponiamo con API minime (register/lookup/names/strikes) sufficienti
    per validator + wrap_execute.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._neurons: Dict[str, "Neuron"] = {}
        self._strikes: Dict[str, int] = {}
        self._quarantined: set = set()

    def register(self, neuron: "Neuron") -> List[ContractViolation]:
        """
        Registra un neurone. Ritorna lista di violazioni (vuota = OK).
        Se il nome è già usato da un'altra istanza → DUPLICATE_NAME.
        """
        name = neuron.name
        with self._lock:
            existing = self._neurons.get(name)
            if existing is not None and existing is not neuron:
                return [ContractViolation(
                    code=ContractViolationCode.REGISTRATION_DUPLICATE_NAME,
                    message=f"nome '{name}' già registrato da {type(existing).__name__}",
                    neuron_name=name,
                    phase=Phase.REGISTERED,
                )]
            self._neurons[name] = neuron
            self._strikes.setdefault(name, 0)
        return []

    def lookup(self, name: str) -> Optional["Neuron"]:
        return self._neurons.get(name)

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._neurons.keys())

    def all(self) -> List["Neuron"]:
        with self._lock:
            return list(self._neurons.values())

    def strike(self, name: str, quarantine_threshold: Optional[int] = None) -> Tuple[int, bool]:
        """Incrementa strike counter; ritorna (count, quarantined_now).
        Se quarantine_threshold è None, legge il valore da execution_rules.yaml."""
        if quarantine_threshold is None:
            quarantine_threshold = _ceilings_from_rules().get("quarantine_threshold", DEFAULT_QUARANTINE_THRESHOLD)
        with self._lock:
            self._strikes[name] = self._strikes.get(name, 0) + 1
            count = self._strikes[name]
            quarantined_now = False
            if count >= quarantine_threshold and name not in self._quarantined:
                self._quarantined.add(name)
                quarantined_now = True
        if quarantined_now:
            emit_event(name, "QUARANTINED", strikes=count, threshold=quarantine_threshold)
        return count, quarantined_now

    def is_quarantined(self, name: str) -> bool:
        return name in self._quarantined

    def strikes_of(self, name: str) -> int:
        return self._strikes.get(name, 0)

    def _reset(self) -> None:
        """Solo per testing."""
        with self._lock:
            self._neurons.clear()
            self._strikes.clear()
            self._quarantined.clear()


_REGISTRY = NeuronRegistry()


def registry() -> NeuronRegistry:
    return _REGISTRY


# ================================================================================
# Classe base Neuron
# ================================================================================

class Neuron:
    """
    Classe base per neuroni della mesh.

    Sottoclassi devono impostare (obbligatori):
        name, input_type, output_type, level, needs_served, resource_budget,
        side_effects, description, version

    Opzionali (None/default se omessi): tags, requires, deprecated_in, author,
    requires_human_approver

    Entrambe le forme — subclassing e decoratore `@neuron` — producono una
    Neuron con identici invarianti di contratto.
    """

    # Metadata obbligatori (sovrascritti dalla sottoclasse/decoratore)
    name: str = ""
    input_type: Optional[Type[OLCBase]] = None
    output_type: Optional[Type[OLCBase]] = None
    level: int = 0
    version: str = ""
    needs_served: List[str] = []
    resource_budget: Dict[str, int] = {}
    side_effects: List[str] = []
    description: str = ""

    # Opzionali
    tags: List[str] = []
    requires: List[str] = []
    deprecated_in: Optional[str] = None
    author: str = ""
    requires_human_approver: bool = False

    # Stato lifecycle
    _phase: Phase = Phase.REGISTERED

    def on_init(self) -> None:
        """Hook di attivazione. Override per setup risorse/dipendenze."""
        return None

    def health(self) -> bool:
        """Hook di verifica. Override per controllare dipendenze esterne."""
        return True

    def activation_gate(self, state: Any) -> bool:
        """Ritorna False per skip in questo heartbeat. Default: sempre attivo."""
        return True

    def precondition(self, input_obj: Any) -> List[str]:
        """Lista di violazioni pre-esecuzione, oltre al type-check. Default: []."""
        return []

    def execute(self, input_obj: Any) -> Any:
        """Override obbligatorio."""
        raise NotImplementedError(f"{type(self).__name__}.execute() must be overridden")

    def on_cleanup(self) -> None:
        """Hook di retire. Override per rilascio risorse."""
        return None

    @property
    def phase(self) -> Phase:
        return self._phase

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Neuron name='{self.name}' L{self.level} v{self.version}>"


# ================================================================================
# Decoratore @neuron — funzione → Neuron subclass
# ================================================================================

def neuron(
    *,
    name: str,
    input_type: Type[OLCBase],
    output_type: Type[OLCBase],
    level: int,
    needs_served: List[str],
    resource_budget: Dict[str, Any],
    side_effects: List[str],
    version: str = "1.0.0",
    description: str = "",
    tags: Optional[List[str]] = None,
    requires: Optional[List[str]] = None,
    deprecated_in: Optional[str] = None,
    author: str = "",
    requires_human_approver: bool = False,
):
    """
    Decoratore che trasforma una funzione `f(inp) -> out` in un neurone
    auto-dichiarato. La funzione decorata ritorna un oggetto callable che:
      - espone `.meta` (dict) e `.instance()` per istanziare il Neuron
      - conserva il comportamento originale di chiamata (`echo(frame)` funziona)

    Esempio:
        @neuron(name="...", input_type=..., ...)
        def f(inp): ...

        assert validate_contract(f.instance()) == []
    """
    _tags = list(tags or [])
    _requires = list(requires or [])

    def decorator(fn: Callable):
        cls_name = "".join(part.capitalize() for part in re.split(r"[.\-_]", name) if part)
        cls_name = (cls_name or "Neuron") + "Neuron"

        # Sintetizza una sottoclasse Neuron con metadata come class attrs
        attrs = {
            "name": name,
            "input_type": input_type,
            "output_type": output_type,
            "level": level,
            "version": version,
            "needs_served": list(needs_served),
            "resource_budget": dict(resource_budget),
            "side_effects": list(side_effects),
            "description": description,
            "tags": _tags,
            "requires": _requires,
            "deprecated_in": deprecated_in,
            "author": author,
            "requires_human_approver": requires_human_approver,
            "execute": lambda self, inp, _fn=fn: _fn(inp),
            "__doc__": fn.__doc__ or description,
        }
        Synthesized = type(cls_name, (Neuron,), attrs)

        def _instance() -> Neuron:
            return Synthesized()

        # callable wrapper che preserva la funzione originale ma espone helpers
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.NeuronClass = Synthesized  # type: ignore[attr-defined]
        wrapper.instance = _instance  # type: ignore[attr-defined]
        wrapper.meta = {  # type: ignore[attr-defined]
            "name": name,
            "level": level,
            "version": version,
            "needs_served": list(needs_served),
            "side_effects": list(side_effects),
        }
        return wrapper

    return decorator


# ================================================================================
# Validazione statica (AC-2, AC-3, AC-4)
# ================================================================================

def _check_name(n: Optional[str]) -> List[ContractViolation]:
    if not n:
        return [ContractViolation(
            ContractViolationCode.REGISTRATION_MISSING_METADATA,
            "name mancante", neuron_name="", phase=Phase.REGISTERED,
        )]
    if not NAME_REGEX.match(n):
        return [ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_NAME,
            f"name='{n}' non soddisfa regex {NAME_REGEX.pattern}", neuron_name=n,
            phase=Phase.REGISTERED,
        )]
    return []


def _check_version(v: Optional[str], nname: str) -> List[ContractViolation]:
    if not v:
        return [ContractViolation(
            ContractViolationCode.REGISTRATION_MISSING_METADATA,
            "version mancante", neuron_name=nname, phase=Phase.REGISTERED,
        )]
    if not SEMVER_REGEX.match(v):
        return [ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_VERSION,
            f"version='{v}' non è SemVer", neuron_name=nname, phase=Phase.REGISTERED,
        )]
    return []


def _check_level(lvl: int, nname: str) -> List[ContractViolation]:
    if lvl not in LEVELS:
        return [ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_LEVEL,
            f"level={lvl} deve essere in {LEVELS}", neuron_name=nname, phase=Phase.REGISTERED,
        )]
    return []


def _check_needs(needs: List[str], nname: str) -> List[ContractViolation]:
    out: List[ContractViolation] = []
    if not isinstance(needs, (list, tuple)) or len(needs) == 0:
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_NEEDS,
            f"needs_served deve essere lista non vuota, trovato {needs!r}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
        return out
    catalog = set(NEEDS_CATALOG)
    bad = [n for n in needs if n not in catalog]
    if bad:
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_NEEDS,
            f"needs fuori dal catalogo {NEEDS_CATALOG}: {bad}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
    return out


def _check_budget(b: Dict[str, Any], nname: str,
                  max_ms_ceiling: Optional[int] = None,
                  max_mb_ceiling: Optional[int] = None) -> List[ContractViolation]:
    # Risoluzione dinamica dei ceiling da execution_rules.yaml (M4.4)
    if max_ms_ceiling is None or max_mb_ceiling is None:
        _cl = _ceilings_from_rules()
        if max_ms_ceiling is None:
            max_ms_ceiling = _cl["max_ms"]
        if max_mb_ceiling is None:
            max_mb_ceiling = _cl["max_mb"]
    max_retries_ceiling = _ceilings_from_rules().get("max_retries", DEFAULT_MAX_RETRIES_CEILING)
    pb_min = _ceilings_from_rules().get("priority_boost_min", DEFAULT_PRIORITY_BOOST_RANGE[0])
    pb_max = _ceilings_from_rules().get("priority_boost_max", DEFAULT_PRIORITY_BOOST_RANGE[1])
    out: List[ContractViolation] = []
    if not isinstance(b, dict):
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_BUDGET,
            f"resource_budget deve essere dict, trovato {type(b).__name__}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
        return out
    for key in ("max_ms", "max_mb"):
        if key not in b:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_MISSING_METADATA,
                f"resource_budget.{key} mancante",
                neuron_name=nname, phase=Phase.REGISTERED,
            ))
    mx_ms = b.get("max_ms", 0)
    mx_mb = b.get("max_mb", 0)
    if not isinstance(mx_ms, int) or mx_ms <= 0:
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_BUDGET,
            f"max_ms={mx_ms} deve essere int > 0",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
    if not isinstance(mx_mb, int) or mx_mb <= 0:
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_BUDGET,
            f"max_mb={mx_mb} deve essere int > 0",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
    if isinstance(mx_ms, int) and mx_ms > max_ms_ceiling:
        # clamp silently (SPEC §7) — non è violazione, solo log
        _log.warning("neuron '%s' max_ms=%s → clamp a %s", nname, mx_ms, max_ms_ceiling)
        b["max_ms"] = max_ms_ceiling
    if isinstance(mx_mb, int) and mx_mb > max_mb_ceiling:
        _log.warning("neuron '%s' max_mb=%s → clamp a %s", nname, mx_mb, max_mb_ceiling)
        b["max_mb"] = max_mb_ceiling
    retries = b.get("max_retries", 0)
    if not (isinstance(retries, int) and 0 <= retries <= max_retries_ceiling):
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_BUDGET,
            f"max_retries={retries} deve essere int in 0..{max_retries_ceiling}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
    pboost = b.get("priority_boost", 0)
    if not (isinstance(pboost, int) and pb_min <= pboost <= pb_max):
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_BUDGET,
            f"priority_boost={pboost} fuori range ({pb_min}..{pb_max})",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
    return out


def _parse_side_effect(s: str) -> Tuple[str, str]:
    m = _SIDE_EFFECT_PATTERN.match(s)
    if not m:
        return ("", "")
    return (m.group(1), m.group(2))


def _check_side_effects(sides: List[str], nname: str,
                        requires_human_approver: bool) -> List[ContractViolation]:
    out: List[ContractViolation] = []
    if not isinstance(sides, list):
        out.append(ContractViolation(
            ContractViolationCode.REGISTRATION_INVALID_SIDE_EFFECT,
            f"side_effects deve essere lista, trovato {type(sides).__name__}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))
        return out
    for s in sides:
        if not isinstance(s, str) or not s:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_INVALID_SIDE_EFFECT,
                f"side_effect non-stringa o vuoto: {s!r}",
                neuron_name=nname, phase=Phase.REGISTERED,
            ))
            continue
        kind, arg = _parse_side_effect(s)
        if kind not in SIDE_EFFECT_KINDS:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_INVALID_SIDE_EFFECT,
                f"side_effect '{s}': kind '{kind}' non in {sorted(SIDE_EFFECT_KINDS)}",
                neuron_name=nname, phase=Phase.REGISTERED,
            ))
            continue
        if not arg:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_INVALID_SIDE_EFFECT,
                f"side_effect '{s}': arg mancante dopo ':'",
                neuron_name=nname, phase=Phase.REGISTERED,
            ))
            continue
        if kind == "proposal":
            if arg not in _RISK_LEVELS:
                out.append(ContractViolation(
                    ContractViolationCode.REGISTRATION_INVALID_SIDE_EFFECT,
                    f"proposal:{arg} — risk level deve essere in {sorted(_RISK_LEVELS)}",
                    neuron_name=nname, phase=Phase.REGISTERED,
                ))
            elif arg == "high" and not requires_human_approver:
                out.append(ContractViolation(
                    ContractViolationCode.REGISTRATION_PROPOSAL_HIGH_NO_APPROVER,
                    "proposal:high richiede requires_human_approver=True",
                    neuron_name=nname, phase=Phase.REGISTERED,
                ))
    return out


def check_types_in_olc(obj: Neuron) -> List[ContractViolation]:
    """AC-4: verifica che input_type e output_type siano registrati nell'OLC registry."""
    out: List[ContractViolation] = []
    for attr_name in ("input_type", "output_type"):
        t = getattr(obj, attr_name, None)
        if t is None:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_MISSING_METADATA,
                f"{attr_name} mancante", neuron_name=obj.name, phase=Phase.REGISTERED,
            ))
            continue
        if not isinstance(t, type) or not issubclass(t, OLCBase):
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_UNKNOWN_TYPE,
                f"{attr_name}={t!r} non è una sottoclasse di OLCBase",
                neuron_name=obj.name, phase=Phase.REGISTERED,
            ))
            continue
        olc_name = getattr(t, "_OLC_NAME", None)
        resolved = olc_lookup(olc_name) if olc_name else None
        if resolved is not t:
            out.append(ContractViolation(
                ContractViolationCode.REGISTRATION_UNKNOWN_TYPE,
                f"{attr_name}={t.__name__} non registrato nell'OLC (_OLC_NAME='{olc_name}')",
                neuron_name=obj.name, phase=Phase.REGISTERED,
            ))
    return out


def validate_contract(obj: Neuron) -> List[ContractViolation]:
    """
    Validazione statica completa del contratto (AC-2, AC-3).
    Ritorna lista di ContractViolation (vuota = contratto valido).

    Eseguita al boot-time; non esegue `execute()` né side effect detection runtime.
    """
    violations: List[ContractViolation] = []

    # Sezione 1: metadati presenza base
    violations.extend(_check_name(obj.name))
    nname = obj.name or "<no-name>"

    # description
    if not getattr(obj, "description", None):
        violations.append(ContractViolation(
            ContractViolationCode.REGISTRATION_MISSING_METADATA,
            "description mancante", neuron_name=nname, phase=Phase.REGISTERED,
        ))
    elif isinstance(obj.description, str) and len(obj.description) > MAX_DESCRIPTION_CHARS:
        violations.append(ContractViolation(
            ContractViolationCode.REGISTRATION_DESCRIPTION_TOO_LONG,
            f"description lunga {len(obj.description)} chars, max {MAX_DESCRIPTION_CHARS}",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))

    # version
    violations.extend(_check_version(obj.version, nname))

    # level
    violations.extend(_check_level(obj.level, nname))

    # needs
    violations.extend(_check_needs(list(obj.needs_served or []), nname))

    # budget (clamp silenzioso su ceiling — SPEC §7 richiede modifica in-place)
    if not isinstance(obj.resource_budget, dict):
        obj.resource_budget = {}
    violations.extend(_check_budget(obj.resource_budget, nname))

    # side effects + proposal:high check
    violations.extend(_check_side_effects(
        list(obj.side_effects or []), nname,
        requires_human_approver=bool(getattr(obj, "requires_human_approver", False)),
    ))

    # tipi OLC registrati
    violations.extend(check_types_in_olc(obj))

    # execute() deve essere override
    if type(obj).execute is Neuron.execute:
        violations.append(ContractViolation(
            ContractViolationCode.REGISTRATION_MISSING_METADATA,
            "execute() non overridden",
            neuron_name=nname, phase=Phase.REGISTERED,
        ))

    return violations


def validate_many(neurons: List[Neuron]) -> Dict[str, List[ContractViolation]]:
    """Validazione batch con rilevamento duplicati nome. AC-9."""
    per: Dict[str, List[ContractViolation]] = {}
    seen: Dict[str, Neuron] = {}
    for n in neurons:
        v = validate_contract(n)
        if n.name:
            if n.name in seen and seen[n.name] is not n:
                v.append(ContractViolation(
                    ContractViolationCode.REGISTRATION_DUPLICATE_NAME,
                    f"duplicate name '{n.name}' nel batch",
                    neuron_name=n.name, phase=Phase.REGISTERED,
                ))
            else:
                seen[n.name] = n
        per[n.name or f"<unnamed:{id(n)}>"] = v
    return per


# ================================================================================
# Runtime hook: wrap_execute (AC-5)
# ================================================================================

def activate(obj: Neuron) -> List[ContractViolation]:
    """
    Esegue on_init() e health(). Ritorna violazioni di attivazione.
    Aggiorna obj._phase a ACTIVATED se OK.
    """
    try:
        obj.on_init()
    except Exception as e:
        emit_event(obj.name, "ACTIVATION_FAILED", error=str(e), trace=traceback.format_exc(limit=3))
        return [ContractViolation(
            ContractViolationCode.ACTIVATION_FAILED,
            f"on_init() raised: {e}", neuron_name=obj.name, phase=Phase.ACTIVATED,
        )]
    try:
        ok = bool(obj.health())
    except Exception as e:
        emit_event(obj.name, "ACTIVATION_FAILED", error=f"health() raised: {e}")
        return [ContractViolation(
            ContractViolationCode.ACTIVATION_FAILED,
            f"health() raised: {e}", neuron_name=obj.name, phase=Phase.ACTIVATED,
        )]
    if not ok:
        emit_event(obj.name, "ACTIVATION_FAILED", reason="health returned False")
        return [ContractViolation(
            ContractViolationCode.ACTIVATION_FAILED,
            "health() returned False", neuron_name=obj.name, phase=Phase.ACTIVATED,
        )]
    obj._phase = Phase.ACTIVATED
    emit_event(obj.name, "ACTIVATED")
    return []


def wrap_execute(obj: Neuron) -> Callable[[Any], Tuple[Any, List[ContractViolation]]]:
    """
    AC-5: produce un callable `run(input) → (output | None, violations)` che:
      - valida input via obj.input_type().validate() (se input è un'istanza) o type-check
      - chiama execute() con hard timeout via ThreadPoolExecutor
      - valida output via obj.output_type.validate()
      - emette eventi lifecycle

    Nota: il thread non viene killato (Python GIL), ma il caller riceve
    TIMEOUT violation e il thread continua in background — M4.6 aggiungerà
    preemption via process sandbox per neuroni non-puri.
    """
    max_ms = int(obj.resource_budget.get("max_ms", DEFAULT_MAX_MS_CEILING))
    max_retries = int(obj.resource_budget.get("max_retries", 0))
    timeout_s = max_ms / 1000.0

    def _run(input_obj: Any) -> Tuple[Any, List[ContractViolation]]:
        violations: List[ContractViolation] = []
        # 1. Input type-check
        if not isinstance(input_obj, obj.input_type):
            violations.append(ContractViolation(
                ContractViolationCode.INPUT_INVALID,
                f"atteso {obj.input_type.__name__}, trovato {type(input_obj).__name__}",
                neuron_name=obj.name, phase=Phase.EXECUTING,
            ))
            return (None, violations)
        inp_violations = input_obj.validate() if hasattr(input_obj, "validate") else []
        if inp_violations:
            violations.append(ContractViolation(
                ContractViolationCode.INPUT_INVALID,
                f"validate() fallito: {inp_violations}",
                neuron_name=obj.name, phase=Phase.EXECUTING,
            ))
            return (None, violations)
        # 2. Precondition
        pre = obj.precondition(input_obj)
        if pre:
            violations.append(ContractViolation(
                ContractViolationCode.PRECONDITION_FAILED,
                f"precondition: {pre}",
                neuron_name=obj.name, phase=Phase.EXECUTING,
            ))
            return (None, violations)

        # 3. Execute with timeout
        obj._phase = Phase.EXECUTING
        emit_event(obj.name, "EXECUTING", timeout_s=timeout_s)

        attempt = 0
        result: Any = None
        last_error: Optional[str] = None
        while True:
            start = time.perf_counter()
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(obj.execute, input_obj)
                    result = future.result(timeout=timeout_s)
                elapsed_ms = (time.perf_counter() - start) * 1000
                break
            except concurrent.futures.TimeoutError:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = f"timeout {max_ms}ms"
                if attempt < max_retries:
                    attempt += 1
                    emit_event(obj.name, "TIMEOUT_RETRY", attempt=attempt, elapsed_ms=elapsed_ms)
                    continue
                violations.append(ContractViolation(
                    ContractViolationCode.BUDGET_EXCEEDED_TIMEOUT,
                    f"execute() > {max_ms}ms (retries={attempt})",
                    neuron_name=obj.name, phase=Phase.ERRORED,
                ))
                obj._phase = Phase.ERRORED
                emit_event(obj.name, "ERRORED", reason="timeout", elapsed_ms=elapsed_ms, retries=attempt)
                return (None, violations)
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = str(e)
                if attempt < max_retries:
                    attempt += 1
                    emit_event(obj.name, "ERROR_RETRY", attempt=attempt, error=last_error)
                    continue
                obj._phase = Phase.ERRORED
                emit_event(obj.name, "ERRORED", error=last_error, elapsed_ms=elapsed_ms,
                           trace=traceback.format_exc(limit=3))
                # Errori non mappati come violazioni strutturate, ma registriamo
                # una INPUT_INVALID generica se la causa è AssertionError sul validate,
                # altrimenti usiamo un marker come nota runtime (M4.8 adapter la userà).
                violations.append(ContractViolation(
                    ContractViolationCode.PRECONDITION_FAILED,
                    f"execute() raised: {last_error}",
                    neuron_name=obj.name, phase=Phase.ERRORED,
                ))
                return (None, violations)

        # 4. Output type-check
        if not isinstance(result, obj.output_type):
            violations.append(ContractViolation(
                ContractViolationCode.OUTPUT_INVALID,
                f"atteso {obj.output_type.__name__}, restituito {type(result).__name__}",
                neuron_name=obj.name, phase=Phase.COMPLETED,
            ))
            obj._phase = Phase.ERRORED
            emit_event(obj.name, "ERRORED", reason="output_type_mismatch", elapsed_ms=elapsed_ms)
            return (None, violations)
        out_violations = result.validate() if hasattr(result, "validate") else []
        if out_violations:
            violations.append(ContractViolation(
                ContractViolationCode.OUTPUT_INVALID,
                f"output.validate() fallito: {out_violations}",
                neuron_name=obj.name, phase=Phase.COMPLETED,
            ))
            obj._phase = Phase.ERRORED
            emit_event(obj.name, "ERRORED", reason="output_validate_failed", elapsed_ms=elapsed_ms)
            return (None, violations)

        # 5. Completed
        obj._phase = Phase.COMPLETED
        emit_event(obj.name, "COMPLETED", latency_ms=round(elapsed_ms, 3), retries=attempt)
        return (result, violations)

    return _run


def retire(obj: Neuron) -> List[ContractViolation]:
    """Esegue on_cleanup(). Ritorna violazioni (vuote = OK)."""
    try:
        obj.on_cleanup()
        obj._phase = Phase.RETIRED
        emit_event(obj.name, "RETIRED")
        return []
    except Exception as e:
        emit_event(obj.name, "CLEANUP_FAILED", error=str(e))
        return [ContractViolation(
            ContractViolationCode.CLEANUP_FAILED,
            f"on_cleanup() raised: {e}", neuron_name=obj.name, phase=Phase.RETIRED,
        )]


# ================================================================================
# __main__ demo runnable (AC-10)
# ================================================================================

def _demo() -> int:  # pragma: no cover
    """Demo runnable: crea un neurone echo, valida, esegue, stampa eventi."""
    from cortex.mesh.olc import SensoryFrame, InterpretationFrame

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    @neuron(
        name="neuron.demo.echo",
        input_type=SensoryFrame,
        output_type=InterpretationFrame,
        level=2,
        needs_served=["integration"],
        resource_budget={"max_ms": 500, "max_mb": 32, "max_retries": 0},
        side_effects=[],
        version="1.0.0",
        description="Neurone demo: echo + confidence=1.0",
    )
    def echo(inp: SensoryFrame) -> InterpretationFrame:
        return InterpretationFrame(intent="echo", confidence=1.0, source=inp.source,
                                   entities=list(inp.payload.keys()))

    n = echo.instance()
    print("=== M4.2 — demo contract.py ===")
    print(f"Neurone: {n!r}")
    v = validate_contract(n)
    print(f"validate_contract → {len(v)} violazioni")
    assert v == [], v
    registry().register(n)

    act_v = activate(n)
    assert act_v == [], act_v

    runner = wrap_execute(n)
    out, violations = runner(SensoryFrame(source="demo", payload={"hello": "world"}))
    print(f"output: {out}")
    print(f"violations runtime: {violations}")

    # Eventi
    events = drain_events()
    print(f"telemetry events: {len(events)}")
    for e in events:
        print("  ", e)

    retire(n)
    print("OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_demo())
