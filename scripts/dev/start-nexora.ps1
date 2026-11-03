$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$stateRoot = Join-Path $repoRoot '.nexora-dev'
$stateFile = Join-Path $stateRoot 'processes.json'

if (Test-Path -LiteralPath $stateFile) {
    throw 'A NEXORA process record already exists. Run scripts/dev/stop-nexora.ps1 or inspect .nexora-dev/processes.json first.'
}

& (Join-Path $PSScriptRoot '..\setup\check-prerequisites.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'))) {
    throw 'Backend virtual environment not found. Run the backend setup steps before starting NEXORA.'
}
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'frontend\node_modules'))) {
    throw 'Frontend dependencies are missing. Run npm install in frontend/ before starting NEXORA.'
}
New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null

$shell = (Get-Command pwsh.exe -ErrorAction SilentlyContinue)
if (-not $shell) { $shell = Get-Command powershell.exe -ErrorAction Stop }
$backendScript = (Resolve-Path (Join-Path $PSScriptRoot 'start-backend.ps1')).Path
$frontendScript = (Resolve-Path (Join-Path $PSScriptRoot 'start-frontend.ps1')).Path
$backendArgs = @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$backendScript`"")
$frontendArgs = @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$frontendScript`"")
$started = @()

try {
    $backendProcess = Start-Process -FilePath $shell.Source -ArgumentList $backendArgs -WorkingDirectory $repoRoot -WindowStyle Normal -PassThru
    $started += [pscustomobject]@{ id = $backendProcess.Id; script = $backendScript }
    $frontendProcess = Start-Process -FilePath $shell.Source -ArgumentList $frontendArgs -WorkingDirectory $repoRoot -WindowStyle Normal -PassThru
    $started += [pscustomobject]@{ id = $frontendProcess.Id; script = $frontendScript }
    $started | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8
    Write-Host 'NEXORA started. Backend: http://127.0.0.1:8000/docs  Frontend: http://127.0.0.1:5173'
    Write-Host 'Use scripts/dev/stop-nexora.ps1 to stop the recorded server windows.'
} catch {
    foreach ($item in $started) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($item.id)" -ErrorAction SilentlyContinue
        if ($process -and $process.CommandLine -like "*$($item.script)*") {
            & taskkill.exe /PID $item.id /T /F | Out-Null
        }
    }
    Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
    throw
}
