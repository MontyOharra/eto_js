#!/bin/bash

# ETO Server Start Script (Bash)
# Starts the deployed Flask server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Save original location
ORIGINAL_LOCATION=$(pwd)

# Deployment root
DEPLOY_ROOT="C:/apps/eto/server"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run build-server first.${NC}"
    exit 1
fi

# Check if main.py exists
APP_PATH="$DEPLOY_ROOT/main.py"
if [ ! -f "$APP_PATH" ]; then
    echo -e "${RED}main.py not found in $DEPLOY_ROOT${NC}"
    exit 1
fi

# Ensure storage/logs exist
mkdir -p "$DEPLOY_ROOT/storage"
mkdir -p "$DEPLOY_ROOT/logs"

echo -e "${GREEN}Starting Flask server from $DEPLOY_ROOT${NC}"

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

# Change to deploy directory and start server
cd "$DEPLOY_ROOT"
"$VENV_PYTHON" main.py

# Restore original location
cd "$ORIGINAL_LOCATION"

exit 0 