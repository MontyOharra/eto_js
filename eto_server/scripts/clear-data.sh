#!/bin/bash

# Clear Data Folders Script (Bash)
# Clears logs and storage directories

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deployment root
DEPLOY_ROOT="C:/apps/eto/server"

# Check for --confirm flag
CONFIRM=false
if [ "$1" = "--confirm" ]; then
    CONFIRM=true
fi

if [ "$CONFIRM" = false ]; then
    echo -e "${YELLOW}This will clear all logs and storage data.${NC}"
    echo -e "${YELLOW}Data will be permanently deleted.${NC}"
    echo -e "${RED}Are you sure you want to continue? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Operation cancelled${NC}"
        exit 0
    fi
fi

echo -e "${GREEN}Clearing data folders...${NC}"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${YELLOW}Deployment not found: $DEPLOY_ROOT${NC}"
    echo -e "${YELLOW}Nothing to clear${NC}"
    exit 0
fi

# Clear logs directory
if [ -d "$DEPLOY_ROOT/logs" ]; then
    echo -e "${GREEN}Clearing logs directory...${NC}"
    rm -rf "$DEPLOY_ROOT/logs"/*
    echo -e "${GREEN}Logs cleared${NC}"
else
    echo -e "${YELLOW}Logs directory not found${NC}"
fi

# Clear storage directory
if [ -d "$DEPLOY_ROOT/storage" ]; then
    echo -e "${GREEN}Clearing storage directory...${NC}"
    rm -rf "$DEPLOY_ROOT/storage"/*
    echo -e "${GREEN}Storage cleared${NC}"
else
    echo -e "${YELLOW}Storage directory not found${NC}"
fi

# Recreate empty directories
mkdir -p "$DEPLOY_ROOT/logs"
mkdir -p "$DEPLOY_ROOT/storage"

echo -e "${GREEN}Data clearing complete${NC}"

exit 0