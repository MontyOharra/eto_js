"""
ETO Run Extraction Domain Types
Dataclasses representing eto_run_extractions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from ._sentinel import UNSET, UnsetType

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

    Uses UNSET sentinel to distinguish between:
    - Field not provided (UNSET) - field will not be updated
    - Field set to None (None) - field will be cleared/nulled in database
    - Field set to value - field will be updated to that value
    """
    status: str | UnsetType = UNSET
    extracted_data: str | None | UnsetType = UNSET
    started_at: datetime | None | UnsetType = UNSET
    completed_at: datetime | None | UnsetType = UNSET


@dataclass
class EtoRunExtraction:
    """
    Complete extraction run record as stored in the database.
    Represents the eto_run_extractions table exactly.
    """
    id: int
    eto_run_id: int
    status: str
    extracted_data: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
