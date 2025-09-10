#!/bin/bash

# Unified ETO Server Build Script (Bash)
# Builds and deploys Flask server to C:\apps\eto\server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(dirname "$SCRIPT_DIR")"

# Check for --confirm flag
SKIP_CONFIRMATION=false
if [ "$1" = "--confirm" ]; then
    SKIP_CONFIRMATION=true
fi

echo -e "${GREEN}Project root: $SERVER_ROOT${NC}"

# Deployment target (matches your requirement)
DEPLOY_ROOT="C:/apps/eto/server"

# Check if deployment directory exists and ask for confirmation
DEPLOYMENT_EXISTS=false
if [ -d "$DEPLOY_ROOT" ]; then
    DEPLOYMENT_EXISTS=true
fi

# Check if database exists (by trying to connect)
DATABASE_EXISTS=false
DATABASE_MANAGER_SCRIPT="$SERVER_ROOT/scripts/database/manage-database.sh"

if [ -f "$DATABASE_MANAGER_SCRIPT" ]; then
    echo -e "${GREEN}Checking database status...${NC}"
    if "$DATABASE_MANAGER_SCRIPT" check --silent 2>/dev/null; then
        DATABASE_EXISTS=true
    fi
fi

# Show confirmation if either deployment or database exists
if [ "$SKIP_CONFIRMATION" = false ]; then
    SHOW_CONFIRMATION=false
    
    if [ "$DEPLOYMENT_EXISTS" = true ] || [ "$DATABASE_EXISTS" = true ]; then
        SHOW_CONFIRMATION=true
        
        echo -e "${YELLOW}=== BUILD CONFIRMATION ===${NC}"
        echo ""
        
        if [ "$DEPLOYMENT_EXISTS" = true ]; then
            echo -e "${RED}⚠️  Existing server deployment found at: $DEPLOY_ROOT${NC}"
            echo -e "${RED}   This will completely remove and rebuild the server application.${NC}"
            echo ""
        fi
        
        if [ "$DATABASE_EXISTS" = true ]; then
            echo -e "${RED}⚠️  Existing database found.${NC}"
            echo -e "${RED}   This will DROP and RECREATE all database tables.${NC}"
            echo -e "${RED}   ALL DATA WILL BE PERMANENTLY LOST.${NC}"
            echo ""
        fi
        
        echo -e "${YELLOW}This build will:${NC}"
        if [ "$DEPLOYMENT_EXISTS" = true ]; then
            echo -e "  • Remove existing server deployment${NC}"
        fi
        echo -e "  • Deploy fresh server application${NC}"
        echo -e "  • Create virtual environment and install dependencies${NC}"
        if [ "$DATABASE_EXISTS" = true ]; then
            echo -e "  • Reset database (drop and recreate all tables)${NC}"
        else
            echo -e "  • Create new database with tables${NC}"
        fi
        echo ""
        echo -e "${YELLOW}Continue with build? [y/N]${NC}"
        read -r response
        
        case "$response" in
            [yY]|[yY][eE][sS])
                echo -e "${GREEN}Proceeding with build...${NC}"
                ;;
            *)
                echo -e "${YELLOW}Build cancelled by user${NC}"
                exit 0
                ;;
        esac
        echo ""
    fi
fi

echo -e "${GREEN}Starting server build...${NC}"

# Remove existing deployment
if [ "$DEPLOYMENT_EXISTS" = true ]; then
    echo -e "${GREEN}Removing existing deployment: $DEPLOY_ROOT${NC}"
    rm -rf "$DEPLOY_ROOT"
fi

echo -e "${GREEN}Creating deployment directory: $DEPLOY_ROOT${NC}"
mkdir -p "$DEPLOY_ROOT"

# Copy server source to deploy root (exclude local venv, scripts, caches)
echo -e "${GREEN}Copying server to $DEPLOY_ROOT${NC}"

# Copy main files
cp "$SERVER_ROOT/main.py" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/requirements.txt" "$DEPLOY_ROOT/" 2>/dev/null || true
cp "$SERVER_ROOT/env.example" "$DEPLOY_ROOT/" 2>/dev/null || true

# Copy src directory
if [ -d "$SERVER_ROOT/src" ]; then
    echo -e "${GREEN}Copying src directory...${NC}"
    cp -r "$SERVER_ROOT/src" "$DEPLOY_ROOT/"
fi

# Create required directories (logs and storage at same level as src)
echo -e "${GREEN}Creating required directories...${NC}"
mkdir -p "$DEPLOY_ROOT/logs"
mkdir -p "$DEPLOY_ROOT/storage"

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
    
    # Add additional dependencies that might be needed for validation
    echo -e "${GREEN}Installing additional validation dependencies${NC}"
    "$PYTHON_EXE" -m pip install jsonschema
fi

# Copy .env files if present from project
ENV_FILE="$SERVER_ROOT/.env"
ENV_EXAMPLE="$SERVER_ROOT/env.example"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Copying .env file${NC}"
    cp "$ENV_FILE" "$DEPLOY_ROOT/"
fi

if [ -f "$ENV_EXAMPLE" ]; then
    echo -e "${GREEN}Copying env.example file${NC}"
    cp "$ENV_EXAMPLE" "$DEPLOY_ROOT/"
fi

# Handle database operations using existing manage-database.sh
echo ""
echo -e "${GREEN}=== DATABASE SETUP ===${NC}"

if [ -f "$DATABASE_MANAGER_SCRIPT" ]; then
    # Change to project root for database operations
    cd "$SERVER_ROOT"
    
    if [ "$DATABASE_EXISTS" = true ]; then
        echo -e "${GREEN}Resetting existing database...${NC}"
        if [ "$SKIP_CONFIRMATION" = true ]; then
            "$DATABASE_MANAGER_SCRIPT" reset --confirm --silent
        else
            "$DATABASE_MANAGER_SCRIPT" reset --confirm --silent
        fi
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Database reset completed successfully${NC}"
        else
            echo -e "${RED}❌ Database reset failed${NC}"
            echo -e "${YELLOW}You may need to run './server-scripts.sh resetdb' manually${NC}"
        fi
    else
        echo -e "${GREEN}Creating new database...${NC}"
        if [ "$SKIP_CONFIRMATION" = true ]; then
            "$DATABASE_MANAGER_SCRIPT" create --confirm --silent
        else
            "$DATABASE_MANAGER_SCRIPT" create --confirm --silent
        fi
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Database created successfully${NC}"
        else
            echo -e "${RED}❌ Database creation failed${NC}"
            echo -e "${YELLOW}You may need to run './server-scripts.sh resetdb' manually${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Database management script not found${NC}"
    echo -e "${YELLOW}You will need to create the database manually${NC}"
fi

echo ""
echo -e "${GREEN}=== BUILD COMPLETE ===${NC}"
echo -e "${GREEN}Deployed to: $DEPLOY_ROOT${NC}"
echo -e "${GREEN}Python executable: $PYTHON_EXE${NC}"
echo ""
echo -e "${GREEN}Directory structure:${NC}"
echo -e "  $DEPLOY_ROOT/src/       - Server source code${NC}"
echo -e "  $DEPLOY_ROOT/logs/      - Log files${NC}"
echo -e "  $DEPLOY_ROOT/storage/   - Storage directory${NC}"
echo -e "  $DEPLOY_ROOT/.venv/     - Python virtual environment${NC}"
echo ""
echo -e "${GREEN}✅ Server build and database setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run './server-scripts.sh start' to start the server${NC}"
echo -e "  2. Visit http://localhost:8080/health to check server status${NC}"
echo -e "  3. Visit http://localhost:8080/api/email-ingestion/status for email service${NC}"

exit 0