"""
ETO Run Template Matching Domain Types
Dataclasses representing eto_run_template_matchings table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from ._sentinel import UNSET, UnsetType

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

    Uses UNSET sentinel to distinguish between:
    - Field not provided (UNSET) - field will not be updated
    - Field set to None (None) - field will be cleared/nulled in database
    - Field set to value - field will be updated to that value
    """
    status: str | UnsetType = UNSET
    matched_template_version_id: int | None | UnsetType = UNSET
    started_at: datetime | None | UnsetType = UNSET
    completed_at: datetime | None | UnsetType = UNSET


@dataclass
class EtoRunTemplateMatching:
    """
    Complete template matching record as stored in the database.
    Represents the eto_run_template_matchings table exactly.
    """
    id: int
    eto_run_id: int
    status: str
    matched_template_version_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
