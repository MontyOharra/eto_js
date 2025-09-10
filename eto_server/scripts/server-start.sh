#!/bin/bash

# Unified ETO Server Start Script (Bash)
# Starts the deployed Flask server from C:\apps\eto\server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deployment root (matches your requirement)
DEPLOY_ROOT="C:/apps/eto/server"

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
    echo -e "${YELLOW}Virtual environment Python not found, using system Python${NC}"
    VENV_PYTHON="python"
fi

# Check if main.py exists
if [ ! -f "$DEPLOY_ROOT/main.py" ]; then
    echo -e "${RED}main.py not found in deployment directory. Make sure build completed successfully.${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Unified ETO Server...${NC}"
echo -e "${GREEN}Using Python: $VENV_PYTHON${NC}"
echo -e "${GREEN}Working directory: $(pwd)${NC}"
echo -e "${YELLOW}Server will be available at http://localhost:8080${NC}"
echo -e "${YELLOW}Health check: http://localhost:8080/health${NC}"
echo -e "${YELLOW}Email ingestion status: http://localhost:8080/api/email-ingestion/status${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
exec "$VENV_PYTHON" main.py