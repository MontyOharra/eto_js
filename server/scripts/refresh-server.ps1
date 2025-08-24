Param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$originalLocation = Get-Location
try {
  $scriptRoot = $PSScriptRoot
  $serverRoot = (Resolve-Path (Join-Path $scriptRoot "..\")).Path
  $deployRoot = "C:\apps\eto\server"

  if (!(Test-Path $deployRoot)) {
    throw "Deployment not found: $deployRoot. Run build first."
  }

  Write-Host "Refreshing deployed server files (no venv rebuild)" -ForegroundColor Cyan

  # Copy source from repo server folder to deploy, excluding deploy-only items and local venv
  & robocopy "$serverRoot" "$deployRoot" /MIR /XD "scripts" ".venv" "__pycache__" | Out-Null

  # Recreate essential directories if needed
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "storage") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "logs") | Out-Null

  # Do NOT touch venv; optionally re-install if requirements.txt changed (skipped by design)
  Write-Host "Refresh complete. Deployed to $deployRoot" -ForegroundColor Green
} finally {
  Set-Location -Path $originalLocation
}

exit 0



