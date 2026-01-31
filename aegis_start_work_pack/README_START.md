# START WORK — Quickstart

1) Copy into repo root and commit:
   git add .
   git commit -m "Start work: orchestrator + tools + CI"
   git push

2) Run Ollama (Terminal A):
   ollama pull llama3.1:8b-instruct
   ollama serve

3) Run orchestrator (Terminal B):
   pip install -r requirements.txt
   uvicorn chat.orchestrator_app:app --reload --port 8088

4) Test:
   POST http://localhost:8088/ask
   Body: {"question":"Draft a backtest spec for SMA(50/200) on SPY and run it"}
