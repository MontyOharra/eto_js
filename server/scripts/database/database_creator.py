#!/usr/bin/env python3
"""
Database Creator - Enhanced Version
Standalone database management operations with robust error handling and logging
"""
import logging
import os
from typing import Optional
from urllib.parse import urlparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, DatabaseError, ProgrammingError

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Custom exception for database connection issues"""
    pass


class DatabaseNotFoundError(DatabaseConnectionError):
    """Raised when database doesn't exist"""
    pass


class DatabaseCreator:
    """
    Static database creation and management operations
    Enhanced with detailed error handling and progress logging
    """

    @staticmethod
    def database_exists(database_url: str) -> bool:
        """Check if database exists with detailed error handling"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"🔍 Checking if database '{database_name}' exists...")

            master_url = DatabaseCreator._get_master_url(database_url)
            logger.debug(f"   Connecting to master database...")

            master_engine = create_engine(master_url, echo=False, pool_pre_ping=True)
            try:
                with master_engine.connect() as conn:
                    logger.debug(f"   Executing query: SELECT database_id FROM sys.databases WHERE name = '{database_name}'")
                    result = conn.execute(
                        text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
                        {"db_name": database_name}
                    ).fetchone()

                    exists = result is not None
                    status_icon = "✅" if exists else "❌"
                    logger.info(f"{status_icon} Database '{database_name}' exists: {exists}")
                    return exists

            finally:
                master_engine.dispose()
                logger.debug("   Master database connection closed")

        except OperationalError as e:
            logger.error(f"❌ Connection error while checking database existence")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Type: {type(e).__name__}")

            # Parse connection string safely
            try:
                parsed = urlparse(database_url)
                logger.error(f"   Server: {parsed.hostname}:{parsed.port or 'default'}")
            except:
                pass

            logger.error("")
            logger.error("   💡 Possible causes:")
            logger.error("      • SQL Server is not running")
            logger.error("      • Incorrect server address or port")
            logger.error("      • Network connectivity issues")
            logger.error("      • Firewall blocking connection")
            logger.error("      • ODBC driver not installed")
            return False

        except ProgrammingError as e:
            logger.error(f"❌ SQL syntax error while checking database")
            logger.error(f"   Error: {str(e)}")
            logger.error("   💡 This usually indicates a SQL Server version mismatch")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error checking database existence")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Type: {type(e).__name__}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            return False

    @staticmethod
    def create_database_with_tables(database_url: str) -> bool:
        """Create database and all tables with progress logging"""
        try:
            logger.info("=" * 60)
            logger.info("🚀 Starting database creation process...")
            logger.info("=" * 60)

            # Step 1: Create database
            logger.info("\n📦 Step 1: Creating database...")
            DatabaseCreator.create_database_if_not_exists(database_url)

            # Step 2: Create tables
            logger.info("\n📊 Step 2: Creating tables...")
            DatabaseCreator.create_tables(database_url)

            # Step 3: Create views
            logger.info("\n👁️  Step 3: Creating views...")
            DatabaseCreator.create_views(database_url)

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info("\n" + "=" * 60)
            logger.info(f"✅ SUCCESS: Database '{database_name}' created with all tables and views!")
            logger.info("=" * 60)
            return True

        except DatabaseConnectionError as e:
            logger.error(f"\n❌ Database connection error: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Failed to create database with tables: {str(e)}"
            logger.error(f"\n❌ {error_msg}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def create_database_if_not_exists(database_url: str) -> bool:
        """Create empty database with detailed logging"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)

            # Check if already exists
            if DatabaseCreator.database_exists(database_url):
                logger.info(f"   ✅ Database '{database_name}' already exists - skipping creation")
                return True

            logger.info(f"   📝 Creating new database '{database_name}'...")

            # Get master database URL
            master_url = DatabaseCreator._get_master_url(database_url)
            logger.debug(f"      Connecting to master database...")

            # Create engine with autocommit
            master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

            try:
                with master_engine.connect() as conn:
                    sql = f"CREATE DATABASE [{database_name}]"
                    logger.debug(f"      Executing: {sql}")
                    conn.execute(text(sql))

                logger.info(f"   ✅ Database '{database_name}' created successfully!")
                return True

            finally:
                master_engine.dispose()
                logger.debug("      Master database connection closed")

        except OperationalError as e:
            error_msg = f"Failed to create database - Connection error: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            raise DatabaseConnectionError(error_msg) from e
        except ProgrammingError as e:
            error_msg = f"Failed to create database - SQL error: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            logger.error("      💡 Check if you have CREATE DATABASE permissions")
            raise DatabaseConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to create database: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def create_tables(database_url: str) -> bool:
        """Create all database tables with detailed progress"""
        try:
            # Import models
            import sys
            from pathlib import Path

            logger.debug("      Loading database models...")
            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / 'src'
            sys.path.insert(0, str(src_path))

            # Import models
            import importlib.util
            models_path = src_path / 'shared' / 'database' / 'models.py'

            if not models_path.exists():
                raise FileNotFoundError(f"Models file not found: {models_path}")

            logger.debug(f"      Loading models from: {models_path}")

            models_spec = importlib.util.spec_from_file_location("models", models_path)
            models_module = importlib.util.module_from_spec(models_spec)
            models_spec.loader.exec_module(models_module)
            Base = models_module.BaseModel

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"   📋 Creating tables in database '{database_name}'...")

            # Create engine
            engine = create_engine(database_url, pool_pre_ping=True)

            try:
                # Get all table names before creation
                table_names = list(Base.metadata.tables.keys())
                logger.info(f"      Found {len(table_names)} tables to create:")
                for table_name in table_names:
                    logger.info(f"         • {table_name}")

                # Create all tables
                logger.debug(f"\n      Executing CREATE TABLE statements...")
                Base.metadata.create_all(bind=engine)

                # Verify tables were created
                inspector = inspect(engine)
                created_tables = inspector.get_table_names()

                logger.info(f"\n   ✅ Successfully created {len(created_tables)} tables:")
                for table_name in created_tables:
                    logger.info(f"         ✓ {table_name}")

                return True

            finally:
                engine.dispose()
                logger.debug("      Database connection closed")

        except FileNotFoundError as e:
            error_msg = f"Models file not found: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            logger.error("      💡 Make sure you're running from the project root directory")
            raise DatabaseConnectionError(error_msg) from e
        except OperationalError as e:
            error_msg = f"Failed to create tables - Connection error: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            raise DatabaseConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to create database tables: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            logger.error(f"      Error type: {type(e).__name__}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def create_views(database_url: str) -> bool:
        """Create all database views with progress logging"""
        try:
            import sys
            from pathlib import Path

            logger.debug("      Loading database views...")
            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / 'src'
            sys.path.insert(0, str(src_path))

            # Import views
            import importlib.util
            views_path = src_path / 'shared' / 'database' / 'views.py'

            if not views_path.exists():
                logger.warning(f"   ⚠️  Views file not found: {views_path} - skipping view creation")
                return True

            logger.debug(f"      Loading views from: {views_path}")

            views_spec = importlib.util.spec_from_file_location("views", views_path)
            views_module = importlib.util.module_from_spec(views_spec)
            views_spec.loader.exec_module(views_module)
            all_views = views_module.ALL_VIEWS

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"   📋 Creating views in database '{database_name}'...")

            # Create engine
            engine = create_engine(database_url, pool_pre_ping=True)

            try:
                logger.info(f"      Found {len(all_views)} views to create:")
                for view_name, _ in all_views:
                    logger.info(f"         • {view_name}")

                # Create each view
                with engine.connect() as conn:
                    for view_name, view_sql in all_views:
                        logger.debug(f"      Creating view: {view_name}")
                        conn.execute(text(view_sql))
                    conn.commit()

                logger.info(f"\n   ✅ Successfully created {len(all_views)} views")
                return True

            finally:
                engine.dispose()
                logger.debug("      Database connection closed")

        except FileNotFoundError as e:
            error_msg = f"Views file not found: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            raise DatabaseConnectionError(error_msg) from e
        except OperationalError as e:
            error_msg = f"Failed to create views - Connection error: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            raise DatabaseConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to create database views: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            logger.error(f"      Error type: {type(e).__name__}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def drop_all_tables(database_url: str) -> bool:
        """Drop all tables with progress logging"""
        try:
            import sys
            from pathlib import Path

            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / 'src'
            sys.path.insert(0, str(src_path))

            import importlib.util
            models_spec = importlib.util.spec_from_file_location(
                "models",
                src_path / 'shared' / 'database' / 'models.py'
            )
            models_module = importlib.util.module_from_spec(models_spec)
            models_spec.loader.exec_module(models_module)
            Base = models_module.BaseModel

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"   🗑️  Dropping all tables from database '{database_name}'...")

            engine = create_engine(database_url, pool_pre_ping=True)

            try:
                # Get table names before dropping
                table_names = list(Base.metadata.tables.keys())
                logger.info(f"      Dropping {len(table_names)} tables...")

                Base.metadata.drop_all(bind=engine)

                logger.info(f"   ✅ All tables dropped successfully")
                return True

            finally:
                engine.dispose()

        except Exception as e:
            error_msg = f"Failed to drop database tables: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def reset_database(database_url: str) -> bool:
        """Complete database reset with detailed progress"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)

            logger.info("=" * 60)
            logger.info(f"🔄 Resetting database '{database_name}'...")
            logger.info("=" * 60)

            # Step 1: Drop database
            logger.info("\n🗑️  Step 1: Dropping existing database...")
            DatabaseCreator.drop_database_if_exists(database_url)

            # Step 2: Recreate
            logger.info("\n📦 Step 2: Creating fresh database with tables...")
            DatabaseCreator.create_database_with_tables(database_url)

            logger.info("\n" + "=" * 60)
            logger.info(f"✅ SUCCESS: Database '{database_name}' reset complete!")
            logger.info("=" * 60)
            return True

        except Exception as e:
            error_msg = f"Failed to reset database: {str(e)}"
            logger.error(f"\n❌ {error_msg}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def drop_database_if_exists(database_url: str) -> bool:
        """Drop database with detailed logging"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)

            if not DatabaseCreator.database_exists(database_url):
                logger.info(f"   ℹ️  Database '{database_name}' doesn't exist - skipping drop")
                return True

            logger.info(f"   🗑️  Dropping database '{database_name}'...")

            master_url = DatabaseCreator._get_master_url(database_url)
            master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

            try:
                with master_engine.connect() as conn:
                    sql = f"DROP DATABASE [{database_name}]"
                    logger.debug(f"      Executing: {sql}")
                    conn.execute(text(sql))

                logger.info(f"   ✅ Database '{database_name}' dropped successfully")
                return True

            finally:
                master_engine.dispose()

        except Exception as e:
            error_msg = f"Failed to drop database: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            import traceback
            logger.debug(f"\n📋 Stack trace:\n{traceback.format_exc()}")
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def _parse_database_name(database_url: str) -> str:
        """Extract database name with validation"""
        try:
            parsed = urlparse(database_url)
            database_name = parsed.path.lstrip('/')
            if '?' in database_name:
                database_name = database_name.split('?')[0]

            if not database_name:
                raise ValueError("Database name is empty in URL")

            return database_name
        except Exception as e:
            raise ValueError(f"Invalid database URL format: {e}")

    @staticmethod
    def _get_master_url(database_url: str) -> str:
        """Get master database URL"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)
            master_url = database_url.replace(f"/{database_name}", "/master")
            logger.debug(f"      Master URL: {master_url.split('@')[0]}...@...")
            return master_url
        except Exception as e:
            raise ValueError(f"Failed to create master URL: {e}")

    @staticmethod
    def test_connection(database_url: str) -> bool:
        """Test database connection with detailed output"""
        try:
            logger.info("🔌 Testing database connection...")

            engine = create_engine(database_url, pool_pre_ping=True)
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1 AS test")).fetchone()
                    if result and result[0] == 1:
                        logger.info("   ✅ Connection test passed!")
                        return True
                    else:
                        logger.error("   ❌ Connection test failed - unexpected result")
                        return False
            finally:
                engine.dispose()

        except OperationalError as e:
            logger.error(f"❌ Connection test failed")
            logger.error(f"   Error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
