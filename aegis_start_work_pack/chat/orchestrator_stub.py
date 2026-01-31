from fastapi import FastAPI, HTTPException  # type: ignore
from pydantic import BaseModel              # type: ignore
from typing import Union
from pathlib import Path
import os, json, re, base64, httpx          # type: ignore

# -------------------------------------------------
# Paths & config
# -------------------------------------------------
ROOT = Path(os.environ.get("AEGIS_HOME", __file__)).resolve()
if ROOT.is_file():
    # When launched as ...\chat\orchestrator_stub.py
    ROOT = ROOT.parent.parent   # go up to aegis_start_work_pack

CONFIG_DIR  = ROOT / "config"
POLICY_PATH = CONFIG_DIR / "policy.yaml"
INDEX_PATH  = ROOT / "rag" / "index.jsonl"

# Your existing backtest API (port 8001)
BACKTEST_URL = "http://127.0.0.1:8001"
# Local LLM (Ollama etc.)
OLLAMA_URL   = "http://127.0.0.1:11434/api/chat"

app = FastAPI(title="Aegis Orchestrator", version="0.1.0")

# -------------------------------------------------
# Tiny YAML reader (no dependency)
# -------------------------------------------------
def read_policy():
    mode = "paper"
    allowed = []
    rates = {}
    if not POLICY_PATH.exists():
        return {"mode": mode, "allowed_tools": allowed, "rate_limits": rates}

    for line in POLICY_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("mode:"):
            mode = s.split(":", 1)[1].strip()
        elif s.startswith("- "):
            allowed.append(s[2:].strip())

    return {"mode": mode, "allowed_tools": allowed, "rate_limits": rates}

POLICY = read_policy()
print(f"[Aegis] Policy loaded from: {POLICY_PATH} | mode={POLICY.get('mode')}, tools={POLICY.get('allowed_tools')}")

# -------------------------------------------------
# Minimal RAG (keyword overlap on index.jsonl)
# -------------------------------------------------
def search_chunks(query: str, k: int = 6):
    if not INDEX_PATH.exists():
        return []
    q = set(re.findall(r"\w+", query.lower()))
    scored = []
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            t = set(re.findall(r"\w+", rec["text"].lower()))
            score = len(q & t)
            if score:
                scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]

@app.get("/debug/policy")
def debug_policy():
    return POLICY

@app.get("/health")
def orch_health():
    return {
        "status": "ok",
        "policy_path": str(POLICY_PATH),
        "mode": POLICY.get("mode"),
        "allowed_tools": POLICY.get("allowed_tools", []),
    }

# -------------------------------------------------
# Pydantic models
# -------------------------------------------------
class ChatRequest(BaseModel):
    message: Union[str, dict]
    system: str | None = None

class ToolBacktest(BaseModel):
    symbol: str
    start: str
    end: str
    fast: int = 50
    slow: int = 200

class PlotRequest(BaseModel):
    csv_path: str
    title: str | None = None

class RunPlotArgs(BaseModel):
    symbol: str
    start: str
    end: str
    fast: int = 50
    slow: int = 200

# -------------------------------------------------
# Tool allow-list
# -------------------------------------------------
def tool_allowed(name: str) -> bool:
    return name in POLICY.get("allowed_tools", [])

# -------------------------------------------------
# Low-level tool helpers that call the backtest API
# -------------------------------------------------
async def tool_backtest(args: ToolBacktest):
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{BACKTEST_URL}/run_backtest", json=args.dict())
        r.raise_for_status()
        return r.json()

async def tool_plot(args: PlotRequest):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{BACKTEST_URL}/plot_equity", json=args.dict())
        r.raise_for_status()
        return {"image/png;base64": base64.b64encode(r.content).decode()}

async def tool_run_and_plot(args: RunPlotArgs):
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{BACKTEST_URL}/run_and_plot", json=args.dict())
        r.raise_for_status()
        return r.json()

async def tool_run_and_plot_save(args: RunPlotArgs):
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{BACKTEST_URL}/run_and_plot_save", json=args.dict())
        r.raise_for_status()
        return r.json()

# -------------------------------------------------
# /tool/run – unified entrypoint for tools
# -------------------------------------------------
from fastapi import Body  # keep import local if your linter whines

@app.post("/tool/run")
async def tool_run(payload: dict = Body(...)):
    name = payload.get("tool", "")
    args = payload.get("args", {})

    if not tool_allowed(name):
        raise HTTPException(status_code=403, detail=f"Tool '{name}' not allowed by policy.")

    if name == "backtest.run":
        return {"tool": name, "result": await tool_backtest(ToolBacktest(**args))}
    if name == "plot.equity":
        return {"tool": name, "result": await tool_plot(PlotRequest(**args))}
    if name == "run_and_plot":
        bt = await tool_backtest(ToolBacktest(**args))
        png = await tool_plot(
            PlotRequest(
                csv_path=bt["csv_path"],
                title=f"{args['symbol']} SMA({args['fast']}/{args['slow']})",
            )
        )
        return {"tool": name, "result": {"backtest": bt, "plot": png}}
    if name == "run_and_plot_save":
        bt = await tool_backtest(ToolBacktest(**args))
        png = await tool_plot(
            PlotRequest(
                csv_path=bt["csv_path"],
                title=f"{args['symbol']} SMA({args['fast']}/{args['slow']})",
            )
        )
        return {"tool": name, "result": {"backtest": bt, "plot": png}}

    raise HTTPException(status_code=400, detail=f"Unknown tool '{name}'")

# -------------------------------------------------
# /chat – normal LLM path, with optional tool calls
# -------------------------------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    # 1) First: see if the user directly sent a tool JSON
    try:
        maybe = req.message if isinstance(req.message, dict) else json.loads(req.message)
        if isinstance(maybe, dict) and "tool" in maybe:
            call = maybe
            tool = call.get("tool", "")
            args = call.get("args", {})

            if not tool_allowed(tool):
                raise HTTPException(status_code=403, detail=f"Tool '{tool}' not allowed by policy.")

            if tool == "backtest.run":
                out = await tool_backtest(ToolBacktest(**args))
                return {"tool": tool, "result": out}
            if tool == "plot.equity":
                out = await tool_plot(PlotRequest(**args))
                return {"tool": tool, "result": out}
            if tool == "run_and_plot":
                out = await tool_run_and_plot(RunPlotArgs(**args))
                return {"tool": tool, "result": out}
            if tool == "run_and_plot_save":
                out = await tool_run_and_plot_save(RunPlotArgs(**args))
                return {"tool": tool, "result": out}

            raise HTTPException(status_code=400, detail=f"Unknown tool '{tool}'")
    except (json.JSONDecodeError, TypeError):
        # Not direct JSON; fall through to model call
        pass

    # 2) Normal LLM chat with RAG context
    ctx = search_chunks(str(req.message), k=6)
    context = "\n\n---\n".join([c["text"] for c in ctx]) if ctx else "No RAG context."

    system = req.system or (
        "You are Aegis, a single-mind trading model. "
        f"Policy mode: {POLICY['mode']}. Use tools only if needed. "
        "When using tools, respond ONLY with a JSON object like "
        '{"tool":"backtest.run","args":{"symbol":"SPY","start":"2020-01-01","end":"2025-11-01","fast":50,"slow":200}}'
    )

    payload = {
        "model": "llama3.1:8b-instruct-q4_K_M",
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question:\n{req.message}\n\n"
                    "If you need tools, respond ONLY with a single JSON object (no prose)."
                ),
            },
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OLLAMA_URL, json=payload)
        r.raise_for_status()
        reply = r.json()["message"]["content"].strip()

    # 3) Try to parse a tool call out of the model's reply
    m = re.search(r"\{.*\}", reply, flags=re.S)
    if m:
        try:
            call = json.loads(m.group(0))
            tool = call.get("tool", "")
            args = call.get("args", {})

            if not tool_allowed(tool):
                raise HTTPException(status_code=403, detail=f"Tool '{tool}' not allowed by policy.")

            if tool == "backtest.run":
                out = await tool_backtest(ToolBacktest(**args))
                return {"tool": tool, "result": out}
            if tool == "plot.equity":
                out = await tool_plot(PlotRequest(**args))
                return {"tool": tool, "result": out}
            if tool == "run_and_plot":
                out = await tool_run_and_plot(RunPlotArgs(**args))
                return {"tool": tool, "result": out}
            if tool == "run_and_plot_save":
                out = await tool_run_and_plot_save(RunPlotArgs(**args))
                return {"tool": tool, "result": out}

            raise HTTPException(status_code=400, detail=f"Unknown tool '{tool}'")
        except Exception:
            # If parsing fails, just fall through
            pass

    # 4) Plain text answer
    return {"answer": reply}
