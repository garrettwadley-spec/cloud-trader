from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, List

import json
import pandas as pd
import numpy as np


# --- Paths ----------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]  # ...\aegis_start_work_pack
DATA_DIR = ROOT / "data" / "backtests"
MULTI_DIR = DATA_DIR / "multi"
MULTI_DIR.mkdir(parents=True, exist_ok=True)

# Pick one of your existing CSVs as the demo series
DEMO_CSV = DATA_DIR / "SPY_SMA50-200_20251114-185715.csv"


# --- Core data structures -------------------------------------------

@dataclass
class StrategyResult:
    name: str
    params: Dict[str, Any]
    equity_curve: List[float]
    trades: List[Dict[str, Any]]
    metrics: Dict[str, Any]


StrategyFn = Callable[[pd.DataFrame, Dict[str, Any]], StrategyResult]


def _get_price_series(df: pd.DataFrame) -> pd.Series:
    """
    Pick the right price column from your backtest CSV.

    Preference order: 'price', 'Price', 'close'.
    """
    for col in ("price", "Price", "close"):
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            return s.ffill()

    raise ValueError(
        "Input DataFrame must contain a 'price', 'Price' or 'close' column."
    )


# --- Example Strategy: SMA crossover --------------------------------

def sma_cross_strategy(df: pd.DataFrame, params: Dict[str, Any]) -> StrategyResult:
    """
    Very simple moving-average crossover strategy on a price series.

    Expects df to have a 'price' column (numeric), but we are robust
    to extra header / metadata rows like 'Ticker,SPY,...'.
    """

    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 200))

    # --- Clean up the input frame ---------------------------------
    # Work on a copy so we don't mutate callers
    df = df.copy()

    # Coerce 'price' to numeric; anything non-numeric (e.g. "SPY") becomes NaN
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Drop rows where price is missing / non-numeric (this kills the Ticker,SPY row)
    df = df.dropna(subset=["price"])

    # Now we are guaranteed price is float-compatible
    prices = df["price"].astype(float)

    # --- SMA computation ------------------------------------------
    fast_ma = prices.rolling(window=fast, min_periods=fast).mean()
    slow_ma = prices.rolling(window=slow, min_periods=slow).mean()

    # Signal: +1 when fast > slow, -1 when fast < slow
    signal = (fast_ma > slow_ma).astype(int) - (fast_ma < slow_ma).astype(int)
    signal = signal.shift(1).fillna(0)  # enter at next bar

    # PnL: signal * daily returns
    ret = prices.pct_change().fillna(0.0)
    strat_ret = signal * ret
    equity = (1.0 + strat_ret).cumprod()

    # Naive metrics
    total_return = equity.iloc[-1] - 1.0
    vol = strat_ret.std() * (252 ** 0.5) if len(strat_ret) > 1 else 0.0
    sharpe = (strat_ret.mean() * 252) / vol if vol > 0 else 0.0

    metrics = {
        "total_return": float(total_return),
        "vol_annual": float(vol),
        "sharpe": float(sharpe),
        "fast": fast,
        "slow": slow,
    }

    # Dummy trades list for now – wire in real fills later
    trades: List[Dict[str, Any]] = []

    return StrategyResult(
        name="sma_cross",
        params={"fast": fast, "slow": slow},
        equity_curve=list(equity.values),
        trades=trades,
        metrics=metrics,
    )





# --- Strategy registry ---

STRATEGIES = {
    "sma_cross": sma_cross_strategy,
}

# --- Run a strategy on a CSV file ---

def run_strategy_on_csv(csv_path: Path, strat_name: str, params: Dict[str, Any]) -> StrategyResult:
    """
    Load a CSV (with 'price' column), run the chosen strategy, and return StrategyResult.
    """
    df = pd.read_csv(csv_path)

    if "price" not in df.columns:
        raise ValueError(f"CSV missing 'price' column: {csv_path}")

    strat_fn = STRATEGIES.get(strat_name)
    if strat_fn is None:
        raise ValueError(f"Unknown strategy: {strat_name}")

    return strat_fn(df, params)
