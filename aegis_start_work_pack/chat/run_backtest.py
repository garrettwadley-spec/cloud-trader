import argparse, os, sys
from datetime import datetime
import pandas as pd
import numpy as np
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: python -m pip install yfinance pandas numpy matplotlib")
    sys.exit(1)

def load_prices(symbol, start, end):
    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data returned for {symbol} in {start}..{end}")
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    df = df[[col]].rename(columns={col: "price"})
    df.index = pd.to_datetime(df.index)
    return df

def sma_crossover(df, fast, slow):
    df = df.copy()
    df[f"sma{fast}"] = df["price"].rolling(fast).mean()
    df[f"sma{slow}"] = df["price"].rolling(slow).mean()
    df["signal"] = (df[f"sma{fast}"] > df[f"sma{slow}"]).astype(int)
    df["position"] = df["signal"].shift(1).fillna(0)
    df["ret"] = df["price"].pct_change().fillna(0)
    df["strategy_ret"] = df["position"] * df["ret"]
    df["equity"] = (1 + df["strategy_ret"]).cumprod()
    return df

def summarize(df):
    total_return = df["equity"].iloc[-1] - 1
    avg_daily = df["strategy_ret"].mean()
    vol_daily = df["strategy_ret"].std(ddof=0)
    sharpe = 0.0 if vol_daily == 0 else (avg_daily / vol_daily) * np.sqrt(252)
    max_dd = (df["equity"] / df["equity"].cummax() - 1).min()
    trades = int((df["position"].diff().fillna(0) != 0).sum() / 2)
    return {
        "total_return_pct": round(total_return * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "trades": trades
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--fast", type=int, required=True)
    ap.add_argument("--slow", type=int, required=True)
    args = ap.parse_args()
    if args.fast >= args.slow:
        print("ERROR: fast SMA must be < slow SMA")
        sys.exit(2)

    df = load_prices(args.symbol, args.start, args.end)
    df = sma_crossover(df, args.fast, args.slow)
    stats = summarize(df)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "backtests"))
    os.makedirs(outdir, exist_ok=True)
    out_csv = os.path.join(outdir, f"{args.symbol}_SMA{args.fast}-{args.slow}_{ts}.csv")
    df.to_csv(out_csv, index=True)

    print(f"Backtest complete for {args.symbol} {args.start}->{args.end}")
    print(f"Total Return: {stats['total_return_pct']}%")
    print(f"Sharpe (daily->annualized): {stats['sharpe']}")
    print(f"Max Drawdown: {stats['max_drawdown_pct']}%")
    print(f"Trades: {stats['trades']}")
    print(f"Saved equity/series CSV: {out_csv}")
    print(f"CSV_PATH::{out_csv}")


if __name__ == "__main__":
    main()
