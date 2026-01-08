"""
ETO Sub-Run Extraction Domain Types
Pydantic models representing eto_sub_run_extractions table and related operations
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# =========================
# ETO Sub-Run Extraction Types
# =========================

class EtoSubRunExtractionCreate(BaseModel):
    """
    Data required to create a new extraction for a sub-run.
    Status defaults to "processing" in the database.
    Timing and data fields are set during processing.
    """
    model_config = ConfigDict(frozen=True)

    sub_run_id: int


class EtoSubRunExtractionUpdate(BaseModel):
    """
    Data for updating a sub-run extraction.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)

    Note: extracted_data is list[dict] in domain but stored as JSON string in DB.
    Repository handles serialization.
    """
    status: str | None = None
    extracted_data: list[dict[str, Any]] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EtoSubRunExtraction(BaseModel):
    """
    Complete extraction record for a sub-run.

    Note: extracted_data is stored as JSON string in database but represented
    as list[dict] in domain. Repository handles serialization/deserialization.

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
    model_config = ConfigDict(frozen=True)

    id: int
    sub_run_id: int
    status: str
    extracted_data: list[dict[str, Any]] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
