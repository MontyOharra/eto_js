#!/usr/bin/env python3
"""
Database Manager Script
Core Python functionality for database operations
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    from src.shared.database.connection import DatabaseCreator, DatabaseConnectionError, DatabaseNotFoundError
except ImportError as e:
    print(f"❌ Import error: {e}", file=sys.stderr)
    print("Make sure you're running from the project root and dependencies are installed", file=sys.stderr)
    sys.exit(3)

# Exit codes (matching bash script)
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_CONNECTION_ERROR = 2
EXIT_CONFIG_ERROR = 3
EXIT_USER_CANCELLED = 4


class DatabaseManager:
    """Database management operations"""
    
    def __init__(self, verbose=False, silent=False):
        self.verbose = verbose
        self.silent = silent
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging based on verbosity level"""
        if self.silent:
            log_level = logging.WARNING
        elif self.verbose:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
            
        logging.basicConfig(
            level=log_level,
            format='%(levelname)s: %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_environment(self):
        """Load environment variables from .env file"""
        env_file = project_root / '.env'
        
        if not env_file.exists():
            self.logger.error(f"Environment file not found: {env_file}")
            self.logger.error("Please copy .env.example to .env and configure your database settings.")
            return None
            
        load_dotenv(env_file)
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            self.logger.error("DATABASE_URL not found in .env file")
            self.logger.error("Please configure DATABASE_URL in your .env file")
            return None
            
        self.logger.debug(f"Environment loaded from: {env_file}")
        return database_url
    
    def create_database(self, database_url):
        """Create database with all tables"""
        try:
            self.logger.info("Creating database with tables...")
            success = DatabaseCreator.create_database_with_tables(database_url)
            
            if success:
                self.logger.info("Database created successfully")
                return True
            else:
                self.logger.error("Failed to create database")
                return False
                
        except DatabaseConnectionError as e:
            self.logger.error(f"Database connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating database: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def reset_database(self, database_url):
        """Reset database (drop and recreate)"""
        try:
            self.logger.info("Resetting database...")
            success = DatabaseCreator.reset_database(database_url)
            
            if success:
                self.logger.info("Database reset successfully")
                return True
            else:
                self.logger.error("Failed to reset database")
                return False
                
        except DatabaseConnectionError as e:
            self.logger.error(f"Database connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error resetting database: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def check_database(self, database_url):
        """Check database status"""
        try:
            self.logger.info("Checking database status...")
            
            # Check if database exists
            exists = DatabaseCreator.database_exists(database_url)
            
            if exists:
                self.logger.info("✅ Database exists and is accessible")
                
                # Try to get table information
                try:
                    from src.shared.database.connection import DatabaseConnectionManager
                    conn_manager = DatabaseConnectionManager(database_url)
                    conn_manager.initialize_connection()
                    
                    # Test connection
                    if conn_manager.test_connection():
                        self.logger.info("✅ Database connection test successful")
                    else:
                        self.logger.warning("⚠️  Database exists but connection test failed")
                        
                    # Get table count
                    with conn_manager.session_scope() as session:
                        from src.shared.database.models import Base
                        table_count = len(Base.metadata.tables)
                        self.logger.info(f"📋 Database schema defines {table_count} tables")
                    
                    conn_manager.close()
                    return True
                    
                except DatabaseNotFoundError:
                    self.logger.error("❌ Database exists but is not accessible")
                    return False
                except Exception as e:
                    self.logger.warning(f"⚠️  Database exists but connection check failed: {e}")
                    return True  # Database exists even if we can't fully test it
                    
            else:
                self.logger.error("❌ Database does not exist")
                self.logger.info("Run with 'create' action to create the database")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking database: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def create_tables(self, database_url):
        """Create tables only (database must exist)"""
        try:
            self.logger.info("Creating database tables...")
            
            # First check if database exists
            if not DatabaseCreator.database_exists(database_url):
                self.logger.error("Database does not exist. Create the database first.")
                return False
            
            success = DatabaseCreator.create_tables(database_url)
            
            if success:
                self.logger.info("Database tables created successfully")
                return True
            else:
                self.logger.error("Failed to create database tables")
                return False
                
        except DatabaseConnectionError as e:
            self.logger.error(f"Database connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating tables: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Database Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python database_manager.py --action create
  python database_manager.py --action reset --confirm
  python database_manager.py --action check --verbose
        """
    )
    
    parser.add_argument(
        '--action',
        required=True,
        choices=['create', 'reset', 'check', 'tables'],
        help='Database operation to perform'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompts (for automation)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--silent',
        action='store_true',
        help='Minimal output (errors only)'
    )
    
    args = parser.parse_args()
    
    # Initialize database manager
    db_manager = DatabaseManager(verbose=args.verbose, silent=args.silent)
    
    # Load environment
    database_url = db_manager.load_environment()
    if not database_url:
        sys.exit(EXIT_CONFIG_ERROR)
    
    # Execute the requested action
    try:
        if args.action == 'create':
            success = db_manager.create_database(database_url)
        elif args.action == 'reset':
            success = db_manager.reset_database(database_url)
        elif args.action == 'check':
            success = db_manager.check_database(database_url)
        elif args.action == 'tables':
            success = db_manager.create_tables(database_url)
        else:
            db_manager.logger.error(f"Unknown action: {args.action}")
            sys.exit(EXIT_GENERAL_ERROR)
        
        # Exit with appropriate code
        if success:
            sys.exit(EXIT_SUCCESS)
        else:
            sys.exit(EXIT_GENERAL_ERROR)
            
    except DatabaseConnectionError:
        sys.exit(EXIT_CONNECTION_ERROR)
    except Exception as e:
        db_manager.logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(EXIT_GENERAL_ERROR)


if __name__ == '__main__':
    main()