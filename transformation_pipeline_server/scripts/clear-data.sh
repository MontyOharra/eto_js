#!/bin/bash

# ETO Transformation Pipeline Server Data Clear Script
# Clears log and storage data without affecting the database

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deployment root
DEPLOY_ROOT="C:/apps/eto/transformation_pipeline_server"

echo -e "${GREEN}Clearing data folders...${NC}"

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT${NC}"
    exit 1
fi

# Clear logs
if [ -d "$DEPLOY_ROOT/logs" ]; then
    echo -e "${YELLOW}Clearing logs...${NC}"
    rm -rf "$DEPLOY_ROOT/logs"/*
fi

# Clear storage
if [ -d "$DEPLOY_ROOT/storage" ]; then
    echo -e "${YELLOW}Clearing storage...${NC}"
    rm -rf "$DEPLOY_ROOT/storage"/*
fi

# Recreate directories
mkdir -p "$DEPLOY_ROOT/logs"
mkdir -p "$DEPLOY_ROOT/storage"

echo -e "${GREEN}Data folders cleared successfully!${NC}"