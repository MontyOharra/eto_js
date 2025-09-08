#!/usr/bin/env python3
"""
Populate Base Modules Script for Unified ETO System

This script discovers and registers all transformation modules in the database.

Usage:
    python populate-modules.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt (for automation)
"""

import sys
import os
import argparse
from pathlib import Path

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import UnifiedDatabaseService, get_unified_db_service, init_unified_database
from modules import get_module_registry, populate_database_with_modules
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or .env file"""
    # Try environment first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    return line.split('=', 1)[1]
    
    # Default fallback
    return 'sqlite:///eto_unified.db'

def main():
    parser = argparse.ArgumentParser(description='Populate base modules in unified ETO database')
    parser.add_argument('--confirm', action='store_true',
                        help='Skip confirmation prompt (for automation)')
    
    args = parser.parse_args()
    
    if not args.confirm:
        response = input("This will populate base modules in the database. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            logger.info("Operation cancelled.")
            return 1
    
    try:
        database_url = get_database_url()
        
        # Initialize unified database if not already initialized
        try:
            db_service = get_unified_db_service()
        except RuntimeError:
            logger.info("Initializing unified database...")
            db_service = init_unified_database(database_url)
        
        # Initialize module registry and populate database
        logger.info("Discovering transformation modules...")
        registry = get_module_registry()
        
        if not registry.modules:
            logger.warning("No modules discovered!")
            return 1
        
        logger.info(f"Found {len(registry.modules)} modules:")
        for module_id, module in registry.modules.items():
            logger.info(f"  - {module_id}: {module.name}")
        
        # Populate database with discovered modules
        logger.info("Populating database with modules...")
        populate_database_with_modules()
        
        logger.info("Base modules populated successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to populate base modules: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())