Param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$originalLocation = Get-Location
try {
  $deployRoot = "C:\apps\eto\server"
  if (!(Test-Path $deployRoot)) {
    throw "Deployment not found: $deployRoot. Run build-server first."
  }

  $appPath = Join-Path $deployRoot "app.py"
  if (!(Test-Path $appPath)) {
    throw "app.py not found in $deployRoot"
  }

  # Ensure storage/logs exist
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "storage") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "logs") | Out-Null

  Write-Host "Starting Flask server from $deployRoot"
  $venvPython = Join-Path $deployRoot ".venv\Scripts\python.exe"
  if (!(Test-Path $venvPython)) { $venvPython = "python" }
  & $venvPython "$appPath" | Write-Output
} finally {
  Set-Location -Path $originalLocation
}

exit 0


