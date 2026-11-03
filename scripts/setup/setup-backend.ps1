$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendRoot = Join-Path $repoRoot 'backend'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
$taskTemp = Join-Path $repoRoot 'data\cache\tmp'
New-Item -ItemType Directory -Path $taskTemp -Force | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp

if (-not (Test-Path -LiteralPath $python)) {
    Push-Location $backendRoot
    try {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally { Pop-Location }
}

& $python -m pip install -r (Join-Path $backendRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Backend environment is ready.'
