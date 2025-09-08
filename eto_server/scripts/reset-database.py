#!/usr/bin/env python3
"""
Database Reset Script for ETO System

This script drops all tables and recreates them with the current schema.
WARNING: This will delete all data in the database!

Usage:
    python reset-database.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt (for automation)
"""

import sys
import os
import argparse
from pathlib import Path

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import UnifiedDatabaseService, Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database connection string using same logic as main app"""
    import os
    
    # Try environment variable first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try to load from .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    return line.split('=', 1)[1].strip().strip('"\'')
    
    # Use same default as the main application
    return "mssql+pyodbc://test:testpassword@localhost:49172/eto_new?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"

def confirm_reset():
    """Ask user to confirm database reset"""
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("   - All emails will be lost")
    print("   - All PDF files will be lost") 
    print("   - All ETO runs will be lost")
    print("   - All templates will be lost")
    print("   - All cursors will be lost")
    print()
    
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    return response.lower() == 'yes'

def drop_all_tables(db_service):
    """Drop all tables by first dropping all foreign key constraints"""
    logger.info("Dropping all tables...")
    
    try:
        session = db_service.get_session()
        
        # First, drop all foreign key constraints
        logger.info("Dropping all foreign key constraints...")
        result = session.execute(text("""
            SELECT 
                fk.name AS FK_Name,
                tp.name AS Parent_Table
            FROM 
                sys.foreign_keys fk
                INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
        """))
        
        constraints = list(result)
        for constraint in constraints:
            fk_name, parent_table = constraint
            try:
                session.execute(text(f"ALTER TABLE [{parent_table}] DROP CONSTRAINT [{fk_name}]"))
                logger.info(f"Dropped FK constraint: {fk_name}")
            except Exception as e:
                logger.warning(f"Could not drop FK constraint {fk_name}: {e}")
        
        # Get all table names from the database
        result = session.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' 
            AND TABLE_SCHEMA = 'dbo'
        """))
        
        tables = [row[0] for row in result]
        
        # Now drop all tables (should work without FK constraints)
        for table in tables:
            try:
                session.execute(text(f"DROP TABLE IF EXISTS [{table}]"))
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Could not drop table {table}: {e}")
        
        session.commit()
        logger.info("✅ All tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def create_all_tables(db_service):
    """Create all tables with current schema"""
    logger.info("Creating all tables with new schema...")
    
    try:
        db_service.create_tables()
        logger.info("✅ All tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Reset ETO database (drops and recreates all tables)')
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompt (for automation)')
    
    args = parser.parse_args()
    
    print("🔄 ETO Database Reset Script")
    print("=" * 40)
    
    # Get confirmation unless --confirm flag is used
    if not args.confirm and not confirm_reset():
        print("❌ Database reset cancelled")
        sys.exit(0)
    
    try:
        # Get database connection
        database_url = get_database_url()
        # Log database info without credentials
        if '@' in database_url:
            db_info = database_url.split('@')[1]
        else:
            # Extract just the server/database part
            db_info = database_url.replace('mssql+pyodbc://', '').split('?')[0]
        logger.info(f"Connecting to database: {db_info}")
        
        db_service = UnifiedDatabaseService(database_url)
        
        # Drop all existing tables
        drop_all_tables(db_service)
        
        # Create all tables with new schema
        create_all_tables(db_service)
        
        print("✅ Database reset completed successfully!")
        print("   - All old tables dropped")
        print("   - All new tables created with current schema")
        print("   - Ready for email ingestion testing")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        print(f"❌ Database reset failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()