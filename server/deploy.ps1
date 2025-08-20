# ETO Server Deployment Script
# Run this script as Administrator

param(
    [string]$ServiceName = "eto-server",
    [string]$AppDir = "C:\apps\eto\server",
    [string]$NodeExe = "C:\Program Files\nodejs\node.exe"
)

Write-Host "Starting ETO Server deployment..." -ForegroundColor Green

# Stop the service if it's running
Write-Host "Stopping service if running..." -ForegroundColor Yellow
try {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} catch {
    Write-Host "Service was not running or could not be stopped" -ForegroundColor Yellow
}

# Create directories if they don't exist
Write-Host "Creating directories..." -ForegroundColor Yellow
$directories = @(
    "$AppDir\bin",
    "$AppDir\logs", 
    "$AppDir\storage",
    "$AppDir\python",
    "$AppDir\tmp"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force
        Write-Host "Created directory: $dir" -ForegroundColor Green
    }
}

# Copy files from current directory to server directory
Write-Host "Copying files..." -ForegroundColor Yellow
$sourceDir = Get-Location

# Copy built files
if (Test-Path "$sourceDir\dist") {
    Copy-Item "$sourceDir\dist\*" "$AppDir\bin\" -Recurse -Force
    Write-Host "Copied dist files" -ForegroundColor Green
}

# Copy package.json and node_modules
if (Test-Path "$sourceDir\package.json") {
    Copy-Item "$sourceDir\package.json" "$AppDir\bin\" -Force
    Write-Host "Copied package.json" -ForegroundColor Green
}

if (Test-Path "$sourceDir\node_modules") {
    Copy-Item "$sourceDir\node_modules" "$AppDir\bin\" -Recurse -Force
    Write-Host "Copied node_modules" -ForegroundColor Green
}

# Copy environment file
if (Test-Path "$sourceDir\.env") {
    Copy-Item "$sourceDir\.env" "$AppDir\bin\" -Force
    Write-Host "Copied .env file" -ForegroundColor Green
} else {
    Write-Host "Warning: .env file not found. Please create one manually." -ForegroundColor Red
}

# Copy Python files
if (Test-Path "$sourceDir\python") {
    Copy-Item "$sourceDir\python\*" "$AppDir\python\" -Recurse -Force
    Write-Host "Copied Python files" -ForegroundColor Green
}

# Set up NSSM service
Write-Host "Configuring NSSM service..." -ForegroundColor Yellow

# Check if NSSM is available
$nssmPath = "C:\Program Files\nssm\nssm.exe"
if (!(Test-Path $nssmPath)) {
    Write-Host "NSSM not found. Please install NSSM first." -ForegroundColor Red
    exit 1
}

# Remove existing service if it exists
& $nssmPath remove $ServiceName confirm

# Create new service
& $nssmPath install $ServiceName $NodeExe "$AppDir\bin\index.js"
& $nssmPath set $ServiceName AppDirectory "$AppDir\bin"
& $nssmPath set $ServiceName DisplayName "ETO PDF Processing Server"
& $nssmPath set $ServiceName Description "Email to PDF processing server for ETO system"
& $nssmPath set $ServiceName Start SERVICE_AUTO_START

# Set environment variables
& $nssmPath set $ServiceName AppEnvironmentExtra NODE_ENV=production
& $nssmPath set $ServiceName AppEnvironmentExtra PORT=8080

# Set up logging
& $nssmPath set $ServiceName AppStdout "$AppDir\logs\service.log"
& $nssmPath set $ServiceName AppStderr "$AppDir\logs\service-error.log"

Write-Host "Service configured successfully" -ForegroundColor Green

# Start the service
Write-Host "Starting service..." -ForegroundColor Yellow
Start-Service -Name $ServiceName

# Check service status
Start-Sleep -Seconds 3
$service = Get-Service -Name $ServiceName
if ($service.Status -eq "Running") {
    Write-Host "Service started successfully!" -ForegroundColor Green
    Write-Host "Service status: $($service.Status)" -ForegroundColor Green
} else {
    Write-Host "Service failed to start. Status: $($service.Status)" -ForegroundColor Red
    Write-Host "Check logs at: $AppDir\logs\service-error.log" -ForegroundColor Yellow
}

Write-Host "Deployment completed!" -ForegroundColor Green
