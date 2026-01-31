DEMO_CSV = DATA_DIR / "SPY_SMA50-200_20251114-185715.csv"
``` :contentReference[oaicite:0]{index=0}  

We’ll build a **single, clean multi-run script** that:

- Runs `sma_cross` over a grid of (fast, slow) values  
- Writes a JSON per combo into `data/backtests/multi/`  
- Writes `sma_cross_summary.json` with exactly the structure you showed  
- Adds a `score` field = `sharpe * abs(total_return)` for ranking  
- Plays nice with `grid_inspector.py`   

---

## 1. Create the multi-run script

In VS Code, in the **same folder as `strategy_engine.py`**, create a new file:

> `multi_run_sma_cross.py`

Paste this **entire** code:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Dict, Any

from strategy_engine import (
    run_strategy_on_csv,
    MULTI_DIR,
    DEMO_CSV,
)


SUMMARY_JSON = MULTI_DIR / "sma_cross_summary.json"


def _as_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def run_sma_cross_grid(
    fast_list: Iterable[int] = (10, 20, 50),
    slow_list: Iterable[int] = (100, 200),
    csv_path: Path | None = None,
) -> None:
    """
    Run SMA crossover across a parameter grid and save:

      - One JSON per run in MULTI_DIR as
            sma_cross_fast{fast}_slow{slow}.json

      - One summary file in MULTI_DIR:
            sma_cross_summary.json

    The summary JSON has the shape:

        {
          "rows": [
            {
              "fast": 10,
              "slow": 100,
              "total_return": ...,
              "vol_annual": ...,
              "sharpe": ...,
              "score": ...
            },
            ...
          ]
        }
    """

    if csv_path is None:
        csv_path = DEMO_CSV

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    MULTI_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Using price CSV   : {csv_path}")
    print(f"Writing outputs to: {MULTI_DIR}\n")

    rows: List[Dict[str, Any]] = []

    for fast in fast_list:
        for slow in slow_list:
            if fast >= slow:
                # optional: skip nonsensical combos where fast >= slow
                print(f"Skipping fast={fast}, slow={slow} (fast >= slow)")
                continue

            params = {"fast": fast, "slow": slow}
            print(f"Running sma_cross with params: {params}")

            # Run the strategy
            result = run_strategy_on_csv(csv_path, "sma_cross", params)

            # Metrics from StrategyResult
            metrics = dict(result.metrics)

            total_return = _as_float(metrics.get("total_return", 0.0))
            vol_annual = _as_float(metrics.get("vol_annual", 0.0))
            sharpe = _as_float(metrics.get("sharpe", 0.0))

            # Composite score, same logic as grid_inspector
            score = sharpe * abs(total_return)
            metrics["score"] = score

            # ----- Per-run JSON -----
            out_data = {
                "name": result.name,
                "params": result.params,
                "metrics": metrics,
                "equity_curve": result.equity_curve,
                "trades": result.trades,
            }

            out_path = MULTI_DIR / f"sma_cross_fast{fast}_slow{slow}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)

            print(f"  -> wrote {out_path.name}")

            # ----- Summary row -----
            rows.append(
                {
                    "fast": fast,
                    "slow": slow,
                    "total_return": total_return,
                    "vol_annual": vol_annual,
                    "sharpe": sharpe,
                    "score": score,
                }
            )

    # ----- Summary JSON -----
    summary = {"rows": rows}

    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[+] Completed {len(rows)} parameter combos.")
    print(f"[+] Summary written to {SUMMARY_JSON}")
    print(f"[+] Individual runs in {MULTI_DIR}")


if __name__ == "__main__":
    run_sma_cross_grid()
