"""
Output Channel Type definitions for domain objects.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# Type aliases for output channel fields
OutputChannelDataType = Literal["str", "int", "float", "datetime", "list[str]", "list[dim]"]
OutputChannelCategory = Literal["identification", "pickup", "delivery", "cargo", "other"]


class OutputChannelType(BaseModel):
    """Domain object for an output channel type."""
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    label: str
    data_type: OutputChannelDataType
    description: str | None
    is_required: bool
    category: OutputChannelCategory
    created_at: datetime
    updated_at: datetime


class OutputChannelTypeCreate(BaseModel):
    """Data for creating an output channel type."""
    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    data_type: OutputChannelDataType
    is_required: bool
    category: OutputChannelCategory
    description: str | None = None


class OutputChannelTypeUpdate(BaseModel):
    """
    Data for updating an output channel type.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    label: str | None = None
    data_type: OutputChannelDataType | None = None
    description: str | None = None
    is_required: bool | None = None
    category: OutputChannelCategory | None = None
