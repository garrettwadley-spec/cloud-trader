# Aegis — Architecture & Setup Guide
_Date: 2025-09-27_

This doc maps the folders in the **Start Work** pack and gives a precise Windows setup you can follow line-by-line.

---

## 1) Folder Map (what each piece does)

```
cloud-trader/
├─ chat/
│  └─ orchestrator_app.py     # FastAPI chat server; routes to LLM (Ollama) and allowed tools
├─ tools/
│  ├─ data_fetch.py           # Safe read-only stub: returns rows for symbols/date range
│  ├─ backtest_run.py         # Safe stub: returns dummy Sharpe/DD
│  ├─ train_run.py            # Safe stub: writes "candidate" metadata
│  └─ risk_simulate.py        # Safe stub: simple VaR-style calc
├─ config/
│  └─ policy.yaml             # Guardrails: allowed tools, rate limits, risk caps
├─ rag/
│  └─ index.json              # Tiny seed index so chat has context; replace with built index later
├─ .github/workflows/
│  └─ aegis-ci.yml            # CI stub: eval placeholder + gates sanity check
├─ requirements.txt           # Python deps for chat server (FastAPI, requests, yaml)
└─ README_START.md            # Quickstart steps
```

> As we advance: `rag/` will be built from your `docs/` + `research/`, and `tools/` will connect to real data/backtest engines. The **policy** file stays your single source of truth for permissions and risk caps.

---

## 2) Windows — Environment Setup (very explicit)

### A) Move the unpacked content into repo root (if not already)
Open **File Explorer** → drag the folders `chat/`, `tools/`, `config/`, `rag/`, `.github/`, and files `requirements.txt`, `README_START.md` **into**:
```
C:\Users\garre\cloud-trader\
```
You want `C:\Users\garre\cloud-trader\chat\orchestrator_app.py` to exist.

### B) Open a terminal in the repo
- Click in the address bar of that folder, type `cmd`, press **Enter** (or use Git Bash).
- Confirm location by running:
```
pwd   # in Git Bash
```
You should see something like: `/c/Users/garre/cloud-trader`

### C) Create Python virtual environment
```
python -m venv .venv
```
Activate it:
```
# PowerShell
. .venv\Scripts\Activate.ps1

# or Git Bash
source .venv/Scripts/activate
```
Your prompt should show `(.venv)` at the start.

### D) Install Python deps
```
pip install --upgrade pip
pip install -r requirements.txt
```

### E) Start the local model (Ollama)
If you don’t have Ollama yet, install it from https://ollama.com/download (Windows).
Then open a new terminal just for Ollama and run:
```
ollama pull llama3.1:8b-instruct
ollama serve
```
Leave this terminal running.

### F) Run the Aegis chat server
Back in your **activated** Python terminal:
```
uvicorn chat.orchestrator_app:app --reload --port 8088
```
You should see “Uvicorn running on http://127.0.0.1:8088”.

### G) Test the endpoint
Open a **new** terminal (or use PowerShell):
```
curl -X POST http://127.0.0.1:8088/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\": \"Draft a backtest spec for SMA(50/200) on SPY and run it\"}"
```
Expected: a JSON response with either an **answer** or a **[Tool:backtest.run]** result.  
(For now, tool results are stubbed metrics; we’ll wire the real backtester next.)

### H) Commit & push
In your repo terminal:
```
git add .
git commit -m "Wire Aegis start-work pack and bring up local chat server"
git push
```

---

## 3) What to do next (short list)
1. Add your first note under `docs/` (e.g., `docs/notes/market_2025-09-27.md`), then run our indexer (next task) to feed RAG.
2. Replace `tools/backtest_run.py` with your real engine (I’ll scaffold a clean interface).
3. Add `config/gates.json` so CI can enforce promotion thresholds.
4. Create `docs/safety-rails.md` with your current caps (position, daily loss, kill switch).

---

## 4) Troubleshooting
- **“Command not found: uvicorn”** → your venv might not be active; re-run activation, then `pip install -r requirements.txt`.
- **403 “Tool not allowed by policy”** → edit `config/policy.yaml` to add the tool name under `tools.allow`.
- **429 “Rate limit exceeded”** → we track backtests/hour in a `.runtime` file; wait an hour or reduce in policy.
- **Endpoint hangs** → make sure `ollama serve` is running and that you pulled `llama3.1:8b-instruct`.
- **Windows firewall popup** → allow access for Python when running `uvicorn`.
