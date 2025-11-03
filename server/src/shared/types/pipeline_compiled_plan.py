"""
Pipeline Compiled Plan Types
Domain types for pipeline_compiled_plans table
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PipelineCompiledPlanFull:
    """
    Complete compiled plan record from database.

    Represents a unique compiled pipeline identified by checksum.
    Multiple pipeline_definitions can reference the same compiled plan
    to avoid redundant compilation of identical logic.

    This table is append-only (no updates) - compiled plans are immutable.
    """
    id: int
    plan_checksum: str
    compiled_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineCompiledPlanCreate:
    """
    Data needed to create new compiled plan.

    Created after:
    1. Pipeline validation succeeds
    2. Graph pruning completes
    3. Checksum calculation completes
    4. Checksum lookup finds no existing plan
    5. Pipeline compilation generates steps
    """
    plan_checksum: str
    compiled_at: datetime
