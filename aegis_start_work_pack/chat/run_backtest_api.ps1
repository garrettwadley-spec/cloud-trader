$ErrorActionPreference = "Stop"

# Handle both: running as a script AND pasting in a console
$here = if ($PSScriptRoot) { $PSScriptRoot } else { (Resolve-Path ".").Path }

$configPath = Join-Path $here "config_backtest.json"

try {
  $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
} catch {
  Write-Host "Failed to parse config_backtest.json. Error:" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  exit 1
}

$py = $cfg.executor_python
$env:PYTHONUNBUFFERED = "1"

Write-Host "Using Python: $py" -ForegroundColor Cyan
Write-Host "Serving on http://$($cfg.host):$($cfg.port)" -ForegroundColor Cyan

# Launch the FastAPI server
& $py ".\backtest_server.py" --host $($cfg.host) --port $($cfg.port)