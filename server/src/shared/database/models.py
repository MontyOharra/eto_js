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

# Output execution status (includes pending state and approval flow)
ETO_OUTPUT_STATUS = SAEnum(
    'pending', 'processing', 'awaiting_approval', 'success', 'rejected', 'error',
    name='eto_output_status',
    native_enum=False,
    validate_strings=True
)

# Output execution action type (create vs update)
ETO_OUTPUT_ACTION_TYPE = SAEnum(
    'create', 'update',
    name='eto_output_action_type',
    native_enum=False,
    validate_strings=True
)


# =========================
# email_accounts (credentials storage)
# =========================

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
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "imap", "gmail_api", "outlook_com"
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Connection settings (JSON) - host, port, use_ssl, etc. (excludes credentials)
    provider_settings: Mapped[str] = mapped_column(Text, nullable=False)

    # Credentials (JSON) - password, oauth_token, refresh_token, etc.
    # TODO: Encrypt this field in future
    credentials: Mapped[str] = mapped_column(Text, nullable=False)

    # Validation status
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Discovered capabilities (JSON array) - ["IDLE", "UIDPLUS"]
    capabilities: Mapped[Optional[str]] = mapped_column(Text)

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
    # module_ref is nullable to support output channel steps (which are not real modules)
    # NULL module_ref indicates an output channel step; channel_type is stored in module_config
    module_ref: Mapped[Optional[str]] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=True, index=True)

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
    module: Mapped[Optional["ModuleModel"]] = relationship(back_populates="steps")  # Optional for output channel steps

    __table_args__ = (
        Index("idx_pipeline_definition_id", "pipeline_definition_id"),
        Index("idx_pipeline_step_number", "step_number", "id"),
    )


# Source type enum for ETO runs
ETO_SOURCE_TYPE = SAEnum(
    'email', 'manual',
    name='eto_source_type',
    native_enum=False,
    validate_strings=True
)


# =========================
# eto_runs (NEW: parent orchestration level)
# =========================

class EtoRunModel(BaseModel):
    __tablename__ = "eto_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pdf_file_id: Mapped[int] = mapped_column(ForeignKey("pdf_files.id"), nullable=False, index=True)

    # Source tracking (where this run came from)
    source_type: Mapped[str] = mapped_column(
        ETO_SOURCE_TYPE,
        nullable=False,
    )
    source_email_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("emails.id"),
        nullable=True,
        index=True
    )

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
    output_execution: Mapped[Optional["EtoSubRunOutputExecutionModel"]] = relationship(
        back_populates="sub_run", cascade="all, delete-orphan", uselist=False
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


# =========================
# eto_sub_run_output_executions (NEW: output execution stage per sub-run)
# =========================

class EtoSubRunOutputExecutionModel(BaseModel):
    """
    Tracks the execution of output operations (order creation, email sending, etc.)
    after pipeline completes successfully.

    Decoupled from pipeline execution - orchestrator passes data in-memory.
    One-to-one with sub_run (one output execution per sub-run).

    Supports create/update flow with user approval for updates:
    - HAWB not found → auto-create order
    - HAWB found once → queue for user approval before updating
    - HAWB found multiple times → error state
    """
    __tablename__ = "eto_sub_run_output_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub_run_id: Mapped[int] = mapped_column(
        ForeignKey("eto_sub_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Which output module to execute (from pipeline return value)
    module_id: Mapped[str] = mapped_column(
        ForeignKey("modules.id"),
        nullable=False,
        index=True
    )

    # Input data for the output module (from pipeline return value)
    input_data_json: Mapped[str] = mapped_column(Text, nullable=False)

    # HAWB extracted from input_data for easy querying
    hawb: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Execution status tracking
    # States: pending -> processing -> success/error/awaiting_approval -> rejected
    status: Mapped[str] = mapped_column(
        ETO_OUTPUT_STATUS,
        nullable=False,
        server_default="pending",
    )

    # Action type: 'create' or 'update' (NULL before HAWB check completes)
    action_type: Mapped[Optional[str]] = mapped_column(ETO_OUTPUT_ACTION_TYPE, nullable=True)

    # For updates: the existing order being updated
    existing_order_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # For updates: snapshot of current order data for comparison UI
    existing_order_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Results from execution
    result_json: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.getutcdate(), onupdate=func.getutcdate(), nullable=False
    )

    # Relationships
    sub_run: Mapped["EtoSubRunModel"] = relationship(back_populates="output_execution", uselist=False)
    module: Mapped["ModuleModel"] = relationship()

    __table_args__ = (
        Index("idx_eto_sub_run_output_exec_sub_run", "sub_run_id"),
        Index("idx_eto_sub_run_output_exec_status", "status"),
        Index("idx_eto_sub_run_output_exec_module", "module_id"),
        Index("idx_eto_sub_run_output_exec_hawb", "hawb"),
        Index("idx_eto_sub_run_output_exec_awaiting", "status", postgresql_where="status = 'awaiting_approval'"),
    )


# =========================
# output_channel_types (catalog of allowed output channels)
# =========================

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
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "str", "datetime", "int", "float"

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Required for order creation?
    category: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "identification", "pickup", "delivery", "cargo"

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
