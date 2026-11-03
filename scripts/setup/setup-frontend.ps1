$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$frontendRoot = Join-Path $repoRoot 'frontend'
$taskTemp = Join-Path $repoRoot 'data\cache\tmp'
$npmCache = Join-Path $repoRoot 'data\cache\npm'
New-Item -ItemType Directory -Path $taskTemp,$npmCache -Force | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:npm_config_cache = $npmCache
Push-Location $frontendRoot
try {
    npm install
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
