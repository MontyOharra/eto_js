# ETO Server Scripts Convenience Script
# Provides easy access to all server management scripts

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("build", "refresh", "start", "help")]
    [string]$Action
)

$scriptsDir = Join-Path $PSScriptRoot "scripts"

switch ($Action) {
    "build" {
        Write-Host "Building and deploying Flask server..." -ForegroundColor Green
        & (Join-Path $scriptsDir "build-server.ps1")
    }
    "refresh" {
        Write-Host "Refreshing deployed Flask server files (no venv rebuild)..." -ForegroundColor Green
        & (Join-Path $scriptsDir "refresh-server.ps1")
    }
    "start" {
        Write-Host "Starting Flask server..." -ForegroundColor Green
        & (Join-Path $scriptsDir "server-start.ps1")
    }
    "help" {
        Write-Host "ETO Server Scripts" -ForegroundColor Cyan
        Write-Host "==================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Usage: .\server-scripts.ps1 <action>" -ForegroundColor White
        Write-Host ""
        Write-Host "Actions:" -ForegroundColor Yellow
        Write-Host "  build   - Build and deploy Flask server to C:\apps\eto\server" -ForegroundColor White
        Write-Host "  refresh - Copy updated app files to deploy without venv rebuild" -ForegroundColor White
        Write-Host "  start   - Start the deployed Flask server" -ForegroundColor White
        Write-Host "  help    - Show this help message" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Yellow
        Write-Host "  .\server-scripts.ps1 build" -ForegroundColor White
        Write-Host "  .\server-scripts.ps1 start" -ForegroundColor White
    }
}
