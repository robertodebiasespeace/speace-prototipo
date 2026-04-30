"""
SPEACE EA Status Monitor — runs alongside EA Evolver
Prints periodic status reports every N minutes.
"""
import time
import json
from pathlib import Path
from datetime import datetime

def get_mt5_path():
    """Detect MT5 terminal data folder."""
    import os
    common = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common"
    if common.exists():
        return common
    terminal_base = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if terminal_base.exists():
        for sub in terminal_base.iterdir():
            if sub.is_dir() and sub.name != "Common" and (sub / "MQL5").exists():
                return sub
    return Path(__file__).parent.parent.parent

MT5_BASE = get_mt5_path()
SHARED_PATH = MT5_BASE / "speace-ea-integration" / "shared_state"
LOG_PATH = Path(__file__).parent / "logs"


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def print_status():
    metrics = load_json(SHARED_PATH / "ea_metrics.json")
    state = load_json(SHARED_PATH / "ea_state.json")
    evolver_log = LOG_PATH / "ea_evolver_log.jsonl"

    # Count evolver cycles
    cycles = 0
    if evolver_log.exists():
        with open(evolver_log) as f:
            cycles = sum(1 for _ in f)

    print("=" * 60)
    print(f"  SPEACE XAUUSD EA Status  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if metrics:
        print(f"  Balance:         ${metrics.get('balance', 'N/A')}")
        print(f"  Equity:          ${metrics.get('equity', 'N/A')}")
        print(f"  Drawdown:         {metrics.get('drawdown_pct', 'N/A')}%")
        print(f"  Win Rate:         {metrics.get('win_rate', 'N/A')}")
        print(f"  Total Trades:     {metrics.get('total_trades', 0)}")
        print(f"  Open Trades:      {metrics.get('open_trades', 0)}")
        print(f"  RSI:              {metrics.get('rsi', 'N/A')}")
        print(f"  MA Fast:          {metrics.get('ma_fast', 'N/A')}")
        print(f"  MA Slow:          {metrics.get('ma_slow', 'N/A')}")
        print(f"  Spread (pips):    {metrics.get('spread_pips', 'N/A')}")
    else:
        print("  [No metrics yet — EA may not be running in MT5]")

    print("-" * 60)
    print(f"  EA State:         {state.get('ea_name', 'N/A')} v{state.get('version', 'N/A')}")
    print(f"  Params Loaded:    {state.get('params_loaded', False)}")
    print(f"  Account:          {state.get('mt5_account', 'N/A')}")
    print(f"  Evolver Cycles:   {cycles}")
    print("=" * 60)


def status_loop(interval_minutes: int = 5):
    print(f"[SPEACE-EA-MONITOR] Status monitor started. Interval: {interval_minutes}min")
    while True:
        print_status()
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    status_loop(args.interval)
