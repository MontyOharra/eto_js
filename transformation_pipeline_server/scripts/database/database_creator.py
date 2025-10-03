#!/usr/bin/env python3
"""
Database Creator
Standalone database management operations - separate from application runtime
"""
import logging
import os
from typing import Optional
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DatabaseError

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
    Separate from application runtime - used only by management scripts
    """

    @staticmethod
    def database_exists(database_url: str) -> bool:
        """Check if database exists"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)
            master_url = DatabaseCreator._get_master_url(database_url)

            master_engine = create_engine(master_url)
            try:
                with master_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
                        {"db_name": database_name}
                    ).fetchone()

                    exists = result is not None
                    logger.debug(f"Database '{database_name}' exists: {exists}")
                    return exists

            finally:
                master_engine.dispose()

        except Exception as e:
            logger.error(f"Error checking database existence: {e}")
            return False

    @staticmethod
    def create_database_with_tables(database_url: str) -> bool:
        """Create database and all tables in one operation"""
        try:
            # Step 1: Create database if it doesn't exist
            DatabaseCreator.create_database_if_not_exists(database_url)

            # Step 2: Create all tables
            DatabaseCreator.create_tables(database_url)

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"Database '{database_name}' created with all tables successfully")
            return True

        except Exception as e:
            error_msg = f"Failed to create database with tables: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def create_database_if_not_exists(database_url: str) -> bool:
        """Create empty database if it doesn't exist"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)

            if DatabaseCreator.database_exists(database_url):
                logger.info(f"Database '{database_name}' already exists")
                return True

            logger.debug(f"Creating database '{database_name}'...")

            # Get master database URL for creation
            master_url = DatabaseCreator._get_master_url(database_url)

            # Create engine for master database with autocommit
            master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")

            try:
                with master_engine.connect() as conn:
                    # Create database - use brackets to handle names with special chars
                    conn.execute(text(f"CREATE DATABASE [{database_name}]"))

                logger.info(f"Database '{database_name}' created successfully")
                return True

            finally:
                master_engine.dispose()

        except Exception as e:
            error_msg = f"Failed to create database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def create_tables(database_url: str) -> bool:
        """Create all database tables from models"""
        try:
            # Import models from the main application
            import sys
            from pathlib import Path

            # Add src to path to import models
            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / 'src'
            sys.path.insert(0, str(src_path))

            # Import models directly to avoid circular imports
            import importlib.util
            models_spec = importlib.util.spec_from_file_location(
                "models",
                src_path / 'shared' / 'database' / 'models.py'
            )
            models_module = importlib.util.module_from_spec(models_spec)
            models_spec.loader.exec_module(models_module)
            Base = models_module.BaseModel

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.debug(f"Creating tables in database '{database_name}'...")

            # Create temporary engine for table creation
            engine = create_engine(database_url)

            try:
                # Create all tables defined in models.py
                Base.metadata.create_all(bind=engine)

                # Log table creation details
                table_names = list(Base.metadata.tables.keys())
                logger.info(f"Created {len(table_names)} tables: {', '.join(table_names)}")
                return True

            finally:
                engine.dispose()

        except Exception as e:
            error_msg = f"Failed to create database tables: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def drop_all_tables(database_url: str) -> bool:
        """Drop all tables from database"""
        try:
            # Import models from the main application
            import sys
            from pathlib import Path

            # Add src to path to import models
            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / 'src'
            sys.path.insert(0, str(src_path))

            # Import models directly to avoid circular imports
            import importlib.util
            models_spec = importlib.util.spec_from_file_location(
                "models",
                src_path / 'shared' / 'database' / 'models.py'
            )
            models_module = importlib.util.module_from_spec(models_spec)
            models_spec.loader.exec_module(models_module)
            Base = models_module.BaseModel

            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.debug(f"Dropping all tables from database '{database_name}'...")

            # Create temporary engine for table operations
            engine = create_engine(database_url)

            try:
                # Drop all tables
                Base.metadata.drop_all(bind=engine)

                logger.info("All database tables dropped successfully")
                return True

            finally:
                engine.dispose()

        except Exception as e:
            error_msg = f"Failed to drop database tables: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def reset_database(database_url: str) -> bool:
        """Complete database reset - drop database and recreate with tables"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.debug(f"Resetting database '{database_name}'...")

            # Step 1: Drop entire database
            DatabaseCreator.drop_database_if_exists(database_url)

            # Step 2: Create fresh database with tables
            DatabaseCreator.create_database_with_tables(database_url)

            logger.info(f"Database '{database_name}' reset successfully")
            return True

        except Exception as e:
            error_msg = f"Failed to reset database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def drop_database_if_exists(database_url: str) -> bool:
        """Drop database if it exists"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)

            if not DatabaseCreator.database_exists(database_url):
                logger.info(f"Database '{database_name}' doesn't exist")
                return True

            logger.debug(f"Dropping database '{database_name}'...")

            # Get master database URL
            master_url = DatabaseCreator._get_master_url(database_url)

            # Create engine for master database with autocommit
            master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")

            try:
                with master_engine.connect() as conn:
                    # Drop database - use brackets to handle names with special chars
                    conn.execute(text(f"DROP DATABASE [{database_name}]"))

                logger.info(f"Database '{database_name}' dropped successfully")
                return True

            finally:
                master_engine.dispose()

        except Exception as e:
            error_msg = f"Failed to drop database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e

    @staticmethod
    def _parse_database_name(database_url: str) -> str:
        """Extract database name from connection URL"""
        try:
            parsed = urlparse(database_url)
            database_name = parsed.path.lstrip('/')
            # Remove query parameters if present
            if '?' in database_name:
                database_name = database_name.split('?')[0]
            return database_name
        except Exception as e:
            raise ValueError(f"Invalid database URL format: {e}")

    @staticmethod
    def _get_master_url(database_url: str) -> str:
        """Get master database URL for database operations"""
        try:
            database_name = DatabaseCreator._parse_database_name(database_url)
            return database_url.replace(f"/{database_name}", "/master")
        except Exception as e:
            raise ValueError(f"Failed to create master URL: {e}")

    @staticmethod
    def test_connection(database_url: str) -> bool:
        """Test database connection"""
        try:
            engine = create_engine(database_url)
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True
            finally:
                engine.dispose()
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False