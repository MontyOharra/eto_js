"""
Weight Dim Builder Transform Module
Builds a dimension object from just weight and piece count,
setting length, width, and height to 1.
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)

DimObject = Dict[str, Any]


class WeightDimBuilderConfig(BaseModel):
    pass


@register
class WeightDimBuilder(BaseModule):
    """
    Weight Dim Builder transform module.
    Builds a dimension object from piece count and weight only,
    with length, width, and height defaulting to 1.
    """

    identifier = "weight_dim_builder"
    version = "1.0.0"
    title = "Weight Dim Builder"
    description = "Build a dimension object from count and weight (L/W/H default to 1)"
    category = "Cargo"
    kind = "transform"
    color = "#F97316"

    ConfigModel = WeightDimBuilderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="count",
                            typing=NodeTypeRule(allowed_types=["int", "str"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="weight",
                            typing=NodeTypeRule(allowed_types=["float", "int", "str"]),
                            min_count=1,
                            max_count=1,
                        ),
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dim",
                            typing=NodeTypeRule(allowed_types=["dim"]),
                            min_count=1,
                            max_count=1,
                        )
                    ]
                ),
            )
        )

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def run(self, inputs: Dict[str, Any], cfg: WeightDimBuilderConfig, context: Any, access_conn_manager: AccessConnectionManager | None = None) -> Dict[str, Any]:
        qty = None
        weight = None

        for input_node in context.inputs:
            node_id = input_node.node_id
            group_index = input_node.group_index
            value = inputs.get(node_id)

            if group_index == 0:  # count
                qty = self._parse_int(value)
            elif group_index == 1:  # weight
                weight = self._parse_float(value)

        output_node_id = context.outputs[0].node_id

        if not qty or not weight:
            logger.info("Count or weight is empty/zero, returning None")
            return {output_node_id: None}

        dim_obj: DimObject = {
            "height": 1,
            "length": 1,
            "width": 1,
            "qty": qty,
            "weight": weight,
        }

        logger.info(f"Built weight dim object: {dim_obj}")

        return {output_node_id: dim_obj}
