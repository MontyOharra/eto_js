#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deployment root
DEPLOY_ROOT="C:/apps/eto/transformation_pipeline_server"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run ./server-scripts.sh build first.${NC}"
    exit 1
fi

# Change to deploy directory
cd "$DEPLOY_ROOT"

# Determine Python executable path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Git Bash/Cygwin on Windows
    VENV_PYTHON="$DEPLOY_ROOT/.venv/Scripts/python.exe"
else
    # Unix-like systems
    VENV_PYTHON="$DEPLOY_ROOT/.venv/bin/python"
fi

# Use system Python if venv Python doesn't exist
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python"
fi

echo -e "${GREEN}Starting ETO Transformation Pipeline Server...${NC}"
echo -e "${GREEN}Using Python: $VENV_PYTHON${NC}"
echo -e "${GREEN}Working directory: $(pwd)${NC}"
echo -e "${YELLOW}Server will be available at http://localhost:8090${NC}"
echo -e "${YELLOW}Health check: http://localhost:8090/health${NC}"
echo ""

# Start the server
exec "$VENV_PYTHON" main.py