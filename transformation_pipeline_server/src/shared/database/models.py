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

    # Relationships
    execution_logs = relationship("PipelineExecutionLogModel", back_populates="pipeline_definition")

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
    input_field_mappings: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {this_input_node_id: upstream_node_id}

    # Node metadata and execution order
    node_metadata: Mapped[str] = mapped_column(Text)  # JSON: {"inputs": [InstanceNodePin], "outputs": [InstanceNodePin]}
    step_number: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        Index('idx_pipeline_steps_checksum', 'plan_checksum'),
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
    pipeline_defintion_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    entry_values: Mapped[str] = mapped_column(Text, nullable=False)  # JSON

    # Relationship to execution steps
    steps = relationship("ExecutionStepModel", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_execution_runs_pipeline', 'pipeline_defintion_id'),
        Index('idx_execution_runs_status', 'status'),
    )


class PipelineExecutionStepModel(BaseModel):
    """
    Execution steps - track individual module executions within a run
    Records inputs, outputs, timing, and errors for each module
    """
    __tablename__ = 'pipeline_execution_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(String(100), ForeignKey("pipeline_execution_runs.id"), nullable=False)
    module_instance_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[str] = mapped_column(Text)  # JSON - serialized inputs
    outputs: Mapped[str] = mapped_column(Text)  # JSON - serialized outputs
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship to execution run
    run = relationship("ExecutionRunModel", back_populates="steps")

    __table_args__ = (
        Index('idx_execution_steps_run', 'run_id'),
        Index('idx_execution_steps_module', 'module_instance_id'),
    )