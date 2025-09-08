#!/bin/bash

# Unified ETO Server Build Script (Bash)
# Builds and deploys unified Flask server to C:\apps\eto\server

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

echo -e "${GREEN}Resetting deployment folder: $DEPLOY_ROOT${NC}"
if [ -d "$DEPLOY_ROOT" ]; then
    rm -rf "$DEPLOY_ROOT"
fi
mkdir -p "$DEPLOY_ROOT"

# Copy server source to deploy root (exclude local venv, scripts, caches)
echo -e "${GREEN}Copying server to $DEPLOY_ROOT${NC}"
# Copy files manually (more compatible with Git Bash)
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/requirements.txt" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/config.py" "$DEPLOY_ROOT/" 2>/dev/null || true
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

# Copy .env file if it exists in project
ENV_FILE="$SERVER_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Copying existing .env file...${NC}"
    cp "$ENV_FILE" "$DEPLOY_ROOT/"
fi

# Create .env from env.example template if .env doesn't exist
if [ ! -f "$DEPLOY_ROOT/.env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    if [ -f "$DEPLOY_ROOT/env.example" ]; then
        cp "$DEPLOY_ROOT/env.example" "$DEPLOY_ROOT/.env"
        echo -e "${YELLOW}Please edit .env file with your actual configuration values${NC}"
    else
        echo -e "${RED}Warning: env.example not found, .env file not created${NC}"
    fi
fi

# Clear data and reset database after successful build
echo -e "${GREEN}Clearing data folders and resetting database...${NC}"

# Clear data folders using our script
echo -e "${GREEN}Clearing data folders...${NC}"
"$SCRIPT_DIR/clear-data.sh" --confirm || echo -e "${YELLOW}Data clearing completed with warnings${NC}"

# Reset database using our script  
echo -e "${GREEN}Resetting database...${NC}"
"$SCRIPT_DIR/reset-database.sh" --confirm || echo -e "${YELLOW}Database reset completed with warnings${NC}"

echo -e "${GREEN}Build complete. Deployed to $DEPLOY_ROOT${NC}"
echo -e "${GREEN}Python executable: $PYTHON_EXE${NC}"
echo -e "${GREEN}Data folders and database have been reset${NC}"

exit 0 