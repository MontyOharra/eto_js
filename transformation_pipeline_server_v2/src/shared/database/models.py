"""
Transformation Pipeline Database Models
Based on the transformation pipeline design document
"""
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

# SQLAlchemy 2.0 Base
class BaseModel(DeclarativeBase):
    pass


class PipelineDefinitionModel(BaseModel):
    """
    Pipeline definitions - canonical pipeline JSON storage
    Stores the source of truth for pipeline configuration with checksums
    Pipelines are immutable once created (no updates allowed)
    """
    __tablename__ = 'pipeline_definitions'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Canonical pipeline JSON (modules, pins, connections, configs) - always required
    pipeline_json: Mapped[str] = mapped_column(Text, nullable=False)
    visual_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Checksum for compiled plan integrity
    plan_checksum: Mapped[Optional[str]] = mapped_column(String(64))
    compiled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Audit fields (no updated_at since pipelines are immutable)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    pipeline_steps = relationship("PipelineStepModel", back_populates="pipeline_definition", cascade="all, delete-orphan")
    execution_logs = relationship("PipelineExecutionLogModel", back_populates="pipeline_definition")

    __table_args__ = (
        Index('idx_pipeline_definitions_name', 'name'),
        Index('idx_pipeline_definitions_checksum', 'plan_checksum'),
        Index('idx_pipeline_definitions_active', 'is_active'),
    )


class PipelineStepModel(BaseModel):
    """
    Pipeline steps - compiled cache for execution
    Stores compiled execution steps with dependency mappings
    """
    __tablename__ = 'pipeline_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(ForeignKey('pipeline_definitions.id'), nullable=False)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Module instance information
    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module_ref: Mapped[str] = mapped_column(String(100), nullable=False)  # "name:version"
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "transform"|"action"|"logic"

    # Validated configuration and mappings
    module_config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {this_input_node_id: upstream_node_id}

    # Optional fields for display and execution order
    output_display_names: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    step_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    pipeline_definition = relationship("PipelineDefinitionModel", back_populates="pipeline_steps")

    __table_args__ = (
        Index('idx_pipeline_steps_pipeline_checksum', 'pipeline_id', 'plan_checksum'),
        Index('idx_pipeline_steps_module_ref', 'module_ref'),
        Index('idx_pipeline_steps_kind', 'module_kind'),
    )


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
    module_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "transform"|"action"|"logic"

    # Dynamic side rules and configuration schemas (JSON)
    meta: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: ModuleMeta with dynamic side rules
    config_schema: Mapped[Optional[str]] = mapped_column(Text)  # JSON: Pydantic JSON Schema
    
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


class PipelineExecutionLogModel(BaseModel):
    """
    Pipeline execution logs - track execution history and performance
    Optional table for monitoring and debugging pipeline runs
    """
    __tablename__ = 'pipeline_execution_logs'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(ForeignKey('pipeline_definitions.id'), nullable=False)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Execution metadata
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False)  # UUID for this execution
    entry_values: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: input values

    # Execution results
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success"|"failed"|"timeout"
    result_values: Mapped[Optional[str]] = mapped_column(Text)  # JSON: output values
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Performance metrics
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Step-level execution details
    step_logs: Mapped[Optional[str]] = mapped_column(Text)  # JSON: per-step execution info

    # Relationships
    pipeline_definition = relationship("PipelineDefinitionModel", back_populates="execution_logs")

    __table_args__ = (
        Index('idx_pipeline_execution_logs_pipeline', 'pipeline_id'),
        Index('idx_pipeline_execution_logs_execution_id', 'execution_id'),
        Index('idx_pipeline_execution_logs_status', 'status'),
        Index('idx_pipeline_execution_logs_started_at', 'started_at'),
    )