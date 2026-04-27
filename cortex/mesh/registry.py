"""
SPEACE Cortex Mesh — Neuron Auto-Discovery Registry (M4.7)

Questo modulo estende il `NeuronRegistry` statico di `contract.py` con un meccanismo
di **auto-discovery**: data una lista di package Python, walk ricorsivo dei moduli,
import, rilevamento dei wrapper `@neuron`-decorati, istanziazione, validazione del
contratto (`validate_contract`), e registrazione nel singleton `_REGISTRY`.

Milestone: M4.7 (PROP-CORTEX-NEURAL-MESH-M4)
Riferimento canonico: cortex/mesh/SPEC_NEURON_CONTRACT.md §9 (Registration)

Filosofia:
  - **Safe by default**: una violation su un singolo neurone non interrompe la discovery
    degli altri. Errori di import sono catturati e riportati come "skipped" con reason.
  - **Determinismo**: l'ordine di registrazione segue walk_packages, quindi l'ordine dei
    sottopacchetti è alfabetico. Due chiamate consecutive su stesso input producono
    identico `DiscoveryReport`.
  - **Idempotenza**: ri-chiamata sullo stesso package non produce duplicati, perché
    `NeuronRegistry.register()` considera lo stesso oggetto Neuron come no-op.
    Se invece un secondo wrapper `@neuron(name="…")` usa lo stesso `name` con
    classe diversa, otteniamo REGISTRATION_DUPLICATE_NAME (comportamento atteso).

Esempio d'uso:

    from cortex.mesh.registry import discover_neurons

    report = discover_neurons(["cortex.comparti", "cortex.mesh._builtin_neurons"])
    print(f"registered: {len(report.registered)}")
    for name, vs in report.violations.items():
        print(f"  {name}: {[v.code.value for v in vs]}")
    for mod, reason in report.skipped:
        print(f"  skipped {mod}: {reason}")

Entry point CLI (smoke):

    python -m cortex.mesh.registry cortex.comparti
"""

from __future__ import annotations

import dataclasses
import importlib
import logging
import pkgutil
import sys
import traceback
from types import ModuleType
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from cortex.mesh.contract import (
    ContractViolation,
    Neuron,
    NeuronRegistry,
    registry as _default_registry,
    validate_contract,
)

_log = logging.getLogger("speace.mesh.registry")


# ================================================================================
# Tipi pubblici
# ================================================================================


@dataclasses.dataclass
class DiscoveryReport:
    """
    Esito di `discover_neurons()`.

    Campi:
        registered:  nomi dei neuroni effettivamente registrati con contract valido.
        violations:  {nome_neurone: [ContractViolation]} per chi ha fallito la
                     validazione o la registrazione. Questi NON sono in `registered`.
        skipped:     [(dotted_module, reason)] per moduli che non è stato possibile
                     importare (ImportError, SyntaxError, dipendenze mancanti).
        scanned_modules: elenco (ordinato) dei moduli effettivamente visitati.
        packages:    elenco dei package radice richiesti dall'utente.
    """

    registered: List[str] = dataclasses.field(default_factory=list)
    violations: Dict[str, List[ContractViolation]] = dataclasses.field(default_factory=dict)
    skipped: List[Tuple[str, str]] = dataclasses.field(default_factory=list)
    scanned_modules: List[str] = dataclasses.field(default_factory=list)
    packages: List[str] = dataclasses.field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True se nessun neurone ha sollevato violations. Moduli skipped non
        invalidano il report: sono "soft failures" isolate."""
        return not self.violations

    def summary(self) -> str:
        parts = [
            f"packages={self.packages}",
            f"scanned={len(self.scanned_modules)}",
            f"registered={len(self.registered)}",
            f"violations={len(self.violations)}",
            f"skipped={len(self.skipped)}",
        ]
        return "DiscoveryReport(" + ", ".join(parts) + ")"

    def __str__(self) -> str:  # pragma: no cover (utility)
        return self.summary()


# ================================================================================
# Detection helpers
# ================================================================================


def _is_neuron_wrapper(obj: object) -> bool:
    """
    True se `obj` è un wrapper prodotto dal decoratore `@neuron(...)` (vedi
    `contract.neuron`): callable con attributi `NeuronClass`, `instance`, `meta`.
    """
    if not callable(obj):
        return False
    return (
        hasattr(obj, "NeuronClass")
        and hasattr(obj, "instance")
        and hasattr(obj, "meta")
    )


def _is_neuron_subclass(obj: object) -> bool:
    """True se `obj` è una sottoclasse concreta di `Neuron` (non la classe base stessa)."""
    try:
        return isinstance(obj, type) and issubclass(obj, Neuron) and obj is not Neuron
    except TypeError:
        return False


def _resolve_neuron_instance(obj: object) -> Optional[Neuron]:
    """
    Estrae una `Neuron` istanziata da un oggetto "discovery-eligible":
      - wrapper @neuron → `obj.instance()`
      - sottoclasse Neuron → `obj()` (costruttore no-args)

    Ritorna None se non estraibile. Non solleva: eccezioni in costruttore sono
    catturate a monte dal caller.
    """
    if _is_neuron_wrapper(obj):
        try:
            inst = obj.instance()  # type: ignore[attr-defined]
            return inst if isinstance(inst, Neuron) else None
        except Exception:  # pragma: no cover (difensivo)
            return None
    if _is_neuron_subclass(obj):
        try:
            inst = obj()  # type: ignore[call-arg]
            return inst if isinstance(inst, Neuron) else None
        except Exception:  # pragma: no cover (difensivo)
            return None
    return None


# ================================================================================
# Module walk
# ================================================================================


def _iter_modules(package_name: str) -> Iterable[str]:
    """
    Yield dotted names di tutti i submoduli (ricorsivo) di `package_name`,
    incluso il package stesso. Se l'import fallisce o non è un package,
    yield solo il nome stesso.

    Implementazione:
      1. walk_packages sul filesystem path del package (caso standard).
      2. Merge con sys.modules — include submoduli già caricati che non si
         trovano sul filesystem (es. package in-memory dei test, plugin
         lazy-loaded, namespace packages non ancora walk-abili).

    L'ordine finale è deterministico (alfabetico) e senza duplicati.
    """
    seen: set = set()

    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        yield package_name
        return

    seen.add(package_name)
    yield package_name

    path = getattr(pkg, "__path__", None)

    # Fase 1: walk_packages sul filesystem (se possibile)
    if path:
        try:
            for mod_info in pkgutil.walk_packages(path, prefix=package_name + "."):
                if mod_info.name not in seen:
                    seen.add(mod_info.name)
                    yield mod_info.name
        except Exception:  # pragma: no cover (difensivo)
            _log.debug("walk_packages failed for %s", package_name, exc_info=True)

    # Fase 2: fallback su sys.modules per moduli già caricati ma non walk-abili.
    # Utile per: (a) test con moduli iniettati, (b) namespace packages,
    # (c) plugin registrati via importlib al volo.
    prefix = package_name + "."
    for loaded_name in sorted(sys.modules.keys()):
        if loaded_name.startswith(prefix) and loaded_name not in seen:
            seen.add(loaded_name)
            yield loaded_name


def _safe_import(dotted: str) -> Tuple[Optional[ModuleType], Optional[str]]:
    """
    Importa `dotted` catturando qualsiasi eccezione. Ritorna (module, None) se OK,
    (None, reason) altrimenti. Reason è una stringa compatta (prima riga exc).
    """
    try:
        mod = importlib.import_module(dotted)
        return mod, None
    except Exception as exc:
        first_line = (str(exc) or exc.__class__.__name__).splitlines()[0][:200]
        reason = f"{exc.__class__.__name__}: {first_line}"
        _log.debug("auto-discovery: skip %s (%s)\n%s", dotted, reason, traceback.format_exc())
        return None, reason


# ================================================================================
# API pubblica
# ================================================================================


def discover_neurons(
    packages: Union[str, Sequence[str]],
    *,
    registry: Optional[NeuronRegistry] = None,
    validate: bool = True,
    predicate: Optional[Callable[[object], bool]] = None,
    skip_existing: bool = True,
) -> DiscoveryReport:
    """
    Walk dei `packages`, discovery dei neuroni dichiarati (via `@neuron` o subclass
    di `Neuron`), istanziazione, validazione contratto, registrazione.

    Args:
        packages:       singolo dotted name o sequenza. Es. "cortex.comparti" o
                        ["cortex.comparti", "cortex.mesh._builtin_neurons"].
        registry:       `NeuronRegistry` su cui registrare (default: singleton di
                        `contract.registry()`).
        validate:       se True (default) esegue `validate_contract(instance)` prima
                        di registrare; su violation l'istanza NON viene registrata.
        predicate:      filtro opzionale `(obj) -> bool` applicato DOPO i controlli
                        standard (`_is_neuron_wrapper` / `_is_neuron_subclass`) per
                        restringere ulteriormente la discovery (es. solo un namespace).
        skip_existing:  se True (default) salta silenziosamente i neuroni il cui nome
                        è già presente nel registry (idempotenza cross-call). Se False,
                        ogni nome già presente produce REGISTRATION_DUPLICATE_NAME e
                        finisce in `violations` (utile per test di verifica unicità).

    Returns:
        DiscoveryReport con registered, violations, skipped, scanned_modules.

    Contratto di robustezza:
      - ImportError su un modulo: registrato come `skipped`, gli altri moduli
        continuano.
      - Neurone con violation: registrato in `violations`, gli altri continuano.
      - Nome duplicato: default `skip_existing=True` → silenzioso no-op; con
        `skip_existing=False` → REGISTRATION_DUPLICATE_NAME in `violations`.

    Idempotenza:
      Con il default `skip_existing=True`, ri-chiamare `discover_neurons` sullo
      stesso package in sequenza non produce né duplicate, né violazioni, né
      nuove registrazioni. Questo è lo use case primario del boot mesh (M4.14).
    """
    reg = registry or _default_registry()
    pkg_list = [packages] if isinstance(packages, str) else list(packages)

    report = DiscoveryReport(packages=list(pkg_list))
    seen_modules: set = set()
    seen_objects: set = set()  # id() dei wrapper già processati (evita duplicati cross-module)

    for pkg_name in pkg_list:
        for dotted in _iter_modules(pkg_name):
            if dotted in seen_modules:
                continue
            seen_modules.add(dotted)

            mod, reason = _safe_import(dotted)
            if mod is None:
                report.skipped.append((dotted, reason or "unknown-import-error"))
                continue

            report.scanned_modules.append(dotted)

            # Itera gli attributi pubblici del modulo.
            # Evitiamo `vars(mod)` modificato durante iter: facciamo snapshot.
            try:
                attrs = list(vars(mod).items())
            except Exception as exc:  # pragma: no cover (difensivo)
                report.skipped.append((dotted, f"vars-error: {exc}"))
                continue

            for attr_name, attr in attrs:
                if attr_name.startswith("_"):
                    continue
                # Solo oggetti definiti "qui dentro" o wrapper @neuron.
                # Un wrapper @neuron riesportato ha comunque `NeuronClass` proprio.
                if not (_is_neuron_wrapper(attr) or _is_neuron_subclass(attr)):
                    continue
                if predicate is not None and not predicate(attr):
                    continue

                key = id(attr)
                if key in seen_objects:
                    continue
                seen_objects.add(key)

                instance = _resolve_neuron_instance(attr)
                if instance is None:
                    # Non fatale: l'oggetto "sembrava" un neurone ma non lo è davvero.
                    continue

                name = getattr(instance, "name", None) or f"<{dotted}.{attr_name}>"

                # Idempotenza: se `skip_existing`, saltiamo nomi già registrati
                # senza generare ContractViolation. Questo previene
                # REGISTRATION_DUPLICATE_NAME spurio dopo ri-boot.
                if skip_existing and reg.lookup(name) is not None:
                    continue

                # Validazione statica opzionale
                if validate:
                    violations = validate_contract(instance)
                    if violations:
                        report.violations.setdefault(name, []).extend(violations)
                        continue

                # Registrazione
                reg_violations = reg.register(instance)
                if reg_violations:
                    report.violations.setdefault(name, []).extend(reg_violations)
                    continue

                report.registered.append(name)

    # Determinismo: ordina registered. walk_packages è già alfabetico ma preservare
    # ordine deterministico è utile per snapshot test.
    report.registered.sort()
    report.scanned_modules.sort()
    report.skipped.sort()

    _log.info(
        "auto-discovery complete: %s",
        report.summary(),
    )
    return report


def require_registered(names: Sequence[str], *, registry: Optional[NeuronRegistry] = None) -> List[str]:
    """
    Utility: verifica che la lista `names` sia presente nel registry. Ritorna
    la lista dei nomi MANCANTI (vuota = tutti presenti). Utile nei test di
    boot per asserire "i 30+ neuroni dei comparti sono stati discovered".
    """
    reg = registry or _default_registry()
    present = set(reg.names())
    return [n for n in names if n not in present]


# ================================================================================
# CLI smoke / debug
# ================================================================================


def _cli(argv: Optional[List[str]] = None) -> int:
    """
    Entry point CLI:
        python -m cortex.mesh.registry <pkg> [<pkg> ...]

    Stampa un riepilogo human-readable e ritorna exit code:
        0 = tutti i neuroni discovered sono validi
        2 = alcuni neuroni hanno violations
        (moduli skipped NON fanno fallire il CLI: sono soft-failures)
    """
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: python -m cortex.mesh.registry <package> [<package> ...]", file=sys.stderr)
        return 64  # EX_USAGE

    # Logging amichevole per CLI
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    report = discover_neurons(args)
    print(report.summary())
    if report.registered:
        print(f"  registered ({len(report.registered)}):")
        for n in report.registered:
            print(f"    - {n}")
    if report.violations:
        print(f"  violations ({len(report.violations)}):")
        for n, vs in sorted(report.violations.items()):
            print(f"    - {n}:")
            for v in vs:
                print(f"        · {v.code.value}: {v.message}")
    if report.skipped:
        print(f"  skipped ({len(report.skipped)}):")
        for mod, reason in report.skipped:
            print(f"    - {mod}: {reason}")

    return 0 if report.ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
