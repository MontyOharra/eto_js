"""
ETO Run Extraction Domain Types
Dataclasses representing eto_run_extractions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

# =========================
# Type Aliases for Enums
# =========================

# Corresponds to EtoStepStatus enum in models.py
EtoStepStatus = Literal["processing", "success", "failure"]


# =========================
# ETO Run Extraction Types
# =========================

@dataclass
class EtoRunExtractionCreate:
    """
    Data required to create a new extraction run.
    Status defaults to "processing" in the database.
    Timing and data fields are set during processing.
    """
    eto_run_id: int


@dataclass
class EtoRunExtractionUpdate:
    """
    Data for updating an extraction run.
    All fields are optional - only provided fields will be updated.
    """
    status: Optional[EtoStepStatus] = None
    extracted_data: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class EtoRunExtraction:
    """
    Complete extraction run record as stored in the database.
    Represents the eto_run_extractions table exactly.
    """
    id: int
    eto_run_id: int
    status: EtoStepStatus
    extracted_data: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
