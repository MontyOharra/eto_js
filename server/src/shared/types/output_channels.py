"""
Output Channel Type definitions for domain objects.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class OutputChannelType:
    """Domain object for an output channel type."""
    id: int
    name: str
    label: str
    data_type: str
    description: str | None
    is_required: bool
    category: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class OutputChannelTypeCreate:
    """Data for creating an output channel type."""
    name: str
    label: str
    data_type: Literal["str", "int", "float", "datetime"]
    is_required: bool
    category: Literal["identification", "pickup", "delivery", "cargo", "other"]
    description: str | None = None


@dataclass(frozen=True)
class OutputChannelTypeUpdate:
    """Data for updating an output channel type."""
    label: str | None = None
    data_type: str | None = None
    description: str | None = None
    is_required: bool | None = None
    category: str | None = None
