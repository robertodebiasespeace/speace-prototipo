"""
Benchmark 5/5 – Latency call_compartment.
Misura p50/p95/max su N chiamate ai 9 comparti via Kernel.call_compartment().
"""

import sys
import time
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run(sample_size: int = 20) -> dict:
    from cortex.SMFOI_v3 import SMFOIKernel
    k = SMFOIKernel(agent_name="BENCH-LATENCY", recursion_level=1)
    comps = k.list_compartments()

    timings_ms = []
    per_compartment = {}
    for comp in comps:
        per_compartment[comp] = []
        for _ in range(sample_size):
            t0 = time.perf_counter()
            out = k.call_compartment(comp)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings_ms.append(dt_ms)
            per_compartment[comp].append(dt_ms)
            # sanity
            if out.get("status") not in ("ok", "unknown", "error"):
                pass

    timings_ms.sort()
    def pct(p):
        if not timings_ms:
            return 0.0
        idx = max(0, min(len(timings_ms) - 1, int(round(p * (len(timings_ms) - 1)))))
        return round(timings_ms[idx], 3)

    return {
        "name": "bench_latency",
        "sample_size": sample_size,
        "total_calls": len(timings_ms),
        "mean_ms": round(statistics.fmean(timings_ms), 3) if timings_ms else 0.0,
        "p50_ms": pct(0.50),
        "p95_ms": pct(0.95),
        "max_ms": round(max(timings_ms), 3) if timings_ms else 0.0,
        "per_compartment_mean_ms": {
            c: round(statistics.fmean(v), 3) for c, v in per_compartment.items() if v
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
