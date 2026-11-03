$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$taskTemp = Join-Path $repoRoot 'data\cache\tmp'
New-Item -ItemType Directory -Path $taskTemp -Force | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$python = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the repository virtual environment first: python -m venv .venv and install backend/requirements.txt.' }
$suite = @(
    'backend/scripts/test_agent_foundation.py',
    'backend/scripts/test_end_to_end_pipeline.py',
    'backend/scripts/test_multisource_discovery.py',
    'backend/scripts/test_individual_extraction_regressions.py',
    'backend/scripts/test_linkedin_metadata_parser.py'
)
foreach ($relative in $suite) {
    $path = Join-Path $repoRoot $relative
    if (-not (Test-Path -LiteralPath $path)) { throw "Expected regression suite file is missing: $relative" }
    Write-Host "Running $relative"
    $previousEncoding = $env:PYTHONIOENCODING
    $env:PYTHONIOENCODING = 'utf-8'
    & $python $path
    $env:PYTHONIOENCODING = $previousEncoding
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
