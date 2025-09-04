#!/bin/bash

# Kill all Python processes (cleanup script)

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Killing all Python processes...${NC}"

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows/Git Bash - use taskkill
    echo -e "${YELLOW}Killing python.exe processes...${NC}"
    taskkill //F //IM python.exe 2>/dev/null || true
    
    echo -e "${YELLOW}Killing pythonw.exe processes...${NC}" 
    taskkill //F //IM pythonw.exe 2>/dev/null || true
    
else
    # Unix-like systems
    echo -e "${YELLOW}Killing python processes...${NC}"
    pkill -f python 2>/dev/null || true
fi

echo -e "${GREEN}Python processes killed.${NC}"