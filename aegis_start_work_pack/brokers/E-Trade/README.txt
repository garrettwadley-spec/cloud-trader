Aegis Trading System — Starter Pack
Unzip into C:\AITrader\ and run scripts\setup.ps1 in PowerShell.

Contents:
- scripts\setup.ps1, run_paper.ps1, run_live.ps1, backup.ps1
- tools\etrade_get_accounts.py, etrade_oauth.py
- config\strategy.yaml, .env.sample
- tasks\ (Task Scheduler XMLs)
- docs\LEGION_SETUP.md

Quick start:
  1) cd C:\AITrader\scripts
     .\setup.ps1
  2) copy C:\AITrader\.env.sample C:\AITrader\.env  (fill keys later)
  3) C:\AITrader\.venv\Scripts\Activate.ps1
     python C:\AITrader\tools\etrade_get_accounts.py
