"""
SPEACE Cortex Mesh — OLC (Organism Language Contract) — Base

Definisce la base per i tipi scambiabili fra neuroni della mesh.

Un tipo OLC è:
  - `@dataclass(frozen=True)` (o equivalente) con soli primitivi o altri tipi OLC
  - ha attributi di classe `_OLC_NAME` (univoco) e `_OLC_VERSION` (semver)
  - implementa `validate()` (lista di violazioni, vuota = OK)
  - implementa `to_dict()` / `from_dict()` simmetrici, senza perdita
  - implementa `is_compatible_with(other_cls)` per subtyping strutturale

Milestone: M4.3 (PROP-CORTEX-NEURAL-MESH-M4)
Stato: seed MVP — 12 tipi fondamentali in `types.py`, pronti per M4.2 (validator).

Riferimenti:
  - SPEC_NEURON_CONTRACT.md §2 (Tipi)
  - SPEC_NEURON_CONTRACT.md §9.3 (Bridge StateBus ↔ OLC via adapter mesh/neurons/)
"""

from __future__ import annotations
import dataclasses
import datetime
from typing import Any, ClassVar, Dict, List, Type

OLC_CONTRACT_VERSION = "1.0"

# Enumeration canonica dei bisogni (sincronizzata con epigenome.mesh.needs.weights, §6.2).
NEEDS_CATALOG: tuple = (
    "survival",
    "expansion",
    "self_improvement",
    "integration",
    "harmony",
)


class OLCValidationError(ValueError):
    """Raised when a type fails its structural validation at construction time."""


class OLCBase:
    """
    Base class for OLC types.

    Subclass requirements:
      - Decorate with @dataclass(frozen=True)
      - Define class attrs _OLC_NAME (str, univoco) and _OLC_VERSION (str semver)
      - Fields must be primitives (str, int, float, bool, None, list, tuple, dict, ISO-8601 str)
        or other OLCBase subclasses.

    `validate()` returns a list[str] of human-readable violations; empty list means OK.
    The default implementation checks that all declared fields are present and of a
    plausible type; subclasses can extend it for domain-specific constraints.
    """

    _OLC_NAME: ClassVar[str] = "olc.base"
    _OLC_VERSION: ClassVar[str] = OLC_CONTRACT_VERSION

    # ----- structural identity ----------------------------------------------------

    @classmethod
    def olc_name(cls) -> str:
        return cls._OLC_NAME

    @classmethod
    def olc_version(cls) -> str:
        return cls._OLC_VERSION

    @classmethod
    def required_fields(cls) -> List[str]:
        """Campi obbligatori: ogni dataclass field senza default / default_factory."""
        out = []
        if not dataclasses.is_dataclass(cls):
            return out
        for f in dataclasses.fields(cls):
            if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:  # type: ignore[misc]
                out.append(f.name)
        return out

    @classmethod
    def field_types(cls) -> Dict[str, Any]:
        if not dataclasses.is_dataclass(cls):
            return {}
        return {f.name: f.type for f in dataclasses.fields(cls)}

    # ----- validation -------------------------------------------------------------

    def validate(self) -> List[str]:
        """
        Validazione strutturale di default.

        Controlla:
          - il tipo è un dataclass
          - ogni required field è presente e non None (eccetto bool/0.0 che sono validi)
          - liste/dict sono rispettivamente list/dict (non None)
        """
        violations: List[str] = []
        if not dataclasses.is_dataclass(self):
            violations.append(f"{type(self).__name__}: non è un dataclass")
            return violations

        for fname in self.required_fields():
            val = getattr(self, fname, None)
            if val is None:
                violations.append(f"{type(self).__name__}.{fname}: required, trovato None")
        # lint: list/dict/tuple non None se annotati tali
        for f in dataclasses.fields(self):
            val = getattr(self, f.name, None)
            ann = str(f.type)
            if "List[" in ann or "list[" in ann:
                if val is not None and not isinstance(val, (list, tuple)):
                    violations.append(f"{type(self).__name__}.{f.name}: atteso list/tuple, trovato {type(val).__name__}")
            elif ("Dict[" in ann or "dict[" in ann) and val is not None and not isinstance(val, dict):
                # NB: elif (non if) — un'annotazione `List[Dict[str, Any]]` contiene
                # entrambi i token; senza elif il check Dict scatterebbe sulla list
                # e produrrebbe un falso positivo "atteso dict, trovato list".
                violations.append(f"{type(self).__name__}.{f.name}: atteso dict, trovato {type(val).__name__}")
        return violations

    # ----- serialization ----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serializzazione ricorsiva (dataclasses.asdict su dataclass, altrimenti valore)."""
        if not dataclasses.is_dataclass(self):
            raise OLCValidationError(f"{type(self).__name__} non è un dataclass")
        d = dataclasses.asdict(self)
        d["_olc"] = {"name": self.olc_name(), "version": self.olc_version()}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Deserializza un dict prodotto da `to_dict()`.
        Ignora `_olc` meta ma può validarne il name per sicurezza.
        """
        if not isinstance(data, dict):
            raise OLCValidationError(f"from_dict: atteso dict, trovato {type(data).__name__}")
        meta = data.get("_olc", {})
        if meta and meta.get("name") and meta["name"] != cls.olc_name():
            raise OLCValidationError(
                f"from_dict: mismatch OLC name — atteso {cls.olc_name()}, trovato {meta.get('name')}"
            )
        payload = {k: v for k, v in data.items() if k != "_olc"}
        try:
            # filtra solo campi noti (tolleranza a campi extra, strict su mancanti required)
            known = {f.name for f in dataclasses.fields(cls)} if dataclasses.is_dataclass(cls) else set()
            kwargs = {k: v for k, v in payload.items() if k in known}
            return cls(**kwargs)  # type: ignore[call-arg]
        except TypeError as e:
            raise OLCValidationError(f"from_dict {cls.__name__}: {e}") from e

    # ----- compatibility (structural subtyping) -----------------------------------

    @classmethod
    def is_compatible_with(cls, other_cls: Type[OLCBase]) -> bool:
        """
        Ritorna True se un'istanza di `cls` può fluire in un neurone che
        attende `other_cls` in input. Regole (SPEC §2.2):
          - exact: cls == other_cls
          - subtype: ogni required field di other_cls è presente in cls con tipo compatibile
        """
        if cls is other_cls:
            return True
        if not (dataclasses.is_dataclass(cls) and dataclasses.is_dataclass(other_cls)):
            return False
        other_req = set(other_cls.required_fields())
        own_fields = {f.name: f.type for f in dataclasses.fields(cls)}
        for req in other_req:
            if req not in own_fields:
                return False
            # confronto tipi: stringa repr grezza (robusta a forward refs), match esatto
            own_t = str(own_fields[req])
            other_t = str(other_cls.field_types()[req])
            if own_t != other_t:
                return False
        return True


# -------------------------------------------------------------------------------
# Decoratore di registrazione: importa il registry in modo lazy per evitare cicli.
# -------------------------------------------------------------------------------

def register_olc_type(cls):
    """
    Decoratore che registra una classe OLCBase nel registry.

    Uso:
        @register_olc_type
        @dataclass(frozen=True)
        class SensoryFrame(OLCBase):
            _OLC_NAME = "olc.sensory_frame"
            _OLC_VERSION = "1.0"
            source: str
            ...
    """
    from .registry import _REGISTRY  # import locale per evitare ciclo
    _REGISTRY.register(cls)
    return cls


# -------------------------------------------------------------------------------
# Utility ISO timestamp (helper per i tipi che necessitano di default `ts` corrente)
# -------------------------------------------------------------------------------

def iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
