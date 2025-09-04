#!/usr/bin/env python3
"""
ETO Transformation Pipeline Database Reset Script

This script drops and recreates the transformation pipeline database and all tables.
Use with caution - this will delete all data!

Usage:
    python reset-database.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt (for automation)
"""

import os
import sys
import logging
import argparse
from urllib.parse import urlparse

# Add the src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
server_root = os.path.dirname(script_dir)
src_dir = os.path.join(server_root, 'src')
sys.path.insert(0, src_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def confirm_reset():
    """Ask user to confirm database reset"""
    print("⚠️  WARNING: This will DELETE ALL DATA in the transformation pipeline database!")
    print("   - All base modules will be lost")
    print("   - All custom modules will be lost") 
    print("   - All pipelines will be lost")
    print()
    
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    return response.lower() == 'yes'

def main():
    """Main database reset function"""
    parser = argparse.ArgumentParser(description='Reset transformation pipeline database (drops and recreates all tables)')
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompt (for automation)')
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)
        
    logger.info("ETO Transformation Pipeline Database Reset")
    logger.info("=" * 50)
    logger.info(f"Database URL: {database_url}")
    
    # Get confirmation unless --confirm flag is used
    if not args.confirm and not confirm_reset():
        logger.info("Database reset cancelled")
        return
    
    try:
        # Parse database URL
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        
        logger.info(f"Resetting database: {database_name}")
        
        # Import database utilities
        from database import create_database_if_not_exists, init_database, Base
        
        # First ensure database exists
        logger.info("Ensuring database exists...")
        create_database_if_not_exists(database_url)
        
        # Initialize database service
        logger.info("Connecting to database...")
        db_service = init_database(database_url)
        
        # Drop all tables
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(db_service.engine)
        
        # Recreate all tables
        logger.info("Creating fresh database tables...")
        Base.metadata.create_all(db_service.engine)
        
        # TODO: Add any default/seed data here
        logger.info("Database schema created successfully")
        
        # Close database connection
        db_service.close()
        
        logger.info("Database reset completed successfully!")
        logger.info("Next steps:")
        logger.info("  - Start the server with: ./server-scripts.sh start")
        logger.info("  - Check health at: http://localhost:8090/health")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()