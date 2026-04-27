"""
Benchmark 4/5 – Fitness v2.0 regression.
Usa il risultato di run_cycle() e confronta con soglia.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run() -> dict:
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="BENCH-FITNESS", recursion_level=1)
    result = k.run_cycle()
    outcome = result.get("outcome", {})
    return {
        "name": "bench_fitness",
        "fitness_before": outcome.get("fitness_before", 0.0),
        "fitness_after": outcome.get("fitness_after", 0.0),
        "delta": round(outcome.get("fitness_after", 0.0) - outcome.get("fitness_before", 0.0), 4),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
