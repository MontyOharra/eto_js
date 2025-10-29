"""
ETO Run Template Matching Domain Types
Dataclasses representing eto_run_template_matchings table and related operations
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
# Template Matching Types
# =========================

@dataclass
class EtoRunTemplateMatchingCreate:
    """
    Data required to create a new template matching record.
    Status defaults to "processing" via model default.
    """
    eto_run_id: int


@dataclass
class EtoRunTemplateMatchingUpdate:
    """
    Data for updating a template matching record.
    All fields are optional - only provided fields will be updated.
    """
    status: Optional[EtoStepStatus] = None
    matched_template_version_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class EtoRunTemplateMatching:
    """
    Complete template matching record as stored in the database.
    Represents the eto_run_template_matchings table exactly.
    """
    id: int
    eto_run_id: int
    status: EtoStepStatus
    matched_template_version_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
