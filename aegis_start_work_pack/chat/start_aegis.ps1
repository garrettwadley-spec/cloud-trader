# Backtest API (8001)
Start-Process powershell -ArgumentList @"
 -NoProfile -NoExit -Command `
  & 'C:\Users\garre\cloud-trader\.venv\Scripts\Activate.ps1'; `
  Set-Location 'C:\Users\garre\cloud-trader\aegis_start_work_pack\chat'; `
  python -m uvicorn backtest_server:app --host 127.0.0.1 --port 8001 --reload
"@

# Orchestrator (8002)
Start-Process powershell -ArgumentList @"
 -NoProfile -NoExit -Command `
  & 'C:\Users\garre\cloud-trader\.venv\Scripts\Activate.ps1'; `
  Set-Location 'C:\Users\garre\cloud-trader\aegis_start_work_pack\chat'; `
  python -m uvicorn orchestrator_stub:app --host 127.0.0.1 --port 8002 --reload
"@
