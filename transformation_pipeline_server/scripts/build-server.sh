#!/bin/bash

# ETO Transformation Pipeline Server Build Script (Bash)
# Builds and deploys Flask server to C:\apps\eto\transformation_pipeline_server

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

echo -e "${GREEN}Resetting deployment folder: $DEPLOY_ROOT${NC}"
if [ -d "$DEPLOY_ROOT" ]; then
    echo -e "${YELLOW}Removing existing deployment...${NC}"
    rm -rf "$DEPLOY_ROOT"
fi
mkdir -p "$DEPLOY_ROOT"

# Copy server source to deploy root (exclude local venv, scripts, caches)
echo -e "${GREEN}Copying server to $DEPLOY_ROOT${NC}"
# Copy files manually (more compatible with Git Bash)
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/requirements.txt" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/env.example" "$DEPLOY_ROOT/" 2>/dev/null || true

# Copy src directory
if [ -d "$SERVER_ROOT/src" ]; then
    cp -r "$SERVER_ROOT/src" "$DEPLOY_ROOT/"
fi

# Ensure storage/logs exist
mkdir -p "$DEPLOY_ROOT/storage"
mkdir -p "$DEPLOY_ROOT/logs"

# Create venv IN THE DEPLOY FOLDER and install dependencies
echo -e "${GREEN}Setting up Python virtual environment in deploy folder${NC}"
VENV_PATH="$DEPLOY_ROOT/.venv"
python -m venv "$VENV_PATH"

# Determine Python executable path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Git Bash/Cygwin on Windows
    PYTHON_EXE="$VENV_PATH/Scripts/python.exe"
else
    # Unix-like systems
    PYTHON_EXE="$VENV_PATH/bin/python"
fi

# Install dependencies
REQ_PATH="$DEPLOY_ROOT/requirements.txt"
if [ -f "$REQ_PATH" ]; then
    echo -e "${GREEN}Installing Python dependencies${NC}"
    "$PYTHON_EXE" -m pip install --upgrade pip
    "$PYTHON_EXE" -m pip install -r "$REQ_PATH"
fi

# Copy .env files if present from project
ENV_FILE="$SERVER_ROOT/.env"
ENV_EXAMPLE="$SERVER_ROOT/env.example"

if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$DEPLOY_ROOT/"
fi

if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$DEPLOY_ROOT/"
fi

echo -e "${GREEN}Build complete. Deployed to $DEPLOY_ROOT${NC}"
echo -e "${GREEN}Python executable: $PYTHON_EXE${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Configure your database in $DEPLOY_ROOT/.env${NC}"
echo -e "  2. Run './server-scripts.sh resetdb' to create database${NC}"
echo -e "  3. Run './server-scripts.sh start' to start the server${NC}"

exit 0