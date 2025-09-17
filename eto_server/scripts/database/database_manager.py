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
    print(f"🔍 Project root: {project_root}")
    print(f"🔍 Script location: {Path(__file__).parent}")
    print(f"🔍 Current working directory: {os.getcwd()}")

    # Load dotenv first
    from dotenv import load_dotenv
    print("✅ dotenv imported successfully")

    # Import database creator from local scripts directory
    print(f"🔍 Attempting to import from: {Path(__file__).parent / 'database_creator.py'}")
    from database_creator import DatabaseCreator, DatabaseConnectionError, DatabaseNotFoundError
    print("✅ database_creator imported successfully")

    # Import connection manager from main application
    src_path = project_root / 'src'
    print(f"🔍 Adding to Python path: {src_path}")
    sys.path.insert(0, str(src_path))

    print(f"🔍 Attempting to import from: {src_path / 'shared' / 'database' / 'connection.py'}")
    from shared.database.connection import DatabaseConnectionManager
    print("✅ DatabaseConnectionManager imported successfully")

except ImportError as e:
    print(f"❌ Import error: {e}", file=sys.stderr)
    print(f"❌ Error type: {type(e).__name__}", file=sys.stderr)
    print(f"❌ Error details: {str(e)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("🔍 Debug information:", file=sys.stderr)
    print(f"   Project root: {project_root}", file=sys.stderr)
    print(f"   Script directory: {Path(__file__).parent}", file=sys.stderr)
    print(f"   Current working directory: {os.getcwd()}", file=sys.stderr)
    print(f"   Python path: {sys.path[:3]}...", file=sys.stderr)
    print("", file=sys.stderr)
    print("💡 Troubleshooting:", file=sys.stderr)
    print("   1. Make sure you're running from the eto_server directory", file=sys.stderr)
    print("   2. Check that database_creator.py exists in scripts/database/", file=sys.stderr)
    print("   3. Verify virtual environment is activated", file=sys.stderr)
    print("   4. Run: pip install -r requirements.txt", file=sys.stderr)

    import traceback
    print("", file=sys.stderr)
    print("📍 Full traceback:", file=sys.stderr)
    traceback.print_exc()
    sys.exit(3)
except Exception as e:
    print(f"❌ Unexpected error during imports: {e}", file=sys.stderr)
    print(f"❌ Error type: {type(e).__name__}", file=sys.stderr)
    import traceback
    print("📍 Full traceback:", file=sys.stderr)
    traceback.print_exc()
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

        self.logger.info(f"🔍 Looking for .env file at: {env_file}")

        if not env_file.exists():
            self.logger.error(f"❌ Environment file not found: {env_file}")
            self.logger.error("📁 Files in project root:")
            try:
                for file in project_root.iterdir():
                    if file.is_file():
                        self.logger.error(f"   {file.name}")
            except Exception as e:
                self.logger.error(f"   Could not list files: {e}")
            self.logger.error("")
            self.logger.error("💡 To fix this:")
            self.logger.error("   1. Copy .env.example to .env")
            self.logger.error("   2. Configure your DATABASE_URL in the .env file")
            return None

        try:
            load_dotenv(env_file)
            self.logger.info(f"✅ Environment file loaded: {env_file}")
        except Exception as e:
            self.logger.error(f"❌ Failed to load .env file: {e}")
            return None

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            self.logger.error("❌ DATABASE_URL not found in .env file")
            self.logger.error("🔍 Available environment variables:")
            env_vars = [key for key in os.environ.keys() if not key.startswith('_')]
            for var in sorted(env_vars)[:10]:  # Show first 10 to avoid spam
                self.logger.error(f"   {var}")
            if len(env_vars) > 10:
                self.logger.error(f"   ... and {len(env_vars) - 10} more")
            self.logger.error("")
            self.logger.error("💡 Add this line to your .env file:")
            self.logger.error('   DATABASE_URL="mssql+pyodbc://user:pass@server:port/dbname?driver=ODBC+Driver+17+for+SQL+Server"')
            return None

        # Validate DATABASE_URL format
        if not database_url.startswith(('mssql+', 'sqlite://', 'postgresql://')):
            self.logger.warning(f"⚠️  Unusual DATABASE_URL format: {database_url[:50]}...")

        self.logger.debug(f"✅ DATABASE_URL loaded: {database_url[:30]}...")
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
                    conn_manager = DatabaseConnectionManager(database_url)
                    conn_manager.initialize_connection()
                    
                    # Test connection
                    if conn_manager.test_connection():
                        self.logger.info("✅ Database connection test successful")
                    else:
                        self.logger.warning("⚠️  Database exists but connection test failed")
                        
                    # Get table count
                    with conn_manager.session_scope() as session:
                        # Import models from main application
                        from shared.database.models import Base
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