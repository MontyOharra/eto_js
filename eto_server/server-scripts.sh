#!/bin/bash

# Unified ETO Server Scripts Convenience Script (Bash)
# Provides easy access to all unified server management scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

# Function to show help
show_help() {
    echo -e "${CYAN}Unified ETO Server Scripts${NC}"
    echo -e "${CYAN}==================${NC}"
    echo ""
    echo -e "Usage: ./server-scripts.sh <action>${NC}"
    echo ""
    echo -e "${YELLOW}Actions:${NC}"
    echo -e "  build      - Build and deploy unified Flask server to C:\\apps\\eto\\server${NC}"
    echo -e "  refresh    - Copy updated files to deploy without venv rebuild${NC}"
    echo -e "  start      - Start the deployed Flask server${NC}"
    echo -e "  kill       - Kill any running Flask server instances${NC}"
    echo -e "  killpython - Kill all Python processes (cleanup before restart)${NC}"
    echo -e "  resetdb    - Reset database (drops and recreates all tables)${NC}"
    echo -e "  cleardata  - Clear data folders (logs, storage) without affecting database${NC}"
    echo -e "  help       - Show this help message${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo -e "  --confirm  - Skip confirmation prompts (for automation)${NC}"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ./server-scripts.sh build${NC}"
    echo -e "  ./server-scripts.sh build --confirm${NC}"
    echo -e "  ./server-scripts.sh start${NC}"
    echo -e "  ./server-scripts.sh resetdb${NC}"
    echo -e "  ./server-scripts.sh killpython${NC}"
}

# Check if action is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Action required${NC}"
    show_help
    exit 1
fi

ACTION="$1"

case "$ACTION" in
    "build")
        echo -e "${GREEN}Building and deploying Flask server...${NC}"
        # Pass through --confirm flag if provided
        if [ "$2" = "--confirm" ]; then
            "$SCRIPTS_DIR/build-server.sh" --confirm
        else
            "$SCRIPTS_DIR/build-server.sh"
        fi
        ;;
    "refresh")
        echo -e "${GREEN}Refreshing deployed Flask server files (no venv rebuild)...${NC}"
        "$SCRIPTS_DIR/refresh-server.sh"
        ;;
    "start")
        echo -e "${GREEN}Starting Flask server...${NC}"
        "$SCRIPTS_DIR/server-start.sh"
        ;;
    "kill")
        echo -e "${GREEN}Killing Flask server instances...${NC}"
        "$SCRIPTS_DIR/server-kill.sh"
        ;;
    "killpython")
        echo -e "${GREEN}Killing all Python processes...${NC}"
        "$SCRIPTS_DIR/kill-python.sh"
        ;;
    "resetdb")
        echo -e "${GREEN}Resetting database (dropping and recreating all tables)...${NC}"
        "$SCRIPTS_DIR/reset-database.sh"
        ;;
    "cleardata")
        echo -e "${GREEN}Clearing data folders (logs, storage)...${NC}"
        "$SCRIPTS_DIR/clear-data.sh"
        ;;
    "help")
        show_help
        ;;
    *)
        echo -e "${RED}Error: Unknown action '$ACTION'${NC}"
        show_help
        exit 1
        ;;
esac

exit 0 