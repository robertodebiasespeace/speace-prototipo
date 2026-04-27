"""
Benchmark 1/5 – Pytest regression.
Esegue la suite pytest e conta pass/fail.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run() -> dict:
    cmd = [sys.executable, "-m", "pytest", "tests/", "--no-header", "-q", "--tb=no"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    out = (proc.stdout or "") + (proc.stderr or "")

    # Parse "N passed" / "N failed"
    passed = 0
    failed = 0
    for line in out.splitlines():
        ls = line.strip().lower()
        if " passed" in ls:
            # es. "16 passed in 0.33s"
            for tok in ls.replace(",", " ").split():
                if tok.isdigit():
                    passed = int(tok)
                    break
        if " failed" in ls and "passed" not in ls:
            for tok in ls.replace(",", " ").split():
                if tok.isdigit():
                    failed = int(tok)
                    break
    return {
        "name": "bench_tests",
        "exit_code": proc.returncode,
        "passed": passed,
        "failed": failed,
        "output_tail": "\n".join(out.splitlines()[-5:]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
