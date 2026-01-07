"""
Boolean AND Logic Module
Infrastructure module for logical AND operation
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import LogicModule
from shared.database.access_connection import AccessConnectionManager


class BooleanAndConfig(BaseModel):
    """Configuration for Boolean AND - no configuration needed"""
    pass

@register
class BooleanAnd(LogicModule):
    """
    Boolean AND logic gate
    Takes two boolean inputs and outputs their logical AND result
    """

    # Class metadata
    identifier = "boolean_and"
    version = "1.0.0"
    title = "Boolean AND"
    description = "Logical AND operation on two boolean inputs"
    category = "Gate"
    color = "#10B981"  # Green

    # Configuration model
    ConfigModel = BooleanAndConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="A",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        ),
                        NodeGroup(
                            label="B",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="And",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: BooleanAndConfig, context: Any) -> Dict[str, Any]:
        """
        Execute boolean AND operation

        Args:
            inputs: Dictionary with two boolean inputs (keyed by node_id)
            cfg: Validated configuration (empty)
            context: Execution context with input/output metadata

        Returns:
            Dictionary with AND result
        """
        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Map input node_ids using context metadata
        # The inputs are ordered: [A, B] based on meta() definition
        a_input = context.inputs[0]  # First input group is "A"
        b_input = context.inputs[1]  # Second input group is "B"

        # Extract values from inputs dict
        a_value = inputs[a_input.node_id]
        b_value = inputs[b_input.node_id]

        # Validate inputs are boolean
        if not isinstance(a_value, bool):
            raise TypeError(f"Input A must be bool, got {type(a_value).__name__}")
        if not isinstance(b_value, bool):
            raise TypeError(f"Input B must be bool, got {type(b_value).__name__}")

        # Perform AND operation
        result = a_value and b_value

        return {output_node_id: result}