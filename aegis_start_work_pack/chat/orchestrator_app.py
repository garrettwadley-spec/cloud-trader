import os, json, yaml, time
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# ----------------------------
# Paths / config
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "policy.yaml"
INDEX_PATH = ROOT / "rag" / "index.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_ID = os.getenv("AEGIS_MODEL", "llama3.1:8b-instruct")


def load_policy() -> Dict[str, Any]:
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_index() -> Dict[str, Any]:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"items": []}


POLICY = load_policy()
INDEX = load_index()

# ----------------------------
# Run registry (Multi-Run v0)
# ----------------------------
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

RUN_REGISTRY: Dict[str, Dict[str, Any]] = {}

# ----------------------------
# Tools
# ----------------------------
from tools.data_fetch import data_fetch
from tools.backtest_run import backtest_run
from tools.train_run import train_run
from tools.risk_simulate import risk_simulate

TOOLS = {
    "data.fetch": data_fetch,
    "backtest.run": backtest_run,
    "train.run": train_run,
    "risk.simulate": risk_simulate,
}


def allowed_tool(name: str) -> bool:
    allow = POLICY.get("tools", {}).get("allow", [])
    deny = POLICY.get("tools", {}).get("deny", [])
    return (name in allow) and (name not in deny)


def rate_limited(name: str) -> bool:
    rl = POLICY.get("rate_limits", {})
    limit = rl.get("backtest_per_hour", None) if name == "backtest.run" else None
    if not limit:
        return False

    now_hour = int(time.time() // 3600)
    os.makedirs(".runtime", exist_ok=True)
    path = Path(".runtime") / f"rate_{name}_{now_hour}.txt"

    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        count = int(raw) if raw else 0
    else:
        count = 0

    if count >= limit:
        return True

    path.write_text(str(count + 1), encoding="utf-8")
    return False


def call_llm(prompt: str) -> str:
    payload = {"model": MODEL_ID, "prompt": prompt, "stream": False}
    r = requests.post(OLLAMA_URL, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")

def make_context(question: str) -> str:
    q = question.lower()
    chunks: List[str] = []
    for item in INDEX.get("items", [])[:10]:
        text = (item.get("text") or "")
        if any(tok in text.lower() for tok in q.split()[:5]):
            p = item.get("path") or "?"
            chunks.append(f"[{p}]\n{text[:400]}")
    return "\n\n".join(chunks[:3])



# ----------------------------
# API Models
# ----------------------------
class Ask(BaseModel):
    question: str


class MultiRunRequest(BaseModel):
    # v0: intentionally minimal; we wire real backtests next
    name: str = "default"
    symbols: List[str] = ["SPY"]
    strategies: List[str] = ["sma_baseline"]
    timeframe: str = "1d"
    start: Optional[str] = None
    end: Optional[str] = None


# ----------------------------
# App
# ----------------------------
app = FastAPI(title="Aegis Orchestrator")


# ----------------------------
# Routes
# ----------------------------
@app.post("/ask")
def ask(m: Ask):
    ctx = make_context(m.question)
    system = (
        "You are Aegis, a finance-focused single model. "
        "Cite from context when possible. "
        "If a tool is needed, output a JSON line exactly like: "
        '{"tool":{"name":"backtest.run","args":{"strategy":"sma","symbols":["SPY"]}}} '
        "Otherwise, answer directly."
    )
    prompt = f"{system}\n\nContext:\n{ctx}\n\nUser:\n{m.question}\n"
    answer = call_llm(prompt).strip()

    # Parse first JSON object containing a tool call
    tool_obj = None
    try:
        start = answer.find('{"tool"')
        if start != -1:
            line = answer[start:].splitlines()[0]
            tool_obj = json.loads(line).get("tool")
    except Exception:
        tool_obj = None

    if tool_obj:
        name = tool_obj.get("name", "")
        args = tool_obj.get("args", {})

        if not allowed_tool(name):
            raise HTTPException(status_code=403, detail=f"Tool not allowed by policy: {name}")
        if rate_limited(name):
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {name}")

        fn = TOOLS.get(name)
        if not fn:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {name}")

        try:
            result = fn(**args)
        except TypeError:
            result = fn(args)

        return {"answer": f"[Tool:{name}] -> {result}", "tool_used": name, "args": args}

    return {"answer": answer, "tool_used": None}


def _write_run_artifact(run_id: str, payload: Dict[str, Any]) -> str:
    path = RUNS_DIR / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)

def _multi_run_job(run_id: str, req: MultiRunRequest) -> None:
    from datetime import datetime

    RUN_REGISTRY[run_id]["status"] = "RUNNING"
    RUN_REGISTRY[run_id]["updated_at"] = datetime.utcnow().isoformat()

    results = []
    errors = []

    # Run every strategy on every symbol
    for strategy in req.strategies:
        for symbol in req.symbols:
            try:
                output = TOOLS["backtest.run"](
                    strategy=strategy,
                    symbols=[symbol],
                    params=None  # use tool defaults
                )

                results.append({
                    "strategy": strategy,
                    "symbol": symbol,
                    "output": output
                })

            except Exception as e:
                errors.append({
                    "strategy": strategy,
                    "symbol": symbol,
                    "error": str(e)
                })

    # Build summary stats
    sharpes = []
    maxdds = []

    for r in results:
        out = r.get("output", {})
        if isinstance(out, dict):
            if isinstance(out.get("sharpe"), (int, float)):
                sharpes.append(out["sharpe"])
            if isinstance(out.get("maxDD"), (int, float)):
                maxdds.append(out["maxDD"])

    summary = {
        "requested_runs": len(req.strategies) * len(req.symbols),
        "successful_runs": len(results),
        "failed_runs": len(errors),
        "mean_sharpe": (sum(sharpes) / len(sharpes)) if sharpes else None,
        "worst_maxDD": max(maxdds) if maxdds else None,
    }

    artifact_payload = {
        "run_id": run_id,
        "status": "COMPLETE" if not errors else "COMPLETE_WITH_ERRORS",
        "request": req.model_dump(),
        "results": results,
        "errors": errors,
        "summary": summary,
        "completed_at": datetime.utcnow().isoformat(),
    }

    artifact_path = _write_run_artifact(run_id, artifact_payload)

    RUN_REGISTRY[run_id]["status"] = artifact_payload["status"]
    RUN_REGISTRY[run_id]["updated_at"] = datetime.utcnow().isoformat()
    RUN_REGISTRY[run_id]["artifact"] = artifact_path



@app.post("/multi-run")
def start_multi_run(req: MultiRunRequest, background: BackgroundTasks):
    run_id = uuid.uuid4().hex[:12]
    now = datetime.utcnow().isoformat()

    RUN_REGISTRY[run_id] = {
        "run_id": run_id,
        "status": "QUEUED",
        "created_at": now,
        "updated_at": now,
        "request": req.model_dump(),
        "artifact": None,
    }

    background.add_task(_multi_run_job, run_id, req)
    return {"run_id": run_id, "status": "QUEUED", "created_at": now}


@app.get("/multi-run/{run_id}")
def get_multi_run(run_id: str):
    run = RUN_REGISTRY.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")
    return run
