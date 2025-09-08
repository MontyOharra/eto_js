"""
Unified ETO Database Service
Combines email/template processing with transformation pipelines
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, BigInteger, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

# ============================================================================
# EMAIL AND PDF MODELS (from ETO server)
# ============================================================================

class Email(Base):
    """Email records from Outlook integration"""
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
    """PDF file storage and metadata"""
    __tablename__ = 'pdf_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger)
    sha256_hash = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(100), default='application/pdf')
    page_count = Column(Integer)
    object_count = Column(Integer)
    objects_json = Column(Text)  # PDF objects for template matching
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="pdf_files")
    eto_runs = relationship("EtoRun", back_populates="pdf_file")

class EmailCursor(Base):
    """Track email processing cursors for downtime recovery"""
    __tablename__ = 'email_cursors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(String(255), nullable=False)
    folder_name = Column(String(255), nullable=False)
    
    # Cursor data
    last_processed_message_id = Column(String(255))
    last_processed_received_date = Column(DateTime)
    last_check_time = Column(DateTime, default=datetime.utcnow)
    
    # Statistics
    total_emails_processed = Column(Integer, default=0)
    total_pdfs_found = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('email_address', 'folder_name', name='_email_folder_cursor_uc'),
    )

# ============================================================================
# TRANSFORMATION PIPELINE MODELS (from pipeline server)
# ============================================================================

class BaseModule(Base):
    """Base transformation modules defined by developers"""
    __tablename__ = 'base_modules'
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50), default='1.0.0')
    
    # Node configuration (JSON strings)
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

class Pipeline(Base):
    """Data transformation pipelines"""
    __tablename__ = 'pipelines'
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user = Column(String(255), nullable=False)
    
    # Pipeline definition (module references and connections)
    pipeline_definition = Column(Text, nullable=False)
    
    # Execution metadata
    execution_metadata = Column(Text)
    
    # Status and metadata
    status = Column(String(50), default='draft')  # draft, active, archived
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    templates = relationship("PdfTemplate", back_populates="pipeline")

    __table_args__ = (
        Index('idx_pipelines_name', 'name'),
        Index('idx_pipelines_user', 'created_by_user'), 
        Index('idx_pipelines_status', 'status'),
        Index('idx_pipelines_active', 'is_active'),
    )

# ============================================================================
# ENHANCED TEMPLATE SYSTEM (combines both systems)
# ============================================================================

class PdfTemplate(Base):
    """PDF templates with integrated transformation pipelines"""
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
    
    # NEW: Pipeline integration
    pipeline_id = Column(String(100), ForeignKey('pipelines.id'), nullable=True)
    
    # Template metadata  
    is_complete = Column(Boolean, default=False)
    coverage_threshold = Column(Float, default=0.6)
    
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
    pipeline = relationship("Pipeline", back_populates="templates")
    eto_runs = relationship("EtoRun", back_populates="template")

# ============================================================================
# ETO PROCESSING MODELS (enhanced for pipeline integration)
# ============================================================================

class EtoRun(Base):
    """ETO processing runs with pipeline-based transformation"""
    __tablename__ = 'eto_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    pdf_file_id = Column(Integer, ForeignKey('pdf_files.id'), nullable=False, index=True)
    
    # Overall processing status
    status = Column(String(50), nullable=False, index=True)  # 'not_started', 'processing', 'success', 'failure', 'needs_template', 'skipped'
    
    # Current processing step
    processing_step = Column(String(50))  # 'template_matching', 'extracting_data', 'transforming_data'
    
    # Error tracking
    error_type = Column(String(50))
    error_message = Column(Text)
    error_details = Column(Text)  # JSON: detailed error info
    
    # Template matching results
    matched_template_id = Column(Integer, ForeignKey('pdf_templates.id'), nullable=True)
    template_version = Column(Integer)
    template_match_coverage = Column(Float)
    unmatched_object_count = Column(Integer)
    suggested_new_template = Column(Boolean, default=False)
    
    # Data extraction results
    extracted_data = Column(Text)  # JSON: base extracted field values from bounding boxes
    
    # NEW: Pipeline-based transformation
    pipeline_execution_data = Column(Text)  # JSON: step-by-step pipeline execution log
    
    # Final transformed data
    target_data = Column(Text)  # JSON: final transformed data ready for order creation
    
    # Processing timeline
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_duration_ms = Column(Integer)
    
    # Order integration
    order_id = Column(Integer)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="eto_runs")
    pdf_file = relationship("PdfFile", back_populates="eto_runs")
    template = relationship("PdfTemplate", back_populates="eto_runs")

# ============================================================================
# DATABASE SERVICE CLASS
# ============================================================================

class UnifiedDatabaseService:
    """Unified database service for ETO system"""
    
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Unified database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()

# Global database service instance
_unified_db_service = None

def init_unified_database(connection_string):
    """Initialize unified database connection"""
    global _unified_db_service
    try:
        logger.info("Initializing unified ETO database...")
        _unified_db_service = UnifiedDatabaseService(connection_string)
        _unified_db_service.create_tables()
        logger.info("Unified database initialized successfully")
        return _unified_db_service
    except Exception as e:
        logger.error(f"Failed to initialize unified database: {e}")
        raise

def get_unified_db_service():
    """Get the global unified database service instance"""
    if _unified_db_service is None:
        raise RuntimeError("Unified database not initialized. Call init_unified_database() first.")
    return _unified_db_service