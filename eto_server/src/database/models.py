"""
ETO Database Models
Unified database models combining email processing and transformation pipelines
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

# SQLAlchemy Base
Base = declarative_base()


# =============================================================================
# EMAIL PROCESSING MODELS (from server/)
# =============================================================================

class Email(Base):
    """Email records from Outlook monitoring"""
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
    """PDF files extracted from emails"""
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
    object_count = Column(Integer)  # Number of PDF objects extracted
    objects_json = Column(Text)  # PDF objects for template matching
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="pdf_files")
    eto_runs = relationship("EtoRun", back_populates="pdf_file")


class PdfTemplate(Base):
    """PDF templates for pattern matching and field extraction"""
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
    """Extraction rules for templates (multi-step data transformation)"""
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
    """Individual steps within extraction rules"""
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
    """ETO processing runs - tracks PDF processing workflow"""
    __tablename__ = 'eto_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    pdf_file_id = Column(Integer, ForeignKey('pdf_files.id'), nullable=False, index=True)
    
    # Overall processing status
    status = Column(String(50), nullable=False, index=True)  # 'not_started', 'processing', 'success', 'failure', 'needs_template', 'skipped'
    
    # Current processing step (only populated when status='processing')
    processing_step = Column(String(50))  # 'template_matching', 'extracting_data', 'transforming_data'
    
    # Error tracking (for status='failure')
    error_type = Column(String(50))  # 'template_matching_error', 'data_extraction_error', 'transformation_error'
    error_message = Column(Text)
    error_details = Column(Text)  # JSON: detailed error info including which step failed
    
    # Template matching results
    matched_template_id = Column(Integer, ForeignKey('pdf_templates.id'), nullable=True)
    template_version = Column(Integer)  # Which version was used
    template_match_coverage = Column(Float)  # % of PDF objects matched
    unmatched_object_count = Column(Integer)
    suggested_new_template = Column(Boolean, default=False)
    
    # Data extraction results (populated during 'extracting_data' step)  
    extracted_data = Column(Text)  # JSON: base extracted field values from bounding boxes
    
    # Data transformation audit trail (populated during 'transforming_data' step)
    transformation_audit = Column(Text)  # JSON: step-by-step transformation inputs/outputs with rule IDs
    
    # Final transformed data (populated after successful transformation)
    target_data = Column(Text)  # JSON: final transformed data ready for order creation
    
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


# =============================================================================
# TRANSFORMATION PIPELINE MODELS (from transformation_pipeline_server/)
# =============================================================================

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