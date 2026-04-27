"""
SPEACE Trading Cortex Compartment — L2 Cognitive
Monitors XAUUSD EA metrics, evaluates trading fitness,
proposes mutations to ea_epigenome.yaml via SafeProactive.
"""
from typing import Any
from cortex.base_compartment import BaseCompartment


class TradingCortex(BaseCompartment):
    """
    L2 Compartment: Language, Analysis & Trading Evaluation

    Watches the EA metrics JSON, computes trading-specific KPIs,
    feeds results into the SMFOI outcome evaluation step, and
    proposes parameter mutations when the EA fitness drops below threshold.
    """

    name = "trading_cortex"
    level = 2
    description = "XAUUSD EA metrics analysis, trading fitness, mutation proposals"

    def __init__(self, state: dict[str, Any]):
        super().__init__(state)
        self.last_evaluation = {}
        self.mutation_threshold = 0.60
        self.consecutive_poor = 0

    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process EA metrics and update state with trading evaluation."""
        import os
        import json
        from pathlib import Path

        # Read EA metrics
        metrics = self._read_ea_metrics()
        if not metrics:
            state["trading_cortex"] = {
                "status": "no_data",
                "message": "EA metrics not available yet"
            }
            return state

        # Compute trading fitness
        fitness = self._compute_trading_fitness(metrics)

        # Compute KPIs
        kpis = self._compute_kpis(metrics, fitness)

        # Detect drawdown crisis
        drawdown_crisis = metrics.get("drawdown_pct", 0) >= 15.0

        # Store evaluation
        self.last_evaluation = {
            "timestamp": metrics.get("timestamp"),
            "fitness": fitness,
            "kpis": kpis,
            "drawdown_crisis": drawdown_crisis,
            "consecutive_poor": self.consecutive_poor
        }

        # Update state
        state["trading_cortex"] = self.last_evaluation
        state["trading_cortex"]["status"] = "evaluated"

        # Set novelty/uncertainty flags based on drawdown
        state["novelty"] = max(state.get("novelty", 0), 0.3 if drawdown_crisis else 0.1)
        state["uncertainty"] = max(state.get("uncertainty", 0), 0.5 if drawdown_crisis else 0.2)

        # Track consecutive poor performance
        if fitness < self.mutation_threshold:
            self.consecutive_poor += 1
        else:
            self.consecutive_poor = 0

        # Set mutation proposal if needed (only if safety allows and not crisis)
        if (self.consecutive_poor >= 3 and
                not drawdown_crisis and
                not state.get("safety_flags", {}).get("blocked", False)):
            state["mutation_proposal"] = self._build_mutation_proposal(fitness, kpis)
            state["trading_cortex"]["proposal_triggered"] = True
        else:
            state["trading_cortex"]["proposal_triggered"] = False

        # Add KPIs to world snapshot
        state["world_snapshot"]["trading_ea"] = kpis

        return state

    def _read_ea_metrics(self) -> dict[str, Any]:
        """Read latest EA metrics from shared state file."""
        import json
        shared_path = os.environ.get(
            "SPEACE_EA_SHARED_PATH",
            "C:\\Users\\rober\\Documents\\Claude\\Projects\\SPEACE-prototipo\\speace-ea-integration\\shared_state\\"
        )
        metrics_file = Path(shared_path) / "ea_metrics.json"
        if not metrics_file.exists():
            return {}
        try:
            with open(metrics_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _compute_trading_fitness(self, metrics: dict[str, Any]) -> float:
        """
        Compute trading fitness using 6-component fitness function.
        Maps SPEACE fitness components to trading KPIs.
        """
        # Alignment: assume aligned if EA is running (safety preserved)
        alignment = 0.85

        # Task success: equity growing vs initial balance
        balance = metrics.get("balance", 0)
        equity = metrics.get("equity", 0)
        session_dur = max(metrics.get("session_duration_min", 1), 1)
        equity_ratio = equity / balance if balance > 0 else 0
        # Score: >1.0 is good, normalize to 0-1
        task_success = min(max((equity_ratio - 0.9) / 0.2, 0), 1) if equity_ratio >= 0.9 else 0.0

        # Stability: inverse of drawdown severity
        dd_pct = metrics.get("drawdown_pct", 0)
        stability = max(1.0 - dd_pct / 30.0, 0) if dd_pct < 30 else 0.0

        # Efficiency: trades per minute, capped
        total_trades = metrics.get("total_trades", 0)
        efficiency = min(total_trades / session_dur * 10, 1.0)

        # Ethics: always trading within safe limits
        ethics = 1.0

        # C-index contribution: from global state
        c_idx = self.state.get("trading_cortex", {}).get("c_index", 0)

        fitness = (
            alignment * 0.25 +
            task_success * 0.20 +
            stability * 0.15 +
            efficiency * 0.10 +
            ethics * 0.05 +
            c_idx * 0.25
        )
        return round(min(max(fitness, 0), 1), 4)

    def _compute_kpis(self, metrics: dict[str, Any], fitness: float) -> dict[str, Any]:
        """Compute detailed trading KPIs for monitoring."""
        return {
            "fitness": fitness,
            "balance": metrics.get("balance"),
            "equity": metrics.get("equity"),
            "drawdown_pct": metrics.get("drawdown_pct"),
            "win_rate": metrics.get("win_rate"),
            "total_trades": metrics.get("total_trades"),
            "open_trades": metrics.get("open_trades"),
            "session_duration_min": metrics.get("session_duration_min"),
            "rsi": metrics.get("rsi"),
            "ma_fast": metrics.get("ma_fast"),
            "ma_slow": metrics.get("ma_slow"),
            "spread_pips": metrics.get("spread_pips"),
            "consecutive_loss": metrics.get("consecutive_loss"),
        }

    def _build_mutation_proposal(self, fitness: float, kpis: dict) -> dict[str, Any]:
        """Build a mutation proposal for the EA epigenome."""
        proposals = []

        # If drawdown high, reduce lot and widen SL
        dd = kpis.get("drawdown_pct", 0)
        if dd > 10:
            proposals.append({
                "param": "LotSize",
                "current": 0.1,
                "suggested": 0.05,
                "reason": f"Drawdown {dd:.1f}% — reducing exposure"
            })
            proposals.append({
                "param": "StopLossPips",
                "current": 500,
                "suggested": 800,
                "reason": f"Widening SL to reduce noise-triggered stops"
            })

        # If RSI period not optimal (check win rate)
        wr = kpis.get("win_rate", 0)
        if wr < 0.40:
            proposals.append({
                "param": "RSI_Period",
                "current": 14,
                "suggested": 21,
                "reason": f"Win rate {wr:.1%} < 40% — smoothing RSI"
            })

        # If MA periods not generating signals (low trade count)
        total = kpis.get("total_trades", 0)
        dur = kpis.get("session_duration_min", 1)
        if total == 0 and dur > 30:
            proposals.append({
                "param": "MA_Slow_Period",
                "current": 30,
                "suggested": 20,
                "reason": "No trades in 30+ min — tightening MA crossover"
            })

        return {
            "proposal_id": f"EA-MUT-{self.state.get('cycle_id', 0):06d}",
            "trigger": "consecutive_poor",
            "current_fitness": fitness,
            "proposals": proposals,
            "compartment": self.name,
            "timestamp": self.state.get("timestamp")
        }

    def get_last_evaluation(self) -> dict[str, Any]:
        """Return the last evaluation result."""
        return self.last_evaluation
