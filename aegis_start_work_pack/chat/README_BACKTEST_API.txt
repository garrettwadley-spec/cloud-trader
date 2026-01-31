Quick start:
1) Save these files in C:\Users\garre\cloud-trader\aegis_start_work_pack\chat
2) PowerShell (in that folder):
   Set-ExecutionPolicy -Scope Process RemoteSigned
   .\run_backtest_api.ps1
3) Browser tests:
   http://127.0.0.1:8001/health
   http://127.0.0.1:8001/run_backtest?symbol=SPY
   http://127.0.0.1:8001/run_backtest?symbol=QQQ
