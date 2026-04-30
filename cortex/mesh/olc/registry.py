"""
SPEACE Cortex Mesh — OLC Registry

Registry centralizzato dei tipi OLC. Un singleton process-locale
(thread-safe per registration via lock; lookup è lock-free dopo init).

Interfaccia pubblica:
  - `register(cls)` — registra una classe OLCBase (idempotente su stessa classe)
  - `lookup(name)` — recupera la classe da `_OLC_NAME`
  - `all_types()` — snapshot della lista registrata
  - `check_compatibility(src_name, dst_name)` — boolean (delega a OLCBase.is_compatible_with)
  - `snapshot()` — dict riassuntivo (per telemetry/debug)

Il registry è popolato automaticamente dal modulo `types.py` al primo import
tramite il decoratore `@register_olc_type`.

Milestone: M4.3 (PROP-CORTEX-NEURAL-MESH-M4)
"""

from __future__ import annotations
import threading
from typing import Dict, List, Optional, Type

from .base import OLCBase, OLCValidationError


class _OLCRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._types: Dict[str, Type[OLCBase]] = {}

    def register(self, cls: Type[OLCBase]) -> Type[OLCBase]:
        """
        Registra `cls`. Idempotente quando si ri-registra la stessa classe
        con lo stesso `_OLC_NAME` e `_OLC_VERSION`. Solleva in caso di conflitto.
        """
        if not isinstance(cls, type) or not issubclass(cls, OLCBase):
            raise OLCValidationError(f"register: {cls!r} non è sottoclasse di OLCBase")
        name = getattr(cls, "_OLC_NAME", None)
        version = getattr(cls, "_OLC_VERSION", None)
        if not name or name == "olc.base":
            raise OLCValidationError(f"register: _OLC_NAME mancante o non sovrascritto per {cls.__name__}")
        if not version:
            raise OLCValidationError(f"register: _OLC_VERSION mancante per {cls.__name__}")

        with self._lock:
            existing = self._types.get(name)
            if existing is None:
                self._types[name] = cls
                return cls
            if existing is cls:
                return cls
            # conflitto: stesso name ma classi diverse
            raise OLCValidationError(
                f"register: nome OLC duplicato '{name}' — "
                f"già assegnato a {existing.__module__}.{existing.__name__}, "
                f"richiesto da {cls.__module__}.{cls.__name__}"
            )

    def lookup(self, name: str) -> Optional[Type[OLCBase]]:
        return self._types.get(name)

    def require(self, name: str) -> Type[OLCBase]:
        cls = self.lookup(name)
        if cls is None:
            raise OLCValidationError(f"OLC type '{name}' non registrato")
        return cls

    def all_types(self) -> List[Type[OLCBase]]:
        with self._lock:
            return list(self._types.values())

    def names(self) -> List[str]:
        with self._lock:
            return sorted(self._types.keys())

    def check_compatibility(self, src_name: str, dst_name: str) -> bool:
        """Convenience: lookup dei due tipi + delega a OLCBase.is_compatible_with."""
        src = self.require(src_name)
        dst = self.require(dst_name)
        return src.is_compatible_with(dst)

    def snapshot(self) -> Dict[str, Dict[str, str]]:
        """Dict riassuntivo {name: {version, class_path}} — utile per telemetry."""
        out: Dict[str, Dict[str, str]] = {}
        with self._lock:
            for name, cls in self._types.items():
                out[name] = {
                    "version": cls.olc_version(),
                    "class_path": f"{cls.__module__}.{cls.__name__}",
                    "required_fields": ",".join(cls.required_fields()),
                }
        return out

    # solo per testing
    def _reset(self) -> None:
        with self._lock:
            self._types.clear()


# singleton
_REGISTRY = _OLCRegistry()


# ---------- public API (module-level) -----------------------------------------

def register(cls: Type[OLCBase]) -> Type[OLCBase]:
    return _REGISTRY.register(cls)


def lookup(name: str) -> Optional[Type[OLCBase]]:
    return _REGISTRY.lookup(name)


def require(name: str) -> Type[OLCBase]:
    return _REGISTRY.require(name)


def all_types() -> List[Type[OLCBase]]:
    return _REGISTRY.all_types()


def names() -> List[str]:
    return _REGISTRY.names()


def check_compatibility(src_name: str, dst_name: str) -> bool:
    return _REGISTRY.check_compatibility(src_name, dst_name)


def snapshot() -> Dict[str, Dict[str, str]]:
    return _REGISTRY.snapshot()
