$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$taskTemp = Join-Path $repoRoot 'data\cache\tmp'
$npmCache = Join-Path $repoRoot 'data\cache\npm'
New-Item -ItemType Directory -Path $taskTemp,$npmCache -Force | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:npm_config_cache = $npmCache
$frontend = Join-Path $repoRoot 'frontend'
Push-Location $frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
