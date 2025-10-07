"""
If Selector Logic Module
Infrastructure module for conditional value selection
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.models import LogicModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from shared.utils.registry import register


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
                            label="False",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        NodeGroup(
                            label="True",
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
                type_params={"T": ["str", "float", "datetime", "bool"]}  # Domain for TypeVar T
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: IfSelectorConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute if selector operation (not implemented yet)

        Args:
            inputs: Dictionary with condition and two value inputs
            cfg: Validated configuration (empty)
            context: Execution context

        Returns:
            Dictionary with selected value
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")
