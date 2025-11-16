"""
Tests for Fuzzy Database Lookup Transform Module

INSTRUCTIONS FOR COMPLETING THESE TESTS:
1. Examine your test databases in tests/test_databases/
2. Identify tables and columns suitable for fuzzy matching tests
3. Replace the PLACEHOLDER values with actual data from your databases
4. Run: make test TEST=tests/test_modules/transform/test_fuzzy_database_lookup.py
"""
import pytest
from typing import Any

from pipeline_modules.transform.fuzzy_database_lookup import FuzzyDatabaseLookup, FuzzyDatabaseLookupConfig
from shared.types.pipelines import ModuleExecutionContext, NodeInstance


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def lookup_module():
    """Provide an instance of FuzzyDatabaseLookup for testing"""
    return FuzzyDatabaseLookup()


def create_node_instance(
    node_id: str,
    type: str = "str",
    name: str = "node",
    position_index: int = 0,
    group_index: int = 0
) -> NodeInstance:
    """Helper to create NodeInstance objects for testing"""
    return NodeInstance(
        node_id=node_id,
        type=type,
        name=name,
        position_index=position_index,
        group_index=group_index
    )


def create_execution_context(module_instance_id: str = "test_module_1") -> ModuleExecutionContext:
    """
    Helper to create ModuleExecutionContext for testing

    Returns context with:
    - 1 input: search_text (str)
    - 3 outputs: matched_value (str), confidence (float), match_found (bool)
    """
    inputs = [create_node_instance("input_1", type="str", name="search_text")]

    outputs = [
        create_node_instance("output_1", type="str", name="matched_value"),
        create_node_instance("output_2", type="float", name="confidence"),
        create_node_instance("output_3", type="bool", name="match_found")
    ]

    return ModuleExecutionContext(
        inputs=inputs,
        outputs=outputs,
        module_instance_id=module_instance_id
    )


# ============================================================================
# Database Integration Tests
# ============================================================================

@pytest.mark.integration
def test_exact_match(lookup_module, db_services):
    """
    Test exact match returns 100% confidence

    TODO: Replace placeholders with actual test data
    """
    # PLACEHOLDER: Update these values based on your test database
    config = FuzzyDatabaseLookupConfig(
        database="htc300_data_01_01",  # e.g., "htc_300_db"
        table="HTC300_G060_T010 Addresses",        # e.g., "Addresses"
        search_column="FavLocnName", # e.g., "AddressText"
        return_column="FavLocnName", # e.g., "AddressText" or "AddressID"
        algorithm="ratio",
        min_confidence=0.0
    )

    context = create_execution_context()

    # PLACEHOLDER: Replace with actual value that exists in your database
    inputs = {"input_1": "FORWARD AIR"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_3"] is True  # match_found
    assert result["output_2"] == 100.0  # confidence (exact match)
    assert result["output_1"] == "FORWARD AIR"


@pytest.mark.integration
def test_fuzzy_match_high_confidence(lookup_module, db_services):
    """
    Test fuzzy match with high confidence (e.g., typo or slight variation)

    TODO: Replace placeholders with actual test data
    Example: "123 Main Street" vs "123 Main St"
    """
    config = FuzzyDatabaseLookupConfig(
        database="htc300_data_01_01",  # e.g., "htc_300_db"
        table="HTC300_G060_T010 Addresses",        # e.g., "Addresses"
        search_column="FavLocnName", # e.g., "AddressText"
        return_column="FavLocnName", # e.g., "AddressText" or "AddressID"
        algorithm="ratio",
        min_confidence=0.0
    )

    context = create_execution_context()

    # PLACEHOLDER: Search text with slight variation from database value
    inputs = {"input_1": "Forward Air, Inc"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_3"] is True  # match_found
    assert result["output_2"] >= 80.0  # confidence above threshold
    assert result["output_1"] == "FORWARD AIR"


@pytest.mark.integration
def test_no_match_below_threshold(lookup_module, db_services):
    """
    Test that poor matches below threshold return None

    TODO: Replace placeholders with actual test data
    """
    config = FuzzyDatabaseLookupConfig(
        database="htc300_data_01_01",  # e.g., "htc_300_db"
        table="HTC300_G060_T010 Addresses",        # e.g., "Addresses"
        search_column="FavLocnName", # e.g., "AddressText"
        return_column="FavLocnName", # e.g., "AddressText" or "AddressID"
        algorithm="partial_ratio",
        min_confidence=10.0
    )

    context = create_execution_context()

    # PLACEHOLDER: Search text that doesn't match well (different address/value)
    inputs = {"input_1": "asdkjldasljkadsjkldask123123312123123;l!ljadsjlkdasjklas"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    print("\n" + "="*60)
    print(f"Search Text:    {inputs['input_1']}")
    print(f"Matched Value:  {result['output_1']}")
    print(f"Confidence:     {result['output_2']}")
    print(f"Match Found:    {result['output_3']}")
    print("="*60 + "\n")

    # Assert
    assert result["output_3"] is False  # match_found = False
    assert result["output_2"] < 90.0    # confidence below threshold
    assert result["output_1"] is None    # matched_value is None


@pytest.mark.integration
def test_case_insensitive_matching(lookup_module, db_services):
    """
    Test case-insensitive matching (default behavior)

    TODO: Replace placeholders with actual test data
    """
    config = FuzzyDatabaseLookupConfig(
        database="htc300_data_01_01",  # e.g., "htc_300_db"
        table="HTC300_G060_T010 Addresses",        # e.g., "Addresses"
        search_column="FavLocnName", # e.g., "AddressText"
        return_column="FavLocnName", # e.g., "AddressText" or "AddressID"
        algorithm="ratio",
        min_confidence=0.0
    )
    context = create_execution_context()

    # PLACEHOLDER: Same value but different case (e.g., "MAIN STREET" vs "main street")
    inputs = {"input_1": "forward air"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_3"] is True  # match_found
    assert result["output_2"] == 100.0  # Should be exact match (case ignored)


@pytest.mark.integration
def test_where_clause_filter(lookup_module, db_services):
    """
    Test using WHERE clause to filter candidates

    TODO: Replace placeholders with actual test data
    Example: Only search active addresses, specific region, etc.
    """
    config = FuzzyDatabaseLookupConfig(
        database="PLACEHOLDER_DATABASE_NAME",
        table="PLACEHOLDER_TABLE_NAME",
        search_column="PLACEHOLDER_SEARCH_COL",
        return_column="PLACEHOLDER_RETURN_COL",
        algorithm="ratio",
        where_clause="PLACEHOLDER_WHERE_CONDITION"  # e.g., "Active = 1" or "Region = 'East'"
    )

    context = create_execution_context()
    inputs = {"input_1": "PLACEHOLDER_VALUE"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    # TODO: Add assertions based on your test data
    assert result["output_3"] is not None  # Replace with actual assertion


@pytest.mark.integration
def test_return_different_column(lookup_module, db_services):
    """
    Test searching on one column but returning another

    TODO: Replace placeholders with actual test data
    Example: Search by address text, return address ID
    """
    config = FuzzyDatabaseLookupConfig(
        database="PLACEHOLDER_DATABASE_NAME",
        table="PLACEHOLDER_TABLE_NAME",
        search_column="PLACEHOLDER_SEARCH_COL",   # e.g., "AddressText"
        return_column="PLACEHOLDER_DIFFERENT_COL", # e.g., "AddressID"
        algorithm="ratio"
    )

    context = create_execution_context()
    inputs = {"input_1": "PLACEHOLDER_SEARCH_VALUE"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_3"] is True
    # PLACEHOLDER: Verify return_column value is correct type/format
    assert result["output_1"] == "PLACEHOLDER_EXPECTED_ID_OR_VALUE"


@pytest.mark.integration
@pytest.mark.parametrize("algorithm", [
    "ratio",
    "partial_ratio",
    "token_sort_ratio",
    "token_set_ratio"
])
def test_different_algorithms(lookup_module, db_services, algorithm):
    """
    Test different fuzzy matching algorithms

    TODO: Replace placeholders with actual test data
    """
    config = FuzzyDatabaseLookupConfig(
        database="PLACEHOLDER_DATABASE_NAME",
        table="PLACEHOLDER_TABLE_NAME",
        search_column="PLACEHOLDER_SEARCH_COL",
        return_column="PLACEHOLDER_RETURN_COL",
        algorithm=algorithm,
        min_confidence=50.0
    )

    context = create_execution_context()
    inputs = {"input_1": "PLACEHOLDER_VALUE"}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert - should work with any algorithm
    assert "output_1" in result
    assert "output_2" in result
    assert "output_3" in result


# ============================================================================
# Unit Tests (No Database Required)
# ============================================================================

@pytest.mark.unit
def test_empty_input(lookup_module, db_services):
    """Test that empty input returns no match"""
    config = FuzzyDatabaseLookupConfig(
        database="any_db",
        table="any_table",
        search_column="col1",
        return_column="col2"
    )

    context = create_execution_context()
    inputs = {"input_1": ""}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_1"] is None
    assert result["output_2"] == 0.0
    assert result["output_3"] is False


@pytest.mark.unit
def test_none_input(lookup_module, db_services):
    """Test that None input returns no match"""
    config = FuzzyDatabaseLookupConfig(
        database="any_db",
        table="any_table",
        search_column="col1",
        return_column="col2"
    )

    context = create_execution_context()
    inputs = {"input_1": None}

    # Act
    result = lookup_module.run(inputs, config, context, services=db_services)

    # Assert
    assert result["output_1"] is None
    assert result["output_2"] == 0.0
    assert result["output_3"] is False


@pytest.mark.unit
def test_module_metadata():
    """Test that module class metadata is correctly defined"""
    assert FuzzyDatabaseLookup.id == "fuzzy_database_lookup"
    assert FuzzyDatabaseLookup.version == "1.0.0"
    assert FuzzyDatabaseLookup.title == "Fuzzy Database Lookup"
    assert FuzzyDatabaseLookup.category == "Database"


@pytest.mark.unit
def test_config_model():
    """Test configuration validation"""
    # Valid config
    config = FuzzyDatabaseLookupConfig(
        database="test_db",
        table="test_table",
        search_column="col1",
        return_column="col2",
        algorithm="ratio",
        min_confidence=75.0
    )

    assert config.database == "test_db"
    assert config.algorithm == "ratio"
    assert config.min_confidence == 75.0
    assert config.case_sensitive is False  # default


@pytest.mark.unit
def test_io_shape_definition():
    """Test that I/O shape is correctly defined in metadata"""
    meta = FuzzyDatabaseLookup.meta()

    # Assert - Input shape
    assert len(meta.io_shape.inputs.nodes) == 1
    input_group = meta.io_shape.inputs.nodes[0]
    assert input_group.label == "search_text"
    assert "str" in input_group.typing.allowed_types

    # Assert - Output shape
    assert len(meta.io_shape.outputs.nodes) == 3

    output_1 = meta.io_shape.outputs.nodes[0]
    assert output_1.label == "matched_value"
    assert "str" in output_1.typing.allowed_types
    assert "None" in output_1.typing.allowed_types

    output_2 = meta.io_shape.outputs.nodes[1]
    assert output_2.label == "confidence"
    assert "float" in output_2.typing.allowed_types

    output_3 = meta.io_shape.outputs.nodes[2]
    assert output_3.label == "match_found"
    assert "bool" in output_3.typing.allowed_types


# ============================================================================
# Instructions for Completing Tests
# ============================================================================

"""
TO COMPLETE THESE TESTS:

1. Examine your test databases:
   - Look in: tests/test_databases/
   - Open .accdb files to see table structure
   - Identify tables with text columns suitable for fuzzy matching

2. Good candidates for testing:
   - Address tables (street addresses with variations)
   - Customer/contact names
   - Product descriptions
   - Any text field with potential variations/typos

3. For each test, replace PLACEHOLDER_ values with:
   - Actual database name (e.g., "htc_300_db")
   - Actual table name
   - Actual column names
   - Real data values from your tables

4. Example replacement:
   BEFORE:
   database="PLACEHOLDER_DATABASE_NAME"
   table="PLACEHOLDER_TABLE_NAME"
   inputs = {"input_1": "PLACEHOLDER_VALUE"}

   AFTER:
   database="htc_300_db"
   table="Addresses"
   inputs = {"input_1": "123 Main Street"}

5. Run tests:
   make test TEST=tests/test_modules/transform/test_fuzzy_database_lookup.py

6. Debug failures by checking:
   - Database connection is working
   - Table/column names are correct
   - Expected values exist in database
   - Confidence thresholds are reasonable
"""
