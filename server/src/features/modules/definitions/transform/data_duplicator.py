"""
Data Duplicator Transform Module
Infrastructure module for duplicating input data to multiple outputs
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager


class DataDuplicatorConfig(BaseModel):
    """Configuration for Data Duplicator - no configuration needed"""
    pass

@register
class DataDuplicator(BaseModule):
    """
    Data Duplicator transform module
    Takes one input and duplicates it to multiple outputs
    All inputs and outputs share the same TypeVar for type consistency
    """

    # Class metadata
    identifier = "data_duplicator"
    version = "1.0.0"
    title = "Data Duplicator"
    description = "Duplicate input data to multiple outputs"
    category = "Flow Control"
    kind = "transform"
    color = "#6B7280"  # Gray

    # Configuration model
    ConfigModel = DataDuplicatorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="Data",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="Duplication",
                            min_count=2,
                            max_count=None,  # Unlimited outputs
                            typing=NodeTypeRule(type_var="T")
                        )
                    ]
                ),
                type_params={"T": []}  # Domain for TypeVar T
            )
        )
        
    def run(self, inputs: Dict[str, Any], cfg: DataDuplicatorConfig, context: Any, access_conn_manager: AccessConnectionManager | None = None) -> Dict[str, Any]:
        """
        Duplicate input value to all output pins

        Args:
            inputs: Dictionary with single input value (keyed by node_id)
            cfg: Empty configuration
            context: Execution context with output metadata

        Returns:
            Dictionary with duplicated value for each output pin
        """
        # Get the single input value
        input_node_id = list(inputs.keys())[0]
        input_value = inputs[input_node_id]

        # Duplicate to all outputs using context
        outputs = {}
        for output_pin in context.outputs:
            outputs[output_pin.node_id] = input_value

        return outputs