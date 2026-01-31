Param([switch]$Force)
$ErrorActionPreference = 'Stop'
Write-Host "=== Aegis Setup (Windows / Legion) ==="

try { Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force | Out-Null } catch {}

# Ensure Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Error "Python not found. Install Python 3.11+ then re-run." }

# Create venv
if (-not (Test-Path ..\.venv)) { python -m venv ..\.venv }
. ..\.venv\Scripts\Activate.ps1

# Upgrade pip tooling
python -m pip install --upgrade pip setuptools wheel

# Core deps
$base = @(
  "python-dotenv>=1.0.1","pandas>=2.2.2","numpy>=1.26.4","scikit-learn>=1.5.0",
  "lightgbm>=4.3.0","xgboost>=2.0.3","pyyaml>=6.0.1","yfinance>=0.2.40",
  "ta>=0.11.0","streamlit>=1.36.0","pydantic>=2.8.0","requests>=2.32.0",
  "tqdm>=4.66.0","plotly>=5.22.0"
)
pip install $base

# Torch GPU preferred
$cudaIndex = "https://download.pytorch.org/whl/cu121"
try {
  pip install --index-url $cudaIndex torch torchvision torchaudio
} catch {
  Write-Warning "GPU wheels failed; installing CPU-only torch."
  pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
}

# Optional NVML
try { pip install nvidia-ml-py3 } catch { Write-Warning "NVML optional failed." }

# Folders
$folders = @("data","data\cache","models","logs","backups","config")
foreach ($f in $folders) { if (-not (Test-Path "..\$f")) { New-Item -ItemType Directory -Path "..\$f" | Out-Null } }

# Seed .env
if (-not (Test-Path "..\.env")) { Copy-Item "..\.env.sample" "..\.env" }

# CUDA check
$code = @"
import torch
print('torch version:', torch.__version__)
print('cuda available:', torch.cuda.is_available())
print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU-only')
"@
python - << $code
Write-Host "Setup complete."
