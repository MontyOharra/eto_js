"""
Database Connection Management
Handles SQL Server connections, session management, and database creation
Uses synchronous SQLAlchemy (SQL Server does not support async operations well)
"""
import logging
import threading
from typing import Generator, TYPE_CHECKING
from urllib.parse import urlparse
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager

if TYPE_CHECKING:
    from shared.database.unit_of_work import UnitOfWork

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

    Uses synchronous SQLAlchemy (SQL Server does not support async operations well)
    """

    def __init__(self, database_url: str) -> None:
        """Initialize connection manager with database URL - doesn't connect yet"""
        if not database_url:
            raise ValueError("Database URL is required")

        self.database_url = database_url
        self.engine: Engine | None = None
        self.session_factory: sessionmaker | None = None
        self._initialized = False
        self._lock = threading.Lock()

        logger.info(f"DatabaseConnectionManager initialized for: {self._safe_url()}")
    
    def initialize_connection(self) -> None:
        """Initialize the database engine and session factory"""
        with self._lock:
            if self._initialized:
                logger.debug("Connection already initialized")
                return

            try:
                logger.debug(f"Initializing database connection to: {self._safe_url()}")

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
                    autoflush=False,
                    expire_on_commit=False,  # Don't expire objects after commit
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
    
    def _verify_database_exists(self) -> None:
        """Verify that the database exists - raises error if not"""
        try:
            # Simple query to test connection and database existence
            assert self.engine is not None
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
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Create a session with automatic commit/rollback.

        Usage:
            with connection_manager.session() as session:
                result = session.execute(query)
                # Auto-commits on success, auto-rolls back on exception
        """
        if not self._initialized:
            raise DatabaseConnectionError(
                "Connection not initialized. Call initialize_connection() first."
            )

        if not self.session_factory:
            raise DatabaseConnectionError("Session factory not available")

        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def unit_of_work(self) -> Generator["UnitOfWork", None, None]:
        """
        Create a Unit of Work for managing multi-table transactions.

        The Unit of Work provides access to all repositories within a single
        transaction context. All operations commit together atomically.

        Usage:
            with connection_manager.unit_of_work() as uow:
                # Access repositories through UoW
                config = uow.email_configs.create(config_data)
                email = uow.emails.create(email_data)
                # Both operations commit together automatically

        Returns:
            UnitOfWork instance with shared session

        Raises:
            DatabaseConnectionError: If connection not initialized
        """
        from shared.database.unit_of_work import UnitOfWork

        if not self._initialized:
            raise DatabaseConnectionError(
                "Connection not initialized. Call initialize_connection() first."
            )

        if not self.session_factory:
            raise DatabaseConnectionError("Session factory not available")

        # Create session and UoW
        session = self.session_factory()
        uow = UnitOfWork(session)
        try:
            yield uow
            # Commit transaction on success
            session.commit()
            logger.debug("UoW transaction committed")
        except Exception:
            # Rollback on any exception
            session.rollback()
            logger.debug("UoW transaction rolled back due to exception")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            if not self._initialized:
                return False

            with self.session() as session:
                session.execute(text("SELECT 1"))

            logger.debug("Database connection test successful")
            return True

        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close database connections and cleanup"""
        with self._lock:
            if self.engine:
                self.engine.dispose()
                self.engine = None
                self.session_factory = None
                self._initialized = False

        logger.info("Closed database connections")
        
    def _safe_url(self) -> str:
        """Return database URL with credentials masked for logging"""
        try:
            parsed = urlparse(self.database_url)
            if parsed.password:
                safe_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
                return self.database_url.replace(parsed.netloc, safe_netloc)
            return self.database_url
        except Exception:
            return "***"
    
    def _parse_database_name(self) -> str:
        """Extract database name from URL"""
        try:
            parsed = urlparse(self.database_url)
            return parsed.path.lstrip('/')
        except Exception:
            return "unknown"




# Global connection manager instance with thread safety
_connection_manager: DatabaseConnectionManager | None = None
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


def get_connection_manager() -> DatabaseConnectionManager | None:
    """Get the global connection manager instance"""
    if _connection_manager is None:
        logger.warning("Database connection not initialized. Call init_database_connection() first.")

    return _connection_manager