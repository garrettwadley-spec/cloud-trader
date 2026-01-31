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

$env:MODE = "paper"
$entry = Find-Entrypoint
if ($null -eq $entry) { Write-Error "No entrypoint found (run.py/main.py or dash\app.py)" }
if ($entry.ToLower().EndsWith("app.py")) { streamlit run $entry } else { python $entry --mode paper }
