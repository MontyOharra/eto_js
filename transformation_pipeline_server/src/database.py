"""
ETO Transformation Pipeline Database Models and Initialization
"""
import os
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Global database variables
_engine = None
_session_factory = None
_db_service = None

class DatabaseService:
    """Database service for managing connections and sessions"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.session_factory = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")
        
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.session_factory()
    
    def close(self):
        """Close the database engine"""
        if self.engine:
            self.engine.dispose()

# Base Models (will be expanded with detailed schema later)
class BaseModule(Base):
    """Base transformation modules defined by developers"""
    __tablename__ = 'base_modules'
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50), default='1.0.0')
    
    # New consolidated node configuration (JSON strings)
    input_config = Column(Text, nullable=False)   # JSON: NodeConfiguration for inputs
    output_config = Column(Text, nullable=False)  # JSON: NodeConfiguration for outputs
    config_schema = Column(Text)                  # JSON: List[ConfigSchema] for configuration options
    
    # Service endpoint information
    service_endpoint = Column(String(512))
    handler_name = Column(String(255))
    
    # UI theming
    color = Column(String(50), default='#3B82F6')
    category = Column(String(100), default='Processing')
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('idx_base_modules_name', 'name'),
        Index('idx_base_modules_active', 'is_active'),
    )

class CustomModule(Base):
    """Custom transformation modules created by users"""
    __tablename__ = 'custom_modules'
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user = Column(String(255), nullable=False)
    
    # JSON schemas for inputs, outputs, and configuration  
    input_schema = Column(Text, nullable=False)
    output_schema = Column(Text, nullable=False)
    config_schema = Column(Text)
    
    # Pipeline definition (references to other modules and connections)
    pipeline_definition = Column(Text, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('idx_custom_modules_name', 'name'),
        Index('idx_custom_modules_user', 'created_by_user'),
        Index('idx_custom_modules_active', 'is_active'),
    )

class Pipeline(Base):
    """Data transformation pipelines"""
    __tablename__ = 'pipelines'
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user = Column(String(255), nullable=False)
    
    # Pipeline definition (module references and connections)
    pipeline_definition = Column(Text, nullable=False)
    
    # Start and end modules for execution planning
    start_modules = Column(Text)  # Array of module IDs that begin the pipeline
    end_modules = Column(Text)   # Array of module IDs that end the pipeline
    
    # Execution metadata
    execution_metadata = Column(Text)
    
    # Status and metadata
    status = Column(String(50), default='draft')  # draft, active, archived
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('idx_pipelines_name', 'name'),
        Index('idx_pipelines_user', 'created_by_user'), 
        Index('idx_pipelines_status', 'status'),
        Index('idx_pipelines_active', 'is_active'),
    )

def init_database(database_url: str) -> DatabaseService:
    """Initialize the database connection and create tables"""
    global _engine, _session_factory, _db_service
    
    try:
        logger.info(f"Initializing transformation pipeline database connection...")
        
        # Try different SQL Server connection formats (similar to main server)
        connection_urls_to_try = [
            database_url,  # Original from .env
            database_url.replace("ODBC+Driver+17+for+SQL+Server", "SQL+Server"),  # SQL Server driver
            database_url.replace("driver=ODBC+Driver+17+for+SQL+Server", "driver=SQL+Server"),  # Alternative
        ]
        
        last_error = None
        for url in connection_urls_to_try:
            try:
                logger.info(f"Trying database connection: {url.split('://')[0]}://***")
                
                # Create database service
                db_service = DatabaseService(url)
                
                # Create tables
                db_service.create_tables()
                
                # Store globally
                _engine = db_service.engine
                _session_factory = db_service.session_factory 
                _db_service = db_service
                
                logger.info("Transformation pipeline database initialized successfully")
                return db_service
                
            except Exception as e:
                # If database doesn't exist, try to create it
                if "Cannot open database" in str(e) or "database" in str(e).lower():
                    logger.info("Database doesn't exist, attempting to create it...")
                    try:
                        # Try to create the database
                        create_database_if_not_exists(url)
                        # Retry connection after creating database
                        db_service = DatabaseService(url)
                        db_service.create_tables()
                        
                        # Store globally
                        _engine = db_service.engine
                        _session_factory = db_service.session_factory 
                        _db_service = db_service
                        
                        logger.info("Database created and initialized successfully")
                        return db_service
                    except Exception as create_error:
                        logger.error(f"Failed to create database: {create_error}")
                
                last_error = e
                logger.warning(f"Database connection attempt failed: {e}")
                continue
        
        # If all attempts failed, raise the last error
        raise last_error
        
    except Exception as e:
        logger.error(f"Failed to initialize transformation pipeline database: {e}")
        # Print available drivers for debugging
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            logger.info(f"Available ODBC drivers: {drivers}")
        except:
            pass
        raise

def get_db_service() -> Optional[DatabaseService]:
    """Get the global database service instance"""
    return _db_service

def create_database_if_not_exists(database_url: str):
    """Create the database if it doesn't exist (SQL Server)"""
    try:
        from urllib.parse import urlparse
        from sqlalchemy import text
        
        # Parse database URL to get database name
        parsed = urlparse(database_url)
        database_name = parsed.path.lstrip('/')
        
        # Create connection to master database to create new database
        master_url = database_url.replace(f"/{database_name}", "/master")
        
        logger.info(f"Checking if database '{database_name}' exists...")
        logger.info("Connecting to master database to create transformation pipeline database...")
        
        # Create engine for master database with autocommit
        master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
        
        with master_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text("SELECT database_id FROM sys.databases WHERE name = :db_name"), {"db_name": database_name}).fetchone()
            
            if not result:
                logger.info(f"Creating database '{database_name}'...")
                # CREATE DATABASE in autocommit mode
                conn.execute(text(f"CREATE DATABASE [{database_name}]"))
                logger.info(f"Database '{database_name}' created successfully")
            else:
                logger.info(f"Database '{database_name}' already exists")
        
        master_engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise