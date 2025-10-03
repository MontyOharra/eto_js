"""
Comprehensive Test Transform Module
Complex module with all possible edge cases for testing the UI node system
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from src.features.modules.core.contracts import TransformModule, ModuleMeta, IOShape, IOSideShape, StaticNodes, DynamicNodes, DynamicNodeGroup, NodeSpec, NodeTypeRule
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
                    # Static inputs with various type constraints
                    static=StaticNodes(
                        slots=[
                            # Fixed string input
                            NodeSpec(
                                label="primary_input",
                                typing=NodeTypeRule(allowed_types=["str"])
                            ),
                            # TypeVar input that can be any type
                            NodeSpec(
                                label="generic_data",
                                typing=NodeTypeRule(type_var="T")
                            ),
                            # Numeric-only input
                            NodeSpec(
                                label="numeric_value",
                                typing=NodeTypeRule(allowed_types=["float", "int"])
                            ),
                            # Boolean control flag
                            NodeSpec(
                                label="enable_flag",
                                typing=NodeTypeRule(allowed_types=["bool"])
                            ),
                            NodeSpec(
                                label="test",
                                typing=NodeTypeRule(allowed_types=["bool", "float"])
                            )
                        ]
                    ),
                    # Dynamic input groups
                    dynamic=DynamicNodes(
                        groups=[
                            # Variable string inputs (1-5)
                            DynamicNodeGroup(
                                min_count=1,
                                max_count=5,
                                item=NodeSpec(
                                    label="text_data",
                                    typing=NodeTypeRule(allowed_types=["str"])
                                )
                            ),
                            # Unlimited numeric inputs
                            DynamicNodeGroup(
                                min_count=0,
                                max_count=None,
                                item=NodeSpec(
                                    label="numeric_array",
                                    typing=NodeTypeRule(allowed_types=["float", "int"])
                                )
                            ),
                            # TypeVar group that must match T from static
                            DynamicNodeGroup(
                                min_count=2,
                                max_count=10,
                                item=NodeSpec(
                                    label="matching_data",
                                    typing=NodeTypeRule(type_var="T")
                                )
                            ),
                            # Flexible type group
                            DynamicNodeGroup(
                                min_count=0,
                                max_count=3,
                                item=NodeSpec(
                                    label="flexible_input",
                                    typing=NodeTypeRule(allowed_types=["str", "float", "bool", "datetime"])
                                )
                            )
                        ]
                    )
                ),
                outputs=IOSideShape(
                    # Static outputs with TypeVar inheritance
                    static=StaticNodes(
                        slots=[
                            # Status output
                            NodeSpec(
                                label="status",
                                typing=NodeTypeRule(allowed_types=["str"])
                            ),
                            # Count output
                            NodeSpec(
                                label="processed_count",
                                typing=NodeTypeRule(allowed_types=["int"])
                            ),
                            # Inherits type from TypeVar T
                            NodeSpec(
                                label="processed_data",
                                typing=NodeTypeRule(type_var="T")
                            ),
                            NodeSpec(
                                label="test",
                                typing=NodeTypeRule(allowed_types=["bool", "int"])
                            )
                        ]
                    ),
                    # Dynamic output groups
                    dynamic=DynamicNodes(
                        groups=[
                            # Processed results (unlimited)
                            DynamicNodeGroup(
                                min_count=1,
                                max_count=None,
                                item=NodeSpec(
                                    label="result",
                                    typing=NodeTypeRule(allowed_types=["str", "float", "int", "bool"])
                                )
                            ),
                            # Error reports (0-5)
                            DynamicNodeGroup(
                                min_count=0,
                                max_count=5,
                                item=NodeSpec(
                                    label="error_report",
                                    typing=NodeTypeRule(allowed_types=["str"])
                                )
                            ),
                            # TypeVar outputs that match input TypeVar
                            DynamicNodeGroup(
                                min_count=1,
                                max_count=None,
                                item=NodeSpec(
                                    label="transformed_data",
                                    typing=NodeTypeRule(type_var="T")
                                )
                            ),
                            # Timestamp outputs
                            DynamicNodeGroup(
                                min_count=0,
                                max_count=1,
                                item=NodeSpec(
                                    label="timestamp",
                                    typing=NodeTypeRule(allowed_types=["datetime"])
                                )
                            )
                        ]
                    )
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