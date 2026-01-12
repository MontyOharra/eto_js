"""
Field Transformers for Order Management

Pure functions that transform output channel data into order field values.
Each transformer handles a specific OrderFieldDataType.
"""
import logging
from typing import Any, Callable

from shared.types.pending_actions import (
    LocationValue,
    DimObject,
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
    Combines company_name + address channels into LocationValue.

    Note: address_id resolution (HTC lookup) happens separately during execution,
    not during accumulation.
    """
    company_name = None
    address = None

    for key, value in source_values.items():
        if value is None:
            continue
        if "company_name" in key:
            company_name = value
        elif "address" in key:
            address = value

    if not company_name and not address:
        return None

    return LocationValue(
        address_id=None,  # Resolved during execution
        name=company_name or "",
        address=address or "",
    )


def transform_dims_field(source_values: dict[str, Any]) -> list[DimObject] | None:
    """Parses dims and calculates dim_weight for each entry."""
    raw_dims = source_values.get("dims")
    if not raw_dims or not isinstance(raw_dims, list):
        return None

    result = []
    for dim in raw_dims:
        try:
            dim_weight = (dim["length"] * dim["width"] * dim["height"]) / 144
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


# Registry: each data_type maps to its transformer
FIELD_TRANSFORMERS: dict[OrderFieldDataType, FieldTransformer] = {
    "string": transform_string_field,
    "location": transform_location_field,
    "dims": transform_dims_field,
}
