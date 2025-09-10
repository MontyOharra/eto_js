#!/bin/bash

# Unified ETO Server Kill Script (Bash)
# Kills running Flask server instances

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Killing Unified ETO Server instances...${NC}"

# Kill processes by port (8080 - default ETO server port)
PORT=8080
echo -e "${YELLOW}Checking for processes on port $PORT...${NC}"

if command -v netstat >/dev/null; then
    # Windows netstat approach
    PIDS=$(netstat -ano | grep ":$PORT " | awk '{print $5}' | sort | uniq)
    if [ -n "$PIDS" ]; then
        for PID in $PIDS; do
            if [ "$PID" != "0" ]; then
                echo -e "${GREEN}Killing process $PID on port $PORT${NC}"
                taskkill //PID $PID //F 2>/dev/null || true
            fi
        done
    else
        echo -e "${YELLOW}No processes found on port $PORT${NC}"
    fi
else
    echo -e "${YELLOW}netstat not available, trying alternative approaches...${NC}"
fi

# Kill by process name patterns
echo -e "${YELLOW}Killing Python processes running main.py...${NC}"

# Windows approach using wmic
if command -v wmic >/dev/null; then
    wmic process where "name='python.exe' and commandline like '%main.py%'" delete 2>/dev/null || true
fi

# Fallback: kill by process name containing main.py
if command -v tasklist >/dev/null; then
    PIDS=$(tasklist //FI "IMAGENAME eq python.exe" //FO CSV | grep -i python | cut -d'"' -f4)
    for PID in $PIDS; do
        # Check if this process is running main.py
        CMDLINE=$(wmic process where "processid=$PID" get commandline 2>/dev/null | grep -i main.py || true)
        if [ -n "$CMDLINE" ]; then
            echo -e "${GREEN}Killing Python process $PID running main.py${NC}"
            taskkill //PID $PID //F 2>/dev/null || true
        fi
    done
fi

echo -e "${GREEN}Server kill complete${NC}"
echo -e "${YELLOW}Note: It may take a moment for ports to be released${NC}"

exit 0