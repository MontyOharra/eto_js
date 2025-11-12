"""
Boolean NOT Logic Module
Infrastructure module for logical NOT operation
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import LogicModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class BooleanNotConfig(BaseModel):
    """Configuration for Boolean NOT - no configuration needed"""
    pass

@register
class BooleanNot(LogicModule):
    """
    Boolean NOT logic gate
    Takes one boolean input and outputs its logical NOT result
    """

    # Class metadata
    id = "boolean_not"
    version = "1.0.0"
    title = "Boolean NOT"
    description = "Logical NOT operation on one boolean input"
    category = "Gate"
    color = "#10B981"  # Green

    # Configuration model
    ConfigModel = BooleanNotConfig

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
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="Not",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: BooleanNotConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute boolean NOT operation

        Args:
            inputs: Dictionary with one boolean input (keyed by node_id)
            cfg: Validated configuration (empty)
            context: Execution context with input/output metadata

        Returns:
            Dictionary with NOT result
        """
        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Map input node_id using context metadata
        a_input = context.inputs[0]  # First input group is "A"

        # Extract value from inputs dict
        a_value = inputs[a_input.node_id]

        # Validate input is boolean
        if not isinstance(a_value, bool):
            raise TypeError(f"Input A must be bool, got {type(a_value).__name__}")

        # Perform NOT operation
        result = not a_value

        return {output_node_id: result}