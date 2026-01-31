# 1) Activate venv (lives at the project root)
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# 2) Move into the pack where the 'chat' package lives
Set-Location "$PSScriptRoot\aegis_start_work_pack"

# 3) Env vars for the orchestrator -> Ollama
$env:AEGIS_MODEL = "llama3.1"
$env:OLLAMA_URL  = "http://127.0.0.1:11434/api/generate"

# 4) Run the server from inside aegis_start_work_pack
python -m uvicorn chat.orchestrator_app:app --reload --port 8088
