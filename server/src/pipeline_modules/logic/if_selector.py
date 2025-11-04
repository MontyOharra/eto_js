"""
If Selector Logic Module
Infrastructure module for conditional value selection
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import LogicModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class IfSelectorConfig(BaseModel):
    """Configuration for If Selector - no configuration needed"""
    pass

@register
class IfSelector(LogicModule):
    """
    If Selector logic module
    Takes a boolean condition and two variable inputs, outputs one of the inputs based on the condition
    All variable inputs/outputs share the same TypeVar for type consistency
    """

    # Class metadata
    id = "if_selector"
    version = "1.0.0"
    title = "If Selector"
    description = "Select one of two values based on a boolean condition"
    category = "Routing"
    color = "#F3F4F6"  # Light gray/white

    # Configuration model
    ConfigModel = IfSelectorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="Condition",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        ),
                        NodeGroup(
                            label="True",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        NodeGroup(
                            label="False",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="selected_value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                type_params={"T": []}  # Domain for TypeVar T
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: IfSelectorConfig, context: Any) -> Dict[str, Any]:
        """
        Execute if selector operation

        Args:
            inputs: Dictionary with condition and two value inputs (keyed by node_id)
            cfg: Validated configuration (empty)
            context: Execution context with input/output metadata

        Returns:
            Dictionary with selected value
        """
        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Map input node_ids to their values using context metadata
        # The inputs are ordered: [Condition, False, True] based on meta() definition
        condition_input = context.inputs[0]  # First input group is "Condition"
        false_input = context.inputs[1]      # Second input group is "False"
        true_input = context.inputs[2]       # Third input group is "True"

        # Extract values from inputs dict
        condition = inputs[condition_input.node_id]
        false_value = inputs[false_input.node_id]
        true_value = inputs[true_input.node_id]

        # Validate condition is boolean
        if not isinstance(condition, bool):
            raise TypeError(f"Condition must be bool, got {type(condition).__name__}")

        # Select value based on condition
        selected_value = true_value if condition else false_value

        return {output_node_id: selected_value}
