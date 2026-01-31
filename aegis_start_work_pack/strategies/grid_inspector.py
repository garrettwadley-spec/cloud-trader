from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


# ---------- Paths / config ----------

# Project root (aegis_start_work_pack)
ROOT = Path(os.environ.get("AEGIS_HOME", Path(__file__).resolve().parents[1]))

# Where the multi-run JSONs live
MULTI_DIR = ROOT / "data" / "backtests" / "multi"

# Output ranked CSV
RANKED_CSV = MULTI_DIR / "sma_cross_ranked.csv"


@dataclass
class RunRow:
    fast: int
    slow: int
    total_return: float
    vol_annual: float
    sharpe: float
    score: float

    def to_list(self) -> List[float]:
        return [
            self.fast,
            self.slow,
            self.total_return,
            self.vol_annual,
            self.sharpe,
            self.score,
        ]


def parse_fast_slow_from_name(name: str) -> tuple[int, int]:
    """
    Fallback parser for file names like:
        sma_cross_fast10_slow200.json
    """
    m = re.search(r"fast(\d+)_slow(\d+)", name)
    if not m:
        raise ValueError(f"Could not parse fast/slow from filename: {name}")
    return int(m.group(1)), int(m.group(2))


def load_run(file_path: Path) -> RunRow | None:
    """
    Load a single run JSON and extract metrics.
    Supports both:
      - hierarchical format: { "params": {...}, "metrics": {...}, ... }
      - flat format: { "fast": ..., "slow": ..., "total_return": ... }
    If anything is missing / broken, return None and skip it.
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Skipping {file_path.name}: JSON load error: {e}")
        return None

    # ----- fast / slow -----

    # Try hierarchical format first
    params = data.get("params", {}) or {}
    fast = params.get("fast")
    slow = params.get("slow")

    # If missing, try flat format
    if fast is None:
        fast = data.get("fast")
    if slow is None:
        slow = data.get("slow")

    # Last resort: extract from filename
    if fast is None or slow is None:
        try:
            fast, slow = parse_fast_slow_from_name(file_path.name)
        except Exception as e:
            print(f"[!] Skipping {file_path.name}: cannot get fast/slow ({e})")
            return None

    try:
        fast = int(fast)
        slow = int(slow)
    except Exception as e:
        print(f"[!] Skipping {file_path.name}: bad fast/slow ({e})")
        return None

    # ----- metrics -----

    # Try hierarchical metrics block
    metrics = data.get("metrics", {}) or {}
    total_return = metrics.get("total_return")
    vol_annual = metrics.get("vol_annual")
    sharpe = metrics.get("sharpe")

    # If missing, fall back to flat keys
    if total_return is None:
        total_return = data.get("total_return", 0.0)
    if vol_annual is None:
        vol_annual = data.get("vol_annual", 0.0)
    if sharpe is None:
        sharpe = data.get("sharpe", 0.0)

    # Normalize to float
    try:
        total_return = float(total_return)
        vol_annual = float(vol_annual)
        sharpe = float(sharpe)
    except Exception as e:
        print(f"[!] Skipping {file_path.name}: bad metrics ({e})")
        return None

    # Composite score: Sharpe * |total_return|
    score = sharpe * abs(total_return)

    return RunRow(
        fast=fast,
        slow=slow,
        total_return=total_return,
        vol_annual=vol_annual,
        sharpe=sharpe,
        score=score,
    )


def main() -> None:
    print(f"AEGIS_HOME    : {ROOT}")
    print(f"MULTI_DIR     : {MULTI_DIR}")

    if not MULTI_DIR.exists():
        print("[!] MULTI_DIR does not exist. Nothing to inspect.")
        return

    json_files = sorted(MULTI_DIR.glob("sma_cross_fast*_slow*.json"))
    if not json_files:
        print("[!] No sma_cross_fast*_slow*.json files found in MULTI_DIR.")
        return

    print(f"Found {len(json_files)} run files. Loading metrics...\n")

    rows: List[RunRow] = []
    for fp in json_files:
        row = load_run(fp)
        if row is not None:
            rows.append(row)

    if not rows:
        print("[!] No valid runs loaded (all skipped).")
        return

    # Sort best → worst by score
    rows.sort(key=lambda r: r.score, reverse=True)

    # Print top handful
    print("=== Top SMA crossover parameter sets ===\n")
    print("fast  slow  total_return  vol_annual  sharpe  score")
    for r in rows[:10]:
        print(
            f"{r.fast:4d}  {r.slow:4d}  "
            f"{r.total_return:11.4f}  {r.vol_annual:10.4f}  "
            f"{r.sharpe:6.3f}  {r.score:6.3f}"
        )

    # Write full ranked grid to CSV
    import csv

    with RANKED_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["fast", "slow", "total_return", "vol_annual", "sharpe", "score"])
        for r in rows:
            writer.writerow(r.to_list())

    print(f"\n[+] Full grid exported to {RANKED_CSV}")


if __name__ == "__main__":
    main()
