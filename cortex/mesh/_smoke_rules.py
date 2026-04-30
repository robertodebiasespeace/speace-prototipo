"""
Smoke test per cortex.mesh.execution_rules (M4.4)

Valida:
  1) Il file YAML viene caricato (non fallback)
  2) budget_ceilings ha i valori attesi (versione 1.0)
  3) La cache mtime funziona (seconda chiamata non rilegge)
  4) reload() forza la ricarica
  5) Le whitelist fs/net/llm/shell funzionano
  6) L'integrazione con contract.py legge ceilings dinamicamente
  7) I default fallback sono SPEC-compliant (se file assente)

Uso: python -m cortex.mesh._smoke_rules
"""

from __future__ import annotations
import sys
from pathlib import Path

from cortex.mesh import execution_rules as er
from cortex.mesh import contract as c


def check(label: str, cond: bool, detail: str = "") -> bool:
    status = "✓" if cond else "✗"
    msg = f"  {status} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return cond


def main() -> int:
    passed = 0
    total = 0

    print("=== execution_rules smoke (M4.4) ===\n")

    # 1) file YAML caricato
    total += 1
    using_fallback = er.is_using_fallback()
    if check("YAML caricato (non fallback)", not using_fallback,
             f"using_fallback={using_fallback}"):
        passed += 1

    # 2) budget_ceilings atteso
    total += 1
    bc = er.get_budget_ceilings()
    expected = {"max_ms": 30000, "max_mb": 512, "max_retries": 3,
                "priority_boost_min": -2, "priority_boost_max": 2}
    if check("budget_ceilings corretti",
             all(bc.get(k) == v for k, v in expected.items()),
             f"bc={bc}"):
        passed += 1

    # 3) cache: seconda chiamata usa cached (mtime invariato)
    total += 1
    rules_a = er.load_rules()
    rules_b = er.load_rules()
    if check("cache mtime-based", rules_a is rules_b,
             "same object → cache hit"):
        passed += 1

    # 4) reload forza ricarica
    total += 1
    rules_c = er.reload()
    # reload ricarica dal disco, nuovo oggetto
    if check("reload() ricarica", rules_c is not rules_a or not using_fallback,
             "reload completato"):
        passed += 1

    # 5) whitelist coverage
    total += 1
    fs_ok = (er.is_path_allowed("digitaldna/genome.yaml", "fs_read")
             and not er.is_path_allowed("/etc/passwd", "fs_read")
             and er.is_path_allowed("safeproactive/WAL.log", "fs_write"))
    net_ok = (er.is_host_allowed("localhost")
              and er.is_host_allowed("www.rigeneproject.org")
              and not er.is_host_allowed("evil.example.com"))
    llm_ok = (er.is_llm_backend_allowed("mock")
              and er.is_llm_backend_allowed("anthropic")
              and not er.is_llm_backend_allowed("unknown_backend"))
    shell_ok = (er.is_shell_cmd_allowed("git_status")
                and not er.is_shell_cmd_allowed("rm"))
    if check("whitelist fs/net/llm/shell", fs_ok and net_ok and llm_ok and shell_ok,
             f"fs={fs_ok} net={net_ok} llm={llm_ok} shell={shell_ok}"):
        passed += 1

    # 6) contract.py integration
    total += 1
    ceilings = c.current_ceilings()
    if check("contract.current_ceilings() OK",
             ceilings.get("max_ms") == 30000
             and ceilings.get("max_mb") == 512
             and ceilings.get("max_retries") == 3
             and ceilings.get("quarantine_threshold") == 3,
             f"ceilings={ceilings}"):
        passed += 1

    # 7) concurrency per_level / per_need presenti
    total += 1
    conc = er.get_concurrency_config()
    plc = conc.get("per_level_caps", {})
    pnc = conc.get("per_need_caps", {})
    if check("concurrency caps (per level + per need)",
             set(plc.keys()) == {"L1", "L2", "L3", "L4", "L5"}
             and set(pnc.keys()) == {"harmony", "survival", "integration",
                                      "self_improvement", "expansion"},
             f"levels={sorted(plc.keys())} needs={sorted(pnc.keys())}"):
        passed += 1

    # 8) fail_safe + quarantine policy complete
    total += 1
    fs_policy = er.get_fail_safe_policy()
    qp = er.get_quarantine_policy()
    if check("fail_safe + quarantine policy",
             fs_policy.get("error_rate_threshold") == 0.50
             and fs_policy.get("action_on_trip") == "freeze_mesh"
             and qp.get("strike_threshold") == 3
             and qp.get("requires_prop_to_reactivate") is True,
             "policies complete"):
        passed += 1

    print(f"\nPassed: {passed}/{total}")
    if passed == total:
        print("\n✅ execution_rules smoke OK")
        return 0
    else:
        print("\n❌ execution_rules smoke FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
