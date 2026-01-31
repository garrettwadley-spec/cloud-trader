from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import subprocess, json, os, yaml
from io import BytesIO
from fastapi.responses import StreamingResponse

import matplotlib
matplotlib.use("Agg")           # headless plotting
import matplotlib.pyplot as plt
import base64

# core data libs
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# make sure Python can see the project root (where strategies/ lives)
import sys
ROOT = Path(__file__).resolve().parents[1]   # ...\aegis_start_work_pack
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.strategy_engine import StrategyResult, run_strategy_on_csv


# ---------- CONFIG ----------
HERE = Path(__file__).parent
CFG_PATH = HERE / "config_backtest.json"  # you already have this working
TASKS_YAML = HERE / "tasks.yaml"          # new file (whitelist)

app = FastAPI(title="Aegis Backtest API", version="0.2.0")

# ---------- MODELS ----------
class BacktestRequest(BaseModel):
    symbol: str
    start: str   # "YYYY-MM-DD"
    end: str     # "YYYY-MM-DD"
    fast: int
    slow: int

class RunTaskRequest(BaseModel):
    name: str
    args: Optional[List[str]] = None
    tail: Optional[int] = 200  # used by tail_logs

class PlotRequest(BaseModel):
    csv_path: str
    title: Optional[str] = None

class StrategyRunRequest(BaseModel):
    csv_path: str          # absolute or relative to AEGIS_HOME
    strategy: str          # e.g. "sma_cross"
    params: dict = {}      # e.g. {"fast": 10, "slow": 100}


class StrategyRunResponse(BaseModel):
    name: str
    params: dict
    equity_curve: list
    trades: list
    metrics: dict


# ---------- HELPERS ----------
def load_cfg() -> dict:
    with CFG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_tasks() -> dict:
    if not TASKS_YAML.exists():
        raise HTTPException(status_code=404, detail="tasks.yaml not found")
    with TASKS_YAML.open("r", encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    return y.get("tasks", {})

def run_proc(cmd: List[str], shell: bool=False, cwd: Optional[Path]=None) -> dict:
    try:
        p = subprocess.run(
            cmd, shell=shell, cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return {"stdout": p.stdout, "stderr": p.stderr, "exit_code": p.returncode}
    except Exception as e:
        return {"stdout": "", "stderr": repr(e), "exit_code": 2}

def _is_under(root: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False



# ---------- HEALTH ----------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- BACKTEST ----------
@app.post("/run_backtest")
def run_backtest(req: BacktestRequest):
    cfg = load_cfg()
    py_exe   = Path(cfg["executor_python"]).resolve()
    script   = Path(cfg["backtest_script"]).resolve()
    logs_dir = Path(cfg["logs_dir"]).resolve()

    errors = {}
    if not py_exe.is_file():
        errors["executor_python"] = f"Not a file: {py_exe}"
    if not script.is_file():
        errors["backtest_script"] = f"Not a file: {script}"
    if errors:
        # EARLY RETURN on config errors
        return {
            "symbol": req.symbol,
            "stdout": "",
            "stderr": json.dumps(errors),
            "exit_code": 2
        }

    # Run the backtest with full parameters
    cmd = [
        str(py_exe), str(script),
        "--symbol", req.symbol,
        "--start",  req.start,
        "--end",    req.end,
        "--fast",   str(req.fast),
        "--slow",   str(req.slow),
    ]
    result = run_proc(cmd, shell=False, cwd=script.parent)

    # Parse CSV path printed by script (CSV_PATH::<fullpath>)
    csv_path = None
    for line in result.get("stdout", "").splitlines():
        if line.strip().startswith("CSV_PATH::"):
            csv_path = line.split("CSV_PATH::", 1)[1].strip()
            break

    # Fallback: glob the newest matching file (only if fresh)
    if not csv_path:
        logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            candidates = list(logs_dir.glob(f"{req.symbol}_SMA{req.fast}-{req.slow}_*.csv"))
            if candidates:
                latest = max(candidates, key=lambda p: p.stat().st_mtime)
                if datetime.fromtimestamp(latest.stat().st_mtime) > datetime.now() - timedelta(minutes=10):
                    csv_path = str(latest)
        except Exception:
            pass

    # FINAL SUCCESS RETURN (must be indented inside the function)
    return {
        "symbol": req.symbol,
        "start": req.start,
        "end": req.end,
        "fast": req.fast,
        "slow": req.slow,
        "csv_path": csv_path,
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "exit_code": result.get("exit_code", -1),
    }  # <-- close the dict, and this closes the function too


@app.post("/plot_equity")
def plot_equity(req: PlotRequest):
    cfg = load_cfg()
    logs_dir = Path(cfg["logs_dir"]).resolve()
    csv_path = Path(req.csv_path).resolve()

    # Safety: must be a file under logs_dir
    if not csv_path.is_file() or not _is_under(logs_dir, csv_path):
        raise HTTPException(status_code=400, detail="csv_path invalid or not found")

    # Read CSV and pick a sensible y-series
    df = pd.read_csv(csv_path)
    lower = {c.lower(): c for c in df.columns}
    equity_cols = [lower[k] for k in ("equity", "equity_curve", "cumret", "cum_return") if k in lower]
    price_cols  = [lower[k] for k in ("adj close", "adj_close", "close", "price") if k in lower]

    if equity_cols:
        ycol = equity_cols[0]
    elif price_cols:
        ycol = price_cols[0]
    else:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            raise HTTPException(status_code=400, detail="No numeric columns to plot")
        ycol = num_cols[0]

    fig = plt.figure(figsize=(8, 4.5), dpi=120)
    ax = plt.gca()
    ax.plot(df.index, df[ycol], label=ycol)
    ax.set_title(req.title or csv_path.name)
    ax.set_xlabel("Bars")
    ax.set_ylabel(ycol)
    ax.grid(True, alpha=0.3)
    ax.legend()

    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

def _plot_png_bytes(csv_path: Path, title: str | None = None) -> bytes:
    df = pd.read_csv(csv_path)
    lower = {c.lower(): c for c in df.columns}
    equity_cols = [lower[k] for k in ("equity","equity_curve","cumret","cum_return") if k in lower]
    price_cols  = [lower[k] for k in ("adj close","adj_close","close","price") if k in lower]

    if equity_cols:
        ycol = equity_cols[0]
    elif price_cols:
        ycol = price_cols[0]
    else:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            raise HTTPException(status_code=400, detail="No numeric columns to plot")
        ycol = num_cols[0]

    fig = plt.figure(figsize=(8, 4.5), dpi=120)
    ax = plt.gca()
    ax.plot(df.index, df[ycol], label=ycol)
    ax.set_title(title or csv_path.name)
    ax.set_xlabel("Bars")
    ax.set_ylabel(ycol)
    ax.grid(True, alpha=0.3)
    ax.legend()
    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()

@app.post("/run_and_plot")
def run_and_plot(req: BacktestRequest):
    result = run_backtest(req)  # reuse your existing function
    if result.get("exit_code", 1) != 0 or not result.get("csv_path"):
        raise HTTPException(status_code=500, detail=f"Backtest failed: {result.get('stderr') or 'no csv_path'}")

    csv_path = Path(result["csv_path"]).resolve()
    cfg = load_cfg()
    logs_dir = Path(cfg["logs_dir"]).resolve()
    if not csv_path.is_file() or not str(csv_path).startswith(str(logs_dir)):
        raise HTTPException(status_code=400, detail="csv_path invalid or not under logs_dir")

    png = _plot_png_bytes(csv_path, title=f"{req.symbol} SMA({req.fast}/{req.slow})")

    return {
        "summary": {
            "symbol": req.symbol,
            "start": req.start,
            "end": req.end,
            "fast": req.fast,
            "slow": req.slow,
            "csv_path": str(csv_path),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "exit_code": result.get("exit_code", -1)
        },
        "image_png_b64": base64.b64encode(png).decode()
    }

from pathlib import Path
import base64

PLOTS_DIR = (HERE / ".." / "data" / "plots").resolve()
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

class RunAndPlotResponse(BaseModel):
    summary: dict
    image_b64: str
    png_path: str

@app.post("/strategy.run", response_model=StrategyRunResponse)
def strategy_run(req: StrategyRunRequest):
    try:
        csv_path = Path(req.csv_path)

        # If it's not absolute, interpret relative to data/backtests
        if not csv_path.is_absolute():
            base = Path(__file__).resolve().parents[1] / "data" / "backtests"
            csv_path = base / csv_path

        result: StrategyResult = run_strategy_on_csv(
            csv_path=csv_path,
            strategy_name=req.strategy,
            params=req.params or {},
        )

        return StrategyRunResponse(
            name=result.name,
            params=result.params,
            equity_curve=result.equity_curve,
            trades=result.trades,
            metrics=result.metrics,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy error: {e}")

@app.post("/run_and_plot_save", response_model=RunAndPlotResponse)
def run_and_plot_save(req: BacktestRequest):
    out = run_backtest(req)  # existing function
    if not out.get("csv_path"):
        raise HTTPException(status_code=400, detail="Backtest produced no CSV")

    # reuse the existing /plot_equity logic without HTTP hop
    df = pd.read_csv(out["csv_path"])
    lower = {c.lower(): c for c in df.columns}
    ycol = lower.get("equity") or lower.get("equity_curve") or next(
        (c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])), None
    )
    if not ycol:
        raise HTTPException(status_code=400, detail="No numeric column to plot")

    fig = plt.figure(figsize=(8, 4.5), dpi=120)
    ax = plt.gca()
    ax.plot(df.index, df[ycol], label=ycol)
    ax.set_title(f"{req.symbol} SMA({req.fast}/{req.slow})")
    ax.set_xlabel("Bars")
    ax.set_ylabel(ycol)
    ax.grid(True, alpha=0.3)
    ax.legend()
    png_path = PLOTS_DIR / f"{req.symbol}_SMA{req.fast}-{req.slow}_{datetime.now():%Y%m%d-%H%M%S}.png"
    fig.savefig(png_path)
    plt.close(fig)

    with open(png_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    return {
        "summary": out,
        "image_b64": img_b64,
        "png_path": str(png_path),
    }

   
# ---------- TASKS ----------
@app.get("/tasks/list")
def list_tasks():
    tasks = load_tasks()
    return {"tasks": list(tasks.keys())}

@app.post("/tasks/run")
def run_task(req: RunTaskRequest):
    tasks = load_tasks()
    spec = tasks.get(req.name)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Task '{req.name}' not found")

    # tail_logs is special: read last N lines from logs_dir
    if req.name == "tail_logs":
        cfg = load_cfg()
        logs_dir = Path(cfg["logs_dir"])
        if not logs_dir.exists():
            return {"stdout": "", "stderr": f"No logs dir: {logs_dir}", "exit_code": 2}
        files = sorted(logs_dir.glob("*.txt")) + sorted(logs_dir.glob("*.json"))
        if not files:
            return {"stdout": "", "stderr": "No log files found", "exit_code": 1}
        last = max(files, key=lambda p: p.stat().st_mtime)
        lines = last.read_text(errors="ignore").splitlines()
        n = max(1, min(int(req.tail or 200), 5000))
        tail = "\n".join(lines[-n:])
        return {"stdout": tail, "stderr": "", "exit_code": 0, "file": str(last)}

    # generic task
    cmd: List[str] = list(spec.get("cmd", []))
    if req.args:
        cmd.extend(req.args)

    shell = bool(spec.get("shell", False))
    return run_proc(cmd, shell=shell)
