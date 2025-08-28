"""
Database models and connection setup for ETO PDF extraction system
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class Email(Base):
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(255), nullable=False, index=True)
    subject = Column(String(500))
    sender_email = Column(String(255))
    sender_name = Column(String(255))
    received_date = Column(DateTime, nullable=False, index=True)
    folder_name = Column(String(100))
    has_pdf_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pdf_files = relationship("PdfFile", back_populates="email")
    eto_runs = relationship("EtoRun", back_populates="email")

class PdfFile(Base):
    __tablename__ = 'pdf_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger)
    sha256_hash = Column(String(64), nullable=False, index=True)  # REMOVED unique constraint
    mime_type = Column(String(100), default='application/pdf')
    page_count = Column(Integer)
    object_count = Column(Integer)  # Number of PDF objects extracted
    objects_json = Column(Text)  # PDF objects for template matching
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="pdf_files")
    eto_runs = relationship("EtoRun", back_populates="pdf_file")

class PdfTemplate(Base):
    __tablename__ = 'pdf_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    customer_name = Column(String(255))
    description = Column(Text)
    
    # Template matching signature
    signature_objects = Column(Text)  # JSON: objects that define this template
    signature_object_count = Column(Integer)  # For quick subset matching
    
    # Spatial extraction field definitions
    extraction_fields = Column(Text)  # JSON: spatial bounding box extraction fields
    
    # Template metadata  
    is_complete = Column(Boolean, default=False)  # User-marked completeness
    coverage_threshold = Column(Float, default=0.6)  # Expected coverage ratio
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Versioning
    version = Column(Integer, default=1)
    is_current_version = Column(Boolean, default=True)
    
    # Audit fields
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default='active')  # 'active', 'archived', 'draft'
    
    # Relationships
    eto_runs = relationship("EtoRun", back_populates="template")
    extraction_rules = relationship("TemplateExtractionRule", back_populates="template")

class TemplateExtractionRule(Base):
    __tablename__ = 'template_extraction_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey('pdf_templates.id'), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)  # "carrier_processing", "pickup_date_processing"
    final_target_field = Column(String(255), nullable=False)  # "address_id", "pickup_date"
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("PdfTemplate", back_populates="extraction_rules")
    extraction_steps = relationship("TemplateExtractionStep", back_populates="extraction_rule", cascade="all, delete-orphan")

class TemplateExtractionStep(Base):
    __tablename__ = 'template_extraction_steps'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    extraction_rule_id = Column(Integer, ForeignKey('template_extraction_rules.id'), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)  # 1, 2, 3... (execution order)
    step_name = Column(String(255), nullable=False)  # "extract_raw_carrier", "lookup_address_id"
    
    # Step configuration
    step_type = Column(String(50), nullable=False)  # 'raw_extract', 'sql_lookup', 'llm_parse'
    step_config = Column(Text)  # JSON: method-specific configuration
    
    # Input/Output
    input_fields = Column(Text)  # JSON: ["carrier_raw"]
    output_field = Column(String(255))  # "carrier_raw", "address_id"
    
    # Error handling
    error_handling = Column(String(50), default='fail_rule')  # 'fail_rule', 'skip_step', 'use_default'
    default_value = Column(Text)
    
    # Performance tracking
    avg_execution_time_ms = Column(Integer, default=0)
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    extraction_rule = relationship("TemplateExtractionRule", back_populates="extraction_steps")
    failed_eto_runs = relationship("EtoRun", foreign_keys="[EtoRun.failed_step_id]")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('extraction_rule_id', 'step_number', name='_rule_step_number_uc'),
    )

class EtoRun(Base):
    __tablename__ = 'eto_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    pdf_file_id = Column(Integer, ForeignKey('pdf_files.id'), nullable=False, index=True)
    
    # Processing status
    status = Column(String(50), nullable=False, index=True)  # 'success', 'failure', 'unrecognized', 'error'
    error_type = Column(String(50))  # 'processing_error', 'extraction_error', 'order_creation_error'
    error_message = Column(Text)
    error_details = Column(Text)  # JSON: detailed error info
    
    # Template matching results
    matched_template_id = Column(Integer, ForeignKey('pdf_templates.id'), nullable=True)
    template_version = Column(Integer)  # Which version was used
    template_match_coverage = Column(Float)  # % of PDF objects matched
    unmatched_object_count = Column(Integer)
    suggested_new_template = Column(Boolean, default=False)
    
    # Extraction results (for success status)
    extracted_data = Column(Text)  # JSON: field_name -> value mapping
    
    # Pipeline execution tracking
    failed_step_id = Column(Integer, ForeignKey('template_extraction_steps.id'))
    step_execution_log = Column(Text)  # JSON: step-by-step execution details
    
    # Processing timeline
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_duration_ms = Column(Integer)
    
    # Order integration
    order_id = Column(Integer)  # References orders table (assumed to exist)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="eto_runs")
    pdf_file = relationship("PdfFile", back_populates="eto_runs")
    template = relationship("PdfTemplate", back_populates="eto_runs")
    failed_step = relationship("TemplateExtractionStep", foreign_keys=[failed_step_id], overlaps="failed_eto_runs")

class EmailCursor(Base):
    """Track email processing cursors for downtime recovery"""
    __tablename__ = 'email_cursors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(String(255), nullable=False)
    folder_name = Column(String(255), nullable=False)
    
    # Outlook-specific cursor data
    last_processed_message_id = Column(String(255))  # EntryID from Outlook
    last_processed_received_date = Column(DateTime)  # ReceivedTime from last processed email
    last_check_time = Column(DateTime, default=datetime.utcnow)
    
    # Processing statistics
    total_emails_processed = Column(Integer, default=0)
    total_pdfs_found = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate cursors for same email/folder combo
    __table_args__ = (
        UniqueConstraint('email_address', 'folder_name', name='_email_folder_cursor_uc'),
    )

class DatabaseService:
    """Database service for ETO system"""
    
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def create_email_record(self, email_data):
        """Create email record"""
        session = self.get_session()
        try:
            email = Email(**email_data)
            session.add(email)
            session.commit()
            session.refresh(email)
            return email
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating email record: {e}")
            raise
        finally:
            session.close()
    
    def create_pdf_file(self, pdf_data):
        """Create PDF file record"""
        session = self.get_session()
        try:
            pdf_file = PdfFile(**pdf_data)
            session.add(pdf_file)
            session.commit()
            session.refresh(pdf_file)
            return pdf_file
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating PDF file record: {e}")
            raise
        finally:
            session.close()
    
    def create_eto_run(self, run_data):
        """Create ETO processing run"""
        session = self.get_session()
        try:
            eto_run = EtoRun(**run_data)
            session.add(eto_run)
            session.commit()
            session.refresh(eto_run)
            return eto_run
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating ETO run: {e}")
            raise
        finally:
            session.close()
    
    def get_pending_eto_runs(self, limit=10):
        """Get pending processing runs"""
        session = self.get_session()
        try:
            return session.query(EtoRun).filter(
                EtoRun.status == 'pending'
            ).order_by(EtoRun.created_at).limit(limit).all()
        finally:
            session.close()
    
    def update_eto_run_status(self, run_id, status, **kwargs):
        """Update ETO run status and other fields"""
        session = self.get_session()
        try:
            run = session.query(EtoRun).filter(EtoRun.id == run_id).first()
            if run:
                run.status = status
                for key, value in kwargs.items():
                    if hasattr(run, key):
                        setattr(run, key, value)
                session.commit()
                return run
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating ETO run status: {e}")
            raise
        finally:
            session.close()
    
    def find_template_by_signature(self, signature_hash):
        """Find template by signature hash"""
        session = self.get_session()
        try:
            return session.query(PdfTemplate).filter(
                PdfTemplate.signature_hash == signature_hash,
                PdfTemplate.is_active == True
            ).first()
        finally:
            session.close()
    
    def get_or_create_email_cursor(self, email_address, folder_name):
        """Get existing cursor or create new one for email/folder combination"""
        session = self.get_session()
        try:
            cursor = session.query(EmailCursor).filter(
                EmailCursor.email_address == email_address,
                EmailCursor.folder_name == folder_name
            ).first()
            
            if not cursor:
                cursor = EmailCursor(
                    email_address=email_address,
                    folder_name=folder_name
                )
                session.add(cursor)
                session.commit()
                session.refresh(cursor)
                logger.info(f"Created new email cursor for {email_address}/{folder_name}")
            
            return cursor
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error getting/creating email cursor: {e}")
            raise
        finally:
            session.close()
    
    def update_email_cursor(self, email_address, folder_name, message_id, received_date):
        """Update cursor with latest processed email info"""
        session = self.get_session()
        try:
            cursor = session.query(EmailCursor).filter(
                EmailCursor.email_address == email_address,
                EmailCursor.folder_name == folder_name
            ).first()
            
            if cursor:
                old_date = cursor.last_processed_received_date
                cursor.last_processed_message_id = message_id
                cursor.last_processed_received_date = received_date
                cursor.last_check_time = datetime.utcnow()
                cursor.total_emails_processed += 1
                session.commit()
                logger.info(f"Updated cursor for {email_address}/{folder_name}: {old_date} -> {received_date}")
            else:
                logger.warning(f"No cursor found to update for {email_address}/{folder_name}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating email cursor: {e}")
            raise
        finally:
            session.close()
    
    def increment_cursor_pdf_count(self, email_address, folder_name):
        """Increment PDF count for cursor"""
        session = self.get_session()
        try:
            cursor = session.query(EmailCursor).filter(
                EmailCursor.email_address == email_address,
                EmailCursor.folder_name == folder_name
            ).first()
            
            if cursor:
                cursor.total_pdfs_found += 1
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error incrementing cursor PDF count: {e}")
            raise
        finally:
            session.close()

# Global database service instance
db_service = None

def init_database(connection_string):
    """Initialize database connection"""
    global db_service
    try:
        # Try different SQL Server connection formats
        connection_urls_to_try = [
            connection_string,  # Original from .env
            connection_string.replace("ODBC+Driver+17+for+SQL+Server", "SQL+Server"),  # SQL Server driver
            connection_string.replace("driver=ODBC+Driver+17+for+SQL+Server", "driver=SQL+Server"),  # Alternative
        ]
        
        last_error = None
        for url in connection_urls_to_try:
            try:
                logger.info(f"Trying database connection: {url.split('://')[0]}://***")
                
                # First try to connect to the database
                db_service = DatabaseService(url)
                db_service.create_tables()
                logger.info("Database initialized successfully")
                return db_service
                
            except Exception as e:
                # If database doesn't exist, try to create it
                if "Cannot open database" in str(e) or "database" in str(e).lower():
                    logger.info("Database doesn't exist, attempting to create it...")
                    try:
                        # Try to create the database
                        _create_database_if_not_exists(url)
                        # Retry connection after creating database
                        db_service = DatabaseService(url)
                        db_service.create_tables()
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
        logger.error(f"Failed to initialize database: {e}")
        # Print available drivers for debugging
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            logger.info(f"Available ODBC drivers: {drivers}")
        except:
            pass
        raise

def _create_database_if_not_exists(connection_url):
    """Try to create database if it doesn't exist"""
    try:
        from urllib.parse import urlparse
        from sqlalchemy import create_engine, text
        
        # Parse the connection URL to get database info
        parsed = urlparse(connection_url)
        
        # Create connection to master database to create new database
        master_url = connection_url.replace(f"/{parsed.path.lstrip('/')}", "/master")
        
        logger.info("Connecting to master database to create ETO database...")
        master_engine = create_engine(master_url)
        
        # Get database name from original URL
        db_name = parsed.path.lstrip('/')
        
        with master_engine.connect() as conn:
            # Use autocommit mode for CREATE DATABASE
            conn.execute(text("COMMIT"))  # End any existing transaction
            conn.execute(text(f"CREATE DATABASE [{db_name}]"))
            logger.info(f"Database '{db_name}' created successfully")
            
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise

def get_db_service():
    """Get the global database service instance"""
    if db_service is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return db_service