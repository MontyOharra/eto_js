"""
Tests for HTC Integration Service - Address Resolution

Strategy: Normalized exact match with precision focus
- We normalize for valid variations (abbreviations, punctuation, case)
- We do NOT fuzzy match - if it doesn't match after normalization, no match
- False negatives are OK (create new correct address)
- False positives are NOT OK (avoid matching to bad data)

INSTRUCTIONS FOR COMPLETING THESE TESTS:
1. Query your HTC database to find real addresses for testing
2. Replace PLACEHOLDER values with actual addresses
3. Run: pytest tests/test_htc_integration/test_address_resolution.py -v
"""
import pytest
from typing import Optional

from features.htc_integration.service import HtcIntegrationService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def htc_service(db_services) -> HtcIntegrationService:
    """
    Provide an instance of HtcIntegrationService for testing.

    Requires environment variable:
    TEST_HTC_300_DB_CONNECTION_STRING="Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/path/to/HTC300_Data-01-01.accdb;"
    """
    return HtcIntegrationService(
        data_database_manager=db_services,
        database_name="htc_300_db"
    )


# ============================================================================
# Unit Tests - Normalization (No Database Required)
# ============================================================================

class TestNormalization:
    """Tests for address normalization functions."""

    @pytest.mark.unit
    def test_normalize_component_uppercase(self, htc_service):
        """Test that normalization uppercases text."""
        result = htc_service.normalize_address_component("dallas")
        assert result == "DALLAS"

    @pytest.mark.unit
    def test_normalize_component_removes_periods(self, htc_service):
        """Test that normalization removes periods."""
        result = htc_service.normalize_address_component("N. Main St.")
        assert result == "N MAIN ST"

    @pytest.mark.unit
    def test_normalize_component_collapses_spaces(self, htc_service):
        """Test that normalization collapses multiple spaces."""
        result = htc_service.normalize_address_component("123   Main    St")
        assert result == "123 MAIN ST"

    @pytest.mark.unit
    def test_normalize_component_strips_whitespace(self, htc_service):
        """Test that normalization strips leading/trailing whitespace."""
        result = htc_service.normalize_address_component("  Dallas  ")
        assert result == "DALLAS"

    @pytest.mark.unit
    def test_normalize_component_empty(self, htc_service):
        """Test that empty string returns empty string."""
        assert htc_service.normalize_address_component("") == ""
        assert htc_service.normalize_address_component(None) == ""

    @pytest.mark.unit
    def test_normalize_street_expands_street_types(self, htc_service):
        """Test that street type abbreviations are expanded."""
        result = htc_service.normalize_street_for_matching("123 Main St")
        assert "STREET" in result
        assert "ST" not in result.split()  # ST as a word should be expanded

    @pytest.mark.unit
    def test_normalize_street_expands_directionals(self, htc_service):
        """Test that directional abbreviations are expanded."""
        result = htc_service.normalize_street_for_matching("123 N Main St")
        assert "NORTH" in result

    @pytest.mark.unit
    def test_normalize_street_strips_unit_types(self, htc_service):
        """Test that unit type designators are stripped, keeping only identifier."""
        result = htc_service.normalize_street_for_matching("123 Main St Ste 100")
        # Unit designator "STE" should be stripped, only "100" remains
        assert "SUITE" not in result
        assert "STE" not in result
        assert "100" in result

    @pytest.mark.unit
    def test_normalize_street_combined(self, htc_service):
        """Test full normalization with all components."""
        result = htc_service.normalize_street_for_matching("123 N. Main St. Ste 100")
        # Should be: "123 NORTH MAIN STREET 100" (unit designator stripped)
        assert "NORTH" in result
        assert "STREET" in result
        assert "100" in result
        assert "SUITE" not in result  # Unit designator stripped
        assert "STE" not in result    # Unit designator stripped
        assert "." not in result

    @pytest.mark.unit
    def test_normalize_street_parkway_variations(self, htc_service):
        """Test that pkwy and parkway normalize the same."""
        result1 = htc_service.normalize_street_for_matching("100 Commerce Pkwy")
        result2 = htc_service.normalize_street_for_matching("100 Commerce Parkway")
        assert result1 == result2
        assert "PARKWAY" in result1

    @pytest.mark.unit
    def test_normalize_street_boulevard_variations(self, htc_service):
        """Test that blvd and boulevard normalize the same."""
        result1 = htc_service.normalize_street_for_matching("500 Oak Blvd")
        result2 = htc_service.normalize_street_for_matching("500 Oak Boulevard")
        assert result1 == result2

    @pytest.mark.unit
    def test_normalize_street_preserves_numbers(self, htc_service):
        """Test that suite/unit numbers are preserved."""
        result = htc_service.normalize_street_for_matching("123 Main St #106D")
        assert "106D" in result


# ============================================================================
# Unit Tests - Address Parsing (No Database Required)
# ============================================================================

class TestAddressParsing:
    """Tests for address parsing."""

    @pytest.mark.unit
    def test_parse_basic_address(self, htc_service):
        """Test parsing a simple US address."""
        result = htc_service.parse_address_string("123 Main St, Dallas, TX 75201")

        assert result is not None
        assert result['city'] == "Dallas"
        assert result['state'] == "TX"
        assert result['zip_code'] == "75201"
        assert "123" in result['street']
        assert "Main" in result['street']

    @pytest.mark.unit
    def test_parse_address_with_suite(self, htc_service):
        """Test parsing an address with suite - suite should be in street."""
        result = htc_service.parse_address_string(
            "456 Oak Ave, Suite 200, Houston, TX 77001"
        )

        assert result is not None
        # Suite info should be included in street (matches DB storage)
        assert "Suite" in result['street'] or "200" in result['street']
        assert result['city'] == "Houston"

    @pytest.mark.unit
    def test_parse_address_with_unit_number(self, htc_service):
        """Test parsing address with # unit notation."""
        result = htc_service.parse_address_string(
            "4901 Keller Springs Rd #106D, Dallas, TX 75248"
        )

        assert result is not None
        # Unit should be in street
        assert "106D" in result['street'] or "#106D" in result['street']

    @pytest.mark.unit
    def test_parse_address_with_directional(self, htc_service):
        """Test parsing address with directional prefix."""
        result = htc_service.parse_address_string(
            "100 N Main St, Plano, TX 75074"
        )

        assert result is not None
        assert "N" in result['street'] or "North" in result['street']

    @pytest.mark.unit
    def test_parse_empty_returns_none(self, htc_service):
        """Test that empty address returns None."""
        assert htc_service.parse_address_string("") is None
        assert htc_service.parse_address_string("   ") is None

    @pytest.mark.unit
    def test_parse_incomplete_returns_none(self, htc_service):
        """Test that incomplete address (missing components) returns None."""
        # Missing city/state/zip
        result = htc_service.parse_address_string("123 Main St")
        assert result is None

    @pytest.mark.unit
    def test_parse_preserves_all_street_components(self, htc_service):
        """Test that all street components are captured."""
        result = htc_service.parse_address_string(
            "5651 Alliance Gateway Pkwy, Fort Worth, TX 76177"
        )

        assert result is not None
        assert "5651" in result['street']
        assert "Alliance" in result['street']
        assert "Gateway" in result['street']


# ============================================================================
# Integration Tests - Database Lookup
# ============================================================================

class TestAddressLookup:
    """Integration tests for address database lookup."""

    @pytest.mark.integration
    def test_find_existing_address(self, htc_service):
        """
        Test finding an address that exists in the database.

        TODO: Replace with actual address from your database.
        """
        # PLACEHOLDER: Replace with real data from HTC300_G060_T010 Addresses
        address_id = htc_service.find_address_by_text(
            street="2320 CULLEN ST",  # e.g., "2900 CABELL RD"
            city="FORT WORTH",       # e.g., "IRVING"
            state="TX",     # e.g., "TX"
            zip_code="76107"     # e.g., "75038"
        )

        assert address_id is not None, "Update placeholders with real address data"
        assert isinstance(address_id, float)
        assert address_id > 0

    @pytest.mark.integration
    def test_find_address_case_insensitive(self, htc_service):
        """
        Test that address lookup is case-insensitive.
        DB has: '1075 S. BELTLINE ROAD' in Coppell, TX 75019
        """
        # Lowercase version of address that exists in DB
        address_id = htc_service.find_address_by_text(
            street="1075 s. beltline road",  # DB has "1075 S. BELTLINE ROAD"
            city="coppell",
            state="tx",
            zip_code="75019"
        )

        assert address_id is not None, "Case-insensitive matching should work"

    @pytest.mark.integration
    def test_find_address_abbreviation_expansion(self, htc_service):
        """
        Test that abbreviations match their expanded forms.

        TODO: Find an address with "ST" in DB and search with "STREET".
        """
        # PLACEHOLDER: Address stored as "123 MAIN ST" should match "123 Main Street"
        address_id = htc_service.find_address_by_text(
            street="1075 S beltline road",  # e.g., "2900 CABELL ROAD"
            city="coppell",
            state="tx",
            zip_code="75019"
        )

        # If your DB has "RD" and you search "ROAD", should still match
        # This test validates abbreviation expansion works
        pass  # Update assertion based on your test data

    @pytest.mark.integration
    def test_find_nonexistent_address_returns_none(self, htc_service):
        """Test that a fake address returns None."""
        address_id = htc_service.find_address_by_text(
            street="99999 FAKE STREET THAT DOES NOT EXIST",
            city="NOWHERE",
            state="ZZ",
            zip_code="00000"
        )

        assert address_id is None

    @pytest.mark.integration
    def test_find_address_wrong_zip_returns_none(self, htc_service):
        """
        Test that correct street in wrong zip returns None.

        TODO: Use real street but wrong zip code.
        """
        # PLACEHOLDER: Real street but wrong zip
        address_id = htc_service.find_address_by_text(
            street="1434 PAtton Place",
            city="Southlake",
            state="TX",
            zip_code="99999"  # Wrong zip
        )

        assert address_id is None, "Wrong zip should not match"

    @pytest.mark.integration
    def test_find_address_partial_street_no_match(self, htc_service):
        """
        Test that partial/incomplete street does NOT match.
        This validates precision-over-recall strategy.

        Example: "2831 south walton walker bl" should NOT match
                 "2831 S WALTON WALKER BLVD"
        """
        # This address is intentionally incomplete (missing "VD" from "BLVD")
        address_id = htc_service.find_address_by_text(
            street="2831 SOUTH WALTON WALKER BL",  # Missing "VD"
            city="DALLAS",
            state="TX",
            zip_code="75211"
        )

        # Should NOT match - we don't fuzzy match
        assert address_id is None, "Incomplete address should not match"


# ============================================================================
# Integration Tests - Full Address String Lookup
# ============================================================================

class TestFindAddressId:
    """Integration tests for the main find_address_id entry point."""

    @pytest.mark.integration
    def test_find_address_id_existing(self, htc_service):
        """
        Test finding address ID from full address string.

        TODO: Replace with actual address from your database.
        """
        # PLACEHOLDER: Full address string that exists in your DB
        address_id = htc_service.find_address_id(
            "2301 neiman marcus pkwy, longview, tx 75602"  # e.g., "2900 Cabell Rd, Irving, TX 75038"
        )

        assert address_id is not None, "Update placeholder with real address"
        assert isinstance(address_id, float)

    @pytest.mark.integration
    def test_find_address_id_nonexistent(self, htc_service):
        """Test that fake address returns None."""
        address_id = htc_service.find_address_id(
            "99999 Fake Street, Nowhere City, ZZ 00000"
        )

        assert address_id is None

    @pytest.mark.integration
    def test_find_address_id_with_suite(self, htc_service):
        """
        Test finding address with suite number.

        TODO: Replace with address that has suite in database.
        """
        # PLACEHOLDER: Address with suite that exists in DB
        address_id = htc_service.find_address_id(
            "4901 KELLER SPRINGS #106D, Addison, TX 75001"  # e.g., "4901 Keller Springs Rd #106D, Dallas, TX 75248"
        )

        # Update based on whether you have such an address
        assert address_id >0

    @pytest.mark.integration
    def test_find_address_id_bad_data_no_match(self, htc_service):
        """
        Test that bad/incomplete DB entries are not matched.

        If DB has "2214 Paddock Way Drive Suit" (incomplete),
        searching for "2214 Paddock Way Dr, Suite 100, Irving, TX 75038"
        should NOT match (they're different).
        """
        # Good address that differs from bad DB entry
        address_id = htc_service.find_address_id(
            "2214 Paddock Way Dr, Suite 100, Irving, TX 75038"
        )
        
        assert address_id is None

        # If DB has incomplete entry, this should return None
        # (which is correct - we'll create a new correct entry)
        # This is the "precision over recall" strategy in action

    @pytest.mark.integration
    def test_find_address_id_unparseable_returns_none(self, htc_service):
        """Test that unparseable garbage returns None gracefully."""
        address_id = htc_service.find_address_id(
            "This is not a valid address just random text"
        )

        assert address_id is None


# ============================================================================
# Parametrized Tests - Normalization Equivalence
# ============================================================================

class TestNormalizationEquivalence:
    """Test that various address formats normalize to the same value."""

    @pytest.mark.unit
    @pytest.mark.parametrize("input_street,expected_contains", [
        ("123 Main St", "STREET"),
        ("123 Main Street", "STREET"),
        ("123 Main ST", "STREET"),
        ("123 Main ST.", "STREET"),
    ])
    def test_street_type_equivalence(self, htc_service, input_street, expected_contains):
        """Test that ST, Street, ST. all normalize the same."""
        result = htc_service.normalize_street_for_matching(input_street)
        assert expected_contains in result

    @pytest.mark.unit
    @pytest.mark.parametrize("input_street,expected_contains", [
        ("100 N Main St", "NORTH"),
        ("100 North Main St", "NORTH"),
        ("100 N. Main St", "NORTH"),
    ])
    def test_directional_equivalence(self, htc_service, input_street, expected_contains):
        """Test that N, North, N. all normalize the same."""
        result = htc_service.normalize_street_for_matching(input_street)
        assert expected_contains in result

    @pytest.mark.unit
    @pytest.mark.parametrize("input_street", [
        "500 Commerce Pkwy",
        "500 Commerce Parkway",
        "500 Commerce PKWY",
        "500 COMMERCE PARKWAY",
        "500 commerce pkwy",
    ])
    def test_parkway_all_equivalent(self, htc_service, input_street):
        """Test that all parkway variations normalize identically."""
        result = htc_service.normalize_street_for_matching(input_street)
        assert result == "500 COMMERCE PARKWAY"


# ============================================================================
# Instructions
# ============================================================================

"""
TO COMPLETE THESE TESTS:

1. Query your database for test addresses:

   SELECT FavID, FavAddrLn1, FavAddrLn2, FavCity, FavState, FavZip
   FROM [HTC300_G060_T010 Addresses]
   WHERE FavActive = 1
   ORDER BY FavID
   LIMIT 20

2. Pick 2-3 addresses to use:
   - One simple address (no suite)
   - One address with suite/unit in FavAddrLn1

3. Replace PLACEHOLDER values in integration tests with real data.

4. Run tests:
   # Unit tests only (no database needed)
   pytest tests/test_htc_integration/test_address_resolution.py -v -k unit

   # Integration tests (needs database)
   pytest tests/test_htc_integration/test_address_resolution.py -v -k integration

   # All tests
   pytest tests/test_htc_integration/test_address_resolution.py -v

5. Expected behavior:
   - Unit tests should all pass without database
   - Integration tests with PLACEHOLDERs will fail until updated
   - Incomplete/bad addresses should NOT match (precision strategy)
"""
