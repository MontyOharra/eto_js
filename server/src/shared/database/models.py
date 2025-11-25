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
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import Enum as SAEnum


class BaseModel(DeclarativeBase):
    pass


# =========================
# ENUMS for new ETO design
# =========================

# Parent orchestration status
ETO_MASTER_STATUS = SAEnum(
    'not_started', 'processing', 'success', 'failure',
    name='eto_master_status',
    native_enum=False,
    validate_strings=True
)

# Parent processing step
ETO_RUN_PROCESSING_STEP = SAEnum(
    'template_matching', 'sub_runs',
    name='eto_run_processing_step',
    native_enum=False,
    validate_strings=True
)

# Sub-run status (business logic level)
ETO_RUN_STATUS = SAEnum(
    'not_started', 'matched', 'processing', 'success', 'failure', 'needs_template', 'skipped',
    name='eto_run_status',
    native_enum=False,
    validate_strings=True
)

# Stage-level status (extraction, pipeline execution)
ETO_STEP_STATUS = SAEnum(
    'processing', 'success', 'failure',
    name='eto_step_status',
    native_enum=False,
    validate_strings=True
)


# =========================
# email_configs
# =========================

class EmailConfigModel(BaseModel):
    __tablename__ = "email_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    provider_type: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_settings: Mapped[str] = mapped_column(Text, nullable=False)
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_rules: Mapped[Optional[str]] = mapped_column(Text)

    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=5)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_check_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    emails: Mapped[List["EmailModel"]] = relationship(back_populates="config")

    __table_args__ = (
        Index("idx_email_config_active", "is_active"),
    )


# =========================
# emails
# =========================

class EmailModel(BaseModel):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    config_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("email_configs.id"), nullable=True)
    message_id: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    sender_email: Mapped[Optional[str]] = mapped_column(String(255))
    sender_name: Mapped[Optional[str]] = mapped_column(String(255))
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    folder_name: Mapped[Optional[str]] = mapped_column(String(100))

    has_pdf_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    pdf_count: Mapped[int] = mapped_column(Integer, default=0)

    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
class PdfTemplateModel(BaseModel):
    __tablename__ = "pdf_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_pdf_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        SAEnum('active', 'inactive', native_enum=False, validate_strings=True, name="pdf_template_status"),
        nullable=False,
        default='active',
    )
    current_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pdf_template_versions.id"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pdf_template: Mapped["PdfTemplateModel"] = relationship(back_populates="versions", foreign_keys=[pdf_template_id])
    pipeline_definition: Mapped["PipelineDefinitionModel"] = relationship(back_populates="template_versions")
    sub_runs: Mapped[List["EtoSubRunModel"]] = relationship(back_populates="template_version")


# =========================
# module_catalog
# =========================

class ModuleModel(BaseModel):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(50), default="#3B82F6")
    category: Mapped[str] = mapped_column(String(100), default="Processing")
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    meta: Mapped[str] = mapped_column(Text, nullable=False)
    config_schema: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
    compiled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
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
    module_ref: Mapped[str] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)

    module_config: Mapped[str] = mapped_column(Text, nullable=False)
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)
    node_metadata: Mapped[str] = mapped_column(Text, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    compiled_plan: Mapped["PipelineCompiledPlanModel"] = relationship(back_populates="steps")
    module: Mapped["ModuleModel"] = relationship(back_populates="steps")

    __table_args__ = (
        Index("idx_pipeline_compiled_plan_id", "pipeline_compiled_plan_id"),
        Index("idx_pipeline_step_number", "step_number", "id"),
    )


# =========================
# eto_runs (NEW: parent orchestration level)
# =========================

class EtoRunModel(BaseModel):
    __tablename__ = "eto_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    # Parent orchestration status
    status: Mapped[str] = mapped_column(
        ETO_MASTER_STATUS,
        nullable=False,
        server_default="not_started",
    )

    # Processing step indicator
    processing_step: Mapped[Optional[str]] = mapped_column(
        ETO_RUN_PROCESSING_STEP,
        nullable=True,
    )

    # User interaction tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Error tracking (system-level failures)
    error_type: Mapped[Optional[str]] = mapped_column(String(50))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pdf_file: Mapped["PdfFileModel"] = relationship(back_populates="eto_runs")
    sub_runs: Mapped[List["EtoSubRunModel"]] = relationship(
        back_populates="eto_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eto_runs_status", "status"),
        Index("idx_eto_runs_processing_step", "processing_step"),
        Index("idx_eto_runs_pdf_file", "pdf_file_id"),
    )


# =========================
# eto_sub_runs (NEW: per page-set business logic)
# =========================

class EtoSubRunModel(BaseModel):
    __tablename__ = "eto_sub_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    eto_run_id: Mapped[int] = mapped_column(ForeignKey("eto_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Page set this sub-run represents (JSON array of page numbers)
    matched_pages: Mapped[str] = mapped_column(Text, nullable=False)

    # Template matched to this page set (NULL for unmatched group)
    template_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pdf_template_versions.id"), nullable=True, index=True
    )

    # Sub-run business logic status
    status: Mapped[str] = mapped_column(
        ETO_RUN_STATUS,
        nullable=False,
        server_default="not_started",
    )

    # Ordering within parent run
    sequence: Mapped[Optional[int]] = mapped_column(Integer)

    # Error tracking (business-level failures)
    error_type: Mapped[Optional[str]] = mapped_column(String(50))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    eto_run: Mapped["EtoRunModel"] = relationship(back_populates="sub_runs")
    template_version: Mapped[Optional["PdfTemplateVersionModel"]] = relationship(back_populates="sub_runs")
    extractions: Mapped[List["EtoSubRunExtractionModel"]] = relationship(
        back_populates="sub_run", cascade="all, delete-orphan"
    )
    pipeline_executions: Mapped[List["EtoSubRunPipelineExecutionModel"]] = relationship(
        back_populates="sub_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eto_sub_runs_status", "status"),
        Index("idx_eto_sub_runs_eto_run", "eto_run_id"),
        Index("idx_eto_sub_runs_template_version", "template_version_id"),
    )


# =========================
# eto_sub_run_extractions (NEW: extraction stage per sub-run)
# =========================

class EtoSubRunExtractionModel(BaseModel):
    __tablename__ = "eto_sub_run_extractions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub_run_id: Mapped[int] = mapped_column(ForeignKey("eto_sub_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        ETO_STEP_STATUS,
        nullable=False,
        server_default="processing",
    )

    extracted_data: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    sub_run: Mapped["EtoSubRunModel"] = relationship(back_populates="extractions")

    __table_args__ = (
        Index("idx_eto_sub_run_extractions_sub_run", "sub_run_id"),
        Index("idx_eto_sub_run_extractions_status", "status"),
    )


# =========================
# eto_sub_run_pipeline_executions (NEW: pipeline execution per sub-run)
# =========================

class EtoSubRunPipelineExecutionModel(BaseModel):
    __tablename__ = "eto_sub_run_pipeline_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub_run_id: Mapped[int] = mapped_column(ForeignKey("eto_sub_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        ETO_STEP_STATUS,
        nullable=False,
        server_default="processing",
    )

    executed_actions: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    sub_run: Mapped["EtoSubRunModel"] = relationship(back_populates="pipeline_executions")
    steps: Mapped[List["EtoSubRunPipelineExecutionStepModel"]] = relationship(
        back_populates="pipeline_execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eto_sub_run_pipeline_exec_sub_run", "sub_run_id"),
        Index("idx_eto_sub_run_pipeline_exec_status", "status"),
    )


# =========================
# eto_sub_run_pipeline_execution_steps (NEW: individual step logs)
# =========================

class EtoSubRunPipelineExecutionStepModel(BaseModel):
    __tablename__ = "eto_sub_run_pipeline_execution_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_execution_id: Mapped[int] = mapped_column(
        ForeignKey("eto_sub_run_pipeline_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    inputs: Mapped[Optional[str]] = mapped_column(Text)
    outputs: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pipeline_execution: Mapped["EtoSubRunPipelineExecutionModel"] = relationship(back_populates="steps")

    __table_args__ = (
        Index("idx_eto_sub_run_pipeline_step_exec", "pipeline_execution_id"),
        Index("idx_eto_sub_run_pipeline_step_number", "step_number"),
    )
