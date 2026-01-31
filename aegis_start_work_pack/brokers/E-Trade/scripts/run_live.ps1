function Load-DotEnv {
  param([string]$Path = "..\.env")
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    $_ = $_.Trim()
    if (-not $_ -or $_.StartsWith("#")) { return }
    $parts = $_ -split "=", 2
    if ($parts.Count -eq 2) { [Environment]::SetEnvironmentVariable($parts[0], $parts[1]) }
  }
}

function Find-Entrypoint {
  $candidates = @("run.py","main.py","app\main.py","src\main.py")
  foreach ($c in $candidates) { if (Test-Path "..\$c") { return "..\$c" } }
  if (Test-Path "..\dash\app.py") { return "..\dash\app.py" }
  return $null
}

$ErrorActionPreference = 'Stop'
cd (Split-Path -Parent $MyInvocation.MyCommand.Path)
. "..\.venv\Scripts\Activate.ps1"
Load-DotEnv

$env:MODE = "live"
$broker = $env:BROKER
if (-not $broker) { Write-Error "BROKER not set in .env (etrade|td)" }
function Require-Vars([string[]]$Names){ foreach ($n in $Names){ if (-not $env:$n){ Write-Error "Missing secret: $n" } } }
switch ($broker) {
  "etrade" { Require-Vars @("ETRADE_API_KEY","ETRADE_API_SECRET","ETRADE_ACCOUNT_ID") }
  "td"     { Require-Vars @("TDA_CLIENT_ID","TDA_REDIRECT_URI","TDA_ACCOUNT_ID") }
  default  { Write-Error "Unsupported BROKER '$broker'" }
}
$entry = Find-Entrypoint
if ($null -eq $entry) { Write-Error "No engine entrypoint found" }
if ($entry.ToLower().EndsWith("app.py")) { Write-Error "Live mode runs engine, not Streamlit" } else { python $entry --mode live }
