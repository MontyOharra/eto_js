"""
If Branch Logic Module
Conditional routing - routes data to one of two downstream paths based on boolean condition
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import LogicModule

logger = logging.getLogger(__name__)


class IfBranchConfig(BaseModel):
    """Configuration for If Branch - no configuration needed"""
    pass


@register
class IfBranch(LogicModule):
    """
    If Branch logic module
    Routes a value to one of two output paths based on a boolean condition
    The non-selected path receives a BranchNotTaken sentinel to skip downstream execution

    This is the inverse of if_selector:
    - if_selector: 2 inputs → 1 output (select which input)
    - if_branch: 1 input → 2 outputs (route to which output)

    Use case: Conditional actions (e.g., create vs update order)

    Example:
        order_data (str) ────┐
                             ├─→ if_branch
        order_exists (bool)──┘      /    \
                                true      false
                                 ↓         ↓
                            update_order  create_order
    """

    # Class metadata
    identifier = "if_branch"
    version = "1.0.0"
    title = "If Branch"
    description = "Route value to one of two paths based on boolean condition"
    category = "Flow Control"
    color = "#6B7280"  # Gray

    # Configuration model
    ConfigModel = IfBranchConfig

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
                            label="Value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="True Path",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        ),
                        NodeGroup(
                            label="False Path",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                type_params={"T": []}  # Generic type variable
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: IfBranchConfig, context: Any) -> Dict[str, Any]:
        """
        Execute branch routing

        Routes the value to the selected path based on condition.
        The non-selected path receives BranchNotTaken sentinel.

        Args:
            inputs: Dictionary with condition (bool) and value (T)
            cfg: Validated configuration (empty)
            context: Execution context with input/output metadata

        Returns:
            Dictionary with true_path and false_path outputs

        Raises:
            TypeError: If condition is not a boolean
        """
        # Import sentinel here to avoid circular import
        from features.pipeline_execution.service import BranchNotTaken

        # Get inputs (ordered: [Condition, Value] based on meta())
        condition_input = context.inputs[0]  # "Condition" group
        value_input = context.inputs[1]      # "Value" group

        condition = inputs[condition_input.node_id]
        value = inputs[value_input.node_id]

        # Validate condition is boolean
        if not isinstance(condition, bool):
            raise TypeError(f"Condition must be bool, got {type(condition).__name__}")

        # Get output node_ids
        true_path_output = context.outputs[0].node_id   # "True Path" group
        false_path_output = context.outputs[1].node_id  # "False Path" group

        # Route value: send to selected path, sentinel to other
        if condition:
            return {
                true_path_output: value,  # Send actual value to true path
                false_path_output: BranchNotTaken("Condition evaluated to false")
            }
        else:
            return {
                true_path_output: BranchNotTaken("Condition evaluated to true"),
                false_path_output: value  # Send actual value to false path
            }
