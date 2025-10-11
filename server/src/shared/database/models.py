"""
Transformation Pipeline Database Models
Based on the transformation pipeline design document
"""
from typing import Optional
from sqlalchemy import String, Integer, DateTime, BigInteger, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from shared.utils import DateTimeUtils

# SQLAlchemy 2.0 Base
class BaseModel(DeclarativeBase):
    pass


class EmailModel(BaseModel):
    """Email records from Outlook monitoring"""
    __tablename__ = 'emails'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(ForeignKey('email_configs.id'), nullable=False)
    message_id: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    sender_email: Mapped[Optional[str]] = mapped_column(String(255))
    sender_name: Mapped[Optional[str]] = mapped_column(String(255))
    received_date: Mapped[datetime] = mapped_column(DATETIME2, index=True)
    folder_name: Mapped[Optional[str]] = mapped_column(String(100))
    has_pdf_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    pdf_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    
    # Relationships
    config = relationship("EmailConfigModel", back_populates="emails")
    pdf_files = relationship("PdfFileModel", back_populates="email")
    
    __table_args__ = (
        UniqueConstraint('config_id', 'message_id', name='uix_config_message'),
        Index('ix_email_config_id', 'config_id'),
        Index('ix_email_received_date', 'received_date'),
    )


class EmailConfigModel(BaseModel):
    """Email ingestion configuration settings"""
    __tablename__ = 'email_configs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Connection settings
    email_address: Mapped[str] = mapped_column(String(255))  # Required specific email address
    folder_name: Mapped[str] = mapped_column(String(255), default='Inbox')

    # Filter configuration (JSON)
    filter_rules: Mapped[str] = mapped_column(Text)

    # Monitoring settings
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=5)
    max_backlog_hours: Mapped[int] = mapped_column(Integer, default=24)
    error_retry_attempts: Mapped[int] = mapped_column(Integer, default=3)

    # Status and control
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    # Statistics
    emails_processed: Mapped[int] = mapped_column(Integer, default=0)
    pdfs_found: Mapped[int] = mapped_column(Integer, default=0)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    
    # Progress tracking fields (replacing cursor)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2, nullable=True)
    last_check_time: Mapped[Optional[datetime]] = mapped_column(DATETIME2, nullable=True)
    total_emails_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_pdfs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    emails = relationship("EmailModel", back_populates="config")

    __table_args__ = (
        Index('idx_email_config_active', 'is_active'),
        Index('idx_email_config_running', 'is_running'),
    )


class EtoRunModel(BaseModel):
    """ETO processing runs - tracks PDF processing workflow"""
    __tablename__ = 'eto_runs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey('pdf_files.id'), index=True)

    # Overall processing status
    status: Mapped[str] = mapped_column(String(50), index=True, default="not_started")  # 'not_started', 'processing', 'success', 'failure', 'needs_template', 'skipped'

    # Current processing step (only populated when status='processing')
    processing_step: Mapped[Optional[str]] = mapped_column(String(50), default=None)  # 'template_matching', 'extracting_data', 'transforming_data'

    # Error tracking (for status='failure')
    error_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)  # 'template_matching_error', 'data_extraction_error', 'transformation_error'
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    error_details: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: detailed error info including which step failed

    # Template matching results
    matched_template_id: Mapped[Optional[int]] = mapped_column(ForeignKey('pdf_templates.id'), default=None)
    matched_template_version: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # Which version was used

    # Data extraction results (populated during 'extracting_data' step)
    extracted_data: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: base extracted field values from bounding boxes

    # Data transformation audit trail (populated during 'transforming_data' step)
    transformation_audit: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: step-by-step transformation inputs/outputs with rule IDs

    # Final transformed data (populated after successful transformation)
    target_data: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: final transformed data ready for order creation

    # Pipeline execution tracking
    step_execution_log: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: step-by-step execution details

    # Processing timeline
    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2, default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2, default=None)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    # Order integration
    order_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # References orders table (assumed to exist)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())
    
    # Relationships
    pdf_file = relationship("PdfFileModel", back_populates="eto_runs")
    template = relationship("PdfTemplateModel", back_populates="eto_runs")


class ModuleCatalogModel(BaseModel):
    """
    Module catalog - populated by dev "sync" for builder + validator
    Stores module metadata for discovery and validation
    """
    __tablename__ = 'module_catalog'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # module name
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(50), default='#3B82F6')
    category: Mapped[str] = mapped_column(String(100), default='Processing')

    # Module type and behavior
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)

    # Dynamic side rules and configuration schemas (JSON)
    meta: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: ModuleMeta with dynamic side rules
    config_schema: Mapped[str] = mapped_column(Text)  # JSON: Pydantic JSON Schema
    
    # Handler information
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "python.module.path:ClassName"

    # Status and audit
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('id', 'version', name='uq_module_catalog_id_version'),
        Index('idx_module_catalog_name', 'name'),
        Index('idx_module_catalog_kind', 'module_kind'),
        Index('idx_module_catalog_active', 'is_active'),
        Index('idx_module_catalog_category', 'category'),
    )


class OrderModel(BaseModel):
    """
    Orders - populated by action module
    Stores order data for external database
    """
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mawb: Mapped[str] = mapped_column(String(100), nullable=False)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False)
    pu_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PdfFileModel(BaseModel):
    """PDF files extracted from emails"""
    __tablename__ = 'pdf_files'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id'), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    relative_path: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    objects_json: Mapped[Optional[str]] = mapped_column(Text)  # PDF objects for template matching
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())
    
    # Relationships
    email = relationship("EmailModel", back_populates="pdf_files")
    eto_runs = relationship("EtoRunModel", back_populates="pdf_file")


class PdfTemplateModel(BaseModel):
    """PDF templates for pattern matching and field extraction"""
    __tablename__ = 'pdf_templates'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_pdf_id: Mapped[int] = mapped_column(ForeignKey('pdf_files.id'), index=True)
    status: Mapped[str] = mapped_column(String(50), default='active')
    current_version_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('pdf_template_versions.id'), default=None)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())

    # Relationships
    eto_runs = relationship("EtoRunModel", back_populates="template")
    pdf_template_versions = relationship("PdfTemplateVersionModel", back_populates="pdf_template", foreign_keys="PdfTemplateVersionModel.pdf_template_id")


class PdfTemplateVersionModel(BaseModel):
    """PDF template versions"""
    __tablename__ = 'pdf_template_versions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_template_id: Mapped[int] = mapped_column(ForeignKey('pdf_templates.id'), index=True)
    version_num: Mapped[int] = mapped_column(Integer, default=1)
    signature_objects: Mapped[str] = mapped_column(Text)
    extraction_fields: Mapped[str] = mapped_column(Text)
    usage_count: Mapped[int] = mapped_column(default=0)
    last_used_at: Mapped[datetime] = mapped_column(DATETIME2, default=DateTimeUtils.utc_now)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())

    # Relationships
    pdf_template = relationship("PdfTemplateModel", back_populates="pdf_template_versions", foreign_keys=[pdf_template_id])


class PipelineDefinitionModel(BaseModel):
    """
    Pipeline definitions - canonical pipeline JSON storage
    Stores the source of truth for pipeline configuration with checksums
    Pipelines are immutable once created (no updates allowed)
    """
    __tablename__ = 'pipeline_definitions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Canonical pipeline JSON (modules, pins, connections, configs) - always required
    pipeline_state: Mapped[str] = mapped_column(Text, nullable=False)
    visual_state: Mapped[str] = mapped_column(Text, nullable=False)

    # Checksum for compiled plan integrity
    plan_checksum: Mapped[Optional[str]] = mapped_column(String(64))
    compiled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Audit fields (no updated_at since pipelines are immutable)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index('idx_pipeline_definitions_name', 'name'),
        Index('idx_pipeline_definitions_checksum', 'plan_checksum'),
        Index('idx_pipeline_definitions_active', 'is_active'),
    )


class PipelineDefinitionStepModel(BaseModel):
    """
    Pipeline steps - compiled cache for execution
    Stores compiled execution steps shared across pipelines via checksum
    Steps are grouped by plan_checksum, not by pipeline_id
    Multiple pipelines with identical structure share the same compiled steps
    """
    __tablename__ = 'pipeline_definition_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Module instance information
    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module_ref: Mapped[str] = mapped_column(String(100), nullable=False)  # "name:version"
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "transform"|"action"|"logic"

    # Validated configuration and mappings
    module_config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {downstream_node_id: upstream_node_id}

    # Node metadata and execution order
    node_metadata: Mapped[str] = mapped_column(Text)  # JSON: {"inputs": [InstanceNodePin], "outputs": [InstanceNodePin]}
    step_number: Mapped[int] = mapped_column(Integer)
    

    __table_args__ = (
        Index('idx_pipeline_steps_checksum', 'plan_checksum', 'step_number', 'id'),
        Index('idx_pipeline_steps_module_ref', 'module_ref'),
        Index('idx_pipeline_steps_kind', 'module_kind'),
    )


class PipelineExecutionRunModel(BaseModel):
    """
    Execution runs - track pipeline execution history
    Records each run of a pipeline with its entry values and status
    """
    __tablename__ = 'pipeline_execution_runs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_definition_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    entry_values: Mapped[str] = mapped_column(Text, nullable=False)  # JSON

    # Relationship to execution steps
    steps = relationship("PipelineExecutionStepModel", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_execution_runs_pipeline', 'pipeline_definition_id'),
        Index('idx_execution_runs_status', 'status'),
    )


class PipelineExecutionStepModel(BaseModel):
    """
    Execution steps - track individual module executions within a run
    Records inputs, outputs, timing, and errors for each module
    """
    __tablename__ = 'pipeline_execution_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_execution_runs.id"), nullable=False)
    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[str] = mapped_column(Text)  # JSON - serialized inputs
    outputs: Mapped[str] = mapped_column(Text)  # JSON - serialized outputs
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship to execution run
    run = relationship("PipelineExecutionRunModel", back_populates="steps")

    __table_args__ = (
        Index('idx_execution_steps_run', 'run_id'),
        Index('idx_execution_steps_module', 'module_instance_id'),
    )