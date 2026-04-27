"""
SPEACE Cortex – State Bus
Protocollo JSON State condiviso tra tutti i comparti del Cortex.

Il State è un dict unico che viene passato lungo il flusso neurale:
ogni comparto lo riceve, lo arricchisce con il proprio contributo,
e lo restituisce. Le modifiche sono additive (append-only sul log).

Schema v1:
{
  "cycle_id": str,
  "timestamp": ISO8601,
  "sensory_input": dict,        # Parietal Lobe
  "interpretation": dict,       # Temporal Lobe
  "decision": dict,             # Prefrontal Cortex
  "action_result": dict,        # Cerebellum
  "memory_delta": dict,         # Hippocampus
  "reflection": dict,           # Default Mode Network
  "world_snapshot": dict,       # World Model
  "mutation_proposal": dict,    # Curiosity Module
  "safety_flags": {             # Safety Module (override)
    "blocked": bool,
    "risk_level": str,
    "reasons": [str]
  },
  "uncertainty": float [0..1],  # quanto l'interpretazione è ambigua
  "risk": float [0..1],         # quanto l'azione è rischiosa
  "novelty": float [0..1],      # quanto l'input è nuovo/inaspettato
  "sensory_drift": float [0..1],# quanto il World Model è disallineato
  "compartment_log": [          # append-only tracking
    {"name": str, "level": int, "ts": ISO8601, "status": str, "note": str?}
  ],
  "_schema_version": 1
}
"""

from __future__ import annotations
import datetime
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1


def new_state(cycle_id: str,
              sensory_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Inizializza uno State neurale vuoto per un ciclo."""
    return {
        "cycle_id": cycle_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "sensory_input": sensory_input or {},
        "interpretation": {},
        "decision": {},
        "action_result": {},
        "memory_delta": {},
        "reflection": {},
        "world_snapshot": {},
        "mutation_proposal": {},
        "safety_flags": {"blocked": False, "risk_level": "low", "reasons": []},
        "uncertainty": 0.0,
        "risk": 0.0,
        "novelty": 0.0,
        "sensory_drift": 0.0,
        "compartment_log": [],
        "_schema_version": SCHEMA_VERSION,
    }


def log_compartment(state: Dict[str, Any],
                    name: str,
                    level: int,
                    status: str = "ok",
                    note: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggiunge un'entry al compartment_log in modo append-only.
    Ritorna lo state modificato per permettere chaining.
    """
    entry = {
        "name": name,
        "level": level,
        "ts": datetime.datetime.now().isoformat(),
        "status": status,
    }
    if note:
        entry["note"] = note
    state.setdefault("compartment_log", []).append(entry)
    return state


def mark_safety_block(state: Dict[str, Any],
                      risk_level: str,
                      reason: str) -> Dict[str, Any]:
    """
    Marca lo state come bloccato dal Safety Module.
    Dopo questa chiamata nessun comparto di livello >= 2 dovrebbe processare.
    """
    sf = state.setdefault("safety_flags",
                           {"blocked": False, "risk_level": "low", "reasons": []})
    sf["blocked"] = True
    sf["risk_level"] = risk_level
    sf.setdefault("reasons", []).append(reason)
    return state


def is_blocked(state: Dict[str, Any]) -> bool:
    return bool(state.get("safety_flags", {}).get("blocked", False))


def validate(state: Dict[str, Any]) -> List[str]:
    """
    Ritorna lista di problemi riscontrati nello state.
    Lista vuota = state valido.
    """
    issues: List[str] = []
    required_keys = (
        "cycle_id", "timestamp", "safety_flags", "compartment_log",
        "_schema_version",
    )
    for k in required_keys:
        if k not in state:
            issues.append(f"missing_key:{k}")
    sv = state.get("_schema_version")
    if sv != SCHEMA_VERSION:
        issues.append(f"schema_version_mismatch:{sv}!={SCHEMA_VERSION}")
    # Numeric fields range check
    for field in ("uncertainty", "risk", "novelty", "sensory_drift"):
        v = state.get(field, 0.0)
        if not (isinstance(v, (int, float)) and 0.0 <= v <= 1.0):
            issues.append(f"out_of_range:{field}={v}")
    return issues
