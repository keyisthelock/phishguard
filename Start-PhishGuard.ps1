param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$workspacePython = Join-Path $PSScriptRoot '../../work/.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $projectPython) { $demoPython = $projectPython }
elseif (Test-Path -LiteralPath $workspacePython) { $demoPython = (Resolve-Path -LiteralPath $workspacePython).Path }
else {
    Write-Host 'First-time setup: create a Python 3.12 virtual environment and install requirements-lock.txt. See README.md.'
    exit 1
}
if ($CheckOnly) {
    & $demoPython azure_diagnostics.py
    exit $LASTEXITCODE
}
Write-Host 'PhishGuard is starting at http://127.0.0.1:5000. Keep this terminal open; Ctrl+C stops it.'
& $demoPython app.py
exit $LASTEXITCODE
