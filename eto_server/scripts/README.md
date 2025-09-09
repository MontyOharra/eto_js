# ETO Server Scripts

This directory contains utility scripts for managing the ETO server application.

## Directory Structure

```
scripts/
├── README.md                   # This file
├── database/                   # Database management scripts
│   ├── manage-database.sh      # Bash interface for database operations
│   └── database_manager.py     # Python implementation
├── deployment/                 # Future: deployment scripts
├── monitoring/                 # Future: monitoring and health check scripts  
└── development/               # Future: development utility scripts
```

## Database Management

### Quick Start

```bash
# Create database with tables
./scripts/database/manage-database.sh create

# Reset database (destructive - removes all data)
./scripts/database/manage-database.sh reset

# Check database status
./scripts/database/manage-database.sh check

# Create tables only (database must exist)
./scripts/database/manage-database.sh tables
```

### Automation/CI Usage

```bash
# Non-interactive mode (no prompts)
./scripts/database/manage-database.sh reset --confirm --silent

# Verbose mode for debugging
./scripts/database/manage-database.sh create --verbose
```

### Integration with Build Scripts

```bash
# In your build script (e.g., server-scripts.sh)
./eto_server/scripts/database/manage-database.sh reset --confirm --silent
if [ $? -ne 0 ]; then
    echo "Database reset failed"
    exit 1
fi
```

### Exit Codes

- `0` - Success
- `1` - General error
- `2` - Database connection error  
- `3` - Configuration/environment error
- `4` - User cancelled operation

### Environment Requirements

The scripts require:
- `.env` file with `DATABASE_URL` configured
- Python environment with required dependencies installed
- SQL Server accessible with configured credentials

## Future Script Categories

### Deployment (`deployment/`)
- Production deployment scripts
- Environment setup and validation
- Configuration management

### Monitoring (`monitoring/`)
- Health check scripts
- Performance monitoring utilities
- Log analysis tools

### Development (`development/`)
- Development environment setup
- Test data generation
- Code quality tools