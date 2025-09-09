#!/bin/bash

#
# Database Management Script
# Provides interface for database operations (create, reset, check, tables)
#

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_GENERAL_ERROR=1
readonly EXIT_CONNECTION_ERROR=2
readonly EXIT_CONFIG_ERROR=3
readonly EXIT_USER_CANCELLED=4

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/database_manager.py"

# Default options
VERBOSE=false
SILENT=false
SKIP_CONFIRMATION=false
ACTION=""

# Logging functions
log_info() {
    if [[ "$SILENT" != "true" ]]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [[ "$SILENT" != "true" ]]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    if [[ "$SILENT" != "true" ]]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

log_verbose() {
    if [[ "$VERBOSE" == "true" && "$SILENT" != "true" ]]; then
        echo -e "${BLUE}🔍 $1${NC}"
    fi
}

# Help function
show_help() {
    cat << EOF
Database Management Script

USAGE:
    $(basename "$0") <action> [options]

ACTIONS:
    create      Create database with all tables
    reset       Drop and recreate database (destructive)
    check       Check if database exists and is accessible
    tables      Create tables only (database must exist)

OPTIONS:
    --confirm       Skip confirmation prompts (for automation)
    --silent        Minimal output (for scripts)
    --verbose       Detailed output (for debugging)
    --help         Show this help message

EXAMPLES:
    $(basename "$0") create
    $(basename "$0") reset --confirm --silent
    $(basename "$0") check --verbose
    
ENVIRONMENT:
    DATABASE_URL            Database connection string (from .env)
    SKIP_CONFIRMATION       Set to 'true' to skip prompts

EXIT CODES:
    0   Success
    1   General error
    2   Database connection error
    3   Configuration/environment error
    4   User cancelled operation
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            create|reset|check|tables)
                if [[ -n "$ACTION" ]]; then
                    log_error "Multiple actions specified. Use only one."
                    exit $EXIT_GENERAL_ERROR
                fi
                ACTION="$1"
                shift
                ;;
            --confirm)
                SKIP_CONFIRMATION=true
                shift
                ;;
            --silent)
                SILENT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit $EXIT_SUCCESS
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit $EXIT_GENERAL_ERROR
                ;;
        esac
    done

    # Check if action was provided
    if [[ -z "$ACTION" ]]; then
        log_error "No action specified."
        show_help
        exit $EXIT_GENERAL_ERROR
    fi
}

# Load environment variables
load_environment() {
    local env_file="$PROJECT_ROOT/.env"
    
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file not found: $env_file"
        log_error "Please copy .env.example to .env and configure your database settings."
        exit $EXIT_CONFIG_ERROR
    fi

    log_verbose "Loading environment from: $env_file"
    
    # Source the .env file
    set -o allexport
    source "$env_file"
    set +o allexport

    # Check for required DATABASE_URL
    if [[ -z "$DATABASE_URL" ]]; then
        log_error "DATABASE_URL not found in .env file"
        log_error "Please configure DATABASE_URL in your .env file"
        exit $EXIT_CONFIG_ERROR
    fi

    # Set skip confirmation from environment if not already set
    if [[ "$SKIP_CONFIRMATION_ENV" == "true" || "$SKIP_CONFIRMATION" == "true" ]]; then
        SKIP_CONFIRMATION=true
    fi

    log_verbose "Database URL loaded (credentials masked)"
}

# Confirmation for destructive operations
confirm_destructive_action() {
    local action="$1"
    local message="$2"
    
    if [[ "$SKIP_CONFIRMATION" == "true" ]]; then
        log_verbose "Skipping confirmation (automated mode)"
        return 0
    fi

    log_warning "$message"
    echo -n "Continue? [y/N]: "
    read -r response
    
    case "$response" in
        [yY]|[yY][eE][sS])
            return 0
            ;;
        *)
            log_info "Operation cancelled by user"
            exit $EXIT_USER_CANCELLED
            ;;
    esac
}

# Execute Python database manager
execute_database_operation() {
    local action="$1"
    local python_args=("--action" "$action")

    # Add options
    if [[ "$VERBOSE" == "true" ]]; then
        python_args+=("--verbose")
    fi

    if [[ "$SILENT" == "true" ]]; then
        python_args+=("--silent")
    fi

    if [[ "$SKIP_CONFIRMATION" == "true" ]]; then
        python_args+=("--confirm")
    fi

    log_verbose "Executing: python \"$PYTHON_SCRIPT\" ${python_args[*]}"

    # Change to project root to ensure proper imports
    cd "$PROJECT_ROOT" || {
        log_error "Failed to change to project root directory"
        exit $EXIT_GENERAL_ERROR
    }

    # Execute the Python script
    if [[ "$VERBOSE" == "true" ]]; then
        python "$PYTHON_SCRIPT" "${python_args[@]}"
    else
        python "$PYTHON_SCRIPT" "${python_args[@]}" 2>/dev/null
    fi

    return $?
}

# Main execution
main() {
    log_verbose "Starting database management script"
    log_verbose "Project root: $PROJECT_ROOT"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Load environment
    load_environment
    
    # Handle different actions
    case "$ACTION" in
        reset)
            confirm_destructive_action "reset" "This will permanently delete the database and all data."
            log_info "Resetting database..."
            ;;
        create)
            log_info "Creating database with tables..."
            ;;
        check)
            log_info "Checking database status..."
            ;;
        tables)
            log_info "Creating database tables..."
            ;;
    esac

    # Execute the database operation
    if execute_database_operation "$ACTION"; then
        case "$ACTION" in
            reset)
                log_success "Database reset completed successfully"
                ;;
            create)
                log_success "Database created successfully"
                ;;
            check)
                log_success "Database check completed"
                ;;
            tables)
                log_success "Database tables created successfully"
                ;;
        esac
        exit $EXIT_SUCCESS
    else
        local exit_code=$?
        case $exit_code in
            2)
                log_error "Database connection failed"
                exit $EXIT_CONNECTION_ERROR
                ;;
            3)
                log_error "Configuration error"
                exit $EXIT_CONFIG_ERROR
                ;;
            *)
                log_error "Database operation failed"
                exit $EXIT_GENERAL_ERROR
                ;;
        esac
    fi
}

# Run main function with all arguments
main "$@"