"""
SPEACE Cortex Mesh — Execution Rules Loader (M4.4)

Legge `cortex/mesh/execution_rules.yaml` e fornisce API tipate per:
  - budget_ceilings (consumato da contract.py)
  - quarantine policy
  - fail-safe thresholds
  - sandbox whitelist (consumato da runtime M4.6)
  - telemetry config (consumato da M4.13)
  - concurrency caps (consumato da M4.6 runtime)

Pattern di caching: il file è letto una volta e cacheato; `reload()` forza
ricarica. Il loader è thread-safe.

Fallback: se il file è assente o corrotto, restituisce i default SPEC-compliant
hard-coded (per permettere unit testing in isolamento).

Milestone: M4.4 (PROP-CORTEX-NEURAL-MESH-M4)
"""

from __future__ import annotations
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # PyYAML
except ImportError as e:  # pragma: no cover
    raise ImportError("execution_rules.py richiede PyYAML (pip install pyyaml)") from e

_log = logging.getLogger("speace.mesh.rules")

RULES_PATH = Path(__file__).parent / "execution_rules.yaml"

# ---------------------------------------------------------------------------
# Fallback defaults (usati se il file YAML è assente)
# ---------------------------------------------------------------------------

_DEFAULT_RULES: Dict[str, Any] = {
    "meta": {"version": "fallback", "description": "Hard-coded fallback defaults"},
    "budget_ceilings": {
        "max_ms": 30000,
        "max_mb": 512,
        "max_retries": 3,
        "priority_boost_min": -2,
        "priority_boost_max": 2,
    },
    "default_timeouts": {
        "activation_ms": 5000,
        "cleanup_ms": 3000,
        "execute_fallback_ms": 10000,
    },
    "concurrency": {
        "max_concurrent_neurons": 8,
        "queue_size": 64,
        "submit_timeout_ms": 1000,
        "backpressure_strategy": "reject_new",
        "per_level_caps": {"L1": 2, "L2": 4, "L3": 2, "L4": 4, "L5": 1},
        "per_need_caps": {
            "harmony": 4, "survival": 3, "integration": 4,
            "self_improvement": 2, "expansion": 2,
        },
    },
    "quarantine": {
        "strike_threshold": 3,
        "strike_reset_after_s": 3600,
        "auto_disable": True,
        "requires_prop_to_reactivate": True,
        "prop_risk_level": "medium",
    },
    "fail_safe": {
        "error_rate_threshold": 0.50,
        "error_rate_window_heartbeats": 2,
        "action_on_trip": "freeze_mesh",
        "auto_flip_epigenome_enabled": True,
        "emit_prop_risk": "high",
    },
    "retry": {
        "default_retries": 0,
        "backoff_base_ms": 100,
        "backoff_multiplier": 2.0,
        "backoff_max_ms": 2000,
    },
    "sandbox": {
        "fs_read_allowed_roots": ["cortex/mesh/"],
        "fs_write_allowed_roots": ["cortex/mesh/logs/"],
        "net_whitelist": ["localhost"],
        "shell_whitelist": [],
        "llm_allowed_backends": ["mock"],
        "state_bus_allowed_keys": [],
    },
    "telemetry": {
        "jsonl_path": "cortex/mesh/mesh_state.jsonl",
        "buffer_max_events": 1000,
        "rotation_mb": 50,
        "keep_rotations": 5,
        "log_backend_used": True,
    },
    "runtime": {
        "boot_validation_required": True,
        "boot_validation_timeout_ms": 5000,
        "refuse_boot_on_violations": True,
        "graceful_shutdown_timeout_s": 30,
        "health_check_interval_s": 300,
    },
    "safeproactive": {
        "proposal_low_auto_approve": False,
        "proposal_medium_requires_human": True,
        "proposal_high_requires_human_and_legal": True,
        "wal_append_only": True,
    },
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_cached_rules: Optional[Dict[str, Any]] = None
_cached_mtime: Optional[float] = None
_using_fallback: bool = False


def _load_from_disk() -> Dict[str, Any]:
    if not RULES_PATH.exists():
        _log.warning("execution_rules.yaml not found at %s — using fallback defaults", RULES_PATH)
        return dict(_DEFAULT_RULES)
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        _log.error("execution_rules.yaml parse error: %s — fallback defaults", e)
        return dict(_DEFAULT_RULES)
    if not isinstance(data, dict):
        _log.error("execution_rules.yaml must be a dict, got %s — fallback defaults", type(data).__name__)
        return dict(_DEFAULT_RULES)
    # merge con default per campi mancanti (deep merge shallow-level)
    merged: Dict[str, Any] = {}
    for key, fallback_val in _DEFAULT_RULES.items():
        if key in data and isinstance(data[key], dict) and isinstance(fallback_val, dict):
            m = dict(fallback_val)
            m.update(data[key])
            merged[key] = m
        elif key in data:
            merged[key] = data[key]
        else:
            merged[key] = fallback_val
    # preserva sezioni extra non standard
    for key in data:
        if key not in merged:
            merged[key] = data[key]
    return merged


def load_rules(force_reload: bool = False) -> Dict[str, Any]:
    """Ritorna le regole (cached). Se il file è cambiato su disco, ricarica."""
    global _cached_rules, _cached_mtime, _using_fallback
    with _lock:
        mtime = RULES_PATH.stat().st_mtime if RULES_PATH.exists() else None
        if force_reload or _cached_rules is None or mtime != _cached_mtime:
            _cached_rules = _load_from_disk()
            _cached_mtime = mtime
            _using_fallback = not RULES_PATH.exists()
        return _cached_rules


def reload() -> Dict[str, Any]:
    return load_rules(force_reload=True)


def is_using_fallback() -> bool:
    """True se il file non esiste e stiamo usando i default hard-coded."""
    load_rules()
    return _using_fallback


# ---------------------------------------------------------------------------
# API tipate (consumate dai moduli mesh)
# ---------------------------------------------------------------------------

def get_budget_ceilings() -> Dict[str, int]:
    return dict(load_rules().get("budget_ceilings", {}))


def get_default_timeouts() -> Dict[str, int]:
    return dict(load_rules().get("default_timeouts", {}))


def get_concurrency_config() -> Dict[str, Any]:
    return dict(load_rules().get("concurrency", {}))


def get_quarantine_policy() -> Dict[str, Any]:
    return dict(load_rules().get("quarantine", {}))


def get_fail_safe_policy() -> Dict[str, Any]:
    return dict(load_rules().get("fail_safe", {}))


def get_retry_policy() -> Dict[str, Any]:
    return dict(load_rules().get("retry", {}))


def get_sandbox_config() -> Dict[str, Any]:
    return dict(load_rules().get("sandbox", {}))


def get_telemetry_config() -> Dict[str, Any]:
    return dict(load_rules().get("telemetry", {}))


def get_runtime_config() -> Dict[str, Any]:
    return dict(load_rules().get("runtime", {}))


def get_safeproactive_policy() -> Dict[str, Any]:
    return dict(load_rules().get("safeproactive", {}))


# ---------------------------------------------------------------------------
# Helper: controllo whitelist
# ---------------------------------------------------------------------------

def is_path_allowed(path: str, kind: str = "fs_read") -> bool:
    """
    Verifica se `path` è coperto da una whitelist fs_read o fs_write.
    Match per prefix string (startswith dopo normalizzazione).
    """
    sb = get_sandbox_config()
    key = "fs_read_allowed_roots" if kind == "fs_read" else "fs_write_allowed_roots"
    roots: List[str] = list(sb.get(key, []))
    p = path.replace("\\", "/").lstrip("./")
    for root in roots:
        r = root.replace("\\", "/").lstrip("./")
        if p.startswith(r):
            return True
    return False


def is_host_allowed(host: str) -> bool:
    """Verifica se `host` è in net_whitelist."""
    wl = get_sandbox_config().get("net_whitelist", [])
    return host in wl


def is_llm_backend_allowed(backend: str) -> bool:
    wl = get_sandbox_config().get("llm_allowed_backends", [])
    return backend in wl


def is_shell_cmd_allowed(cmd: str) -> bool:
    wl = get_sandbox_config().get("shell_whitelist", [])
    return cmd in wl


# ---------------------------------------------------------------------------
# __main__: stampa regole correnti (debug)
# ---------------------------------------------------------------------------

def _main() -> int:  # pragma: no cover
    import json
    rules = load_rules()
    print(f"# execution_rules.yaml — version={rules.get('meta', {}).get('version')}")
    print(f"# using fallback: {is_using_fallback()}")
    print(f"# source: {RULES_PATH}")
    print(json.dumps(rules, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(_main())
