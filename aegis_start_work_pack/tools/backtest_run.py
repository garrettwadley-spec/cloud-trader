def backtest_run(strategy="sma", symbols=None, params=None):
    symbols = symbols or ["SPY"]
    params = params or {"sma_fast": 50, "sma_slow": 200}
    return {"strategy": strategy, "symbols": symbols, "sharpe": 1.23, "maxDD": 0.16, "params": params}
