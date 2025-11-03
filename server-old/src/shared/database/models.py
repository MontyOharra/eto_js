from __future__ import annotations

from enum import StrEnum
from typing import Optional, List

from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    BigInteger,
    Boolean,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import Enum as SAEnum


class BaseModel(DeclarativeBase):
    pass

class EtoStepStatus(StrEnum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"


class EtoRunStatus(StrEnum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    NEEDS_TEMPLATE = "needs_template"
    SKIPPED = "skipped"


class EtoRunProcessingStep(StrEnum):
    TEMPLATE_MATCHING = "template_matching"
    DATA_EXTRACTION = "data_extraction"
    DATA_TRANSFORMATION = "data_transformation"


# =========================
# email_configs
# =========================

class EmailConfigModel(BaseModel):
    __tablename__ = "email_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_rules: Mapped[Optional[str]] = mapped_column(Text)

    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=5)
    max_backlog_hours: Mapped[int] = mapped_column(Integer, default=24)
    error_retry_attempts: Mapped[int] = mapped_column(Integer, default=3)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_check_time: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    emails: Mapped[List["EmailModel"]] = relationship(back_populates="config")

    __table_args__ = (
        Index("idx_email_config_active", "is_active"),
        Index("idx_email_config_running", "is_running"),
    )


# =========================
# emails
# =========================

class EmailModel(BaseModel):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    config_id: Mapped[int] = mapped_column(ForeignKey("email_configs.id"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    sender_email: Mapped[Optional[str]] = mapped_column(String(255))
    sender_name: Mapped[Optional[str]] = mapped_column(String(255))
    received_date: Mapped[Optional[datetime]] = mapped_column(DATETIME2, index=True)
    folder_name: Mapped[Optional[str]] = mapped_column(String(100))

    has_pdf_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    pdf_count: Mapped[int] = mapped_column(Integer, default=0)

    processed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    config: Mapped["EmailConfigModel"] = relationship(back_populates="emails")
    pdf_files: Mapped[List["PdfFileModel"]] = relationship(back_populates="email")

    __table_args__ = (
        UniqueConstraint("config_id", "message_id", name="uix_config_message"),
        Index("ix_email_config_id", "config_id"),
        Index("ix_email_received_date", "received_date"),
    )


# =========================
# pdf_files
# =========================

class PdfFileModel(BaseModel):
    __tablename__ = "pdf_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    email_id: Mapped[Optional[int]] = mapped_column(ForeignKey("emails.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)

    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)

    objects_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    email: Mapped[Optional["EmailModel"]] = relationship(back_populates="pdf_files")
    eto_runs: Mapped[List["EtoRunModel"]] = relationship(back_populates="pdf_file", cascade="all, delete-orphan")
    source_for_templates: Mapped[List["PdfTemplateModel"]] = relationship(
        back_populates="source_pdf", cascade="all, delete-orphan", foreign_keys="PdfTemplateModel.source_pdf_id"
    )


# =========================
# pdf_templates
# =========================

class PdfTemplateStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class PdfTemplateModel(BaseModel):
    __tablename__ = "pdf_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_pdf_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    status: Mapped[PdfTemplateStatus] = mapped_column(
        SAEnum(PdfTemplateStatus, native_enum=False, validate_strings=True, name="pdf_template_status"),
        nullable=False,
        default=PdfTemplateStatus.ACTIVE,
    )
    current_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pdf_template_versions.id"))

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    source_pdf: Mapped["PdfFileModel"] = relationship(
        back_populates="source_for_templates", foreign_keys=[source_pdf_id]
    )
    versions: Mapped[List["PdfTemplateVersionModel"]] = relationship(
        back_populates="pdf_template", cascade="all, delete-orphan", foreign_keys="PdfTemplateVersionModel.pdf_template_id"
    )
    current_version: Mapped[Optional["PdfTemplateVersionModel"]] = relationship(foreign_keys=[current_version_id])


class PdfTemplateVersionModel(BaseModel):
    __tablename__ = "pdf_template_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    pdf_template_id: Mapped[int] = mapped_column(ForeignKey("pdf_templates.id"), nullable=False, index=True)
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_objects: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_fields: Mapped[str] = mapped_column(Text, nullable=False)
    pipeline_definition_id: Mapped[int] = mapped_column(ForeignKey("pipeline_definitions.id"), nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pdf_template: Mapped["PdfTemplateModel"] = relationship(back_populates="versions", foreign_keys=[pdf_template_id])
    pipeline_definition: Mapped["PipelineDefinitionModel"] = relationship(back_populates="template_versions")
    template_matching_runs: Mapped[List["EtoRunTemplateMatchingModel"]] = relationship(back_populates="matched_template_version")


# =========================
# module_catalog
# =========================

class ModuleCatalogModel(BaseModel):
    __tablename__ = "module_catalog"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(50), default="#3B82F6")
    category: Mapped[str] = mapped_column(String(100), default="Processing")
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    meta: Mapped[str] = mapped_column(Text, nullable=False)
    config_schema: Mapped[Optional[str]] = mapped_column(Text)
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    steps: Mapped[List["PipelineDefinitionStepModel"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("idx_module_catalog_name", "name"),
        Index("idx_module_catalog_kind", "module_kind"),
        Index("idx_module_catalog_active", "is_active"),
        Index("idx_module_catalog_category", "category"),
        Index("uq_module_catalog_id_version", "id", "version"),
    )


# =========================
# pipeline_compiled_plans
# =========================

class PipelineCompiledPlanModel(BaseModel):
    __tablename__ = "pipeline_compiled_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    compiled_at: Mapped[datetime] = mapped_column(DATETIME2, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    definitions: Mapped[List["PipelineDefinitionModel"]] = relationship(
        back_populates="compiled_plan", cascade="all, delete-orphan"
    )
    steps: Mapped[List["PipelineDefinitionStepModel"]] = relationship(
        back_populates="compiled_plan", cascade="all, delete-orphan"
    )


# =========================
# pipeline_definitions
# =========================

class PipelineDefinitionModel(BaseModel):
    __tablename__ = "pipeline_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_state: Mapped[str] = mapped_column(Text, nullable=False)
    visual_state: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pipeline_compiled_plans.id"), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    compiled_plan: Mapped[Optional["PipelineCompiledPlanModel"]] = relationship(back_populates="definitions")
    template_versions: Mapped[List["PdfTemplateVersionModel"]] = relationship(back_populates="pipeline_definition")


# =========================
# pipeline_definition_steps
# =========================

class PipelineDefinitionStepModel(BaseModel):
    __tablename__ = "pipeline_definition_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_compiled_plan_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_compiled_plans.id"), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module_ref: Mapped[str] = mapped_column(ForeignKey("module_catalog.id", ondelete="CASCADE"), nullable=False, index=True)

    module_config: Mapped[str] = mapped_column(Text, nullable=False)
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)
    node_metadata: Mapped[str] = mapped_column(Text, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    compiled_plan: Mapped["PipelineCompiledPlanModel"] = relationship(back_populates="steps")
    module: Mapped["ModuleCatalogModel"] = relationship(back_populates="steps")

    __table_args__ = (
        Index("idx_pipeline_compiled_plan_id", "pipeline_compiled_plan_id"),
        Index("idx_pipeline_step_number", "step_number", "id"),
    )


# =========================
# eto_runs (parent of stage runs)
# =========================

class EtoRunModel(BaseModel):
    __tablename__ = "eto_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    status: Mapped[EtoRunStatus] = mapped_column(
        SAEnum(EtoRunStatus, native_enum=False, validate_strings=True, name="eto_run_status"),
        nullable=False,
        default=EtoRunStatus.NOT_STARTED,
    )
    processing_step: Mapped[Optional[EtoRunProcessingStep]] = mapped_column(
        SAEnum(EtoRunProcessingStep, native_enum=False, validate_strings=True, name="eto_run_processing_step"),
        nullable=True,
    )

    error_type: Mapped[Optional[str]] = mapped_column(String(50))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pdf_file: Mapped["PdfFileModel"] = relationship(back_populates="eto_runs")
    template_matching_runs: Mapped[List["EtoRunTemplateMatchingModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    extraction_runs: Mapped[List["EtoRunExtractionModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    pipeline_execution_runs: Mapped[List["EtoRunPipelineExecutionModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eto_runs_status", "status"),
        Index("idx_eto_runs_processing_step", "processing_step"),
        Index("idx_eto_runs_pdf_file_id", "pdf_file_id"),
    )


# =========================
# Stage: Template Matching
# =========================

class EtoRunTemplateMatchingModel(BaseModel):
    __tablename__ = "eto_run_template_matchings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey("eto_runs.id"), nullable=False, index=True)

    status: Mapped[EtoStepStatus] = mapped_column(
        SAEnum(EtoStepStatus, native_enum=False, validate_strings=True, name="eto_step_status_tm"),
        nullable=False,
        default=EtoStepStatus.PROCESSING,
    )

    matched_template_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pdf_template_versions.id"), index=True
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    run: Mapped["EtoRunModel"] = relationship(back_populates="template_matching_runs")
    matched_template_version: Mapped[Optional["PdfTemplateVersionModel"]] = relationship(
        back_populates="template_matching_runs"
    )

    __table_args__ = (
        Index("idx_eto_template_matching_runs_status", "status"),
    )


# =========================
# Stage: Data Extraction
# =========================

class EtoRunExtractionModel(BaseModel):
    __tablename__ = "eto_run_extractions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey("eto_runs.id"), nullable=False, index=True)

    status: Mapped[EtoStepStatus] = mapped_column(
        SAEnum(EtoStepStatus, native_enum=False, validate_strings=True, name="eto_step_status_ex"),
        nullable=False,
        default=EtoStepStatus.PROCESSING,
    )
    extracted_data: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    run: Mapped["EtoRunModel"] = relationship(back_populates="extraction_runs")

    __table_args__ = (
        Index("idx_eto_extraction_runs_status", "status"),
    )


# =========================
# Stage: Pipeline Execution (run)
# =========================

class EtoRunPipelineExecutionModel(BaseModel):
    __tablename__ = "eto_run_pipeline_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey("eto_runs.id"), nullable=False, index=True)

    status: Mapped[EtoStepStatus] = mapped_column(
        SAEnum(EtoStepStatus, native_enum=False, validate_strings=True, name="eto_step_status_px"),
        nullable=False,
        default=EtoStepStatus.PROCESSING,
    )

    executed_actions: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    run: Mapped["EtoRunModel"] = relationship(back_populates="pipeline_execution_runs")
    steps: Mapped[List["EtoRunPipelineExecutionStepModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


# =========================
# Stage: Pipeline Execution (steps)
# =========================

class EtoRunPipelineExecutionStepModel(BaseModel):
    __tablename__ = "eto_run_pipeline_execution_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("eto_run_pipeline_executions.id"), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[Optional[str]] = mapped_column(Text)
    outputs: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2, server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    run: Mapped["EtoRunPipelineExecutionModel"] = relationship(back_populates="steps")

    __table_args__ = (
        Index("idx_execution_steps_module", "module_instance_id"),
    )
