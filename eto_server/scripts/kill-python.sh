#!/bin/bash

# Kill All Python Processes Script (Bash)
# Nuclear option - kills all Python processes (use with caution)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}WARNING: This will kill ALL Python processes!${NC}"
echo -e "${YELLOW}This includes any other Python applications you may have running.${NC}"
echo -e "${YELLOW}Press Ctrl+C within 5 seconds to cancel...${NC}"

sleep 5

echo -e "${GREEN}Killing all Python processes...${NC}"

# Windows approach using taskkill
if command -v taskkill >/dev/null; then
    echo -e "${GREEN}Using taskkill to kill all python.exe processes...${NC}"
    taskkill //IM python.exe //F 2>/dev/null || echo -e "${YELLOW}No python.exe processes found${NC}"
    taskkill //IM pythonw.exe //F 2>/dev/null || echo -e "${YELLOW}No pythonw.exe processes found${NC}"
fi

# Alternative approach using wmic
if command -v wmic >/dev/null; then
    echo -e "${GREEN}Using wmic to kill remaining Python processes...${NC}"
    wmic process where "name='python.exe'" delete 2>/dev/null || true
    wmic process where "name='pythonw.exe'" delete 2>/dev/null || true
fi

echo -e "${GREEN}Python process cleanup complete${NC}"
echo -e "${YELLOW}You may need to wait a few seconds for ports to be released${NC}"

exit 0