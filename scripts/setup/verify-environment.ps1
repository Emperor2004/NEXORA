$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$checks = [ordered]@{
    'Backend virtual environment' = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
    'Backend environment template' = Join-Path $repoRoot 'backend\.env.example'
    'Frontend package manifest' = Join-Path $repoRoot 'frontend\package.json'
    'Frontend installed dependencies' = Join-Path $repoRoot 'frontend\node_modules'
    'Model registry' = Join-Path $repoRoot 'models\registry\model-registry.yaml'
}

$missing = 0
foreach ($entry in $checks.GetEnumerator()) {
    if (Test-Path -LiteralPath $entry.Value) {
        Write-Host "OK      $($entry.Key)"
    } else {
        Write-Warning "MISSING $($entry.Key)"
        $missing++
    }
}

$backendEnv = Join-Path $repoRoot 'backend\.env'
if (Test-Path -LiteralPath $backendEnv) {
    Write-Host 'OK      Backend .env exists (contents were not read or printed)'
} else {
    Write-Warning 'MISSING Backend .env; copy backend/.env.example and configure only the providers you use.'
    $missing++
}

if ($missing -gt 0) { exit 1 }
exit 0
