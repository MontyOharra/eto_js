"""
Field Transformers for Order Management

Pure functions that transform output channel data into order field values.
Each transformer handles a specific OrderFieldDataType.
"""
import logging
from datetime import datetime
from typing import Any, Callable

from shared.types.pending_actions import (
    LocationValue,
    DimObject,
    DatetimeRangeValue,
    DatetimeRangeError,
    OrderFieldDataType,
)

logger = logging.getLogger(__name__)


# Transformer signature: (source_channel_values) -> transformed value
FieldTransformer = Callable[[dict[str, Any]], Any]


def transform_string_field(source_values: dict[str, Any]) -> str | None:
    """Passthrough - returns first non-None value as string."""
    for value in source_values.values():
        if value is not None:
            return str(value)
    return None


def transform_location_field(source_values: dict[str, Any]) -> LocationValue | None:
    """
    Combines address_id + company_name + address channels into LocationValue.

    For pipeline output: address_id is resolved during execution (HTC lookup).
    For HTC data: address_id is already present in the source values.
    """
    address_id = None
    company_name = None
    address = None

    for key, value in source_values.items():
        if value is None:
            continue
        if "address_id" in key:
            # Convert to int if it's a float (HTC uses float for IDs)
            address_id = int(value) if value else None
        elif "company_name" in key:
            company_name = value
        elif "address" in key:
            address = value

    if not company_name and not address:
        return None

    return LocationValue(
        address_id=address_id,
        name=company_name or "",
        address=address or "",
    )


def transform_dims_field(source_values: dict[str, Any]) -> list[DimObject] | None:
    """Parses dims and calculates dim_weight for each entry."""
    import json as json_module

    raw_dims = source_values.get("dims")
    if not raw_dims:
        return None

    # Handle JSON string (from HTC database) or list (from pipeline output)
    if isinstance(raw_dims, str):
        try:
            raw_dims = json_module.loads(raw_dims)
        except json_module.JSONDecodeError:
            logger.warning(f"Failed to parse dims JSON: {raw_dims}")
            return None

    if not isinstance(raw_dims, list):
        return None

    result = []
    for dim in raw_dims:
        try:
            # Use existing dim_weight if provided, otherwise calculate
            dim_weight = dim.get("dim_weight")
            if dim_weight is None:
                dim_weight = (dim["length"] * dim["width"] * dim["height"]) / 144

            # Round dim_weight to 3 decimal places to avoid floating point issues
            dim_weight = round(dim_weight, 3)

            result.append(DimObject(
                length=dim["length"],
                width=dim["width"],
                height=dim["height"],
                qty=dim["qty"],
                weight=dim["weight"],
                dim_weight=dim_weight,
            ))
        except (KeyError, TypeError) as e:
            logger.warning(f"Invalid dims entry, skipping: {dim} - {e}")
            continue

    return result if result else None


# Common datetime formats to try when parsing
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",    # 2024-01-15 09:00:00
    "%Y-%m-%d %H:%M",       # 2024-01-15 09:00
    "%Y-%m-%dT%H:%M:%S",    # ISO format
    "%Y-%m-%dT%H:%M",       # ISO format without seconds
    "%m/%d/%Y %H:%M:%S",    # US format
    "%m/%d/%Y %H:%M",       # US format
    "%d/%m/%Y %H:%M:%S",    # EU format
    "%d/%m/%Y %H:%M",       # EU format
]


def _parse_datetime(value: str) -> datetime | None:
    """Try to parse a datetime string using common formats."""
    if not value:
        return None

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse datetime: {value}")
    return None


def transform_datetime_range_field(source_values: dict[str, Any]) -> DatetimeRangeValue | None:
    """
    Transforms two datetime values into a DatetimeRangeValue.

    Expects source_values with keys ending in '_start' and '_end'.
    Validates that both datetimes are on the same date.

    Raises:
        DatetimeRangeError: If the dates don't match
    """
    start_value = None
    end_value = None

    # Find the start and end values
    for key, value in source_values.items():
        if value is None:
            continue
        if key.endswith("_start"):
            start_value = str(value)
        elif key.endswith("_end"):
            end_value = str(value)

    # Need at least one value
    if not start_value and not end_value:
        return None

    # Parse the datetime values
    start_dt = _parse_datetime(start_value) if start_value else None
    end_dt = _parse_datetime(end_value) if end_value else None

    # If only one is provided, we can't validate or create a proper range
    if start_dt and not end_dt:
        logger.warning(f"Only start datetime provided: {start_value}")
        return DatetimeRangeValue(
            date=start_dt.strftime("%Y-%m-%d"),
            time_start=start_dt.strftime("%H:%M"),
            time_end="",  # Unknown
        )

    if end_dt and not start_dt:
        logger.warning(f"Only end datetime provided: {end_value}")
        return DatetimeRangeValue(
            date=end_dt.strftime("%Y-%m-%d"),
            time_start="",  # Unknown
            time_end=end_dt.strftime("%H:%M"),
        )

    # Both provided - validate dates match
    if start_dt.date() != end_dt.date():
        raise DatetimeRangeError(
            f"Start and end datetimes have different dates: "
            f"{start_dt.date()} vs {end_dt.date()}"
        )

    return DatetimeRangeValue(
        date=start_dt.strftime("%Y-%m-%d"),
        time_start=start_dt.strftime("%H:%M"),
        time_end=end_dt.strftime("%H:%M"),
    )


# Registry: each data_type maps to its transformer
FIELD_TRANSFORMERS: dict[OrderFieldDataType, FieldTransformer] = {
    "string": transform_string_field,
    "location": transform_location_field,
    "dims": transform_dims_field,
    "datetime_range": transform_datetime_range_field,
}


def transform_htc_values_to_order_fields(htc_values: dict[str, Any]) -> dict[str, Any]:
    """
    Transform raw HTC field values into our ORDER_FIELDS structure.

    Maps HTC raw fields to combined fields:
    - pickup_company_name + pickup_address → pickup_location
    - pickup_time_start + pickup_time_end → pickup_datetime
    - delivery_company_name + delivery_address → delivery_location
    - delivery_time_start + delivery_time_end → delivery_datetime
    - etc.

    Args:
        htc_values: Dict from asdict(HtcOrderFields) with raw field names

    Returns:
        Dict with keys matching ORDER_FIELDS (pickup_location, pickup_datetime, etc.)
    """
    from shared.types.pending_actions import ORDER_FIELDS

    result: dict[str, Any] = {}

    for field_name, field_def in ORDER_FIELDS.items():
        # Gather source channel values from HTC data
        source_values = {}
        for channel in field_def.source_channels:
            if channel in htc_values and htc_values[channel] is not None:
                source_values[channel] = htc_values[channel]

        # Skip if no source values found
        if not source_values:
            continue

        # Apply the appropriate transformer
        transformer = FIELD_TRANSFORMERS.get(field_def.data_type)
        if not transformer:
            logger.warning(f"No transformer for data_type: {field_def.data_type}")
            continue

        try:
            transformed = transformer(source_values)
            if transformed is not None:
                # Convert Pydantic models to dicts for JSON serialization
                if hasattr(transformed, "model_dump"):
                    result[field_name] = transformed.model_dump()
                elif isinstance(transformed, list):
                    result[field_name] = [
                        item.model_dump() if hasattr(item, "model_dump") else item
                        for item in transformed
                    ]
                else:
                    result[field_name] = transformed
        except DatetimeRangeError as e:
            # Log but don't fail - date mismatch in HTC data is unusual but possible
            logger.warning(f"DateTime range error for HTC field {field_name}: {e}")
        except Exception as e:
            logger.warning(f"Error transforming HTC field {field_name}: {e}")

    return result
