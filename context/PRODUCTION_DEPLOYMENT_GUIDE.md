# Production Deployment Guide: FastAPI Application with Docker

> **Comprehensive guide for deploying a FastAPI application to production on-premises using Docker, CI/CD, and industry best practices**

**Last Updated**: October 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Docker Foundation](#docker-foundation)
3. [Code Deployment Strategy](#code-deployment-strategy)
4. [Containerization](#containerization)
5. [Database Connectivity](#database-connectivity)
6. [Networking & Reverse Proxy](#networking--reverse-proxy)
7. [Security & Secrets Management](#security--secrets-management)
8. [SSL/TLS Certificates](#ssltls-certificates)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup & Disaster Recovery](#backup--disaster-recovery)
11. [CI/CD Pipeline](#cicd-pipeline)
12. [Deployment Strategies](#deployment-strategies)
13. [Common Production Questions](#common-production-questions)

---

## Overview

### What This Guide Covers

This guide addresses **on-premises production deployment** for a FastAPI application using:
- **Docker** for containerization
- **GitHub** for version control
- **GitHub Actions** with self-hosted runners for CI/CD
- **External SQL Server** database connectivity
- **NGINX** as reverse proxy
- **Let's Encrypt** for SSL certificates
- **Prometheus & Grafana** for monitoring

### Key Principles

1. **Never store code directly on the server** - Always pull from version control
2. **Containers are ephemeral** - Treat them as disposable
3. **Configuration as code** - All infrastructure defined in version-controlled files
4. **Security by default** - Minimize attack surface, use secrets management
5. **Observability is mandatory** - Monitoring, logging, and alerting from day one

**Sources:**
- [Docker Best Practices 2025](https://thinksys.com/devops/docker-best-practices/)
- [Modern Docker Best Practices](https://talent500.com/blog/modern-docker-best-practices-2025/)

---

## Docker Foundation

### Why Docker for Production?

Docker provides:
- **Consistency**: Same environment from dev to production
- **Isolation**: Application dependencies contained
- **Portability**: Run anywhere Docker runs
- **Scalability**: Easy horizontal scaling
- **Version control**: Image tags track versions

### Production Docker Best Practices

#### 1. Use Specific Image Tags

```dockerfile
# ❌ BAD - Uses latest, unpredictable
FROM python:latest

# ✅ GOOD - Specific version
FROM python:3.11.7-slim
```

**Why:** The `latest` tag can change without warning, breaking production builds.

#### 2. Multi-Stage Builds

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY ./src /app
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Benefits:**
- Smaller final image (build tools excluded)
- Faster deployment
- Reduced attack surface

#### 3. Use Minimal Base Images

```dockerfile
# 🔴 Full image: ~1GB
FROM python:3.11

# 🟢 Slim image: ~150MB
FROM python:3.11-slim

# 🟢 Alpine image: ~50MB (may have compatibility issues)
FROM python:3.11-alpine
```

#### 4. Run as Non-Root User

```dockerfile
# Create user
RUN adduser --disabled-password --gecos "" appuser

# Switch to non-root user
USER appuser

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Security Impact:** Prevents privilege escalation attacks.

#### 5. Implement Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1
```

#### 6. Set Resource Limits

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

**Purpose:** Prevents resource exhaustion attacks.

#### 7. Scan Images for Vulnerabilities

```bash
# Using Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image your-image:tag

# Using Docker Scout (built-in)
docker scout cves your-image:tag
```

**Sources:**
- [Docker Official Docs: Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Top 8 Docker Production Best Practices](https://dev.to/techworld_with_nana/top-8-docker-best-practices-for-using-docker-in-production-1m39)
- [Aqua Security: Docker in Production](https://www.aquasec.com/cloud-native-academy/docker-container/docker-in-production-getting-it-right/)

---

## Code Deployment Strategy

### Question: Is code stored on the server or pulled from GitHub?

**Answer: Always pull from GitHub (or your version control system).**

### Recommended Workflow

```
GitHub Repository
    ↓
CI/CD Pipeline (GitHub Actions)
    ↓
Build Docker Image
    ↓
Push to Registry (GitHub Container Registry, Docker Hub, or private registry)
    ↓
On-Premises Server pulls image
    ↓
Deploy containers
```

### Why Not Store Code Directly on Server?

| Approach | Pros | Cons |
|----------|------|------|
| **Code on Server** | Simple initial setup | No version control, no audit trail, manual updates, no rollback capability |
| **Pull from GitHub** | Version control, audit trail, automated deployments, easy rollback | Requires CI/CD setup |

### Implementation Approaches

#### Option 1: GitHub Actions with Self-Hosted Runner (Recommended for On-Premises)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: self-hosted  # Runs on your on-premises server

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Tag as latest
        run: docker tag myapp:${{ github.sha }} myapp:latest

      - name: Deploy with docker-compose
        run: docker-compose up -d
```

#### Option 2: Manual Pull with Git Hooks

```bash
# On server, set up a bare repository
git init --bare ~/app.git

# Create post-receive hook
cat > ~/app.git/hooks/post-receive << 'EOF'
#!/bin/bash
cd /opt/app
git pull
docker-compose up -d --build
EOF

chmod +x ~/app.git/hooks/post-receive

# From local machine, add remote and push
git remote add production user@server:~/app.git
git push production main
```

#### Option 3: GitHub Container Registry

```bash
# Build and push image
docker build -t ghcr.io/username/myapp:latest .
docker push ghcr.io/username/myapp:latest

# On server, pull and run
docker pull ghcr.io/username/myapp:latest
docker-compose up -d
```

**Sources:**
- [GitHub Actions CI/CD Pipeline](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)
- [GitHub On-Prem Connectivity with Self-Hosted Runners](https://blogs.perficient.com/2024/06/05/github-on-prem-server-connectivity-using-self-hosted-runners/)

---

## Containerization

### Complete Dockerfile for FastAPI Production

```dockerfile
# syntax=docker/dockerfile:1

# ============================================================================
# Build Stage
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies to user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Production Stage
# ============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PORT=8000

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --chown=appuser:appuser ./server-new /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Start application with Gunicorn + Uvicorn workers
CMD ["gunicorn", "src.app:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Docker Compose for Production

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    image: eto-api:latest
    container_name: eto-api
    restart: unless-stopped

    ports:
      - "8000:8000"

    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY_FILE=/run/secrets/api_secret_key

    secrets:
      - api_secret_key

    networks:
      - app_network

    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

secrets:
  api_secret_key:
    file: ./secrets/api_secret_key.txt

networks:
  app_network:
    driver: bridge
```

### Worker Process Configuration

#### Gunicorn + Uvicorn Workers (Recommended)

```bash
# Install both
pip install "uvicorn[standard]" gunicorn

# Run with optimal worker count
# Formula: (2 × CPU cores) + 1
gunicorn src.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-connections 1000 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

#### Uvicorn with Multiple Workers (Simpler Alternative)

```bash
uvicorn src.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

**When to Use Which:**
- **Gunicorn + Uvicorn**: Traditional deployments, better process management
- **Uvicorn only**: Kubernetes/container orchestration (one process per container)

**Sources:**
- [FastAPI in Containers - Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [FastAPI Docker Best Practices](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/)
- [Mastering Gunicorn and Uvicorn](https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e)

---

## Database Connectivity

### Question: How do containers connect to external SQL Server?

**Answer: Use special DNS names or network configuration.**

### Connecting to SQL Server on Host Machine

#### For Windows/Mac (Development)

```python
# Connection string using host.docker.internal
DATABASE_URL = "mssql+pyodbc://username:password@host.docker.internal:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
```

**Note:** `host.docker.internal` resolves to the host's internal IP address.

#### For Linux Production Servers

##### Option 1: Use Host Network Mode

```yaml
# docker-compose.yml
services:
  api:
    network_mode: "host"
```

**Connection string:**
```python
DATABASE_URL = "mssql+pyodbc://username:password@localhost:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
```

**Trade-off:** Loses container network isolation.

##### Option 2: Use Host IP Address

```bash
# Find host IP on Docker bridge
ip addr show docker0

# Example output: inet 172.17.0.1/16
```

**Connection string:**
```python
DATABASE_URL = "mssql+pyodbc://username:password@172.17.0.1:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
```

##### Option 3: Use Fully Qualified Domain Name (Best for Production)

```python
# Use FQDN to force external DNS resolution
DATABASE_URL = "mssql+pyodbc://username:password@sqlserver.yourdomain.com:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
```

### SQL Server Configuration Requirements

#### Enable TCP/IP Protocol

```sql
-- SQL Server Configuration Manager
-- Enable TCP/IP for SQL Server instance
-- Restart SQL Server service
```

#### Enable Mixed Authentication Mode

```sql
-- SQL Server Management Studio
-- Server Properties → Security
-- Server authentication mode: SQL Server and Windows Authentication mode
-- Restart SQL Server service
```

#### Firewall Rules

```powershell
# Windows Firewall - Allow SQL Server port
New-NetFirewallRule -DisplayName "SQL Server" -Direction Inbound -Protocol TCP -LocalPort 1433 -Action Allow
```

### Common Issues & Solutions

#### Issue 1: DNS Resolution Fails

**Problem:** Docker's internal DNS can't resolve bare hostnames.

**Solution:** Use FQDN (e.g., `server.domain.com` instead of `server`).

#### Issue 2: Network Conflicts

**Problem:** Docker bridge subnet overlaps with SQL Server IP range.

**Solution:** Configure Docker daemon with custom bridge IP:

```json
// /etc/docker/daemon.json (Linux)
// C:\ProgramData\docker\config\daemon.json (Windows)
{
  "bip": "192.168.100.1/24"
}
```

Restart Docker daemon.

#### Issue 3: Connection Timeout

**Problem:** Firewall blocking connection.

**Solution:**
1. Check SQL Server is listening: `netstat -an | findstr 1433`
2. Verify firewall rules
3. Test connection from container: `docker exec -it container_name bash`, then `telnet sqlserver 1433`

### Docker Compose Example

```yaml
version: '3.8'

services:
  api:
    image: eto-api:latest
    environment:
      # Use environment variable for database connection
      - DATABASE_URL=mssql+pyodbc://username:password@sqlserver.yourdomain.com:1433/eto_db?driver=ODBC+Driver+17+for+SQL+Server

    # Or use secrets (recommended)
    secrets:
      - db_connection_string

    extra_hosts:
      # Add host entry if needed
      - "sqlserver:192.168.1.100"

secrets:
  db_connection_string:
    file: ./secrets/db_connection.txt
```

**Sources:**
- [Connect to External SQL Server from Docker Container](https://stackoverflow.com/questions/72489729/how-to-connect-external-ms-sql-server-database-from-container)
- [Connect to Local MS SQL Server from Docker](https://medium.com/@vedkoditkar/connect-to-local-ms-sql-server-from-docker-container-9d2b3d33e5e9)
- [Microsoft Docs: SQL Server Linux Containers](https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-docker-container-deployment)

---

## Networking & Reverse Proxy

### Why Use NGINX as Reverse Proxy?

Benefits:
- **Single entry point**: All traffic goes through NGINX on ports 80/443
- **SSL termination**: NGINX handles HTTPS, backend uses HTTP
- **Load balancing**: Distribute traffic across multiple containers
- **Security**: Hide internal architecture, rate limiting, IP filtering
- **Static files**: Serve static content efficiently

### NGINX Configuration

#### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8000;
        # For multiple instances:
        # server api1:8000;
        # server api2:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name yourdomain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API routes
        location /api/ {
            # Apply rate limiting
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://api_backend/health;
        }

        # Static files (if serving from NGINX)
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

#### Docker Compose with NGINX

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    container_name: nginx-proxy
    restart: unless-stopped

    ports:
      - "80:80"
      - "443:443"

    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx

    networks:
      - app_network

    depends_on:
      - api

    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  api:
    image: eto-api:latest
    container_name: eto-api
    restart: unless-stopped

    # Don't expose ports externally - only accessible through NGINX
    expose:
      - "8000"

    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  nginx-logs:
```

### Automated NGINX Proxy (nginx-proxy)

For simpler setups, use the automated nginx-proxy:

```yaml
version: '3.8'

services:
  nginx-proxy:
    image: nginxproxy/nginx-proxy
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/tmp/docker.sock:ro
      - nginx-certs:/etc/nginx/certs
    networks:
      - proxy_network

  api:
    image: eto-api:latest
    expose:
      - "8000"
    environment:
      - VIRTUAL_HOST=api.yourdomain.com
      - VIRTUAL_PORT=8000
    networks:
      - proxy_network

networks:
  proxy_network:
    external: true

volumes:
  nginx-certs:
```

**Sources:**
- [Docker Nginx Reverse Proxy Setup](https://www.theserverside.com/blog/Coffee-Talk-Java-News-Stories-and-Opinions/Docker-Nginx-reverse-proxy-setup-example)
- [nginx-proxy GitHub](https://github.com/nginx-proxy/nginx-proxy)
- [How to Deploy NGINX Reverse Proxy on Docker](https://phoenixnap.com/kb/docker-nginx-reverse-proxy)

---

## Security & Secrets Management

### Never Hardcode Secrets

**❌ BAD:**
```python
# In code
DATABASE_URL = "mssql+pyodbc://sa:Password123@server/db"
SECRET_KEY = "super-secret-key-123"
```

**❌ BAD:**
```yaml
# In docker-compose.yml
environment:
  - DATABASE_PASSWORD=MySecretPassword
```

### Docker Secrets (Recommended)

Docker Secrets store sensitive data as files in `/run/secrets/` inside containers.

#### Step 1: Create Secret Files

```bash
# Create secrets directory
mkdir -p secrets/

# Store secrets in files
echo "your-secret-api-key" > secrets/api_secret_key.txt
echo "your-db-password" > secrets/db_password.txt

# Secure permissions
chmod 600 secrets/*.txt
```

#### Step 2: Configure Docker Compose

```yaml
version: '3.8'

services:
  api:
    image: eto-api:latest
    secrets:
      - api_secret_key
      - db_password
    environment:
      # Point to secret files
      - SECRET_KEY_FILE=/run/secrets/api_secret_key
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  api_secret_key:
    file: ./secrets/api_secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
```

#### Step 3: Read Secrets in Application

```python
# app.py
import os
from pathlib import Path

def get_secret(secret_name: str) -> str:
    """Read secret from Docker secrets file or environment variable."""
    # Try Docker secret file first
    secret_file = Path(f"/run/secrets/{secret_name}")
    if secret_file.exists():
        return secret_file.read_text().strip()

    # Fallback to environment variable
    return os.getenv(secret_name, "")

# Usage
SECRET_KEY = get_secret("api_secret_key")
DB_PASSWORD = get_secret("db_password")

# Build connection string
DATABASE_URL = f"mssql+pyodbc://username:{DB_PASSWORD}@server/db"
```

### Environment Variables from .env File

```bash
# .env file (add to .gitignore!)
DATABASE_URL=mssql+pyodbc://user:pass@server/db
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO
```

```yaml
# docker-compose.yml
services:
  api:
    image: eto-api:latest
    env_file:
      - .env
```

**Important:** Add `.env` to `.gitignore`!

### Using External Secret Management

For enterprise deployments:

#### HashiCorp Vault

```python
import hvac

client = hvac.Client(url='https://vault.yourdomain.com')
client.token = os.getenv('VAULT_TOKEN')

# Read secrets
secrets = client.secrets.kv.read_secret_version(path='eto/production')
db_password = secrets['data']['data']['db_password']
```

#### AWS Secrets Manager (for hybrid deployments)

```python
import boto3

client = boto3.client('secretsmanager', region_name='us-east-1')
response = client.get_secret_value(SecretId='eto/production/db_password')
db_password = response['SecretString']
```

### Security Checklist

- [ ] No secrets in source code
- [ ] No secrets in Docker images
- [ ] `.env` files in `.gitignore`
- [ ] Secret files have restricted permissions (600)
- [ ] Secrets directory excluded from version control
- [ ] Use Docker secrets in production
- [ ] Rotate secrets regularly
- [ ] Use separate secrets for dev/staging/production
- [ ] Audit secret access

**Sources:**
- [Docker Compose Secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- [Managing Docker Secrets](https://phase.dev/blog/docker-compose-secrets/)
- [Docker Secrets Security Guide](https://spacelift.io/blog/docker-secrets)

---

## SSL/TLS Certificates

### Using Let's Encrypt with Docker

Let's Encrypt provides **free SSL/TLS certificates** that auto-renew.

### Method 1: Certbot with NGINX

#### Docker Compose Setup

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot-webroot:/var/www/certbot
      - certbot-certs:/etc/nginx/ssl
    networks:
      - app_network

  certbot:
    image: certbot/certbot:latest
    container_name: certbot
    volumes:
      - certbot-webroot:/var/www/certbot
      - certbot-certs:/etc/letsencrypt
    command: certonly --webroot --webroot-path=/var/www/certbot --email your@email.com --agree-tos --no-eff-email -d yourdomain.com -d www.yourdomain.com

volumes:
  certbot-webroot:
  certbot-certs:

networks:
  app_network:
```

#### NGINX Configuration for Let's Encrypt

```nginx
http {
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        # Let's Encrypt ACME challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Redirect all other traffic to HTTPS
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL certificates from Let's Encrypt
        ssl_certificate /etc/nginx/ssl/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/live/yourdomain.com/privkey.pem;

        # SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
        ssl_prefer_server_ciphers off;

        # HSTS
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location / {
            proxy_pass http://api:8000;
            # ... proxy settings
        }
    }
}
```

#### Certificate Renewal Automation

```bash
# Add to crontab (runs daily)
0 3 * * * docker-compose run --rm certbot renew && docker-compose exec nginx nginx -s reload
```

Or use a renew script:

```bash
#!/bin/bash
# renew-certs.sh

docker-compose run --rm certbot renew

# Reload NGINX if certificates were renewed
if [ $? -eq 0 ]; then
    docker-compose exec nginx nginx -s reload
    echo "Certificates renewed successfully"
fi
```

### Method 2: Automated with nginx-proxy-acme

Fully automated solution combining nginx-proxy + Let's Encrypt:

```yaml
version: '3.8'

services:
  nginx-proxy:
    image: nginxproxy/nginx-proxy
    container_name: nginx-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/tmp/docker.sock:ro
      - nginx-certs:/etc/nginx/certs
      - nginx-html:/usr/share/nginx/html
      - nginx-vhost:/etc/nginx/vhost.d
    networks:
      - proxy

  acme-companion:
    image: nginxproxy/acme-companion
    container_name: nginx-proxy-acme
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - nginx-certs:/etc/nginx/certs
      - nginx-html:/usr/share/nginx/html
      - nginx-vhost:/etc/nginx/vhost.d
      - acme:/etc/acme.sh
    environment:
      - DEFAULT_EMAIL=your@email.com
    depends_on:
      - nginx-proxy
    networks:
      - proxy

  api:
    image: eto-api:latest
    expose:
      - "8000"
    environment:
      - VIRTUAL_HOST=api.yourdomain.com
      - VIRTUAL_PORT=8000
      - LETSENCRYPT_HOST=api.yourdomain.com
      - LETSENCRYPT_EMAIL=your@email.com
    networks:
      - proxy

networks:
  proxy:
    external: true

volumes:
  nginx-certs:
  nginx-html:
  nginx-vhost:
  acme:
```

**Benefits:**
- Automatic certificate issuance
- Automatic renewal (checks daily)
- Zero manual intervention

### Certificate Validity

- **Let's Encrypt certificates are valid for 90 days**
- Auto-renewal typically runs 30 days before expiration
- Daily cron jobs ensure certificates never expire

**Sources:**
- [How to Setup SSL with Docker, NGINX and Let's Encrypt](https://www.programonaut.com/setup-ssl-with-docker-nginx-and-lets-encrypt/)
- [nginx-proxy + Let's Encrypt in 5 Minutes](https://pentacent.medium.com/nginx-and-lets-encrypt-with-docker-in-less-than-5-minutes-b4b8a60d3a71)
- [Let's Encrypt Docker Compose](https://github.com/eugene-khyst/letsencrypt-docker-compose)

---

## Monitoring & Logging

### Why Monitoring is Critical

Production applications need:
- **Real-time visibility**: Know what's happening right now
- **Historical data**: Identify trends and capacity plan
- **Alerting**: Be notified when things go wrong
- **Troubleshooting**: Debug issues quickly

### Monitoring Stack: Prometheus + Grafana + Loki

**Architecture:**
```
Application → Prometheus (metrics) → Grafana (visualization)
           → Loki (logs) → Grafana
Container  → cAdvisor (container metrics) → Prometheus
```

### Complete Docker Compose Setup

```yaml
version: '3.8'

services:
  # Your application
  api:
    image: eto-api:latest
    container_name: eto-api
    expose:
      - "8000"
    networks:
      - app_network
      - monitoring
    labels:
      logging: "promtail"

  # Prometheus - Metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - monitoring

  # Grafana - Visualization
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD_FILE=/run/secrets/grafana_password
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    secrets:
      - grafana_password
    networks:
      - monitoring

  # cAdvisor - Container metrics
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    networks:
      - monitoring

  # Node Exporter - Host metrics
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

  # Loki - Log aggregation
  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki/loki-config.yml:/etc/loki/local-config.yaml
      - loki-data:/loki
    networks:
      - monitoring

  # Promtail - Log shipping
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    restart: unless-stopped
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./monitoring/promtail/promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring

networks:
  app_network:
  monitoring:

volumes:
  prometheus-data:
  grafana-data:
  loki-data:

secrets:
  grafana_password:
    file: ./secrets/grafana_password.txt
```

### Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Your FastAPI application
  - job_name: 'fastapi'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  # cAdvisor - Container metrics
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # Node Exporter - Host metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### FastAPI Prometheus Metrics Integration

```python
# Install prometheus-fastapi-instrumentator
# pip install prometheus-fastapi-instrumentator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

# This creates a /metrics endpoint automatically
```

### Grafana Dashboard Setup

1. **Access Grafana**: `http://localhost:3000`
2. **Add Data Sources**:
   - Prometheus: `http://prometheus:9090`
   - Loki: `http://loki:3100`
3. **Import Dashboards**:
   - Docker & Host Monitoring: Dashboard ID `179`
   - Node Exporter Full: Dashboard ID `1860`
   - Loki Logs: Dashboard ID `13639`

### Log Aggregation with Loki

```yaml
# monitoring/loki/loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

### Alerting Configuration

```yaml
# monitoring/prometheus/alert-rules.yml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{name="eto-api"} / container_spec_memory_limit_bytes{name="eto-api"} > 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Container using {{ $value }}% of memory limit"

      - alert: ContainerDown
        expr: up{job="fastapi"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API container is down"
          description: "API has been down for more than 1 minute"
```

**Sources:**
- [Application Monitoring with Prometheus, Grafana, and Loki](https://medium.com/@rajpg16/application-monitoring-with-prometheus-grafana-and-loki-for-logs-using-docker-27ac98499d17)
- [Docker Monitoring with Prometheus and Grafana](https://signoz.io/guides/how-to-monitor-docker-containers-with-prometheus-and-grafana/)
- [Grafana Cloud: Monitoring Linux with Prometheus](https://grafana.com/docs/grafana-cloud/send-data/metrics/metrics-prometheus/prometheus-config-examples/docker-compose-linux/)

---

## Backup & Disaster Recovery

### Critical Understanding

**Docker containers are ephemeral** - They can be destroyed and recreated at any time.

**What to backup:**
- ✅ Database data (external SQL Server)
- ✅ Persistent volumes (uploaded files, etc.)
- ✅ Configuration files
- ✅ Secrets
- ❌ **NOT** container images (rebuild from code)
- ❌ **NOT** running containers (recreate from images)

### Database Backup Strategy

#### Option 1: SQL Server Native Backup (Recommended)

```bash
#!/bin/bash
# backup-database.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
DB_NAME="eto_db"

# Create backup using SQL Server
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -Q \
  "BACKUP DATABASE [$DB_NAME] TO DISK = N'/var/opt/mssql/backup/${DB_NAME}_${TIMESTAMP}.bak' WITH INIT, COMPRESSION"

# Copy backup to network storage
cp "/var/opt/mssql/backup/${DB_NAME}_${TIMESTAMP}.bak" "$BACKUP_DIR/"

# Retain only last 7 days of backups
find "$BACKUP_DIR" -name "*.bak" -mtime +7 -delete

echo "Backup completed: ${DB_NAME}_${TIMESTAMP}.bak"
```

**Cron schedule:**
```bash
# Daily at 2 AM
0 2 * * * /opt/scripts/backup-database.sh >> /var/log/db-backup.log 2>&1
```

#### Option 2: Docker Volume Backup

```bash
#!/bin/bash
# backup-volumes.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/volumes"

# Stop container to ensure consistency
docker-compose stop api

# Backup volume
docker run --rm \
  -v eto_app_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine \
  tar czf /backup/app_data_${TIMESTAMP}.tar.gz /data

# Restart container
docker-compose start api

echo "Volume backup completed: app_data_${TIMESTAMP}.tar.gz"
```

#### Option 3: Automated with docker-db-backup

```yaml
services:
  db-backup:
    image: tiredofit/db-backup
    container_name: db-backup
    restart: unless-stopped
    volumes:
      - ./backups:/backup
    environment:
      - DB_TYPE=mssql
      - DB_HOST=sqlserver.yourdomain.com
      - DB_NAME=eto_db
      - DB_USER=backup_user
      - DB_PASS_FILE=/run/secrets/db_backup_password
      - DB_BACKUP_INTERVAL=1440  # Daily (minutes)
      - DB_BACKUP_BEGIN=0200     # 2 AM
      - DB_CLEANUP_TIME=10080    # Keep 7 days
      - COMPRESSION=GZ
    secrets:
      - db_backup_password

secrets:
  db_backup_password:
    file: ./secrets/db_backup_password.txt
```

### Disaster Recovery Plan

#### DR Environment Setup

**Purpose:** Production mirror in different location for business continuity.

```yaml
# docker-compose.dr.yml
version: '3.8'

services:
  api:
    image: eto-api:latest
    # Same configuration as production
    environment:
      - DATABASE_URL=${DR_DATABASE_URL}
      - ENVIRONMENT=disaster-recovery
    networks:
      - dr_network

networks:
  dr_network:
    driver: bridge
```

#### Recovery Procedures

**Scenario 1: Container Failure**
```bash
# Container crashed - Docker restarts automatically (restart: unless-stopped)
# Manual restart if needed:
docker-compose restart api
```

**Scenario 2: Complete Host Failure**
```bash
# On new/backup server:

# 1. Pull latest code
git clone https://github.com/yourorg/eto_js.git
cd eto_js

# 2. Restore secrets
cp /backup/secrets/* ./secrets/

# 3. Restore database (if needed)
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -Q \
  "RESTORE DATABASE [eto_db] FROM DISK = N'/backup/eto_db_latest.bak' WITH REPLACE"

# 4. Deploy application
docker-compose pull
docker-compose up -d

# 5. Verify
curl https://api.yourdomain.com/health
```

**Scenario 3: Database Corruption**
```bash
# Restore from latest backup
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -Q \
  "RESTORE DATABASE [eto_db] FROM DISK = N'/backup/eto_db_20250101_020000.bak' WITH REPLACE"
```

### Backup Testing

**Critical:** Regularly test your backups!

```bash
#!/bin/bash
# test-backup-restore.sh

BACKUP_FILE="/backups/database/eto_db_latest.bak"
TEST_DB="eto_db_test"

# Restore to test database
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -Q \
  "RESTORE DATABASE [$TEST_DB] FROM DISK = N'$BACKUP_FILE' WITH MOVE 'eto_db' TO '/var/opt/mssql/data/${TEST_DB}.mdf', MOVE 'eto_db_log' TO '/var/opt/mssql/data/${TEST_DB}_log.ldf'"

# Verify data integrity
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -d $TEST_DB -Q \
  "SELECT COUNT(*) FROM information_schema.tables"

# Cleanup
sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -Q \
  "DROP DATABASE [$TEST_DB]"

echo "Backup test completed successfully"
```

**Schedule monthly:** First Sunday of each month

### Backup Checklist

- [ ] Database backed up daily
- [ ] Backups stored off-site (network storage or cloud)
- [ ] Backup retention policy defined (7-30 days)
- [ ] Backups tested monthly
- [ ] Recovery procedures documented
- [ ] DR environment maintained and tested quarterly
- [ ] Backup monitoring/alerting configured

**Sources:**
- [Docker Backup and Restore](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/)
- [How to Backup Docker Containers](https://www.baculasystems.com/blog/docker-backup-containers/)
- [Database Backup with Docker](https://github.com/tiredofit/docker-db-backup)

---

## CI/CD Pipeline

### GitHub Actions with Self-Hosted Runner

For on-premises deployment, use a **self-hosted runner** on your production server.

### Step 1: Install Self-Hosted Runner

```bash
# On your production server

# Create runner directory
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download runner (get latest URL from GitHub)
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure (follow prompts, get token from GitHub repo settings)
./config.sh --url https://github.com/yourorg/eto_js --token YOUR_TOKEN

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### Step 2: Secure Self-Hosted Runner

**Critical Security Practices:**

1. **Use dedicated unprivileged user:**
```bash
sudo adduser github-runner
sudo usermod -aG docker github-runner
# Configure runner as github-runner user
```

2. **Restrict runner to specific workflows:**
```yaml
# In GitHub repo settings → Actions → Runners
# Restrict runner to selected workflows only
```

3. **Never use for public repositories:**
```
⚠️ NEVER use self-hosted runners for public repos!
Risk: Malicious PRs can compromise your infrastructure
```

4. **Harden the OS:**
```bash
# Keep system updated
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable

# Disable root SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Step 3: Create Deployment Workflow

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd server-new
          pip install -r requirements.txt
          pip install pytest

      - name: Run tests
        run: |
          cd server-new
          pytest tests/

  build:
    needs: test
    runs-on: self-hosted  # Run on your on-premises server

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Create secrets directory
        run: mkdir -p secrets

      - name: Write secrets to files
        run: |
          echo "${{ secrets.API_SECRET_KEY }}" > secrets/api_secret_key.txt
          echo "${{ secrets.DB_PASSWORD }}" > secrets/db_password.txt
          chmod 600 secrets/*.txt

      - name: Build Docker image
        run: |
          docker build \
            -t eto-api:${{ github.sha }} \
            -t eto-api:latest \
            -f Dockerfile .

      - name: Run security scan
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy image eto-api:latest

  deploy:
    needs: build
    runs-on: self-hosted

    steps:
      - name: Deploy with Docker Compose
        run: |
          docker-compose down
          docker-compose up -d

      - name: Wait for health check
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

      - name: Verify deployment
        run: |
          docker-compose ps
          curl -f http://localhost:8000/health || exit 1

      - name: Cleanup old images
        run: |
          docker image prune -af --filter "until=168h"

  notify:
    needs: deploy
    runs-on: self-hosted
    if: always()

    steps:
      - name: Send deployment notification
        run: |
          if [ "${{ needs.deploy.result }}" == "success" ]; then
            echo "✅ Deployment successful: ${{ github.sha }}"
          else
            echo "❌ Deployment failed: ${{ github.sha }}"
          fi
          # Send to Slack, email, etc.
```

### Step 4: Advanced Deployment with Rollback

```yaml
# .github/workflows/deploy-with-rollback.yml
name: Deploy with Rollback Capability

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: self-hosted

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Record previous image
        run: |
          docker inspect eto-api:latest | jq -r '.[0].Id' > previous-image.txt
          echo "Previous image: $(cat previous-image.txt)"

      - name: Build new image
        run: docker build -t eto-api:${{ github.sha }} -t eto-api:latest .

      - name: Deploy new version
        run: docker-compose up -d

      - name: Health check
        id: health-check
        run: |
          for i in {1..30}; do
            if curl -f http://localhost:8000/health; then
              echo "✅ Health check passed"
              exit 0
            fi
            echo "Waiting for service to be healthy... ($i/30)"
            sleep 2
          done
          echo "❌ Health check failed"
          exit 1

      - name: Rollback on failure
        if: failure() && steps.health-check.outcome == 'failure'
        run: |
          echo "🔄 Rolling back to previous version"
          PREVIOUS_IMAGE=$(cat previous-image.txt)
          docker tag $PREVIOUS_IMAGE eto-api:latest
          docker-compose up -d

          # Verify rollback
          sleep 5
          curl -f http://localhost:8000/health
```

### GitHub Secrets Configuration

In GitHub repo: **Settings → Secrets and variables → Actions**

Add secrets:
- `API_SECRET_KEY`
- `DB_PASSWORD`
- `DATABASE_URL`

### Alternative: Build on GitHub, Deploy on Self-Hosted

```yaml
name: Build on Cloud, Deploy on-Premises

jobs:
  build:
    runs-on: ubuntu-latest  # GitHub-hosted

    steps:
      - uses: actions/checkout@v4

      - name: Build and push to registry
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker build -t ghcr.io/${{ github.repository }}/api:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}/api:${{ github.sha }}

  deploy:
    needs: build
    runs-on: self-hosted  # Your server

    steps:
      - name: Pull and deploy
        run: |
          docker pull ghcr.io/${{ github.repository }}/api:${{ github.sha }}
          docker tag ghcr.io/${{ github.repository }}/api:${{ github.sha }} eto-api:latest
          docker-compose up -d
```

**Sources:**
- [GitHub Actions CI/CD Pipeline](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)
- [Self-Hosted Runner Security Best Practices](https://aws.amazon.com/blogs/devops/best-practices-working-with-self-hosted-github-action-runners-at-scale-on-aws/)
- [GitHub Self-Hosted Runners Security Guide](https://github.com/dduzgun-security/github-self-hosted-runners)

---

## Deployment Strategies

### Blue-Green Deployment

**Concept:** Run two identical production environments ("blue" and "green"). Only one serves traffic at a time.

```
Blue (v1.0 - Currently live) ← NGINX routes all traffic here
Green (v1.1 - Staging)       ← Not receiving traffic
```

**Deploy process:**
1. Deploy new version to Green environment
2. Test Green environment
3. Switch NGINX to route traffic to Green
4. Blue becomes the new staging environment

**Benefits:**
- ✅ Zero downtime
- ✅ Instant rollback (just switch back)
- ✅ Full environment for testing before switch

**Drawbacks:**
- ❌ Requires 2x resources
- ❌ Database changes must be backward-compatible

#### Implementation with Docker Compose

```yaml
# docker-compose.blue-green.yml
version: '3.8'

services:
  api-blue:
    image: eto-api:1.0.0
    container_name: api-blue
    expose:
      - "8000"
    networks:
      - app_network
    labels:
      - "environment=blue"

  api-green:
    image: eto-api:1.1.0
    container_name: api-green
    expose:
      - "8000"
    networks:
      - app_network
    labels:
      - "environment=green"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    networks:
      - app_network

networks:
  app_network:
```

#### NGINX Configuration for Blue-Green

```nginx
# nginx.conf
upstream backend {
    # Route to blue (current version)
    server api-blue:8000;

    # Switch to green by commenting blue and uncommenting green:
    # server api-green:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
    }
}
```

#### Automated Switching Script

```bash
#!/bin/bash
# switch-environment.sh

CURRENT=$(docker exec nginx nginx -T | grep -oP 'api-\K(blue|green)' | head -1)

if [ "$CURRENT" == "blue" ]; then
    NEW="green"
else
    NEW="blue"
fi

echo "Switching from $CURRENT to $NEW"

# Update NGINX config
sed -i "s/server api-$CURRENT:8000/server api-$NEW:8000/" nginx/nginx.conf

# Reload NGINX
docker exec nginx nginx -s reload

# Verify
sleep 2
curl -f http://localhost/health

echo "✅ Successfully switched to $NEW environment"
```

### Rolling Deployment

**Concept:** Update containers one at a time.

```
Container 1: v1.0 → v1.1 (updated)
Container 2: v1.0 (still running)
Container 3: v1.0 (still running)
         ↓
Container 1: v1.1
Container 2: v1.0 → v1.1 (updating)
Container 3: v1.0 (still running)
         ↓
All containers: v1.1
```

**Benefits:**
- ✅ No additional resources needed
- ✅ Gradual rollout reduces risk
- ✅ Can pause/rollback mid-deployment

**Drawbacks:**
- ❌ Multiple versions running simultaneously
- ❌ Slower than blue-green

#### Docker Compose Rolling Update

```bash
# Update one service at a time
docker-compose up -d --no-deps --scale api=3 --no-recreate api

# Or with scale down/up approach
docker-compose up -d --scale api=2  # Scale down
docker-compose pull api             # Pull new image
docker-compose up -d --scale api=3  # Scale up with new image
```

### Canary Deployment

**Concept:** Route small percentage of traffic to new version, gradually increase.

```
v1.0: 90% of traffic
v1.1: 10% of traffic (canary)
     ↓ (if stable)
v1.0: 50% of traffic
v1.1: 50% of traffic
     ↓ (if stable)
v1.1: 100% of traffic
```

#### NGINX Configuration for Canary

```nginx
upstream backend_stable {
    server api-v1:8000 weight=9;
}

upstream backend_canary {
    server api-v2:8000 weight=1;
}

split_clients "$request_id" $backend_servers {
    90%     backend_stable;
    *       backend_canary;
}

server {
    location / {
        proxy_pass http://$backend_servers;
    }
}
```

**Sources:**
- [Blue-Green vs Rolling Deployments](https://www.harness.io/blog/difference-between-rolling-and-blue-green-deployments)
- [Blue-Green Deployment Best Practices](https://octopus.com/devops/software-deployments/blue-green-deployment/)
- [AWS Blue-Green Deployments](https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/introduction.html)

---

## Common Production Questions

### Q1: Should I use Kubernetes?

**Answer:** Not necessarily for your use case.

**Use Kubernetes when:**
- ✅ Running microservices (10+ services)
- ✅ Need auto-scaling across multiple nodes
- ✅ Have dedicated DevOps team
- ✅ Multi-cloud or hybrid cloud deployment

**Use Docker Compose when:**
- ✅ Monolithic or small service count (1-5)
- ✅ Single server or small cluster
- ✅ Team is small, infrastructure needs are simple
- ✅ On-premises with limited resources

**Your situation:** Docker Compose is sufficient. You have a FastAPI backend and potentially a React frontend - this doesn't require Kubernetes complexity.

### Q2: How do I handle environment-specific configuration?

**Answer:** Use environment variables and separate compose files.

```bash
# Project structure
.
├── docker-compose.yml           # Base configuration
├── docker-compose.dev.yml       # Development overrides
├── docker-compose.prod.yml      # Production overrides
├── .env.dev                     # Dev environment variables
└── .env.prod                    # Prod environment variables
```

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

### Q3: How do I handle database migrations?

**Answer:** Run migrations as a separate container before starting the application.

```yaml
services:
  migration:
    image: eto-api:latest
    command: alembic upgrade head
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
    networks:
      - app_network

  api:
    image: eto-api:latest
    depends_on:
      migration:
        condition: service_completed_successfully
```

Or in GitHub Actions:

```yaml
- name: Run database migrations
  run: |
    docker run --rm \
      --network host \
      -e DATABASE_URL="${{ secrets.DATABASE_URL }}" \
      eto-api:latest \
      alembic upgrade head
```

### Q4: How do I handle file uploads in containers?

**Answer:** Use Docker volumes or external storage.

**Option 1: Named Volume**
```yaml
services:
  api:
    volumes:
      - uploads:/app/uploads

volumes:
  uploads:
```

**Option 2: Bind Mount (for backup)**
```yaml
services:
  api:
    volumes:
      - /opt/app-data/uploads:/app/uploads
```

**Option 3: S3-compatible storage (recommended for scale)**
```python
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='https://s3.yourdomain.com',
    aws_access_key_id='...',
    aws_secret_access_key='...'
)
```

### Q5: How many replicas/workers should I run?

**Answer:** Start with formula, then tune based on monitoring.

**Workers per container:**
- Formula: `(2 × CPU cores) + 1`
- Example: 4-core server → 9 workers

**Container replicas:**
- Start with 2-3 replicas for redundancy
- Scale based on CPU/memory usage
- Monitor with Prometheus and adjust

```yaml
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Q6: How do I do zero-downtime deployments?

**Answer:** Use health checks and rolling updates.

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 40s
```

Docker Compose will wait for health check to pass before stopping old container.

### Q7: Should I run the database in Docker?

**Answer:** Generally NO for production.

**Reasons to run database outside Docker:**
- ✅ Better performance (no container overhead)
- ✅ Easier backup/restore
- ✅ More mature tooling
- ✅ Better high availability options
- ✅ Your SQL Server is already external

**When Docker database is OK:**
- Development environments
- Testing/CI pipelines
- Stateless databases (cache, temporary data)

### Q8: How do I secure Docker in production?

**Security Checklist:**
- [ ] Run containers as non-root user
- [ ] Use secrets management (Docker secrets)
- [ ] Scan images for vulnerabilities
- [ ] Use minimal base images
- [ ] Set resource limits
- [ ] Enable Docker Content Trust (image signing)
- [ ] Regularly update images
- [ ] Use private registry for sensitive images
- [ ] Enable Docker daemon TLS
- [ ] Implement network segmentation

### Q9: How do I handle log rotation?

**Answer:** Configure Docker logging driver.

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"    # Maximum file size
        max-file: "5"       # Keep 5 files (50MB total)
        compress: "true"    # Compress rotated files
```

Or use external log aggregation (Loki, ELK stack).

### Q10: How do I perform load testing before production?

**Answer:** Use tools like Locust, k6, or Apache JMeter.

```python
# locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def get_modules(self):
        self.client.get("/api/modules")
```

```bash
# Run load test
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10
```

### Q11: What about CI/CD for frontend?

**Answer:** Build frontend as static files, serve through NGINX.

```dockerfile
# Frontend Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

```yaml
# docker-compose.yml
services:
  frontend:
    build: ./client
    ports:
      - "3000:80"
```

---

## Summary Checklist

### Initial Setup
- [ ] Install Docker and Docker Compose on server
- [ ] Set up GitHub repository
- [ ] Configure self-hosted GitHub Actions runner
- [ ] Create secrets directory structure
- [ ] Configure SQL Server for external connections

### Containerization
- [ ] Create production Dockerfile with multi-stage build
- [ ] Implement health check endpoint
- [ ] Configure Gunicorn + Uvicorn workers
- [ ] Set resource limits
- [ ] Create docker-compose.yml

### Security
- [ ] Use Docker secrets for sensitive data
- [ ] Run containers as non-root user
- [ ] Scan images for vulnerabilities
- [ ] Configure NGINX with security headers
- [ ] Set up SSL/TLS with Let's Encrypt
- [ ] Implement rate limiting

### Networking
- [ ] Configure NGINX reverse proxy
- [ ] Set up external SQL Server connection
- [ ] Configure Docker networks
- [ ] Set up firewall rules

### Monitoring
- [ ] Deploy Prometheus for metrics
- [ ] Deploy Grafana for visualization
- [ ] Deploy Loki for log aggregation
- [ ] Configure alerting rules
- [ ] Set up health check monitoring

### Backup & DR
- [ ] Configure automated database backups
- [ ] Set up off-site backup storage
- [ ] Create disaster recovery procedures
- [ ] Test backup restoration monthly
- [ ] Document recovery procedures

### CI/CD
- [ ] Create deployment workflow
- [ ] Configure automated testing
- [ ] Implement deployment verification
- [ ] Set up rollback capability
- [ ] Configure deployment notifications

### Production Launch
- [ ] Perform load testing
- [ ] Run security audit
- [ ] Verify all backups working
- [ ] Test rollback procedure
- [ ] Train team on operations
- [ ] Create runbook documentation

---

## Additional Resources

### Official Documentation
- [Docker Docs](https://docs.docker.com/)
- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Tools
- [Trivy - Vulnerability Scanner](https://github.com/aquasecurity/trivy)
- [docker-db-backup](https://github.com/tiredofit/docker-db-backup)
- [nginx-proxy](https://github.com/nginx-proxy/nginx-proxy)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)

### Community Resources
- [Docker Community Forums](https://forums.docker.com/)
- [r/docker Subreddit](https://www.reddit.com/r/docker/)
- [Stack Overflow - Docker Tag](https://stackoverflow.com/questions/tagged/docker)

---

**Document Version:** 1.0
**Last Updated:** October 2025
**Maintained By:** ETO Development Team
