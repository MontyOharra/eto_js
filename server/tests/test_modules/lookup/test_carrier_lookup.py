"""
Tests for Carrier Lookup Module

Tests the carrier lookup module that finds carrier address IDs using the
Address Name Swaps table in HTC350D_Database.
"""
import pytest
from typing import Any

from pipeline_modules.lookup.carrier_lookup import CarrierLookup, CarrierLookupConfig
from shared.types.pipelines import ModuleExecutionContext, NodeInstance


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def carrier_lookup_module():
    """Provide an instance of CarrierLookup for testing"""
    return CarrierLookup()


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
    - 1 input: carrier_name (str)
    - 3 outputs: carrier_id (float), carrier_found (bool), actual_carrier_name (str)
    """
    inputs = [create_node_instance("input_1", type="str", name="carrier_name")]

    outputs = [
        create_node_instance("output_1", type="float", name="carrier_id"),
        create_node_instance("output_2", type="bool", name="carrier_found"),
        create_node_instance("output_3", type="str", name="actual_carrier_name")
    ]

    return ModuleExecutionContext(
        inputs=inputs,
        outputs=outputs,
        module_instance_id=module_instance_id
    )


# ============================================================================
# Database Integration Test
# ============================================================================

@pytest.mark.integration
def test_carrier_lookup_name_swap(carrier_lookup_module, db_services):
    """
    Test carrier lookup using Address Name Swaps table

    This test will print the values returned and verify the lookup works
    """
    config = CarrierLookupConfig()

    context = create_execution_context()

    # Test with a carrier name that should be in the Name Swaps table
    # Update this with an actual carrier from your HTC350_G060_T100 Address Name Swaps table
    test_carrier_name = "Southwest Airlines"
    inputs = {"input_1": test_carrier_name}

    # Act
    result = carrier_lookup_module.run(inputs, config, context, services=db_services)

    # Print results
    print(f"\n{'='*60}")
    print(f"Carrier Lookup Test Results")
    print(f"{'='*60}")
    print(f"Input carrier name: '{test_carrier_name}'")
    print(f"carrier_id (output_1): {result['output_1']}")
    print(f"carrier_found (output_2): {result['output_2']}")
    print(f"actual_carrier_name (output_3): {result['output_3']}")
    print(f"{'='*60}\n")

    # Assert basic conditions
    assert "output_1" in result, "Should have carrier_id output"
    assert "output_2" in result, "Should have carrier_found output"
    assert "output_3" in result, "Should have actual_carrier_name output"

    # Verify successful lookup
    assert result["output_2"] is True, "carrier_found should be True"
    assert isinstance(result["output_1"], (int, float)), "carrier_id should be numeric"
    assert result["output_1"] is not None, "carrier_id should not be None"
    assert isinstance(result["output_3"], str), "actual_carrier_name should be string"
    assert len(result["output_3"]) > 0, "actual_carrier_name should not be empty"


@pytest.mark.integration
def test_carrier_lookup_not_found(carrier_lookup_module, db_services):
    """
    Test that carrier lookup raises error when name not found in swaps table

    This should raise a ValueError with helpful message
    """
    config = CarrierLookupConfig()

    context = create_execution_context()

    # Test with a carrier name that definitely doesn't exist
    test_carrier_name = "Nonexistent Carrier XYZ123"
    inputs = {"input_1": test_carrier_name}

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError, match="not found in Address Name Swaps table"):
        carrier_lookup_module.run(inputs, config, context, services=db_services)


@pytest.mark.integration
def test_carrier_lookup_empty_name(carrier_lookup_module, db_services):
    """
    Test that carrier lookup raises error when name is empty

    This should raise a ValueError
    """
    config = CarrierLookupConfig()

    context = create_execution_context()

    # Test with empty string
    inputs = {"input_1": ""}

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError, match="Carrier name cannot be empty"):
        carrier_lookup_module.run(inputs, config, context, services=db_services)
