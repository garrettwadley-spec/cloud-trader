from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, List
import json
import pandas as pd
from datetime import datetime

from strategies.strategy_engine import (
    param_grid,
    build_strategy,
    run_simple_backtest,
    BacktestResult,
)


AEGIS_ROOT = Path(__file__).resolve().parent
DATA_DIR = AEGIS_ROOT / "data" / "backtests"
RESULTS_DIR = DATA_DIR / "multi_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_grid(
    csv_path: Path,
    strategy_name: str,
    grid: Dict[str, List[Any]],
    initial_capital: float = 10_000.0,
) -> Dict[str, Any]:
    """
    Offline multi-backtest runner for ONE price CSV + param grid.
    Returns a dict with all run results and writes a summary JSON.
    """
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    print(f"[multi] Loading prices from: {csv_path}")
    prices = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date")

    combos = param_grid(grid)
    print(f"[multi] Strategy={strategy_name}, combos={len(combos)}")

    run_results: List[Dict[str, Any]] = []

    for i, params in enumerate(combos, start=1):
        print(f"  -> Run {i}/{len(combos)} params={params}")
        strat = build_strategy(strategy_name, params)
        pos = strat.generate_signals(prices)
        bt = run_simple_backtest(prices, pos, initial_capital=initial_capital)
        bt.params = params  # attach params

        run_results.append(
            {
                "strategy": bt.strategy_name,
                "params": params,
                "start": bt.start.isoformat(),
                "end": bt.end.isoformat(),
                "trades": bt.trades,
                "final_equity": bt.final_equity,
                "max_drawdown": bt.max_drawdown,
            }
        )

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_name = f"multi_{strategy_name}_{csv_path.stem}_{ts}.json"
    out_path = RESULTS_DIR / out_name

    payload = {
        "csv": str(csv_path),
        "strategy": strategy_name,
        "grid": grid,
        "results": run_results,
    }

    out_path.write_text(json.dumps(payload, indent=2))
    print(f"[multi] Saved summary -> {out_path}")

    return payload


if __name__ == "__main__":
    # TEMP HARDCODED DEMO:
    # We’ll wire this to CLI args or the orchestrator later.
    csv_demo = Path(r"C:\Users\garre\cloud-trader\aegis_start_work_pack\data\backtests\SPY_SMA50-200_20251114-185715.csv")
    
    grid = {
        "fast": [10, 20, 50],
        "slow": [100, 200],
    }

    run_grid(csv_demo, "sma_cross", grid)
