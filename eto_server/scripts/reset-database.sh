#!/bin/bash

# Reset Database Script (Bash)
# Drops and recreates all database tables using existing database management infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Deployment root
DEPLOY_ROOT="C:/apps/eto/server"

# Check for --confirm flag
CONFIRM_FLAG=""
if [ "$1" = "--confirm" ]; then
    CONFIRM_FLAG="--confirm"
else
    echo -e "${RED}WARNING: This will DROP and RECREATE all database tables!${NC}"
    echo -e "${RED}All data will be permanently lost.${NC}"
    echo -e "${YELLOW}Are you sure you want to continue? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Operation cancelled${NC}"
        exit 0
    fi
    CONFIRM_FLAG="--confirm"
fi

# Check if deployment exists
if [ ! -d "$DEPLOY_ROOT" ]; then
    echo -e "${RED}Deployment not found: $DEPLOY_ROOT. Run ./server-scripts.sh build first.${NC}"
    exit 1
fi

# Change to deploy directory
cd "$DEPLOY_ROOT"

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
    echo -e "${YELLOW}Virtual environment Python not found, using system Python${NC}"
    VENV_PYTHON="python"
fi

echo -e "${GREEN}Resetting database using proper database layer...${NC}"
echo -e "${GREEN}Using Python: $VENV_PYTHON${NC}"

# Use the existing database management script from the src
DATABASE_MANAGER_SCRIPT="src/scripts/database/database_manager.py"

if [ -f "$DATABASE_MANAGER_SCRIPT" ]; then
    # Use existing database manager
    echo -e "${GREEN}Using existing database manager...${NC}"
    "$VENV_PYTHON" "$DATABASE_MANAGER_SCRIPT" --action reset $CONFIRM_FLAG
else
    # Fallback to direct database operations
    echo -e "${YELLOW}Database manager script not found, using direct operations...${NC}"
    
    cat > reset_db.py << 'EOF'
#!/usr/bin/env python3
"""Database Reset Script - Fallback Implementation"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting database reset...")
        
        # Import database components
        from src.database.connection import DatabaseCreator
        
        # Get database URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        logger.info("Resetting database using DatabaseCreator...")
        success = DatabaseCreator.reset_database(database_url)
        
        if success:
            logger.info("Database reset completed successfully!")
        else:
            logger.error("Database reset failed!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

    # Run the reset script
    "$VENV_PYTHON" reset_db.py
    
    # Clean up temporary script
    rm -f reset_db.py
fi

echo -e "${GREEN}Database reset complete!${NC}"
echo -e "${YELLOW}All tables have been dropped and recreated.${NC}"

exit 0