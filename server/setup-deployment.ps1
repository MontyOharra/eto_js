# ETO Server Deployment Setup Script
# Run this script as Administrator on your Windows server

param(
    [string]$RepoUrl = "https://github.com/yourusername/eto_js.git",
    [string]$AppDir = "C:\apps\eto\server",
    [string]$WebhookSecret = "your-webhook-secret-here"
)

Write-Host "Setting up ETO Server deployment environment..." -ForegroundColor Green

# Create directories
Write-Host "Creating directories..." -ForegroundColor Yellow
$directories = @(
    $AppDir,
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

# Clone repository if it doesn't exist
if (!(Test-Path "$AppDir\.git")) {
    Write-Host "Cloning repository..." -ForegroundColor Yellow
    Set-Location $AppDir
    git clone $RepoUrl .
    Write-Host "Repository cloned successfully" -ForegroundColor Green
} else {
    Write-Host "Repository already exists, pulling latest changes..." -ForegroundColor Yellow
    Set-Location $AppDir
    git pull origin main
    Write-Host "Repository updated" -ForegroundColor Green
}

# Install Node.js dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
Set-Location $AppDir
npm install

# Generate Prisma client
Write-Host "Generating Prisma client..." -ForegroundColor Yellow
npm run prisma:generate

# Create .env file if it doesn't exist
if (!(Test-Path "$AppDir\.env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item "$AppDir\env.example" "$AppDir\.env"
    Write-Host "Please edit .env file with your configuration" -ForegroundColor Red
}

# Update .env with deployment settings
Write-Host "Updating deployment configuration..." -ForegroundColor Yellow
$envContent = Get-Content "$AppDir\.env" -Raw
$envContent = $envContent -replace "DEPLOY_WEBHOOK_SECRET=.*", "DEPLOY_WEBHOOK_SECRET=$WebhookSecret"
$envContent = $envContent -replace "GIT_REPO_URL=.*", "GIT_REPO_URL=$RepoUrl"
$envContent = $envContent -replace "APP_DIR=.*", "APP_DIR=$AppDir"
Set-Content "$AppDir\.env" $envContent

# Build the application
Write-Host "Building application..." -ForegroundColor Yellow
npm run build

# Copy files to bin directory
Write-Host "Copying files to bin directory..." -ForegroundColor Yellow
Copy-Item "$AppDir\dist\*" "$AppDir\bin\" -Recurse -Force
Copy-Item "$AppDir\package.json" "$AppDir\bin\" -Force
Copy-Item "$AppDir\node_modules" "$AppDir\bin\node_modules\" -Recurse -Force
Copy-Item "$AppDir\.env" "$AppDir\bin\" -Force

# Set up Python virtual environment
Write-Host "Setting up Python environment..." -ForegroundColor Yellow
if (!(Test-Path "$AppDir\python\.venv")) {
    Set-Location "$AppDir\python"
    python -m venv .venv
    & "$AppDir\python\.venv\Scripts\Activate.ps1"
    pip install pdfplumber pillow pdfminer.six
    Write-Host "Python environment created" -ForegroundColor Green
} else {
    Write-Host "Python environment already exists" -ForegroundColor Green
}

# Configure Git for deployment
Write-Host "Configuring Git..." -ForegroundColor Yellow
git config --global pull.rebase false
git config --global core.autocrlf true

# Set up firewall rule for webhook (if needed)
Write-Host "Setting up firewall rule for webhook..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "ETO Server Webhook" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
    Write-Host "Firewall rule created" -ForegroundColor Green
} catch {
    Write-Host "Firewall rule may already exist or requires manual setup" -ForegroundColor Yellow
}

Write-Host "Deployment environment setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit $AppDir\.env with your database and email settings" -ForegroundColor White
Write-Host "2. Run the deployment script: .\deploy.ps1" -ForegroundColor White
Write-Host "3. Configure GitHub repository secrets:" -ForegroundColor White
Write-Host "   - DEPLOY_WEBHOOK_URL: http://your-server-ip:8080/api/deploy/webhook" -ForegroundColor White
Write-Host "4. Test deployment by pushing to main branch" -ForegroundColor White
