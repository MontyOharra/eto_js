"""
Dim List Collector Transform Module
Collects multiple dim objects into a list[dim]
"""
import logging
from typing import Dict, Any, List
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import TransformModule

logger = logging.getLogger(__name__)


class DimListCollectorConfig(BaseModel):
    """Configuration for Dim List Collector - no config needed"""
    pass


@register
class DimListCollector(TransformModule):
    """
    Dim List Collector transform module
    Collects multiple dim objects into a list[dim] for output channels
    """

    # Class metadata
    id = "dim_list_collector"
    version = "1.0.0"
    title = "Dim List Collector"
    description = "Collect multiple dim objects into a list"
    category = "Cargo"
    color = "#F97316"  # Orange (same as DimBuilder)

    # Configuration model
    ConfigModel = DimListCollectorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dim",
                            typing=NodeTypeRule(allowed_types=["dim"]),
                            min_count=1,
                            max_count=None  # Unlimited dim inputs
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dim_list",
                            typing=NodeTypeRule(allowed_types=["list[dim]"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DimListCollectorConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute dim list collection

        Args:
            inputs: Dictionary with dim objects
            cfg: Validated configuration (empty for this module)
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with list[dim] output
        """
        # Collect dim objects in order from context
        dim_list: List[Dict[str, Any]] = []

        for input_node in context.inputs:
            node_id = input_node.node_id
            dim_obj = inputs.get(node_id)

            if dim_obj is not None:
                # Validate it's a dict with expected structure
                if isinstance(dim_obj, dict):
                    dim_list.append(dim_obj)
                else:
                    logger.warning(f"Skipping invalid dim input (not a dict): {dim_obj}")

        logger.info(f"Collected {len(dim_list)} dim objects into list")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {
            output_node_id: dim_list
        }
