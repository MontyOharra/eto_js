#!/bin/bash

# Unified ETO Server Refresh Script (Bash)
# Refreshes deployed files without rebuilding venv

set -e

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
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run ./server-scripts.sh build first.${NC}"
    exit 1
fi

echo -e "${GREEN}Refreshing server files in: $DEPLOY_ROOT${NC}"

# Copy main files
echo -e "${GREEN}Copying main.py...${NC}"
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true

# Copy src directory
if [ -d "$SERVER_ROOT/src" ]; then
    echo -e "${GREEN}Refreshing src directory...${NC}"
    if [ -d "$DEPLOY_ROOT/src" ]; then
        rm -rf "$DEPLOY_ROOT/src"
    fi
    cp -r "$SERVER_ROOT/src" "$DEPLOY_ROOT/"
fi

# Copy .env files if present from project
ENV_FILE="$SERVER_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Copying .env file${NC}"
    cp "$ENV_FILE" "$DEPLOY_ROOT/"
fi

echo -e "${GREEN}Refresh complete. Files updated in $DEPLOY_ROOT${NC}"
echo -e "${YELLOW}Note: Virtual environment and dependencies were not updated.${NC}"
echo -e "${YELLOW}Run './server-scripts.sh build' for a full rebuild including dependencies.${NC}"

exit 0