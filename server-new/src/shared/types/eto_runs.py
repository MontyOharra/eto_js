"""
ETO Run Domain Types
Dataclasses representing eto_runs table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

# =========================
# Type Aliases for Enums
# =========================

# Corresponds to EtoRunStatus enum in models.py
EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]

# Corresponds to EtoRunProcessingStep enum in models.py
EtoProcessingStep = Literal["template_matching", "data_extraction", "data_transformation"]


# =========================
# ETO Run Types
# =========================

@dataclass
class EtoRunCreate:
    """
    Data required to create a new ETO run.
    All other fields are set to defaults by the database.
    """
    pdf_file_id: int


@dataclass
class EtoRunUpdate:
    """
    Data for updating an ETO run.
    All fields are optional - only provided fields will be updated.
    """
    status: Optional[EtoRunStatus] = None
    processing_step: Optional[EtoProcessingStep] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class EtoRun:
    """
    Complete ETO run record as stored in the database.
    Represents the eto_runs table exactly.
    """
    id: int
    pdf_file_id: int
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep]
    error_type: Optional[str]
    error_message: Optional[str]
    error_details: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
