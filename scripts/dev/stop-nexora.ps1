$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$stateFile = Join-Path $repoRoot '.nexora-dev\processes.json'

if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host 'No NEXORA process record found; nothing was stopped.'
    exit 0
}

$items = @(Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json)
foreach ($item in $items) {
    if ([int]$item.id -le 0) { continue }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$item.id)" -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    if ($process.CommandLine -notlike "*$($item.script)*") {
        Write-Warning "PID $($item.id) no longer matches the recorded NEXORA script; leaving it running."
        continue
    }
    & taskkill.exe /PID ([int]$item.id) /T /F | Out-Null
}

Remove-Item -LiteralPath $stateFile -Force
Remove-Item -LiteralPath (Split-Path $stateFile -Parent) -Force -ErrorAction SilentlyContinue
Write-Host 'Stopped the recorded NEXORA server windows.'
