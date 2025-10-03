"""
Comprehensive Test Transform Module
Complex module with all possible edge cases for testing the UI node system
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from src.features.modules.core.contracts import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from src.features.modules.core.registry import register


class ComprehensiveTestConfig(BaseModel):
    """Configuration for Comprehensive Test Module"""
    processing_mode: str = Field("standard", description="Select processing mode")
    enable_validation: bool = Field(True, description="Enable input validation")
    output_format: str = Field("json", description="Output format for results")
    max_iterations: int = Field(10, description="Maximum processing iterations")


@register
class ComprehensiveTest(TransformModule):
    """
    Comprehensive test module with all possible node configurations
    - Static inputs with different types and TypeVars
    - Dynamic input groups with various constraints
    - Static outputs with TypeVar inheritance
    - Dynamic output groups with type restrictions
    - Mixed static/dynamic scenarios
    """

    # Class metadata
    id = "comprehensive_test"
    version = "1.0.0"
    title = "Comprehensive Test Module"
    description = "Complex test module with all edge cases for node configurations"

    # Configuration model
    ConfigModel = ComprehensiveTestConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints with comprehensive edge cases"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        # Fixed string input (static: min=max=1)
                        NodeGroup(
                            label="primary_input",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        # TypeVar input that can be any type (static)
                        NodeGroup(
                            label="generic_data",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        # Numeric-only input (static)
                        NodeGroup(
                            label="numeric_value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["float", "int"])
                        ),
                        # Boolean control flag (static)
                        NodeGroup(
                            label="enable_flag",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        ),
                        # Test input (static)
                        NodeGroup(
                            label="test",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool", "float"])
                        ),
                        # Variable string inputs (1-5) (dynamic)
                        NodeGroup(
                            label="text_data",
                            min_count=1,
                            max_count=5,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        # Unlimited numeric inputs (dynamic)
                        NodeGroup(
                            label="numeric_array",
                            min_count=0,
                            max_count=None,
                            typing=NodeTypeRule(allowed_types=["float", "int"])
                        ),
                        # TypeVar group that must match T (dynamic)
                        NodeGroup(
                            label="matching_data",
                            min_count=2,
                            max_count=10,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        # Flexible type group (dynamic)
                        NodeGroup(
                            label="flexible_input",
                            min_count=0,
                            max_count=3,
                            typing=NodeTypeRule(allowed_types=["str", "float", "bool", "datetime"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        # Status output (static)
                        NodeGroup(
                            label="status",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        # Count output (static)
                        NodeGroup(
                            label="processed_count",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["int"])
                        ),
                        # Inherits type from TypeVar T (static)
                        NodeGroup(
                            label="processed_data",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        # Test output (static)
                        NodeGroup(
                            label="test",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool", "int"])
                        ),
                        # Processed results (unlimited) (dynamic)
                        NodeGroup(
                            label="result",
                            min_count=1,
                            max_count=None,
                            typing=NodeTypeRule(allowed_types=["str", "float", "int", "bool"])
                        ),
                        # Error reports (0-5) (dynamic)
                        NodeGroup(
                            label="error_report",
                            min_count=0,
                            max_count=5,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        # TypeVar outputs that match input TypeVar (dynamic)
                        NodeGroup(
                            label="transformed_data",
                            min_count=1,
                            max_count=None,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        # Timestamp outputs (dynamic)
                        NodeGroup(
                            label="timestamp",
                            min_count=0,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["datetime"])
                        )
                    ]
                ),
                # TypeVar declarations
                type_params={
                    "T": ["str", "float", "int", "bool", "datetime"]
                }
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: ComprehensiveTestConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute comprehensive test processing (mock implementation)

        Args:
            inputs: Dictionary with all input values
            cfg: Validated configuration
            context: Execution context

        Returns:
            Dictionary with all output values
        """
        # Mock implementation for testing
        outputs = {}

        # Static outputs
        outputs["status"] = "completed"
        outputs["processed_count"] = len(inputs)

        # Echo back the primary generic data
        if "generic_data" in inputs:
            outputs["processed_data"] = inputs["generic_data"]

        # Add some mock dynamic outputs
        outputs["result_1"] = "Mock result 1"
        outputs["result_2"] = 42
        outputs["transformed_data_1"] = inputs.get("generic_data", "default")

        return outputs