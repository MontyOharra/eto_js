"""
ETO Sub-Run Extraction Domain Types
Dataclasses representing eto_sub_run_extractions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

# =========================
# ETO Sub-Run Extraction Types
# =========================

@dataclass
class EtoSubRunExtractionCreate:
    """
    Data required to create a new extraction for a sub-run.
    Status defaults to "processing" in the database.
    Timing and data fields are set during processing.
    """
    sub_run_id: int


class EtoSubRunExtractionUpdate(TypedDict, total=False):
    """
    Dict for updating a sub-run extraction.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value

    Note: extracted_data is List[Dict] in domain but stored as JSON string in DB.
    Repository handles serialization.
    """
    status: str
    extracted_data: List[Dict[str, Any]] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRunExtraction:
    """
    Complete extraction record for a sub-run.

    Note: extracted_data is stored as JSON string in database but represented
    as List[Dict] in domain. Repository handles serialization/deserialization.

    extracted_data format:
    [
        {
            "name": "field_name",
            "description": "field description",
            "bbox": [x1, y1, x2, y2],
            "page": 1,
            "extracted_value": "the extracted text"
        },
        ...
    ]
    """
    id: int
    sub_run_id: int
    status: str
    extracted_data: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
