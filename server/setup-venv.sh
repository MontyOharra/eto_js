#!/bin/bash

# ETO Server Virtual Environment Setup Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up ETO Server Virtual Environment${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed or not in PATH${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
python -m venv .venv

# Determine Python executable path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Git Bash/Cygwin on Windows
    VENV_PYTHON=".venv/Scripts/python.exe"
    VENV_PIP=".venv/Scripts/pip.exe"
else
    # Unix-like systems
    VENV_PYTHON=".venv/bin/python"
    VENV_PIP=".venv/bin/pip"
fi

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
"$VENV_PYTHON" -m pip install --upgrade pip

# Install requirements
echo -e "${GREEN}Installing requirements...${NC}"
"$VENV_PYTHON" -m pip install -r requirements.txt

echo -e "${GREEN}Virtual environment setup complete!${NC}"
echo -e "${YELLOW}Python executable: $VENV_PYTHON${NC}"
echo -e "${YELLOW}Pip executable: $VENV_PIP${NC}"
echo ""
echo -e "${GREEN}To activate the virtual environment:${NC}"
echo -e "${YELLOW}  source .venv/Scripts/activate  # Windows (Git Bash)${NC}"
echo -e "${YELLOW}  source .venv/bin/activate      # Unix/Linux${NC}"
echo ""
echo -e "${GREEN}To run the server:${NC}"
echo -e "${YELLOW}  $VENV_PYTHON main.py${NC}"

exit 0 