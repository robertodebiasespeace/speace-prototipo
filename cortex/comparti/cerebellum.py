"""
SPEACE Cortex – Cerebellum
Comparto 6: Low-level Execution (solo comandi whitelisted)

Fase 1: esecuzione RIGOROSAMENTE limitata a una whitelist statica.
Qualsiasi comando fuori whitelist genera un errore e registra automaticamente
una proposta SafeProactive High.

Nessun `os.system` con input esterno, nessun `eval`, nessun `subprocess` arbitrario.

Creato: 2026-04-18 | M1 | PROP-CORTEX-COMPLETE-M1
M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
"""

import sys
import datetime
from pathlib import Path
from typing import Dict, List, Callable

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class Cerebellum(BaseCompartment):
    """Esecutore low-level con whitelist statica."""

    name = "cerebellum"
    level = 4  # Azione
    _WHITELIST = ("snapshot", "rollback_dry_run", "log_rotate", "self_test")

    def __init__(self):
        self._handlers: Dict[str, Callable] = {
            "snapshot": self._cmd_snapshot,
            "rollback_dry_run": self._cmd_rollback_dry_run,
            "log_rotate": self._cmd_log_rotate,
            "self_test": self._cmd_self_test,
        }
        self._execution_log: List[Dict] = []

    # ------------------------------------------------------------------
    # API principale
    # ------------------------------------------------------------------

    def execute(self, script_name: str, args: List[str] = None) -> Dict:
        """
        Esegue un comando se nella whitelist, altrimenti registra attempt
        fuori policy e ritorna errore.
        """
        args = args or []
        ts = datetime.datetime.now().isoformat()

        if script_name not in self._WHITELIST:
            # Registra tentativo fuori whitelist e propone gate High a SafeProactive
            self._propose_out_of_whitelist(script_name, args)
            return {
                "status": "rejected",
                "reason": "command_not_in_whitelist",
                "command": script_name,
                "whitelist": list(self._WHITELIST),
                "timestamp": ts,
            }

        try:
            result = self._handlers[script_name](args)
            record = {
                "timestamp": ts,
                "command": script_name,
                "args": args,
                "status": "executed",
                "result_summary": str(result)[:200],
            }
            self._execution_log.append(record)
            return {
                "status": "executed",
                "command": script_name,
                "result": result,
                "timestamp": ts,
            }
        except Exception as e:
            return {
                "status": "error",
                "command": script_name,
                "reason": str(e),
                "timestamp": ts,
            }

    # ------------------------------------------------------------------
    # Handlers whitelisted (implementazioni safe)
    # ------------------------------------------------------------------

    def _cmd_snapshot(self, args: List[str]) -> Dict:
        """Delega la creazione snapshot a SafeProactive (import lazy)."""
        try:
            from safeproactive.safeproactive import SafeProactive
            sp = SafeProactive()
            label = args[0] if args else "cerebellum_manual"
            snap_id = sp.snapshot(label=label)
            return {"snapshot_id": snap_id, "label": label}
        except Exception as e:
            return {"error": f"snapshot_failed: {e}"}

    def _cmd_rollback_dry_run(self, args: List[str]) -> Dict:
        """Dry-run: lista snapshot disponibili senza toccare nulla."""
        snap_dir = ROOT_DIR / "safeproactive" / "snapshots"
        if not snap_dir.exists():
            return {"available_snapshots": [], "dry_run": True}
        snaps = sorted([p.name for p in snap_dir.iterdir() if p.is_dir()])
        return {
            "available_snapshots": snaps,
            "dry_run": True,
            "note": "Rollback reale richiede SafeProactive High + rollback.py (M2)",
        }

    def _cmd_log_rotate(self, args: List[str]) -> Dict:
        """Rotazione log: tronca logs/*.log > 5 MB a 1000 righe più recenti."""
        logs_dir = ROOT_DIR / "logs"
        rotated = []
        if logs_dir.exists():
            for log in logs_dir.glob("*.log"):
                if log.stat().st_size > 5 * 1024 * 1024:
                    lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
                    log.write_text("\n".join(lines[-1000:]), encoding="utf-8")
                    rotated.append(log.name)
        return {"rotated_logs": rotated}

    def _cmd_self_test(self, args: List[str]) -> Dict:
        """Test interno: verifica integrità directory chiave."""
        checks = {
            "digitaldna_dir": (ROOT_DIR / "digitaldna").exists(),
            "safeproactive_dir": (ROOT_DIR / "safeproactive").exists(),
            "cortex_dir": (ROOT_DIR / "cortex").exists(),
            "state_json": (ROOT_DIR / "state.json").exists(),
        }
        return {"checks": checks, "all_ok": all(checks.values())}

    # ------------------------------------------------------------------
    # Meccanismo di difesa fuori whitelist
    # ------------------------------------------------------------------

    def _propose_out_of_whitelist(self, cmd: str, args: List[str]) -> None:
        """
        Qualsiasi comando fuori whitelist viene automaticamente proposto
        come Risk HIGH a SafeProactive per review umana.
        """
        try:
            from safeproactive.safeproactive import SafeProactive, RiskLevel
            sp = SafeProactive()
            sp.propose(
                action_name=f"cerebellum_out_of_whitelist:{cmd}",
                description=f"Tentativo di eseguire comando '{cmd}' fuori whitelist. Args: {args}",
                risk_level=RiskLevel.HIGH,
                source_agent="cerebellum",
            )
        except Exception:
            # Non propaghiamo errori: il rifiuto è già stato comunicato al chiamante
            pass

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def self_report(self) -> Dict:
        return {
            "module": "cerebellum",
            "version": "1.0",
            "whitelist": list(self._WHITELIST),
            "executions_logged": len(self._execution_log),
        }

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Se decision contiene un'azione concreta whitelisted, la esegue.
        Se l'azione non è whitelisted, segnala rifiuto (non ritenta).
        Se state è bloccato da Safety, NON esegue nulla.
        """
        if state_bus.is_blocked(state):
            # Se bloccato, registra comunque un action_result coerente
            state.setdefault("action_result", {})["status"] = "skipped_safety_block"
            return self._log(state, status="skipped", note="state_blocked")

        decision = state.get("decision", {}) or {}
        proposed = decision.get("proposed_action")
        action_result = state.setdefault("action_result", {})

        if not proposed:
            # Nessuna azione richiesta: no-op coerente
            action_result["status"] = "no_action"
            return self._log(state, status="ok", note="no_action")

        # Estrai nome comando
        cmd = None
        if isinstance(proposed, dict):
            cmd = proposed.get("name") or proposed.get("command")
            args = proposed.get("args") or []
        elif isinstance(proposed, str):
            cmd = proposed
            args = []
        else:
            args = []

        if not cmd:
            action_result["status"] = "invalid_action_descriptor"
            return self._log(state, status="error", note="invalid_action")

        exec_result = self.execute(cmd, args)
        action_result["command"] = cmd
        action_result["status"] = exec_result.get("status", "unknown")
        action_result["detail"] = exec_result

        note = f"{cmd}:{action_result['status']}"
        log_status = "ok" if action_result["status"] in ("executed", "no_action") else "warning"
        return self._log(state, status=log_status, note=note)
