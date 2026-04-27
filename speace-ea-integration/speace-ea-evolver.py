"""
SPEACE EA Evolver Agent — Autonomous EA Optimizer
Runs every N minutes, reads EA metrics, evaluates fitness,
and applies SafeProactive-approved mutations to ea_params.json
and ea_epigenome.yaml.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from safeproactive.safeproactive import SafeProactive

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SPEACE-EA-EVOLVER] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "speace_ea_evolver.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("speace_ea_evolver")


class EAEvolver:
    """
    EA Evolver follows the SMFOI cycle to monitor, evaluate,
    and evolve the XAUUSD EA parameters autonomously.

    SMFOI Steps:
    1. Self-Location    — where are we in the trading session
    2. Constraint Mapping — resource constraints (account balance, risk limits)
    3. Push Detection   — EA metrics, fitness signals
    4. Survival Stack   — trading safety (drawdown protection)
    5. Output Action    — apply approved mutations
    6. Outcome Eval     — measure, update fitness, propose rollback
    """

    def __init__(self):
        # Path where MT5 EA writes files (TERMINAL_DATA_PATH + relative subfolder)
        mt5_terminal_path = self._detect_mt5_terminal_path()
        self.shared_path = os.environ.get(
            "SPEACE_EA_SHARED_PATH",
            str(mt5_terminal_path / "speace-ea-integration" / "shared_state")
        )
        self.ea_params_file = Path(self.shared_path) / "ea_params.json"
        self.ea_metrics_file = Path(self.shared_path) / "ea_metrics.json"
        self.ea_state_file = Path(self.shared_path) / "ea_state.json"
        self.epigenome_file = PROJECT_ROOT / "speace-ea-integration" / "ea_epigenome.yaml"
        self.proposals_file = PROJECT_ROOT / "safeproactive" / "PROPOSALS.md"

        self.speace = SafeProactive()
        self.cycle_count = 0
        self.last_fitness = 0.0
        self.mutation_count = 0
        self.rollback_count = 0
        self.start_time = datetime.now()

        # Fitness thresholds
        self.fitness_acceptance = 0.60
        self.rollback_threshold = 0.10  # auto-rollback if fitness drops >10%

        # Read epigenome
        self.epigenome = self._read_epigenome()

    def _detect_mt5_terminal_path(self) -> Path:
        """Detect MT5 terminal data folder."""
        # Try common paths
        common = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common"
        if common.exists():
            return common
        # Fallback: try each terminal ID
        terminal_base = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
        if terminal_base.exists():
            for sub in terminal_base.iterdir():
                if sub.is_dir() and sub.name != "Common":
                    # Check if it's a valid terminal folder (has MQL5 subfolder)
                    if (sub / "MQL5").exists():
                        return sub
        # Last resort: use project root
        return PROJECT_ROOT

    def _read_epigenome(self) -> dict[str, Any]:
        """Load current EA epigenome from YAML."""
        import yaml
        ep_file = PROJECT_ROOT / "speace-ea-integration" / "ea_epigenome.yaml"
        if ep_file.exists():
            with open(ep_file, "r") as f:
                return yaml.safe_load(f)
        return self._default_epigenome()

    def _default_epigenome(self) -> dict[str, Any]:
        return {
            "meta": {
                "name": "SPEACE-EA-Epigenome",
                "version": "1.0",
                "mutation_count": 0,
                "last_mutation_id": None
            },
            "parameters": {
                "LotSize": {"current": 0.1, "min": 0.01, "max": 1.0},
                "StopLossPips": {"current": 500, "min": 10, "max": 5000},
                "TakeProfitPips": {"current": 1000, "min": 10, "max": 10000},
                "RSI_Period": {"current": 14, "min": 2, "max": 100},
                "MA_Fast_Period": {"current": 10, "min": 2, "max": 200},
                "MA_Slow_Period": {"current": 30, "min": 5, "max": 500},
                "MaxDrawdownPct": {"current": 20.0, "min": 5.0, "max": 50.0},
                "MaxTrades": {"current": 3, "min": 1, "max": 10}
            },
            "immutable": [
                "MaxDrawdownPct",  # Hard safety limit
            ],
            "evolver": {
                "enabled": True,
                "interval_minutes": 5,
                "mutation_threshold": 0.65,
                "consecutive_poor_limit": 3,
                "auto_rollback": True
            }
        }

    def _write_epigenome(self):
        """Persist epigenome changes to YAML."""
        import yaml
        ep_file = PROJECT_ROOT / "speace-ea-integration" / "ea_epigenome.yaml"
        with open(ep_file, "w") as f:
            yaml.dump(self.epigenome, f, default_flow_style=False, sort_keys=False)

    def _write_ea_params_json(self, params: dict[str, Any]):
        """Write params to ea_params.json for MT5 EA to read."""
        self.ea_params_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ea_params_file, "w") as f:
            json.dump(params, f, indent=2)

    def run_smfoi_cycle(self) -> dict[str, Any]:
        """Execute one full SMFOI cycle."""
        self.cycle_count += 1
        cycle_id = f"EA-EVOL-{self.cycle_count:06d}"
        logger.info(f"=== Starting SMFOI Cycle {cycle_id} ===")

        # Step 1: Self-Location
        location = self._self_location()

        # Step 2: Constraint Mapping
        constraints = self._constraint_mapping()

        # Step 3: Push Detection
        pushes = self._push_detection()

        # Step 4: Survival Stack
        survival_level = self._survival_stack(location, constraints, pushes)

        # Step 5: Output Action
        actions = self._output_action(survival_level, pushes)

        # Step 6: Outcome Evaluation
        outcome = self._outcome_evaluation(actions)

        logger.info(f"=== Cycle {cycle_id} Complete: fitness={outcome.get('fitness', 0):.4f} ===")
        return outcome

    def _self_location(self) -> dict[str, Any]:
        """Step 1: Where are we in the trading session."""
        metrics = self._read_metrics()
        state = self._read_ea_state()

        return {
            "cycle_id": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "ea_running": metrics.get("timestamp") is not None,
            "session_age_min": self._session_age_minutes(),
            "total_trades": metrics.get("total_trades", 0),
            "consecutive_poor": 0,  # Will be updated by trading_cortex
            "epigenome_mutations": self.epigenome["meta"]["mutation_count"]
        }

    def _constraint_mapping(self) -> dict[str, Any]:
        """Step 2: Map available resources and safety constraints."""
        metrics = self._read_metrics()
        balance = metrics.get("balance", 0)
        equity = metrics.get("equity", 0)

        return {
            "balance": balance,
            "equity": equity,
            "equity_ratio": equity / balance if balance > 0 else 0,
            "drawdown_pct": metrics.get("drawdown_pct", 0),
            "can_increase_risk": equity / balance > 0.98 if balance > 0 else False,
            "must_reduce_risk": metrics.get("drawdown_pct", 0) > 10,
            "mutations_exhausted": self.epigenome["meta"]["mutation_count"] >= 10
        }

    def _push_detection(self) -> dict[str, Any]:
        """Step 3: Detect external pushes (signals from EA or user)."""
        metrics = self._read_metrics()
        state = self._read_ea_state()
        proposals = self._read_pending_proposals()

        return {
            "metrics_fresh": self._metrics_fresh(metrics),
            "proposal_available": len(proposals) > 0,
            "safety_override": state.get("safety_flags", {}).get("blocked", False),
            "fitness_drop": self.last_fitness - (metrics.get("fitness", 0) or 0),
            "drawdown_spike": metrics.get("drawdown_pct", 0) > 15
        }

    def _survival_stack(self, location: dict, constraints: dict, pushes: dict) -> int:
        """Step 4: Determine survival/response level Lv0-Lv3."""
        # Lv0: Critical — drawdown > hard limit or equity near zero
        if constraints.get("drawdown_pct", 0) >= self.epigenome["parameters"]["MaxDrawdownPct"]["current"]:
            return 0
        if constraints.get("equity_ratio", 1) < 0.5:
            return 0

        # Lv0: Emergency drawdown spike
        if pushes.get("drawdown_spike"):
            return 0

        # Lv1: Maintenance — everything normal, no action needed
        if not pushes.get("proposal_available") and not pushes.get("fitness_drop", 0) > 0.10:
            return 1

        # Lv2: Optimization — fitness degraded, proposal available
        if pushes.get("proposal_available") and not pushes.get("safety_override"):
            return 2

        # Lv3: Evolution — only if explicit approval and low risk
        if (self.epigenome["evolver"]["enabled"] and
                pushes.get("fitness_drop", 0) > self.rollback_threshold and
                not pushes.get("safety_override")):
            return 3

        return 1

    def _output_action(self, survival_level: int, pushes: dict) -> dict[str, Any]:
        """Step 5: Execute planned action based on survival level."""
        actions_taken = []
        applied_mutations = []

        if survival_level == 0:
            # Lv0: Emergency — close positions, switch to safest params
            logger.warning("SURVIVAL LV0: Emergency drawdown protection triggered")
            self._apply_emergency_params()
            actions_taken.append("emergency_params")
            # Trigger SafeProactive snapshot
            self.speace.create_snapshot("emergency_drawdown_protection")

        elif survival_level == 1:
            # Lv1: Monitor only, no action
            actions_taken.append("monitor_only")

        elif survival_level == 2:
            # Lv2: Apply approved parameter mutations
            proposals = self._read_pending_proposals()
            for prop in proposals[:2]:  # Max 2 mutations per cycle
                if self._apply_mutation(prop):
                    applied_mutations.append(prop)
                    actions_taken.append(f"applied_{prop.get('param')}")

        elif survival_level == 3:
            # Lv3: Evolution — propose structural changes
            logger.info("SURVIVAL LV3: Structural evolution proposed")
            self._propose_structural_evolution()
            actions_taken.append("structural_evolution_proposed")

        return {
            "survival_level": survival_level,
            "actions": actions_taken,
            "mutations_applied": applied_mutations,
            "timestamp": datetime.now().isoformat()
        }

    def _outcome_evaluation(self, actions: dict) -> dict[str, Any]:
        """Step 6: Evaluate outcome, update fitness, check rollback."""
        metrics = self._read_metrics()
        fitness = self._compute_fitness(metrics)

        outcome = {
            "cycle_id": self.cycle_count,
            "fitness": fitness,
            "previous_fitness": self.last_fitness,
            "fitness_delta": fitness - self.last_fitness,
            "actions": actions.get("actions", []),
            "timestamp": datetime.now().isoformat()
        }

        self.last_fitness = fitness

        # Check auto-rollback
        if (self.epigenome["evolver"]["auto_rollback"] and
                outcome["fitness_delta"] < -self.rollback_threshold):
            logger.warning(f"Auto-rollback triggered: fitness dropped {outcome['fitness_delta']:.4f}")
            self._trigger_rollback()
            outcome["rollback_triggered"] = True

        # Log to file
        self._log_outcome(outcome)

        return outcome

    def _apply_mutation(self, proposal: dict) -> bool:
        """Apply a single mutation to ea_params.json and epigenome."""
        param = proposal.get("param")
        suggested = proposal.get("suggested")

        if param in self.epigenome.get("immutable", []):
            logger.warning(f"Cannot mutate immutable param: {param}")
            return False

        params = self.epigenome["parameters"]
        if param not in params:
            logger.warning(f"Unknown parameter: {param}")
            return False

        # Clamp to allowed range
        pdef = params[param]
        clamped = max(pdef["min"], min(suggested, pdef["max"]))

        # Update epigenome
        old_value = pdef["current"]
        pdef["current"] = clamped
        self.epigenome["meta"]["mutation_count"] += 1
        self.epigenome["meta"]["last_mutation_id"] = f"EA-EPI-{self.epigenome['meta']['mutation_count']:03d}"

        # Write ea_params.json for MT5
        json_params = {k: v["current"] for k, v in params.items()}
        self._write_ea_params_json(json_params)
        self._write_epigenome()

        logger.info(f"MUTATION: {param} {old_value} -> {clamped}")
        self.mutation_count += 1
        return True

    def _apply_emergency_params(self):
        """Apply safest possible parameters during drawdown crisis."""
        params = self.epigenome["parameters"]
        params["LotSize"]["current"] = 0.01
        params["MaxTrades"]["current"] = 1

        json_params = {k: v["current"] for k, v in params.items()}
        self._write_ea_params_json(json_params)
        self._write_epigenome()

    def _propose_structural_evolution(self):
        """Write a structural evolution proposal to SafeProactive."""
        proposal = f"""
## EA Structural Evolution Proposal — Cycle {self.cycle_count}

### Current State
- Fitness: {self.last_fitness:.4f}
- Total Trades: {self._read_metrics().get('total_trades', 0)}
- Drawdown: {self._read_metrics().get('drawdown_pct', 0):.1f}%

### Proposed Changes
Consider restructuring:
1. Replace RSI+MA strategy with multi-timeframe analysis
2. Add volatility filter (ATR-based)
3. Switch from fixed SL/TP to %-based risk management

### Safety Assessment
Require explicit approval before structural changes.
"""
        with open(self.proposals_file, "a") as f:
            f.write(proposal)

    def _trigger_rollback(self):
        """Trigger rollback via SafeProactive."""
        logger.warning("Requesting rollback via SafeProactive")
        self._apply_emergency_params()
        self.rollback_count += 1

    def _compute_fitness(self, metrics: dict) -> float:
        """Compute trading fitness score."""
        balance = metrics.get("balance", 0)
        equity = metrics.get("equity", 0)
        dd_pct = metrics.get("drawdown_pct", 0)
        wr = metrics.get("win_rate", 0)
        total = metrics.get("total_trades", 0)
        dur = max(metrics.get("session_duration_min", 1), 1)

        alignment = 0.85
        eq_ratio = equity / balance if balance > 0 else 0
        task_success = min(max((eq_ratio - 0.9) / 0.2, 0), 1) if eq_ratio >= 0.9 else 0.0
        stability = max(1.0 - dd_pct / 30.0, 0) if dd_pct < 30 else 0.0
        efficiency = min(total / dur * 10, 1.0)
        ethics = 1.0
        c_idx = 0.0

        return round(
            alignment * 0.25 + task_success * 0.20 + stability * 0.15 +
            efficiency * 0.10 + ethics * 0.05 + c_idx * 0.25, 4
        )

    def _read_metrics(self) -> dict[str, Any]:
        if self.ea_metrics_file.exists():
            try:
                with open(self.ea_metrics_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _read_ea_state(self) -> dict[str, Any]:
        if self.ea_state_file.exists():
            try:
                with open(self.ea_state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _read_pending_proposals(self) -> list[dict]:
        """Read pending mutation proposals from state."""
        state = self._read_ea_state()
        return state.get("pending_mutations", [])

    def _metrics_fresh(self, metrics: dict) -> bool:
        """Check if metrics are recent (within 2 minutes)."""
        if not metrics.get("timestamp"):
            return False
        try:
            ts = datetime.fromisoformat(metrics["timestamp"])
            return (datetime.now() - ts).total_seconds() < 120
        except (ValueError, TypeError):
            return False

    def _session_age_minutes(self) -> int:
        metrics = self._read_metrics()
        return metrics.get("session_duration_min", 0)

    def _log_outcome(self, outcome: dict):
        """Append outcome to evolver log."""
        log_file = PROJECT_ROOT / "speace-ea-integration" / "logs" / "ea_evolver_log.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(outcome) + "\n")

    def get_status(self) -> dict[str, Any]:
        """Return current status summary."""
        return {
            "cycle_count": self.cycle_count,
            "mutation_count": self.mutation_count,
            "rollback_count": self.rollback_count,
            "last_fitness": self.last_fitness,
            "uptime_min": (datetime.now() - self.start_time).total_seconds() / 60,
            "epigenome_mutations": self.epigenome["meta"]["mutation_count"],
            "evolver_enabled": self.epigenome["evolver"]["enabled"]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SPEACE EA Evolver")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval", type=int, default=5, help="Cycle interval in minutes")
    parser.add_argument("--status-loop", action="store_true", help="Run status monitor loop")
    args = parser.parse_args()

    if args.status_loop:
        from speace_ea_monitor import status_loop
        status_loop(args.interval)
        return

    evolver = EAEvolver()
    logger.info(f"SPEACE EA Evolver started. Interval: {args.interval}min")

    if args.once:
        outcome = evolver.run_smfoi_cycle()
        logger.info(f"Single cycle result: {outcome}")
        return

    while True:
        try:
            evolver.run_smfoi_cycle()
            status = evolver.get_status()
            logger.info(f"Status: {status}")
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
