"""
Transformation Pipeline Database Models
Based on the transformation pipeline design document
"""
from typing import Optional, List
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
    config: Mapped['EmailConfigModel'] = relationship(back_populates="emails")
    pdf_files: Mapped[List['PdfFileModel']] =  relationship(back_populates="email") 
    
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
    emails: Mapped[List['EmailModel']] = relationship(back_populates="config")

    __table_args__ = (
        Index('idx_email_config_active', 'is_active'),
        Index('idx_email_config_running', 'is_running'),
    )


class EtoRunModel(BaseModel):
    """High-level ETO run; per-stage details live in stage tables"""
    __tablename__ = 'eto_runs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey('pdf_files.id'), nullable=False, index=True)

    status: Mapped[Optional[str]] = mapped_column(String(50), default='not_started')  # ETO_STATUS
    processing_step: Mapped[Optional[str]] = mapped_column(String(50))               # ETO_STAGE

    error_type: Mapped[Optional[str]] = mapped_column(String(50))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    order_id: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())

    # Relationships
    pdf_file: Mapped['PdfFileModel'] = relationship(back_populates='eto_runs')
    template_matching_runs: Mapped[List['EtoRunTemplateMatchingModel']] = relationship(
        back_populates='run', cascade='all, delete-orphan'
    )
    extraction_runs: Mapped[List['EtoRunExtractionModel']] = relationship(
        back_populates='run', cascade='all, delete-orphan'
    )
    pipeline_execution_runs: Mapped[List['EtoRunPipelineExecutionModel']] = relationship(
        back_populates='run', cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_eto_runs_status', 'status'),
        Index('idx_eto_runs_processing_step', 'processing_step'),
    )


class EtoRunExtractionModel(BaseModel):
    """Per-run record for the Data Extraction stage"""
    __tablename__ = 'eto_run_extractions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey('eto_runs.id'), nullable=False, index=True)

    status: Mapped[Optional[str]] = mapped_column(String(50), default='processing')  # ETO_STATUS
    extracted_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    # Relationships
    run: Mapped['EtoRunModel'] = relationship(back_populates='extraction_runs')

    __table_args__ = (
        Index('idx_eto_extraction_runs_status', 'status'),
    )


class EtoRunPipelineExecutionModel(BaseModel):
    """Per-run record for the Pipeline Execution stage (transform + action)"""
    __tablename__ = 'eto_run_pipeline_executions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey('eto_runs.id'), nullable=False, index=True)

    status: Mapped[Optional[str]] = mapped_column(String(50), default='processing')  # ETO_STATUS
    executed_actions: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    # Relationships
    run: Mapped['EtoRunModel'] = relationship(back_populates='pipeline_execution_runs')
    steps: Mapped[List['EtoRunPipelineExecutionStepModel']] = relationship(
        back_populates='run', cascade='all, delete-orphan'
    )
    
    
class EtoRunPipelineExecutionStepModel(BaseModel):
    """Recorded execution steps for a single ETO pipeline execution run"""
    __tablename__ = 'eto_run_pipeline_execution_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey('eto_pipeline_execution_runs.id'), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[Optional[str]] = mapped_column(Text)    # JSON
    outputs: Mapped[Optional[str]] = mapped_column(Text)   # JSON
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    run: Mapped['EtoRunPipelineExecutionModel'] = relationship(back_populates='steps')

    __table_args__ = (
        Index('idx_execution_steps_module', 'module_instance_id'),
    )


class EtoRunTemplateMatchingModel(BaseModel):
    """Per-run record for the Template Matching stage"""
    __tablename__ = 'eto_run_template_matchings'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey('eto_runs.id'), nullable=False, index=True)

    status: Mapped[Optional[str]] = mapped_column(String(50), default='processing')  # ETO_STATUS
    matched_template_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('pdf_template_versions.id'), nullable=True, index=True
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    # Relationships
    run: Mapped['EtoRunModel'] = relationship(back_populates='template_matching_runs')
    matched_template_version: Mapped[Optional['PdfTemplateVersionModel']] = relationship(
        back_populates='template_matching_runs'
    )

    __table_args__ = (
        Index('idx_eto_template_matching_runs_status', 'status'),
    )


class ModuleCatalogModel(BaseModel):
    """Catalog of available modules (metadata)"""
    __tablename__ = 'module_catalog'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # module id (name)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(50), default='#3B82F6')
    category: Mapped[str] = mapped_column(String(100), default='Processing')
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    meta: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    config_schema: Mapped[str] = mapped_column(Text)
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())

    # (Optional) relationship to steps that reference this module by id
    steps: Mapped[List['PipelineDefinitionStepModel']] = relationship(
        back_populates='module', cascade='all, delete-orphan', passive_deletes=True
    )

    __table_args__ = (
        Index('idx_module_catalog_name', 'name'),
        Index('idx_module_catalog_kind', 'module_kind'),
        Index('idx_module_catalog_active', 'is_active'),
        Index('idx_module_catalog_category', 'category'),
        Index('uq_module_catalog_id_version', 'id', 'version'),
    )


class PdfFileModel(BaseModel):
    """PDF files extracted from emails"""
    __tablename__ = 'pdf_files'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey('emails.id'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    objects_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())

    # Relationships
    email: Mapped['EmailModel'] = relationship(back_populates='pdf_files')
    eto_runs: Mapped[List['EtoRunModel']] = relationship(back_populates='pdf_file', cascade='all, delete-orphan')
    source_for_templates: Mapped[List['PdfTemplateModel']] = relationship(
        back_populates='source_pdf', cascade='all, delete-orphan', foreign_keys='PdfTemplateModel.source_pdf_id'
    )


class PdfTemplateModel(BaseModel):
    """PDF templates (logical family)"""
    __tablename__ = 'pdf_templates'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_pdf_id: Mapped[int] = mapped_column(ForeignKey('pdf_files.id'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default='active')
    current_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey('pdf_template_versions.id'), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate())

    # Relationships
    source_pdf: Mapped['PdfFileModel'] = relationship(back_populates='source_for_templates', foreign_keys=[source_pdf_id])
    versions: Mapped[List['PdfTemplateVersionModel']] = relationship(
        back_populates='pdf_template', cascade='all, delete-orphan', foreign_keys='PdfTemplateVersionModel.pdf_template_id'
    )
    current_version: Mapped[Optional['PdfTemplateVersionModel']] = relationship(
        foreign_keys=[current_version_id]
    )


class PdfTemplateVersionModel(BaseModel):
    """Concrete version of a PDF template (signature + fields + linked pipeline)"""
    __tablename__ = 'pdf_template_versions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_template_id: Mapped[int] = mapped_column(ForeignKey('pdf_templates.id'), nullable=False, index=True)
    version_num: Mapped[int] = mapped_column(Integer, default=1)
    signature_objects: Mapped[str] = mapped_column(Text)
    extraction_fields: Mapped[str] = mapped_column(Text)
    pipeline_definition_id: Mapped[int] = mapped_column(ForeignKey('pipeline_definitions.id'), nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())

    # Relationships
    pdf_template: Mapped['PdfTemplateModel'] = relationship(back_populates='versions', foreign_keys=[pdf_template_id])
    pipeline_definition: Mapped['PipelineDefinitionModel'] = relationship(back_populates='template_versions')
    template_matching_runs: Mapped[List['EtoRunTemplateMatchingModel']] = relationship(
        back_populates='matched_template_version'
    )


class PipelineCompiledPlanModel(BaseModel):
    """Compiled plan identity (dedup via checksum)"""
    __tablename__ = 'pipeline_compiled_plans'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    compiled_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    # Relationships
    definitions: Mapped[List['PipelineDefinitionModel']] = relationship(
        back_populates='compiled_plan', cascade='all, delete-orphan'
    )
    steps: Mapped[List['PipelineDefinitionStepModel']] = relationship(
        back_populates='compiled_plan', cascade='all, delete-orphan'
    )


class PipelineDefinitionModel(BaseModel):
    """Canonical pipeline JSON (source of truth)"""
    __tablename__ = 'pipeline_definitions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_state: Mapped[str] = mapped_column(Text, nullable=False)
    visual_state: Mapped[str] = mapped_column(Text, nullable=False)

    compiled_plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('pipeline_compiled_plans.id'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=func.getutcdate())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    compiled_plan: Mapped[Optional['PipelineCompiledPlanModel']] = relationship(back_populates='definitions')
    template_versions: Mapped[List['PdfTemplateVersionModel']] = relationship(
        back_populates='pipeline_definition'
    )

    __table_args__ = (
        Index('idx_pipeline_definitions_active', 'is_active'),
    )


class PipelineDefinitionStepModel(BaseModel):
    """Compiled steps that belong to a compiled plan"""
    __tablename__ = 'pipeline_definition_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_compiled_plan_id: Mapped[int] = mapped_column(
        ForeignKey('pipeline_compiled_plans.id'), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module_ref: Mapped[str] = mapped_column(ForeignKey('module_catalog.id', ondelete='CASCADE'), nullable=False, index=True)

    module_config: Mapped[str] = mapped_column(Text, nullable=False)            # JSON
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)     # JSON
    node_metadata: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {"inputs": [InstanceNodePin], "outputs": [InstanceNodePin]}
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    compiled_plan: Mapped['PipelineCompiledPlanModel'] = relationship(back_populates='steps')
    module: Mapped['ModuleCatalogModel'] = relationship(back_populates='steps')

    __table_args__ = (
        Index('idx_pipeline_compiled_plan_id', 'pipeline_compiled_plan_id'),
        Index('idx_pipeline_step_number', 'step_number', 'id')
    )