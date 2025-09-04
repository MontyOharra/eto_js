#!/bin/bash
set -e

echo "ETO Transformation Pipeline Database Reset Script"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Save original location
ORIGINAL_LOCATION=$(pwd)

# Deployment root
DEPLOY_ROOT="C:/apps/eto/transformation_pipeline_server"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run ./server-scripts.sh build first.${NC}"
    exit 1
fi

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

echo -e "${GREEN}Using Python: $VENV_PYTHON${NC}"

# Change to deploy directory
cd "$DEPLOY_ROOT"

# Run the database reset script from source directory (since reset-database.py is not deployed)
SOURCE_SCRIPT="$(dirname "$0")/reset-database.py"
"$VENV_PYTHON" "$SOURCE_SCRIPT" "$@"

# Restore original location
cd "$ORIGINAL_LOCATION"

echo -e "${GREEN}Database reset completed!${NC}"