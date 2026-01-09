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

from shared.types.email_accounts import ProviderType
from shared.types.eto_runs import EtoSourceType, EtoMasterStatus, EtoRunProcessingStep, EtoStepStatus, EtoOutputStatus
from shared.types.eto_sub_runs import EtoSubRunStatus
from shared.types.modules import ModuleKind
from shared.types.output_channels import OutputChannelDataType, OutputChannelCategory
from shared.types.pdf_templates import PdfTemplateStatus
from shared.types.pending_actions import PendingActionType, PendingActionStatus

class BaseModel(DeclarativeBase):
    """Base class for all table models. Used by create_all() to create tables."""
    pass


class ViewBase(DeclarativeBase):
    """
    Separate base class for VIEW models.

    Views inherit from this instead of BaseModel so they are NOT included
    in BaseModel.metadata.create_all() - which would try to create tables.
    Views are created separately via raw SQL in database_creator.py.
    """
    pass


# =========================
# ENUMS for new ETO design
# =========================

# Source type for ETO runs
ETO_SOURCE_TYPE = SAEnum(
    'email', 'manual',
    name='eto_source_type',
    native_enum=False,
    validate_strings=True
)

# Parent orchestration status
ETO_MASTER_STATUS = SAEnum(
    'not_started', 'processing', 'success', 'failure', 'skipped',
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

# Output execution status
ETO_OUTPUT_STATUS = SAEnum(
    'pending', 'processing', 'success', 'error', 'manual_review',
    name='eto_output_status',
    native_enum=False,
    validate_strings=True
)




# =========================
# email_accounts (credentials storage)
# =========================

# Email provider type enum
EMAIL_PROVIDER_TYPE = SAEnum(
    'standard',
    name='email_provider_type',
    native_enum=False,
    validate_strings=True
)

class EmailAccountModel(BaseModel):
    """
    Stores email account credentials and connection settings.
    Decoupled from ingestion configs - one account can be used by multiple listeners.
    Future: Also used for email sending configurations.
    """
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Display info
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # "Work Gmail", "Dispatch Inbox"
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Provider info
    provider_type: Mapped[ProviderType] = mapped_column(EMAIL_PROVIDER_TYPE, nullable=False)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Connection settings (JSON) - host, port, use_ssl, etc. (excludes credentials)
    provider_settings: Mapped[str] = mapped_column(Text, nullable=False)

    credentials: Mapped[str] = mapped_column(Text, nullable=False)

    # Validation status
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Error tracking
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    ingestion_configs: Mapped[List["EmailIngestionConfigModel"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_email_accounts_email", "email_address"),
        Index("idx_email_accounts_validated", "is_validated"),
    )


# =========================
# email_ingestion_configs (listener settings)
# =========================

class EmailIngestionConfigModel(BaseModel):
    """
    Stores email ingestion listener configuration.
    References an email_account for credentials.
    One account can have multiple ingestion configs (different folders, filters).
    """
    __tablename__ = "email_ingestion_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Display info
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # "SOS Auto Orders"
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Reference to account (credentials stored there)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("email_accounts.id"), nullable=False, index=True
    )

    # Ingestion-specific settings
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "INBOX.SOS Auto Order"
    filter_rules: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of filter rules

    # Polling settings
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    use_idle: Mapped[bool] = mapped_column(Boolean, default=True)  # Prefer IDLE if available

    # State tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_check_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_processed_uid: Mapped[Optional[int]] = mapped_column(BigInteger)  # For UID-based tracking

    # Error tracking (listener-specific errors)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    account: Mapped["EmailAccountModel"] = relationship(back_populates="ingestion_configs")
    emails: Mapped[List["EmailModel"]] = relationship(back_populates="ingestion_config")

    __table_args__ = (
        Index("idx_email_ingestion_config_active", "is_active"),
        Index("idx_email_ingestion_config_account", "account_id"),
    )


# =========================
# emails
# =========================

class EmailModel(BaseModel):
    """
    Tracks processed emails for deduplication.

    Deduplication is per-account (not per-config) so that emails moved
    between folders on the same account are not re-processed.
    """
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Account this email belongs to (for deduplication)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("email_accounts.id"), nullable=False, index=True
    )

    # Config that first ingested this email (for audit/debugging, nullable if config deleted)
    ingestion_config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("email_ingestion_configs.id", ondelete="SET NULL"), nullable=True
    )

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
    account: Mapped["EmailAccountModel"] = relationship()
    ingestion_config: Mapped[Optional["EmailIngestionConfigModel"]] = relationship(back_populates="emails")
    # Note: PDF files no longer track email_id - use eto_runs.source_email_id instead

    __table_args__ = (
        # Deduplication: same Message-ID on same account = same email
        UniqueConstraint("account_id", "message_id", name="uix_account_message"),
        Index("ix_email_account_id", "account_id"),
        Index("ix_email_ingestion_config_id", "ingestion_config_id"),
        Index("ix_email_received_date", "received_date"),
    )


# =========================
# pdf_files
# =========================

class PdfFileModel(BaseModel):
    __tablename__ = "pdf_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

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
    # Note: Source tracking moved to eto_runs table
    eto_runs: Mapped[List["EtoRunModel"]] = relationship(back_populates="pdf_file", cascade="all, delete-orphan")
    source_for_templates: Mapped[List["PdfTemplateModel"]] = relationship(
        back_populates="source_pdf", cascade="all, delete-orphan", foreign_keys="PdfTemplateModel.source_pdf_id"
    )


# =========================
# pdf_templates
# =========================

# PDF template status enum
PDF_TEMPLATE_STATUS = SAEnum(
    'active', 'inactive',
    name='pdf_template_status',
    native_enum=False,
    validate_strings=True
)


class PdfTemplateModel(BaseModel):
    __tablename__ = "pdf_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # References external Access DB
    source_pdf_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    status: Mapped[PdfTemplateStatus] = mapped_column(PDF_TEMPLATE_STATUS, nullable=False, default='active')
    is_autoskip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    pipeline_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pipeline_definitions.id"), nullable=True, index=True)  # Nullable for autoskip templates
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
# modules
# =========================

# Module kind enum
MODULE_KIND = SAEnum(
    'transform', 'logic', 'comparator', 'misc', 'output',
    name='module_kind',
    native_enum=False,
    validate_strings=True
)


class ModuleModel(BaseModel):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "text_cleaner"
    version: Mapped[str] = mapped_column(String(50), nullable=False)       # e.g., "1.0.0"
    name: Mapped[str] = mapped_column(String(255), nullable=False)         # Display name
    description: Mapped[str | None] = mapped_column(Text)
    module_kind: Mapped[ModuleKind] = mapped_column(MODULE_KIND, nullable=False)
    meta: Mapped[str] = mapped_column(Text, nullable=False)
    config_schema: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(50), default="#3B82F6")
    category: Mapped[str] = mapped_column(String(100), default="Processing")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    steps: Mapped[list["PipelineDefinitionStepModel"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("identifier", "version", name="uq_module_identifier_version"),
        Index("idx_module_identifier", "identifier"),
        Index("idx_module_kind", "module_kind"),
        Index("idx_module_active", "is_active"),
        Index("idx_module_category", "category"),
    )


# =========================
# pipeline_definitions
# =========================

class PipelineDefinitionModel(BaseModel):
    __tablename__ = "pipeline_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_state: Mapped[str] = mapped_column(Text, nullable=False)
    visual_state: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    steps: Mapped[List["PipelineDefinitionStepModel"]] = relationship(
        back_populates="pipeline_definition", cascade="all, delete-orphan"
    )
    template_versions: Mapped[List["PdfTemplateVersionModel"]] = relationship(back_populates="pipeline_definition")


# =========================
# pipeline_definition_steps
# =========================

class PipelineDefinitionStepModel(BaseModel):
    __tablename__ = "pipeline_definition_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_definition_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_definitions.id"), nullable=False, index=True
    )

    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    # module_id is nullable to support output channel steps (which are not real modules)
    # NULL module_id indicates an output channel step; channel_type is stored in module_config
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("modules.id", ondelete="SET NULL"), nullable=True, index=True
    )

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
    pipeline_definition: Mapped["PipelineDefinitionModel"] = relationship(back_populates="steps")
    module: Mapped["ModuleModel | None"] = relationship(back_populates="steps")  # Optional for output channel steps

    __table_args__ = (
        Index("idx_pipeline_step_definition_id", "pipeline_definition_id"),
        Index("idx_pipeline_step_module_id", "module_id"),
        Index("idx_pipeline_step_number", "step_number", "id"),
    )


# =========================
# eto_runs (NEW: parent orchestration level)
# =========================

class EtoRunModel(BaseModel):
    __tablename__ = "eto_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    # Source tracking (where this run came from)
    source_type: Mapped[EtoSourceType] = mapped_column(
        ETO_SOURCE_TYPE,
        nullable=False,
    )
    source_email_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("emails.id"),
        nullable=True,
        index=True
    )

    # Parent orchestration status
    status: Mapped[EtoMasterStatus] = mapped_column(
        ETO_MASTER_STATUS,
        nullable=False,
        server_default="not_started",
    )

    # Processing step indicator
    processing_step: Mapped[EtoRunProcessingStep | None] = mapped_column(
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
    # Stable timestamp for list sorting - only updated when run reaches terminal state
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    pdf_file: Mapped["PdfFileModel"] = relationship(back_populates="eto_runs")
    source_email: Mapped[Optional["EmailModel"]] = relationship(foreign_keys=[source_email_id])
    sub_runs: Mapped[List["EtoSubRunModel"]] = relationship(
        back_populates="eto_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eto_runs_status", "status"),
        Index("idx_eto_runs_processing_step", "processing_step"),
        Index("idx_eto_runs_pdf_file", "pdf_file_id"),
        Index("idx_eto_runs_source_email", "source_email_id"),
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
    status: Mapped[EtoSubRunStatus] = mapped_column(
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
    output_executions: Mapped[List["EtoSubRunOutputExecutionModel"]] = relationship(
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

    status: Mapped[EtoStepStatus] = mapped_column(
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

    status: Mapped[EtoStepStatus] = mapped_column(
        ETO_STEP_STATUS,
        nullable=False,
        server_default="processing",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # JSON object with output channel names as keys and their collected values
    # e.g., {"hawb": "ABC123", "pickup_time_start": "2024-01-15T09:00:00"}
    transformed_data: Mapped[Optional[str]] = mapped_column(Text)

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


# =========================
# eto_sub_run_output_executions (output channel processing per HAWB)
# =========================

class EtoSubRunOutputExecutionModel(BaseModel):
    """
    Tracks output channel processing for a single HAWB from a sub-run.

    One sub-run can produce multiple output executions (one per HAWB if list).
    This is the crash-resilience layer - data persists before processing begins.

    The unique order identifier is (customer_id, hawb) since different customers
    may have overlapping HAWB values.
    """
    __tablename__ = "eto_sub_run_output_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    sub_run_id: Mapped[int] = mapped_column(
        ForeignKey("eto_sub_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
        # NOTE: No unique constraint - one sub-run can have multiple (for HAWB lists)
    )

    # The unique order identifier (customer_id + hawb)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # All output channel values from pipeline (JSON dict)
    # e.g., {"pickup_address": "123 Main St", "pieces": 5, ...}
    output_channel_data: Mapped[str] = mapped_column(Text, nullable=False)

    # Execution status: pending -> processing -> success/error
    status: Mapped[EtoOutputStatus] = mapped_column(
        ETO_OUTPUT_STATUS,
        nullable=False,
        server_default="pending",
    )

    # What action was taken (set after processing completes)
    # Values: 'pending_order_created', 'pending_order_updated',
    #         'pending_updates_created', 'order_created'
    action_taken: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # HTC order number if order was created during this execution
    htc_order_number: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

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
    sub_run: Mapped["EtoSubRunModel"] = relationship(back_populates="output_executions")

    __table_args__ = (
        Index("idx_output_exec_sub_run", "sub_run_id"),
        Index("idx_output_exec_status", "status"),
        Index("idx_output_exec_customer_hawb", "customer_id", "hawb"),
    )


# =========================
# output_channel_types (catalog of allowed output channels)
# =========================

# Output channel data type enum
OUTPUT_CHANNEL_DATA_TYPE = SAEnum(
    'str', 'int', 'float', 'datetime', 'list[str]', 'list[dim]',
    name='output_channel_data_type',
    native_enum=False,
    validate_strings=True
)

# Output channel category enum
OUTPUT_CHANNEL_CATEGORY = SAEnum(
    'identification', 'pickup', 'delivery', 'cargo', 'other',
    name='output_channel_category',
    native_enum=False,
    validate_strings=True
)


class OutputChannelTypeModel(BaseModel):
    """
    Catalog of allowed output channel types for pipeline outputs.

    Unlike modules, output channels are simple data definitions with no handlers.
    They define the allowed fields that can flow out of a pipeline into the
    pending orders system.
    """
    __tablename__ = "output_channel_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g., "hawb", "pickup_address"
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "HAWB", "Pickup Address"

    # Data type constraint
    data_type: Mapped[OutputChannelDataType] = mapped_column(OUTPUT_CHANNEL_DATA_TYPE, nullable=False)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Required for order creation?
    category: Mapped[OutputChannelCategory] = mapped_column(OUTPUT_CHANNEL_CATEGORY, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    __table_args__ = (
        Index("idx_output_channel_types_name", "name"),
        Index("idx_output_channel_types_category", "category"),
        Index("idx_output_channel_types_required", "is_required"),
    )


# =========================
# ENUMS for pending orders system
# =========================

# Pending order status
PENDING_ORDER_STATUS = SAEnum(
    'incomplete', 'ready', 'processing', 'created', 'failed', 'rejected',
    name='pending_order_status',
    native_enum=False,
    validate_strings=True
)

# Pending update status
PENDING_UPDATE_STATUS = SAEnum(
    'pending', 'approved', 'rejected', 'manual_review',
    name='pending_update_status',
    native_enum=False,
    validate_strings=True
)

# =========================
# ENUMS for unified pending actions system
# =========================

# Pending action type (create vs update vs ambiguous)
PENDING_ACTION_TYPE = SAEnum(
    'create', 'update', 'ambiguous',
    name='pending_action_type',
    native_enum=False,
    validate_strings=True
)

# Pending action status
PENDING_ACTION_STATUS = SAEnum(
    'accumulating', 'incomplete', 'conflict', 'ambiguous', 'ready',
    'processing', 'completed', 'failed', 'rejected',
    name='pending_action_status',
    native_enum=False,
    validate_strings=True
)


# =========================
# pending_orders (aggregated order state by HAWB)
# =========================
'''
class PendingOrderModel(BaseModel):
    """
    Aggregated order state for a single HAWB.

    Compiles data from multiple sub-runs into a single order.
    When all required fields are present and no conflicts exist,
    the order becomes 'ready' for HTC creation by the worker.

    Status flow:
    - incomplete: Missing required fields or has conflicts
    - ready: All required fields present, queued for HTC creation
    - processing: Worker is currently creating HTC order
    - created: Successfully created in HTC
    - failed: HTC creation failed (see error_message)

    Unique identifier is (customer_id, hawb) since different customers
    may have overlapping HAWB values.
    """
    __tablename__ = "pending_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Unique identifier (customer_id + hawb)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Status: incomplete -> ready -> processing -> created/failed/rejected
    status: Mapped[str] = mapped_column(
        PENDING_ORDER_STATUS,
        nullable=False,
        server_default="incomplete",
    )

    # HTC integration (set when order created in HTC)
    htc_order_number: Mapped[Optional[float]] = mapped_column(nullable=True)
    htc_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking (for failed HTC creation)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Required fields (all must be non-null for status='ready')
    pickup_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pickup_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pickup_time_start: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pickup_time_end: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_time_start: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_time_end: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Optional fields
    mawb: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dimensions (JSON array of dim objects)
    # Each dim: {"height": float, "length": float, "width": float, "qty": int, "weight": float, "dim_weight": float}
    dims: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Read/unread tracking for UI
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Timestamps
    # last_processed_at: Updated when actual processing occurs (field changes, status changes)
    # NOT updated on read/unread toggle - use for stable list sorting
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    history: Mapped[List["PendingOrderHistoryModel"]] = relationship(
        back_populates="pending_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("customer_id", "hawb", name="uq_pending_orders_customer_hawb"),
        Index("idx_pending_orders_status", "status"),
        Index("idx_pending_orders_customer_hawb", "customer_id", "hawb"),
    )


# =========================
# pending_order_history (field contribution audit trail)
# =========================

class PendingOrderHistoryModel(BaseModel):
    """
    Tracks each field contribution from sub-runs.

    Used to compute field state (set/conflict/confirmed) and provide
    audit trail of which sub-runs contributed which data.

    One row per field per contribution (a sub-run contributing 5 fields = 5 rows).
    """
    __tablename__ = "pending_order_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Parent pending order
    pending_order_id: Mapped[int] = mapped_column(
        ForeignKey("pending_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Source tracking
    sub_run_id: Mapped[int] = mapped_column(
        ForeignKey("eto_sub_runs.id", ondelete="SET NULL"),
        nullable=True,  # Nullable due to SET NULL on delete
        index=True
    )

    # Field contribution
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Conflict resolution - TRUE if user explicitly chose this value
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamp
    contributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )

    # Relationships
    pending_order: Mapped["PendingOrderModel"] = relationship(back_populates="history")
    sub_run: Mapped[Optional["EtoSubRunModel"]] = relationship()

    __table_args__ = (
        Index("idx_poh_pending_order", "pending_order_id"),
        Index("idx_poh_field", "pending_order_id", "field_name"),
        Index("idx_poh_sub_run", "sub_run_id"),
        Index("idx_poh_selected", "pending_order_id", "field_name", "is_selected"),
    )


# =========================
# pending_updates (approval queue for existing HTC orders)
# =========================

class PendingUpdateModel(BaseModel):
    """
    Aggregated proposed changes for a single HAWB that already exists in HTC.

    When pipeline outputs data for a HAWB that's already in HTC,
    updates are queued here for user approval instead of auto-applying.

    Structure mirrors PendingOrderModel - one record per unique (customer_id, hawb)
    with status='pending'. Multiple field changes accumulate into the same record
    via PendingUpdateHistoryModel until user approves/rejects.

    Status flow:
    - pending: Awaiting user review, may accumulate more field changes
    - approved: User approved, changes applied to HTC
    - rejected: User rejected the changes

    After approval/rejection, a NEW pending_update record is created for
    subsequent field changes from ETO.
    """
    __tablename__ = "pending_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Order identification (unique per customer_id + hawb when status='pending')
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # NULL when multiple HTC orders exist (manual_review status)
    htc_order_number: Mapped[Optional[float]] = mapped_column(nullable=True, index=True)

    # Status: pending -> approved/rejected
    status: Mapped[str] = mapped_column(
        PENDING_UPDATE_STATUS,
        nullable=False,
        server_default="pending",
    )

    # Proposed field values (NULL means no change proposed for that field)
    # Required fields
    pickup_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pickup_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pickup_time_start: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_time_end: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_time_start: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_time_end: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Optional fields
    mawb: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dimensions (JSON array of dim objects)
    # Each dim: {"height": float, "length": float, "width": float, "qty": int, "weight": float, "dim_weight": float}
    dims: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Read/unread tracking for UI
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Timestamps
    # last_processed_at: Updated when actual processing occurs (field changes, status changes)
    # NOT updated on read/unread toggle - use for stable list sorting
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    history: Mapped[List["PendingUpdateHistoryModel"]] = relationship(
        back_populates="pending_update", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_pending_updates_status", "status"),
        Index("idx_pending_updates_customer_hawb", "customer_id", "hawb"),
        Index("idx_pending_updates_order", "htc_order_number"),
    )


# =========================
# pending_update_history (field contribution audit trail for updates)
# =========================

class PendingUpdateHistoryModel(BaseModel):
    """
    Tracks each field contribution from sub-runs for pending updates.

    Mirrors PendingOrderHistoryModel structure for consistency.
    Used to track which sub-runs contributed which proposed changes
    and support conflict resolution if multiple sub-runs propose
    different values for the same field.
    """
    __tablename__ = "pending_update_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Parent pending update
    pending_update_id: Mapped[int] = mapped_column(
        ForeignKey("pending_updates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Source tracking
    sub_run_id: Mapped[int] = mapped_column(
        ForeignKey("eto_sub_runs.id", ondelete="SET NULL"),
        nullable=True,  # Nullable due to SET NULL on delete
        index=True
    )

    # Field contribution
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Conflict resolution - TRUE if user explicitly chose this value
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamp
    contributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )

    # Relationships
    pending_update: Mapped["PendingUpdateModel"] = relationship(back_populates="history")
    sub_run: Mapped[Optional["EtoSubRunModel"]] = relationship()

    __table_args__ = (
        Index("idx_puh_pending_update", "pending_update_id"),
        Index("idx_puh_field", "pending_update_id", "field_name"),
        Index("idx_puh_sub_run", "sub_run_id"),
        Index("idx_puh_selected", "pending_update_id", "field_name", "is_selected"),
    )
'''

# ============================================================
# system_settings - Application configuration key-value store
# ============================================================


class SystemSettingModel(BaseModel):
    """
    Key-value store for application-wide settings.

    Used for storing configuration like:
    - email.default_sender_account_id - Which email account to use for sending
    - Future: notification preferences, default recipients, etc.
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON serialized for complex values
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )


# =========================
# pending_actions (unified order action system)
# =========================

class PendingActionModel(BaseModel):
    """
    Unified pending action for order creation or update.

    Replaces the old separate pending_orders and pending_updates tables.
    Action type (create vs update) is determined at execution time, not
    accumulation time, to protect against TOCTOU race conditions.

    Key Design:
    - Lightweight main record with denormalized counts
    - Field values stored in pending_action_fields table
    - Status determined by field state (conflicts, required fields)

    Status Flow:
    - accumulating: Still receiving data from sub-runs
    - incomplete: Missing required fields
    - conflict: Has unresolved field conflicts
    - ambiguous: Multiple HTC orders exist for this HAWB
    - ready: Ready for execution
    - processing: Currently executing against HTC
    - completed: Successfully executed
    - failed: Execution failed (retryable)
    - rejected: User rejected the action

    Unique constraint on (customer_id, hawb) for active actions only.
    """
    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Unique identifier (customer_id + hawb for active actions)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # HTC order number (set for updates, set after create succeeds)
    htc_order_number: Mapped[Optional[float]] = mapped_column(nullable=True, index=True)

    # Action type: create, update, or ambiguous (multiple HTC orders exist)
    action_type: Mapped[PendingActionType] = mapped_column(
        PENDING_ACTION_TYPE,
        nullable=False,
        server_default="create",
    )

    # Status
    status: Mapped[PendingActionStatus] = mapped_column(
        PENDING_ACTION_STATUS,
        nullable=False,
        server_default="accumulating",
    )

    # Denormalized counts for quick status evaluation
    required_fields_present: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Error tracking (for failed execution)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Read/unread tracking for UI
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )
    # last_processed_at: Updated on actual processing (not read/unread toggle)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    fields: Mapped[List["PendingActionFieldModel"]] = relationship(
        back_populates="pending_action", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Unique constraint only for active actions (not completed/rejected/failed)
        # Note: SQLite doesn't support partial unique indexes, so this is enforced in code
        Index("idx_pending_actions_customer_hawb", "customer_id", "hawb"),
        Index("idx_pending_actions_status", "status"),
        Index("idx_pending_actions_action_type", "action_type"),
        Index("idx_pending_actions_htc_order", "htc_order_number"),
    )


# =========================
# pending_action_fields (field values + history combined)
# =========================

class PendingActionFieldModel(BaseModel):
    """
    Individual field value for a pending action.

    Serves as both current value storage and audit trail. The "current"
    value for a field is WHERE is_selected = TRUE.

    Key Design:
    - Multiple values per field allowed (for conflict resolution)
    - sub_run_id = NULL indicates user-provided value (manual entry)
    - is_selected tracks which value is chosen for this field
    - is_approved_for_update allows partial updates (updates only)

    Conflict Resolution:
    - First value for a field: is_selected = TRUE
    - Same value again: is_selected = FALSE (duplicate)
    - Different value: ALL is_selected = FALSE (conflict - user must resolve)

    User-Provided Values:
    - Created via set_user_value() service method
    - sub_run_id = NULL distinguishes from extracted values
    - Deleted when all extracted values are removed (no orphan manual entries)
    """
    __tablename__ = "pending_action_fields"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Parent pending action
    pending_action_id: Mapped[int] = mapped_column(
        ForeignKey("pending_actions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Source tracking (NULL = user-provided value)
    sub_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("eto_sub_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Field identification
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Field value (JSON - string, dict, or list depending on field type)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Selection state for conflict resolution
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

    # Approval state for partial updates (only relevant for action_type='update')
    is_approved_for_update: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    # Relationships
    pending_action: Mapped["PendingActionModel"] = relationship(back_populates="fields")
    sub_run: Mapped[Optional["EtoSubRunModel"]] = relationship()

    __table_args__ = (
        Index("idx_paf_pending_action", "pending_action_id"),
        Index("idx_paf_field", "pending_action_id", "field_name"),
        Index("idx_paf_sub_run", "sub_run_id"),
        Index("idx_paf_selected", "pending_action_id", "field_name", "is_selected"),
    )


# =========================
# DATABASE VIEWS
# =========================
'''
class UnifiedActionsViewModel(ViewBase):
    """
    Maps to the unified_actions_view VIEW (read-only).

    Combines pending_orders and pending_updates into a single queryable view.
    Used by the Orders page to display both types in a unified list with
    efficient filtering, sorting, and pagination.

    NOTE: This is a VIEW, not a table. INSERT/UPDATE/DELETE will fail.
    The view is created by database_creator.py from views.py SQL.

    Inherits from ViewBase (not BaseModel) so it's excluded from create_all().
    """
    __tablename__ = "unified_actions_view"

    # Composite primary key (id alone is not unique across types)
    type: Mapped[str] = mapped_column(String(10), primary_key=True)  # 'create' or 'update'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Common fields
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    hawb: Mapped[str] = mapped_column(String(100), nullable=False)
    htc_order_number: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Type-specific fields (may be NULL for the other type)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
'''