$ErrorActionPreference = 'Continue'
$failures = 0

foreach ($commandName in @('python', 'node', 'npm')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "OK  $commandName`: $($command.Source)"
    } else {
        Write-Error "Missing required command: $commandName"
        $failures++
    }
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Warning 'Ollama is not on PATH. Local inference will be unavailable until installed; configured cloud fallback may still work.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'))) {
    Write-Warning 'Backend virtual environment is missing. Run scripts/setup/setup-backend.ps1.'
}

if ($failures -gt 0) { exit 1 }
exit 0
