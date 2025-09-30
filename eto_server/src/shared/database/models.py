"""
ETO Database Models
Unified database models combining email processing and transformation pipelines
"""
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint, BigInteger
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
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
    failed_pipeline_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey('transformation_pipeline_steps.id'), default=None)
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
    failed_pipeline_step = relationship("TransformationPipelineStepModel", foreign_keys=[failed_pipeline_step_id])

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