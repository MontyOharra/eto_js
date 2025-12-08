"""
Output Channel Type Definitions

Static definitions of allowed output channel types for pipeline outputs.
These are synced to the database via the admin sync endpoint.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OutputChannelDefinition:
    """Definition of an output channel type."""
    name: str
    label: str
    data_type: Literal["str", "int", "float", "datetime"]
    is_required: bool
    category: Literal["identification", "pickup", "delivery", "cargo", "other"]
    description: str | None = None


# All available output channel types
# Note: is_required means the output channel MUST be placed in the pipeline (only HAWB is required)
OUTPUT_CHANNEL_DEFINITIONS: list[OutputChannelDefinition] = [
    # Identification
    OutputChannelDefinition(
        name="hawb",
        label="HAWB",
        data_type="str",
        is_required=True,
        category="identification",
        description="House Air Waybill number - primary order identifier"
    ),
    OutputChannelDefinition(
        name="mawb",
        label="MAWB",
        data_type="str",
        is_required=False,
        category="identification",
        description="Master Air Waybill number"
    ),

    # Pickup
    OutputChannelDefinition(
        name="pickup_address",
        label="Pickup Address",
        data_type="str",
        is_required=False,
        category="pickup",
        description="Full pickup address text"
    ),
    OutputChannelDefinition(
        name="pickup_time_start",
        label="Pickup Start",
        data_type="datetime",
        is_required=False,
        category="pickup",
        description="Pickup window start time"
    ),
    OutputChannelDefinition(
        name="pickup_time_end",
        label="Pickup End",
        data_type="datetime",
        is_required=False,
        category="pickup",
        description="Pickup window end time"
    ),
    OutputChannelDefinition(
        name="pickup_notes",
        label="Pickup Notes",
        data_type="str",
        is_required=False,
        category="pickup",
        description="Special instructions for pickup"
    ),

    # Delivery
    OutputChannelDefinition(
        name="delivery_address",
        label="Delivery Address",
        data_type="str",
        is_required=False,
        category="delivery",
        description="Full delivery address text"
    ),
    OutputChannelDefinition(
        name="delivery_time_start",
        label="Delivery Start",
        data_type="datetime",
        is_required=False,
        category="delivery",
        description="Delivery window start time"
    ),
    OutputChannelDefinition(
        name="delivery_time_end",
        label="Delivery End",
        data_type="datetime",
        is_required=False,
        category="delivery",
        description="Delivery window end time"
    ),
    OutputChannelDefinition(
        name="delivery_notes",
        label="Delivery Notes",
        data_type="str",
        is_required=False,
        category="delivery",
        description="Special instructions for delivery"
    ),

    # Cargo
    OutputChannelDefinition(
        name="pieces",
        label="Pieces",
        data_type="int",
        is_required=False,
        category="cargo",
        description="Number of pieces in shipment"
    ),
    OutputChannelDefinition(
        name="weight",
        label="Weight",
        data_type="float",
        is_required=False,
        category="cargo",
        description="Total weight of shipment"
    ),

    # Other
    OutputChannelDefinition(
        name="order_notes",
        label="Order Notes",
        data_type="str",
        is_required=False,
        category="other",
        description="General order notes"
    ),
]


def get_required_channel_names() -> list[str]:
    """Get list of channel names that are required for order creation."""
    return [ch.name for ch in OUTPUT_CHANNEL_DEFINITIONS if ch.is_required]


def get_channel_by_name(name: str) -> OutputChannelDefinition | None:
    """Get a channel definition by name."""
    for ch in OUTPUT_CHANNEL_DEFINITIONS:
        if ch.name == name:
            return ch
    return None
