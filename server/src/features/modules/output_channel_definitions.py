"""
Output Channel Type Definitions

Static definitions of allowed output channel types for pipeline outputs.
These define what data can flow out of pipelines (hawb, pickup_address, etc.)
and are synced to the database via the admin sync endpoint.
"""
from shared.types.output_channels import OutputChannelTypeCreate


# All available output channel types
# Note: is_required means the output channel MUST be placed in the pipeline (only HAWB is required)
OUTPUT_CHANNEL_DEFINITIONS: list[OutputChannelTypeCreate] = [
    # Identification
    OutputChannelTypeCreate(
        name="hawb",
        label="HAWB",
        data_type="str",
        is_required=True,
        category="identification",
        description="House Air Waybill number - primary order identifier",
    ),
    OutputChannelTypeCreate(
        name="hawb_list",
        label="HAWB List",
        data_type="list[str]",
        is_required=False,
        category="identification",
        description="List of House Air Waybill numbers - for multi-HAWB orders from single PDF",
    ),
    OutputChannelTypeCreate(
        name="mawb",
        label="MAWB",
        data_type="str",
        is_required=False,
        category="identification",
        description="Master Air Waybill number",
    ),

    # Pickup
    OutputChannelTypeCreate(
        name="pickup_company_name",
        label="Pickup Company",
        data_type="str",
        is_required=False,
        category="pickup",
        description="Company name at pickup location",
    ),
    OutputChannelTypeCreate(
        name="pickup_address",
        label="Pickup Address",
        data_type="str",
        is_required=False,
        category="pickup",
        description="Full pickup address text",
    ),
    OutputChannelTypeCreate(
        name="pickup_time_start",
        label="Pickup Start",
        data_type="datetime",
        is_required=False,
        category="pickup",
        description="Pickup window start time",
    ),
    OutputChannelTypeCreate(
        name="pickup_time_end",
        label="Pickup End",
        data_type="datetime",
        is_required=False,
        category="pickup",
        description="Pickup window end time",
    ),
    OutputChannelTypeCreate(
        name="pickup_notes",
        label="Pickup Notes",
        data_type="str",
        is_required=False,
        category="pickup",
        description="Special instructions for pickup",
    ),

    # Delivery
    OutputChannelTypeCreate(
        name="delivery_company_name",
        label="Delivery Company",
        data_type="str",
        is_required=False,
        category="delivery",
        description="Company name at delivery location",
    ),
    OutputChannelTypeCreate(
        name="delivery_address",
        label="Delivery Address",
        data_type="str",
        is_required=False,
        category="delivery",
        description="Full delivery address text",
    ),
    OutputChannelTypeCreate(
        name="delivery_time_start",
        label="Delivery Start",
        data_type="datetime",
        is_required=False,
        category="delivery",
        description="Delivery window start time",
    ),
    OutputChannelTypeCreate(
        name="delivery_time_end",
        label="Delivery End",
        data_type="datetime",
        is_required=False,
        category="delivery",
        description="Delivery window end time",
    ),
    OutputChannelTypeCreate(
        name="delivery_notes",
        label="Delivery Notes",
        data_type="str",
        is_required=False,
        category="delivery",
        description="Special instructions for delivery",
    ),

    # Cargo
    OutputChannelTypeCreate(
        name="pieces",
        label="Pieces",
        data_type="int",
        is_required=False,
        category="cargo",
        description="Number of pieces in shipment",
    ),
    OutputChannelTypeCreate(
        name="weight",
        label="Weight",
        data_type="float",
        is_required=False,
        category="cargo",
        description="Total weight of shipment",
    ),
    OutputChannelTypeCreate(
        name="dims",
        label="Dimensions",
        data_type="list[dim]",
        is_required=False,
        category="cargo",
        description="List of dimension sets with height, length, width, qty, and weight",
    ),

    # Other
    OutputChannelTypeCreate(
        name="order_notes",
        label="Order Notes",
        data_type="str",
        is_required=False,
        category="other",
        description="General order notes",
    ),
]


def get_required_channel_names() -> list[str]:
    """Get list of channel names that are required for order creation."""
    return [ch.name for ch in OUTPUT_CHANNEL_DEFINITIONS if ch.is_required]


def get_channel_by_name(name: str) -> OutputChannelTypeCreate | None:
    """Get a channel definition by name."""
    for ch in OUTPUT_CHANNEL_DEFINITIONS:
        if ch.name == name:
            return ch
    return None


def get_all_channel_names() -> list[str]:
    """Get list of all channel names."""
    return [ch.name for ch in OUTPUT_CHANNEL_DEFINITIONS]
