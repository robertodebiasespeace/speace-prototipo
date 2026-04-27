"""
Benchmark 2/5 – Smoke multi-ciclo.
Esegue SPEACE-main.py per N cicli (default 3) e verifica exit code.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cycles: int = 3, timeout: int = 180) -> dict:
    cmd = [sys.executable, "SPEACE-main.py", f"--cycles={cycles}"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "")
    err = (proc.stderr or "")

    # Conta i cicli eseguiti leggendo i marker
    cycles_run = out.count("--- Ciclo ")
    session_ok = "SESSIONE COMPLETATA" in out

    return {
        "name": "bench_smoke",
        "exit_code": proc.returncode,
        "cycles_requested": cycles,
        "cycles_observed": cycles_run,
        "session_completed": session_ok,
        "stderr_tail": "\n".join(err.splitlines()[-3:]) if err else "",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(cycles=3), indent=2))
