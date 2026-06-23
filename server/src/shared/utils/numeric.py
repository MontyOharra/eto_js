"""
Numeric parsing utilities.

Robustly convert human/PDF-formatted numeric strings into Python numbers.
Values pulled from PDF form fields routinely carry thousands separators,
currency symbols, and accounting-style negatives (e.g. '$1,259.00' or
'(1,259.00)') that Python's built-in float()/int() cannot parse directly.

These helpers normalize such strings before conversion while leaving
already-valid representations (including scientific notation) untouched.
"""
import re
from typing import Any


def clean_numeric_string(value: str) -> str:
    """
    Normalize a numeric string so it can be parsed by float()/int().

    Handles values commonly found on PDF forms:
      - thousands separators:     '1,259.00'    -> '1259.00'
      - currency symbols / units: '$1,259.00'   -> '1259.00'
      - surrounding whitespace:   '  1,259.00 ' -> '1259.00'
      - accounting negatives:     '(1,259.00)'  -> '-1259.00'

    Assumes US-style formatting (',' = thousands separator, '.' = decimal
    point), consistent with the rest of this codebase.
    """
    cleaned = value.strip()

    # Accounting notation: parentheses denote a negative value
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1].strip()

    # Keep only digits, sign, and separators (drops $, spaces, units, etc.)
    cleaned = re.sub(r"[^\d.,+-]", "", cleaned)

    # Drop thousands-separator commas
    cleaned = cleaned.replace(",", "")

    if negative and cleaned and not cleaned.startswith("-"):
        cleaned = "-" + cleaned

    return cleaned


def to_float(value: Any) -> float:
    """
    Convert a value to float, tolerating formatted numeric strings.

    Non-string values are passed straight to float(). Strings are first tried
    as-is (so valid forms like '1e3' keep working), then normalized via
    clean_numeric_string() as a fallback so values like '$1,259.00' parse.

    Raises:
        ValueError / TypeError: if the value cannot be converted (same as float()).
    """
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return float(clean_numeric_string(value))
    return float(value)


def to_int(value: Any) -> int:
    """
    Convert a value to int, tolerating formatted numeric strings.

    Falls back to parsing through float (so '1,259.00' -> 1259 and '3.9' -> 3),
    mirroring the existing conversion behavior across the transform modules.

    Raises:
        ValueError / TypeError: if the value cannot be converted (same as int()).
    """
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return int(to_float(value))
    return int(value)


def try_float(value: Any, default: float | None = None) -> float | None:
    """float() variant that returns `default` instead of raising on failure."""
    if value is None:
        return default
    try:
        return to_float(value)
    except (ValueError, TypeError):
        return default


def try_int(value: Any, default: int | None = None) -> int | None:
    """int() variant that returns `default` instead of raising on failure."""
    if value is None:
        return default
    try:
        return to_int(value)
    except (ValueError, TypeError):
        return default
