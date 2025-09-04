#!/bin/bash

# ETO Transformation Pipeline Server Kill Script
# Kills Flask server processes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Killing ETO Transformation Pipeline Server processes...${NC}"

# Find and kill Python processes running on port 8090
if command -v netstat &> /dev/null; then
    # Find processes using port 8090
    PIDS=$(netstat -ano | grep ":8090" | awk '{print $5}' | sort -u 2>/dev/null || true)
    
    for PID in $PIDS; do
        if [ ! -z "$PID" ] && [ "$PID" != "0" ]; then
            echo -e "${YELLOW}Killing process $PID (using port 8090)${NC}"
            taskkill //PID $PID //F 2>/dev/null || kill -9 $PID 2>/dev/null || true
        fi
    done
fi

# Also kill any Python processes with "transformation_pipeline" in the command
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows/Git Bash - use wmic/taskkill
    PYTHON_PIDS=$(wmic process where "name='python.exe' and commandline like '%transformation_pipeline%'" get processid /value 2>/dev/null | grep ProcessId | cut -d= -f2 | tr -d '\r' || true)
    
    for PID in $PYTHON_PIDS; do
        if [ ! -z "$PID" ] && [ "$PID" != "0" ]; then
            echo -e "${YELLOW}Killing transformation pipeline Python process $PID${NC}"
            taskkill //PID $PID //F 2>/dev/null || true
        fi
    done
else
    # Unix-like systems
    pkill -f "transformation_pipeline" 2>/dev/null || true
fi

echo -e "${GREEN}Server kill completed.${NC}"