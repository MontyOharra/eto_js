#!/bin/bash

# ETO Transformation Pipeline Server Refresh Script (Bash)
# Copies updated files to deploy without rebuilding virtual environment

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
DEPLOY_ROOT="C:/apps/eto/transformation_pipeline_server"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run ./server-scripts.sh build first.${NC}"
    exit 1
fi

# Copy server source to deploy root
echo -e "${GREEN}Refreshing server files in $DEPLOY_ROOT${NC}"

# Copy main files
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/requirements.txt" "$DEPLOY_ROOT/" 2>/dev/null || true

# Copy src directory
if [ -d "$SERVER_ROOT/src" ]; then
    rm -rf "$DEPLOY_ROOT/src"
    cp -r "$SERVER_ROOT/src" "$DEPLOY_ROOT/"
fi

echo -e "${GREEN}Server refresh completed!${NC}"
echo -e "${YELLOW}Files updated in: $DEPLOY_ROOT${NC}"