"""
Data Duplicator Transform Module
Infrastructure module for duplicating input data to multiple outputs
"""
from typing import Dict, Any
from pydantic import BaseModel

from src.features.modules.core.contracts import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from src.features.modules.core.registry import register


class DataDuplicatorConfig(BaseModel):
    """Configuration for Data Duplicator - no configuration needed"""
    pass


@register
class DataDuplicator(TransformModule):
    """
    Data Duplicator transform module
    Takes one input and duplicates it to multiple outputs
    All inputs and outputs share the same TypeVar for type consistency
    """

    # Class metadata
    id = "data_duplicator"
    version = "1.0.0"
    title = "Data Duplicator"
    description = "Duplicate input data to multiple outputs"
    category = "Data"
    color = "#F3F4F6"  # White

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

    def run(self, inputs: Dict[str, Any], cfg: DataDuplicatorConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute data duplication (not implemented yet)

        Args:
            inputs: Dictionary with one input value
            cfg: Validated configuration (empty)
            context: Execution context

        Returns:
            Dictionary with duplicated values
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")
