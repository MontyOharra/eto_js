# ETO Server CI/CD Deployment Guide

This guide explains how to set up automated CI/CD for the ETO server using GitHub Actions and a Windows server.

## Overview

The CI/CD pipeline consists of:
1. **GitHub Actions**: Runs tests and triggers deployment
2. **Windows Server**: Receives webhooks and automatically deploys updates
3. **Automated Testing**: SQL Server container tests in CI
4. **Zero-downtime Deployment**: Service restart with health checks

## Prerequisites

### On Your Development Machine
- Git repository with server code
- GitHub account with repository access

### On Your Windows Server
- Windows Server 2019/2022
- Node.js 18+
- Python 3.12+
- SQL Server
- Git
- NSSM (for Windows services)
- Administrator access

## Setup Instructions

### Step 1: Configure GitHub Repository

1. **Add Repository Secrets**
   Go to your GitHub repository → Settings → Secrets and variables → Actions
   Add these secrets:
   ```
   DEPLOY_WEBHOOK_URL: http://your-server-ip:8080/api/deploy/webhook
   DEPLOY_WEBHOOK_SECRET: your-secure-webhook-secret
   ```

2. **Push the CI/CD Code**
   ```bash
   git add .
   git commit -m "Add CI/CD pipeline"
   git push origin main
   ```

### Step 2: Set Up Windows Server

1. **Run the Setup Script**
   ```powershell
   # Download and run the setup script
   .\setup-deployment.ps1 -RepoUrl "https://github.com/yourusername/eto_js.git" -WebhookSecret "your-secure-webhook-secret"
   ```

2. **Configure Environment**
   Edit `C:\apps\eto\server\.env`:
   ```env
   # Database
   DATABASE_URL="sqlserver://localhost:1433;database=eto_db;user=eto_user;password=your_password;trustServerCertificate=true"
   
   # Email
   EMAIL_HOST=outlook.office365.com
   EMAIL_PORT=993
   EMAIL_SECURE=true
   EMAIL_USERNAME=your_email@company.com
   EMAIL_PASSWORD=your_app_password
   
   # Deployment
   DEPLOY_WEBHOOK_SECRET=your-secure-webhook-secret
   GIT_REPO_URL=https://github.com/yourusername/eto_js.git
   DEPLOY_BRANCH=main
   APP_DIR=C:\apps\eto\server
   ```

3. **Deploy the Service**
   ```powershell
   .\deploy.ps1
   ```

### Step 3: Test the Pipeline

1. **Make a Test Change**
   ```bash
   # Make a small change to server code
   echo "# Test deployment" >> server/README.md
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```

2. **Monitor Deployment**
   - Check GitHub Actions: https://github.com/yourusername/eto_js/actions
   - Check server logs: `Get-Content C:\apps\eto\server\logs\service.log -Tail 50`
   - Check service status: `Get-Service eto-server`

## How It Works

### GitHub Actions Workflow

1. **Trigger**: Push to `main` branch with changes in `server/` directory
2. **Test Job**:
   - Spins up SQL Server container
   - Installs dependencies
   - Runs linting and tests
   - Builds the application
3. **Deploy Job** (only on main branch):
   - Creates deployment package
   - Triggers webhook on your server

### Server Deployment Process

1. **Webhook Reception**: Server receives POST to `/api/deploy/webhook`
2. **Security Check**: Validates webhook secret
3. **Service Stop**: Stops the ETO service
4. **Code Update**: Pulls latest changes from Git
5. **Dependencies**: Installs npm packages and generates Prisma client
6. **Database**: Runs migrations
7. **Build**: Compiles TypeScript
8. **Deploy**: Copies files to bin directory
9. **Service Start**: Restarts the service
10. **Health Check**: Verifies service is running

## Monitoring and Troubleshooting

### Check Deployment Status
```powershell
# Service status
Get-Service eto-server

# Recent logs
Get-Content C:\apps\eto\server\logs\service.log -Tail 100

# Deployment webhook status
Invoke-RestMethod -Uri "http://localhost:8080/api/deploy/status"
```

### Common Issues

**Service Won't Start**
```powershell
# Check service logs
Get-Content C:\apps\eto\server\logs\service-error.log

# Check environment variables
Get-Content C:\apps\eto\server\bin\.env

# Manual service start
Start-Service eto-server
```

**Webhook Not Receiving**
```powershell
# Check firewall
Get-NetFirewallRule -DisplayName "ETO Server Webhook"

# Test webhook locally
Invoke-RestMethod -Uri "http://localhost:8080/api/deploy/webhook" -Method POST -Headers @{"Authorization"="Bearer your-secret"}
```

**Database Connection Issues**
```powershell
# Test database connection
sqlcmd -S localhost -U eto_user -P your_password -Q "SELECT 1"
```

### Rollback Process

If deployment fails, you can rollback:

```powershell
# Stop service
Stop-Service eto-server

# Reset to previous commit
cd C:\apps\eto\server
git reset --hard HEAD~1

# Rebuild and redeploy
npm run build
.\deploy.ps1
```

## Security Considerations

1. **Webhook Secret**: Use a strong, unique secret
2. **Firewall**: Only allow necessary ports (8080 for webhook)
3. **Database**: Use least-privilege database user
4. **Environment Variables**: Keep secrets in `.env` file
5. **HTTPS**: Consider using HTTPS for webhook in production

## Advanced Configuration

### Custom Deployment Branches
Edit `.github/workflows/ci-cd.yml`:
```yaml
on:
  push:
    branches: [ main, staging, develop ]
```

### Environment-Specific Deployments
Add environment variables to GitHub secrets:
```
STAGING_WEBHOOK_URL: http://staging-server:8080/api/deploy/webhook
PRODUCTION_WEBHOOK_URL: http://prod-server:8080/api/deploy/webhook
```

### Slack Notifications
Add Slack webhook to GitHub secrets and modify the workflow to send notifications on deployment success/failure.

## Maintenance

### Regular Tasks
1. **Log Rotation**: Logs are automatically rotated by Winston
2. **Database Backups**: Set up SQL Server maintenance plans
3. **Security Updates**: Regularly update Node.js and dependencies
4. **Monitoring**: Set up health checks and alerting

### Updates
To update the deployment system:
1. Modify the GitHub Actions workflow
2. Update server deployment scripts
3. Test in staging environment
4. Deploy to production

## Support

For issues with the CI/CD pipeline:
1. Check GitHub Actions logs
2. Review server deployment logs
3. Verify environment configuration
4. Test webhook connectivity