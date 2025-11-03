"""
ETO Run Template Matching Domain Types
Dataclasses representing eto_run_template_matchings table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, TypedDict

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


class EtoRunTemplateMatchingUpdate(TypedDict, total=False):
    """
    Dict for updating a template matching record.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value
    """
    status: str
    matched_template_version_id: int | None
    started_at: datetime | None
    completed_at: datetime | None


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
