from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

# NEW: make sure Python can see the project root (where strategies/ lives)
import sys
ROOT = Path(__file__).resolve().parents[1]   # ...\aegis_start_work_pack
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.strategy_engine import run_strategy_on_csv, StrategyResult


# --- Paths --------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]  # ...\aegis_start_work_pack
DATA_DIR = ROOT / "data" / "backtests"
MULTI_DIR = DATA_DIR / "multi"
MULTI_DIR.mkdir(parents=True, exist_ok=True)

# Pick one of your existing CSVs as the demo series
# You can change this to any of the SPY_SMA50-200_*.csv files you prefer.
DEMO_CSV = DATA_DIR / "SPY_SMA50-200_20251119-161716.csv"


# --- Grid runner --------------------------------------------------------


def run_grid(csv_path: Path, strat_name: str, grid: Dict[str, List[int]]) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print(f"CSV exists: {csv_path}")
    rows: List[Dict[str, Any]] = []

    for fast in grid["fast"]:
        for slow in grid["slow"]:
            params = {"fast": fast, "slow": slow}
            print(f"→ Running {strat_name} fast={fast} slow={slow}")

            # Run strategy locally (no HTTP / no port 8001)
            result: StrategyResult = run_strategy_on_csv(csv_path, strat_name, params)

            m = result.metrics
            total_return = float(m.get("total_return", 0.0))
            vol_annual = float(m.get("vol_annual", 0.0))
            sharpe = float(m.get("sharpe", 0.0))

            # Simple composite score: Sharpe * positive total_return
            score = sharpe * max(total_return, 0.0)

            row = {
                "fast": fast,
                "slow": slow,
                "total_return": total_return,
                "vol_annual": vol_annual,
                "sharpe": sharpe,
                "score": score,
            }
            rows.append(row)

            # Save per-run JSON (handy for debugging later)
            out_path = MULTI_DIR / f"sma_cross_fast{fast}_slow{slow}.json"
            out_path.write_text(json.dumps(row, indent=2))
            print(f"  Saved: {out_path}")

    # Save summary JSON that grid_inspector.py reads
    summary_payload = {"rows": rows}
    summary_path = MULTI_DIR / "sma_cross_summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2))
    print(f"\n✓ Summary saved → {summary_path}")


if __name__ == "__main__":
    grid = {
        "fast": [10, 20, 50],
        "slow": [100, 200],
    }

    run_grid(DEMO_CSV, "sma_cross", grid)
