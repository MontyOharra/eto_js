Param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$originalLocation = Get-Location
try {
  $scriptRoot = $PSScriptRoot
  $serverRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
  Write-Host "Project root: $serverRoot"

  # Deployment target
  $deployRoot = "C:\apps\eto\server"

  Write-Host "Resetting deployment folder: $deployRoot"
  if (Test-Path $deployRoot) {
    Remove-Item -Path $deployRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
  New-Item -ItemType Directory -Force -Path $deployRoot | Out-Null

  # Copy server source to deploy root (exclude local venv, scripts, caches)
  Write-Host "Copying server to $deployRoot"
  & robocopy "$serverRoot" "$deployRoot" /MIR /XD "scripts" ".venv" "__pycache__" | Out-Null

  # Ensure storage/logs exist
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "storage") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $deployRoot "logs") | Out-Null

  # Create venv IN THE DEPLOY FOLDER and install dependencies
  Write-Host "Setting up Python virtual environment in deploy folder"
  $venvPath = Join-Path $deployRoot ".venv"
  python -m venv "$venvPath" | Out-Host
  $pythonExe = Join-Path $venvPath "Scripts\python.exe"
  if (!(Test-Path $pythonExe)) { $pythonExe = Join-Path $venvPath "bin/python" }

  $reqPath = Join-Path $deployRoot "requirements.txt"
  if (Test-Path $reqPath) {
    & $pythonExe -m pip install --upgrade pip | Out-Host
    & $pythonExe -m pip install -r "$reqPath" | Out-Host
  }

  # Copy .env files if present from project
  $envFile = Join-Path $serverRoot ".env"
  $envExample = Join-Path $serverRoot "env.example"
  if (Test-Path $envFile) { Copy-Item $envFile $deployRoot -Force }
  if (Test-Path $envExample) { Copy-Item $envExample $deployRoot -Force }

  Write-Host "Build complete. Deployed to $deployRoot"
} finally {
  Set-Location -Path $originalLocation
}

exit 0


