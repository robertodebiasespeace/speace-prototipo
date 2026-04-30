"""
Benchmark 3/5 – C-index regression.
Istanzia SMFOIKernel, esegue run_cycle() e legge c_index dalle metrics.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run() -> dict:
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="BENCH-CINDEX", recursion_level=1)
    result = k.run_cycle()
    outcome = result.get("outcome", {}) or {}
    ci = outcome.get("c_index") or {}
    components = ci.get("components", {}) if isinstance(ci, dict) else {}
    return {
        "name": "bench_cindex",
        "c_index": ci.get("c_index", 0.0) if isinstance(ci, dict) else 0.0,
        "phi": components.get("phi", 0.0),
        "w_activation": components.get("w_activation", 0.0),
        "a_complexity": components.get("a_complexity", 0.0),
        "consciousness_level": ci.get("level", "Reattivo") if isinstance(ci, dict) else "Reattivo",
        "fitness_after": outcome.get("fitness_after", 0.0),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
