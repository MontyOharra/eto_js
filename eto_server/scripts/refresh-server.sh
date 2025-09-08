#!/bin/bash

# ETO Server Refresh Script (Bash)
# Refreshes deployed server files without rebuilding venv

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Project root: $SERVER_ROOT${NC}"

# Deployment target
DEPLOY_ROOT="C:/apps/eto/server"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run build-server first.${NC}"
    exit 1
fi

echo -e "${GREEN}Refreshing server files in $DEPLOY_ROOT${NC}"

# Copy server source to deploy root (exclude local venv, scripts, caches)
# Copy files manually (more compatible with Git Bash)
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/requirements.txt" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/env.example" "$DEPLOY_ROOT/" 2>/dev/null || true

# Copy src directory
if [ -d "$SERVER_ROOT/src" ]; then
    cp -r "$SERVER_ROOT/src" "$DEPLOY_ROOT/"
fi

# Ensure storage/logs exist (don't overwrite)
mkdir -p "$DEPLOY_ROOT/storage"
mkdir -p "$DEPLOY_ROOT/logs"

# Copy .env files if present from project
ENV_FILE="$SERVER_ROOT/.env"
ENV_EXAMPLE="$SERVER_ROOT/env.example"

if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$DEPLOY_ROOT/"
    echo -e "${GREEN}Updated .env file${NC}"
fi

if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$DEPLOY_ROOT/"
    echo -e "${GREEN}Updated env.example file${NC}"
fi

echo -e "${GREEN}Refresh complete. Files updated in $DEPLOY_ROOT${NC}"
echo -e "${YELLOW}Note: Virtual environment was not rebuilt.${NC}"
echo -e "${YELLOW}If you added new dependencies, run build-server instead.${NC}"

exit 0 