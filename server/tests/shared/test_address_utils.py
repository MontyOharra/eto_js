"""
Tests for shared.utils.address

These helpers decide whether text usaddress labelled as secondary address info
is a real suite/unit or a customer's order/reference number riding along inside
the address blob. Getting this wrong in either direction is costly:

  - too permissive -> reference numbers land in FavAddrLn2 and every order
    number mints a duplicate HTC address
  - too strict     -> legitimate suites are rejected and valid addresses fail
"""
import pytest

from shared.utils.address import (
    address_has_suspicious_content,
    is_valid_secondary_designator,
    looks_like_reference_value,
    sanitize_secondary_line,
    split_secondary_designator,
)


class TestLooksLikeReferenceValue:
    """Reference/order number detection."""

    @pytest.mark.parametrize("value", [
        "100000",           # long digit run
        "55123",            # 5 digits
        "ORDER 100000",     # keyword tagged
        "REF A-8842",
        "SO123456",         # digit-heavy alphanumeric code
        "INVOICE 4412",
    ])
    def test_detects_reference_values(self, value):
        assert looks_like_reference_value(value) is True

    @pytest.mark.parametrize("value", [
        "400",              # ordinary suite number
        "106D",
        "3B",
        "A",
        "12",
        "",
    ])
    def test_allows_unit_identifiers(self, value):
        assert looks_like_reference_value(value) is False


class TestSplitSecondaryDesignator:
    """Designators are often embedded in the identifier itself."""

    @pytest.mark.parametrize("text,expected", [
        ("STE 400", ("STE", "400")),
        ("# 400", ("#", "400")),
        ("#400", ("#", "400")),
        ("SUITE 106D", ("SUITE", "106D")),
        ("106D", ("", "106D")),
        ("ORDER 55123", ("", "ORDER 55123")),
        ("", ("", "")),
    ])
    def test_split(self, text, expected):
        assert split_secondary_designator(text) == expected


class TestIsValidSecondaryDesignator:
    """Validation of parsed occupancy/subaddress info."""

    @pytest.mark.parametrize("occ_type,occ_id", [
        ("STE", "400"),
        ("#", "400"),
        ("APT", "3B"),
        ("DOCK", "5"),
        ("SUITE", "106D"),
        ("", "106D"),           # bare but plausible unit
        ("", "# 400"),          # usaddress puts the hash in the identifier
        ("BLDG", "A"),
    ])
    def test_accepts_real_units(self, occ_type, occ_id):
        is_valid, reason = is_valid_secondary_designator(occ_type, occ_id)
        assert is_valid is True, reason

    @pytest.mark.parametrize("occ_type,occ_id", [
        ("#", "100000"),        # the reported failure mode
        ("", "# 100000"),
        ("ORDER", "100000"),    # junk designator
        ("", "100000"),
        ("", "ORDER 55123"),
        ("STE", "SO123456"),    # valid designator, reference identifier
    ])
    def test_rejects_reference_numbers(self, occ_type, occ_id):
        is_valid, reason = is_valid_secondary_designator(occ_type, occ_id)
        assert is_valid is False
        assert reason  # must explain itself for the log


class TestSanitizeSecondaryLine:
    """Last line of defence before an address record is written."""

    @pytest.mark.parametrize("line", [
        "STE 400",
        "APT 3B",
        "DOCK 5",
        "UNIT 12",
        "SUITE 106D",
        "BLDG A",
        "# 400",
        "106D",
    ])
    def test_keeps_real_secondary_lines(self, line):
        assert sanitize_secondary_line(line) == line

    @pytest.mark.parametrize("line", [
        "# 100000",
        "ORDER 100000",
        "100000",
        "REF A-8842",
        "SO123456",
    ])
    def test_drops_reference_lines(self, line):
        assert sanitize_secondary_line(line) == ""

    def test_handles_empty(self):
        assert sanitize_secondary_line("") == ""
        assert sanitize_secondary_line("   ") == ""


class TestAddressHasSuspiciousContent:
    """Gate for the proactive LLM cleanup pass."""

    @pytest.mark.parametrize("address", [
        "1234 MAIN ST # 100000 DALLAS TX 75201",
        "1234 MAIN ST ORDER 55123 DALLAS TX 75201",
        "1234 MAIN ST REF A-8842, DALLAS, TX 75201",
        "1234 MAIN ST PO 44821, DALLAS, TX 75201",
        "1234 MAIN ST STE 400 ORDER 55123, DALLAS, TX 75201",
    ])
    def test_flags_blobs_with_reference_content(self, address):
        assert address_has_suspicious_content(address) is True

    @pytest.mark.parametrize("address", [
        "100 INDUSTRIAL BLVD, DALLAS, TX 75201",
        "500 COMMERCE ST STE 400, FORT WORTH, TX 76102",
        "9 W 57TH ST APT 3B, NEW YORK, NY 10019",
        "1234 MAIN ST, DALLAS, TX 75201-1234",
        "1234 MAIN ST PO BOX 55, DALLAS, TX 75201",  # PO BOX is a real address
        "1234 MAIN ST STE 106D, DALLAS, TX 75201",
        "",
    ])
    def test_leaves_clean_addresses_alone(self, address):
        assert address_has_suspicious_content(address) is False
