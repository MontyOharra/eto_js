#!/bin/bash

# ETO Server Kill Script (Bash)
# Kills any running Flask server instances

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Killing running Flask server instances...${NC}"

# Kill Python processes (Flask server instances)
if taskkill //F //IM python.exe 2>/dev/null; then
    echo -e "${GREEN}Successfully killed Python server processes${NC}"
else
    echo -e "${YELLOW}No Python server processes were running${NC}"
fi

# Also check for any processes using port 8080
echo -e "${YELLOW}Checking for processes on port 8080...${NC}"
netstat -ano | grep ":8080" | while read line; do
    pid=$(echo $line | awk '{print $5}')
    if [ -n "$pid" ] && [ "$pid" != "0" ]; then
        echo -e "${YELLOW}Found process $pid using port 8080, attempting to kill...${NC}"
        taskkill //F //PID $pid 2>/dev/null || echo -e "${RED}Could not kill process $pid${NC}"
    fi
done

echo -e "${GREEN}Server kill operation complete${NC}"

exit 0