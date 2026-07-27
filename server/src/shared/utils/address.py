"""
Address text utilities.

Customer-supplied address blobs routinely carry non-address content inline -
order numbers, reference codes, PO numbers, tracking numbers - e.g.

    "1234 MAIN ST # 100000 DALLAS TX 75201"

usaddress happily tags "100000" as an OccupancyIdentifier, so the address
"parses" cleanly and the junk rides along into address line 2. Every distinct
order number then looks like a distinct address, which floods HTC with
duplicate address records that differ only by line 2.

These helpers identify that content so callers can reject it (forcing the LLM
cleanup path) or strip it before an address is looked up or created.
"""
import re


# Secondary-unit designators that denote a genuine part of a physical address.
# Anything usaddress labels as occupancy/subaddress info outside this set is
# treated as non-address text.
VALID_OCCUPANCY_TYPES = {
    '#', 'STE', 'SUITE', 'APT', 'APARTMENT', 'UNIT', 'FL', 'FLR', 'FLOOR',
    'RM', 'ROOM', 'DEPT', 'DEPARTMENT', 'BLDG', 'BUILDING', 'DOCK', 'DOOR',
    'GATE', 'BAY', 'RAMP', 'LOT', 'SPC', 'SPACE', 'STOP', 'TRLR', 'TRAILER',
    'BOX', 'PMB', 'PIER', 'SLIP', 'WING', 'HANGAR', 'HNGR', 'BSMT', 'BASEMENT',
    'PH', 'PENTHOUSE', 'LBBY', 'LOBBY', 'OFC', 'OFFICE', 'FRNT', 'FRONT',
    'REAR', 'SIDE', 'LOWR', 'LOWER', 'UPPR', 'UPPER', 'WHSE', 'WAREHOUSE',
}

# Tokens that mark a value as a business reference rather than an address.
# Deliberately excludes bare "PO" (see _has_reference_marker) so that
# "PO BOX 123" is not mistaken for a purchase-order number.
REFERENCE_KEYWORDS = {
    'ORDER', 'ORDERS', 'ORD', 'REF', 'REFERENCE', 'INV', 'INVOICE',
    'TRACKING', 'TRACK', 'JOB', 'WO', 'BOL', 'PRO', 'LOAD', 'ACCT',
    'ACCOUNT', 'HAWB', 'MAWB', 'AWB', 'TICKET', 'CONFIRMATION', 'CONF',
    'SHIPMENT', 'MANIFEST', 'RELEASE', 'SEAL',
}

# A digit run this long is a reference number, not a unit number.
_MIN_REFERENCE_DIGITS = 5

# A digit run this long anywhere in a free-text address is suspicious
# (street numbers and ZIPs are shorter).
_MIN_SUSPICIOUS_DIGITS = 6

_WORD_SPLIT_RE = re.compile(r"[^A-Z0-9]+")
_UNIT_IDENTIFIER_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]*$")
_HASH_NUMBER_RE = re.compile(r"#\s*\d{4,}")
_LONG_DIGIT_RUN_RE = re.compile(rf"\d{{{_MIN_SUSPICIOUS_DIGITS},}}")
_PO_NOT_BOX_RE = re.compile(r"\bP\.?\s?O\.?\s*#|\bPO\b(?!\s*BOX)")


def _words(text: str) -> list[str]:
    """Split text into uppercase alphanumeric words."""
    return [w for w in _WORD_SPLIT_RE.split(text.upper()) if w]


def _has_reference_marker(text: str) -> bool:
    """True if the text contains a keyword marking it as a business reference."""
    upper = text.upper()
    if any(word in REFERENCE_KEYWORDS for word in _words(upper)):
        return True
    return bool(_PO_NOT_BOX_RE.search(upper))


def looks_like_reference_value(value: str) -> bool:
    """
    True if a value looks like an order/reference number rather than a unit number.

    Catches:
      - keyword-tagged values:  "ORDER 100000", "REF A-8842"
      - long digit runs:        "100000"  (real suites are rarely 5+ digits)
      - digit-heavy codes:      "SO123456"
    """
    if not value:
        return False

    norm = value.upper().strip()

    if _has_reference_marker(norm):
        return True

    compact = re.sub(r"[\s\-]", "", norm)
    if compact.isdigit() and len(compact) >= _MIN_REFERENCE_DIGITS:
        return True

    # Alphanumeric codes: long and digit-heavy (e.g. "SO123456")
    if (
        len(compact) >= 6
        and any(c.isalpha() for c in compact)
        and sum(c.isdigit() for c in compact) >= 4
    ):
        return True

    return False


def _looks_like_unit_identifier(value: str) -> bool:
    """True if a bare (undesignated) value plausibly identifies a unit, e.g. "106D"."""
    norm = value.upper().strip()
    return len(norm) <= 6 and bool(_UNIT_IDENTIFIER_RE.match(norm))


def split_secondary_designator(text: str) -> tuple[str, str]:
    """
    Split a secondary address line into its designator and identifier.

    usaddress often returns the designator inside the identifier itself
    (e.g. OccupancyIdentifier="# 400" with no OccupancyType), so callers
    cannot rely on the labels alone.

    Returns:
        Tuple of (designator, identifier); designator is "" when the text
        carries no recognizable one.
    """
    stripped = (text or '').strip()
    if not stripped:
        return '', ''

    # "#400" / "# 400" - the hash may be attached to the identifier
    if stripped.startswith('#'):
        return '#', stripped[1:].strip()

    parts = stripped.split()
    if parts[0].upper().rstrip('.') in VALID_OCCUPANCY_TYPES:
        return parts[0], ' '.join(parts[1:])

    return '', stripped


def is_valid_secondary_designator(
    occupancy_type: str,
    occupancy_identifier: str,
) -> tuple[bool, str]:
    """
    Validate parsed secondary-address info (suite/unit/dock and its identifier).

    Args:
        occupancy_type: The designator usaddress found (e.g. "STE", "#"), may be empty
        occupancy_identifier: The identifier that follows it (e.g. "100"), may be empty

    Returns:
        Tuple of (is_valid, reason). `reason` is empty when valid, and describes
        the rejection otherwise (suitable for logging).
    """
    occ_type = (occupancy_type or '').upper().strip().rstrip('.')
    occ_id = (occupancy_identifier or '').strip()

    # The identifier may carry its own designator when usaddress didn't label one
    if not occ_type:
        designator, occ_id = split_secondary_designator(occ_id)
        occ_type = designator.upper().rstrip('.')

    if occ_type and occ_type not in VALID_OCCUPANCY_TYPES:
        return False, f"unrecognized unit designator '{occ_type}'"

    if occ_id and looks_like_reference_value(occ_id):
        return False, f"'{occ_id}' looks like a reference/order number, not a unit number"

    if occ_id and not occ_type and not _looks_like_unit_identifier(occ_id):
        return False, f"bare secondary value '{occ_id}' is not a recognizable unit number"

    return True, ""


def sanitize_secondary_line(addr_ln2: str) -> str:
    """
    Return the secondary address line if it is genuine, or "" if it is junk.

    Used as a last line of defence before an address is looked up or written to
    HTC, so that reference numbers never become part of an address record.
    """
    if not addr_ln2 or not addr_ln2.strip():
        return ''

    designator, identifier = split_secondary_designator(addr_ln2)
    is_valid, _reason = is_valid_secondary_designator(designator, identifier)
    return addr_ln2 if is_valid else ''


def address_has_suspicious_content(address: str) -> bool:
    """
    True if a raw address blob likely contains non-address text.

    Used to decide whether to pre-clean an address with the LLM *before*
    parsing, since usaddress can silently absorb junk into components that
    would otherwise look like a valid parse.
    """
    if not address:
        return False

    upper = address.upper()

    if _has_reference_marker(upper):
        return True

    # "#100000" style reference numbers
    if _HASH_NUMBER_RE.search(upper):
        return True

    # Long digit runs - street numbers and ZIPs are shorter than this
    if _LONG_DIGIT_RUN_RE.search(upper):
        return True

    return False
