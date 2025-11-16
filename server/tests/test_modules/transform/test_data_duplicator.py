"""
Tests for Data Duplicator Transform Module

Tests the data_duplicator module which duplicates a single input value
to multiple output pins.
"""
import pytest
from typing import Any, List

from pipeline_modules.transform.data_duplicator import DataDuplicator, DataDuplicatorConfig
from shared.types.pipelines import ModuleExecutionContext, NodeInstance


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def duplicator_module():
    """Provide an instance of DataDuplicator for testing"""
    return DataDuplicator()


def create_node_instance(
    node_id: str,
    type: str = "str",
    name: str = "node",
    position_index: int = 0,
    group_index: int = 0
) -> NodeInstance:
    """
    Helper to create NodeInstance objects for testing

    Args:
        node_id: Unique identifier for the node
        type: Data type (str, int, float, bool, etc.)
        name: Display name
        position_index: Position within the group
        group_index: Index of the NodeGroup

    Returns:
        NodeInstance object
    """
    return NodeInstance(
        node_id=node_id,
        type=type,
        name=name,
        position_index=position_index,
        group_index=group_index
    )


def create_execution_context(
    num_outputs: int = 2,
    output_type: str = "str",
    module_instance_id: str = "test_module_1"
) -> ModuleExecutionContext:
    """
    Helper to create ModuleExecutionContext for testing

    Args:
        num_outputs: Number of output pins to create
        output_type: Type for output pins
        module_instance_id: ID for the module instance

    Returns:
        ModuleExecutionContext with single input and specified outputs
    """
    # Create single input
    inputs = [create_node_instance("input_1", type=output_type, name="data")]

    # Create multiple outputs
    outputs = [
        create_node_instance(
            f"output_{i+1}",
            type=output_type,
            name=f"duplication_{i+1}",
            position_index=i,
            group_index=0
        )
        for i in range(num_outputs)
    ]

    return ModuleExecutionContext(
        inputs=inputs,
        outputs=outputs,
        module_instance_id=module_instance_id
    )


# ============================================================================
# Basic Functionality Tests
# ============================================================================

@pytest.mark.unit
def test_duplicate_to_two_outputs(duplicator_module):
    """Test duplicating a value to exactly 2 outputs"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=2)
    inputs = {"input_1": "test_value"}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert
    assert len(result) == 2
    assert result["output_1"] == "test_value"
    assert result["output_2"] == "test_value"


@pytest.mark.unit
def test_duplicate_to_multiple_outputs(duplicator_module):
    """Test duplicating a value to many outputs (5)"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=5)
    inputs = {"input_1": "shared_data"}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert
    assert len(result) == 5
    for i in range(1, 6):
        assert result[f"output_{i}"] == "shared_data"


@pytest.mark.unit
def test_duplicate_preserves_reference(duplicator_module):
    """Test that the same object reference is duplicated (not deep copied)"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=3)
    original_dict = {"key": "value", "nested": {"data": 123}}
    inputs = {"input_1": original_dict}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert - all outputs should reference the same object
    assert result["output_1"] is original_dict
    assert result["output_2"] is original_dict
    assert result["output_3"] is original_dict


@pytest.mark.unit
def test_output_node_id_mapping(duplicator_module):
    """Test that output keys correctly match context.outputs node_ids"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=4)
    inputs = {"input_1": "mapped_value"}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert - result keys should match context output node_ids
    expected_keys = {output.node_id for output in context.outputs}
    actual_keys = set(result.keys())
    assert actual_keys == expected_keys


# ============================================================================
# Data Type Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("test_value,expected_type", [
    ("string_value", str),
    (42, int),
    (3.14, float),
    (True, bool),
    (None, type(None)),
    ([1, 2, 3], list),
    ({"a": 1, "b": 2}, dict),
])
def test_duplicate_different_types(duplicator_module, test_value, expected_type):
    """Test duplication preserves different data types"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=2)
    inputs = {"input_1": test_value}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert - type and value preserved
    assert isinstance(result["output_1"], expected_type)
    assert isinstance(result["output_2"], expected_type)
    assert result["output_1"] == test_value
    assert result["output_2"] == test_value


@pytest.mark.unit
def test_duplicate_complex_nested_data(duplicator_module):
    """Test duplication of complex nested data structures"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=3)
    complex_data = {
        "level1": {
            "level2": {
                "level3": ["a", "b", "c"],
                "numbers": [1, 2, 3]
            },
            "metadata": {
                "created": "2025-01-15",
                "tags": ["important", "test"]
            }
        },
        "simple": "value"
    }
    inputs = {"input_1": complex_data}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert - all outputs have identical structure
    for i in range(1, 4):
        output_key = f"output_{i}"
        assert result[output_key] == complex_data
        assert result[output_key]["level1"]["level2"]["level3"] == ["a", "b", "c"]


# ============================================================================
# Edge Cases and Validation
# ============================================================================

@pytest.mark.unit
def test_single_input_used(duplicator_module):
    """Test that only the first input is used when multiple inputs provided"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=2)
    # Provide multiple inputs (shouldn't happen in practice, but test robustness)
    inputs = {
        "input_1": "correct_value",
        "input_2": "wrong_value"
    }

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert - should use first input value
    assert result["output_1"] == "correct_value"
    assert result["output_2"] == "correct_value"


@pytest.mark.unit
def test_empty_config(duplicator_module):
    """Test that module works with empty configuration"""
    # Arrange
    config = DataDuplicatorConfig()
    context = create_execution_context(num_outputs=2)
    inputs = {"input_1": "test"}

    # Act
    result = duplicator_module.run(inputs, config, context)

    # Assert
    assert len(result) == 2
    assert result["output_1"] == "test"


# ============================================================================
# Metadata Tests
# ============================================================================

@pytest.mark.unit
def test_module_metadata():
    """Test that module class metadata is correctly defined"""
    # Assert
    assert DataDuplicator.id == "data_duplicator"
    assert DataDuplicator.version == "1.0.0"
    assert DataDuplicator.title == "Data Duplicator"
    assert DataDuplicator.description == "Duplicate input data to multiple outputs"
    assert DataDuplicator.category == "Data"
    assert DataDuplicator.color == "#F3F4F6"


@pytest.mark.unit
def test_config_model():
    """Test that ConfigModel is correctly set"""
    # Assert
    assert DataDuplicator.ConfigModel == DataDuplicatorConfig


@pytest.mark.unit
def test_io_shape_definition():
    """Test that I/O shape is correctly defined in metadata"""
    # Act
    meta = DataDuplicator.meta()

    # Assert - Input shape
    assert len(meta.io_shape.inputs.nodes) == 1
    input_group = meta.io_shape.inputs.nodes[0]
    assert input_group.label == "Data"
    assert input_group.min_count == 1
    assert input_group.max_count == 1
    assert input_group.typing.type_var == "T"

    # Assert - Output shape
    assert len(meta.io_shape.outputs.nodes) == 1
    output_group = meta.io_shape.outputs.nodes[0]
    assert output_group.label == "Duplication"
    assert output_group.min_count == 2
    assert output_group.max_count is None  # Unlimited
    assert output_group.typing.type_var == "T"

    # Assert - Type parameters
    assert "T" in meta.io_shape.type_params
    assert meta.io_shape.type_params["T"] == []


@pytest.mark.unit
def test_type_var_consistency():
    """Test that input and output use the same TypeVar T"""
    # Act
    meta = DataDuplicator.meta()

    # Assert - both should use TypeVar "T"
    input_type_var = meta.io_shape.inputs.nodes[0].typing.type_var
    output_type_var = meta.io_shape.outputs.nodes[0].typing.type_var
    assert input_type_var == output_type_var == "T"
