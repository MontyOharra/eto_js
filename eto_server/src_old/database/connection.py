"""
Database Connection Management
Handles SQL Server connections, session management, and database creation
"""
import logging
import threading
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError, DatabaseError
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Custom exception for database connection issues"""
    pass


class DatabaseNotFoundError(DatabaseConnectionError):
    """Raised when database doesn't exist"""
    pass


class DatabaseConnectionManager:
    """
    Manages database connections and session creation
    Does NOT create databases - only connects to existing ones
    """
    
    def __init__(self, database_url: str):
        """Initialize connection manager with database URL - doesn't connect yet"""
        if not database_url:
            raise ValueError("Database URL is required")
        
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._initialized = False
        self._lock = threading.Lock()
        
        logger.info(f"DatabaseConnectionManager initialized for: {self._safe_url()}")
    
    def initialize_connection(self):
        """Initialize the database engine and session factory"""
        with self._lock:
            if self._initialized:
                logger.debug("Connection already initialized")
                return
            
            try:
                logger.info(f"Initializing database connection to: {self._safe_url()}")
                
                # Create engine with SQL Server optimized settings
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,  # Verify connections before use
                    pool_recycle=3600,   # Recycle connections every hour
                    connect_args={
                        "timeout": 30,  # 30 second connection timeout
                    }
                )
                
                # Test connection and verify database exists
                self._verify_database_exists()
                
                # Create session factory
                self.session_factory = sessionmaker(
                    bind=self.engine,
                    autocommit=False,
                    autoflush=False
                )
                
                self._initialized = True
                logger.info("Database connection initialized successfully")
                
            except DatabaseNotFoundError:
                raise
            except OperationalError as e:
                error_msg = f"Failed to connect to database: {str(e)}"
                logger.error(error_msg)
                raise DatabaseConnectionError(error_msg) from e
            except Exception as e:
                error_msg = f"Unexpected error initializing database connection: {str(e)}"
                logger.error(error_msg)
                raise DatabaseConnectionError(error_msg) from e
    
    def _verify_database_exists(self):
        """Verify that the database exists - raises error if not"""
        try:
            # Simple query to test connection and database existence
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.debug("Database existence verified")
        except OperationalError as e:
            error_str = str(e).lower()
            database_name = self._parse_database_name()
            
            if "cannot open database" in error_str or "database" in error_str:
                raise DatabaseNotFoundError(
                    f"Database '{database_name}' does not exist. "
                    f"Please run the database creation script first."
                ) from e
            else:
                # Re-raise as connection error
                raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        if not self._initialized:
            raise DatabaseConnectionError("Connection not initialized. Call initialize_connection() first.")
        
        if not self.session_factory:
            raise DatabaseConnectionError("Session factory not available")
        
        return self.session_factory()
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around database operations"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            if not self._initialized:
                return False
            
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            
            logger.debug("Database connection test successful")
            return True
            
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close database connections and cleanup"""
        with self._lock:
            if self.engine:
                logger.info("Closing database connections")
                self.engine.dispose()
                self.engine = None
                self.session_factory = None
                self._initialized = False
    
    def _safe_url(self) -> str:
        """Return database URL with credentials masked for logging"""
        try:
            parsed = urlparse(self.database_url)
            if parsed.password:
                safe_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
                return self.database_url.replace(parsed.netloc, safe_netloc)
            return self.database_url
        except:
            return "***"
    
    def _parse_database_name(self) -> str:
        """Extract database name from URL"""
        try:
            parsed = urlparse(self.database_url)
            return parsed.path.lstrip('/')
        except:
            return "unknown"


class DatabaseCreator:
    """
    Utility class for creating SQL Server databases and tables
    Used by scripts only - not by application code
    """
    
    @staticmethod
    def create_database_with_tables(database_url: str) -> bool:
        """Create database and all tables - main method for scripts"""
        try:
            # Step 1: Create empty database
            DatabaseCreator.create_database_if_not_exists(database_url)
            
            # Step 2: Create all tables from models
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
            
            logger.info(f"Creating database '{database_name}'...")
            
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
            from .models import Base
            
            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"Creating tables in database '{database_name}'...")
            
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
            from .models import Base
            
            database_name = DatabaseCreator._parse_database_name(database_url)
            logger.info(f"Dropping all tables from database '{database_name}'...")
            
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
            logger.info(f"Resetting database '{database_name}'...")
            
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
            
            logger.info(f"Dropping database '{database_name}'...")
            
            # Get master database URL
            master_url = DatabaseCreator._get_master_url(database_url)
            
            # Create engine for master database with autocommit
            master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
            
            try:
                with master_engine.connect() as conn:
                    # Drop database - use brackets and force close connections
                    conn.execute(text(f"""
                        IF EXISTS (SELECT name FROM sys.databases WHERE name = '{database_name}')
                        BEGIN
                            ALTER DATABASE [{database_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE
                            DROP DATABASE [{database_name}]
                        END
                    """))
                
                logger.info(f"Database '{database_name}' dropped successfully")
                return True
                
            finally:
                master_engine.dispose()
                
        except Exception as e:
            error_msg = f"Failed to drop database: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e
    
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
    def _parse_database_name(database_url: str) -> str:
        """Extract database name from URL"""
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/').split('?')[0]
        
        if not database_name:
            raise ValueError("No database name found in URL")
        
        return database_name
    
    @staticmethod
    def _get_master_url(database_url: str) -> str:
        """Convert database URL to master database URL"""
        database_name = DatabaseCreator._parse_database_name(database_url)
        return database_url.replace(f"/{database_name}", "/master")


# Global connection manager instance with thread safety
_connection_manager: Optional[DatabaseConnectionManager] = None
_connection_lock = threading.Lock()


def init_database_connection(database_url: str) -> DatabaseConnectionManager:
    """Initialize global database connection"""
    global _connection_manager
    
    with _connection_lock:
        if _connection_manager is not None:
            logger.debug("Database connection already initialized")
            return _connection_manager
        
        try:
            _connection_manager = DatabaseConnectionManager(database_url)
            _connection_manager.initialize_connection()
            
            logger.info("Global database connection initialized")
            return _connection_manager
            
        except Exception as e:
            logger.error(f"Failed to initialize global database connection: {e}")
            _connection_manager = None
            raise


def get_connection_manager() -> Optional[DatabaseConnectionManager]:
    """Get the global connection manager instance"""
    if _connection_manager is None:
        logger.warning("Database connection not initialized. Call init_database_connection() first.")
    
    return _connection_manager