"""
Dim Weight Distributor Transform Module
Distributes a total weight across a list of dim objects.
Deterministic — no LLM involved.
"""
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)


class DimWeightDistributorConfig(BaseModel):
    """Configuration for Dim Weight Distributor"""
    method: str = Field(
        default="by_piece_count",
        description="Distribution method: 'by_piece_count' (proportional to qty) or 'by_volume' (proportional to L*W*H*qty)"
    )


@register
class DimWeightDistributor(BaseModule):
    """
    Distributes a total weight across dim objects.

    If dims already have non-zero weights, they are passed through unchanged.
    Only distributes when all dim weights are zero.
    """

    identifier = "dim_weight_distributor"
    version = "1.0.0"
    title = "Dim Weight Distributor"
    description = "Distribute a total weight across dim objects by piece count or volume"
    category = "Cargo"
    kind = "transform"
    color = "#F97316"

    ConfigModel = DimWeightDistributorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dims",
                            typing=NodeTypeRule(allowed_types=["list[dim]"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="total_weight",
                            typing=NodeTypeRule(allowed_types=["float", "int", "str"]),
                            min_count=1,
                            max_count=1,
                        ),
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dims",
                            typing=NodeTypeRule(allowed_types=["list[dim]"]),
                            min_count=1,
                            max_count=1,
                        )
                    ]
                ),
            )
        )

    @classmethod
    def validate_config(cls, cfg, inputs, outputs, services=None):
        errors = []
        if cfg.method not in ("by_piece_count", "by_volume"):
            errors.append(
                f"Invalid method '{cfg.method}'. Must be 'by_piece_count' or 'by_volume'."
            )
        return errors

    def run(
        self,
        inputs: Dict[str, Any],
        cfg: DimWeightDistributorConfig,
        context: Any,
        access_conn_manager: AccessConnectionManager | None = None,
    ) -> Dict[str, Any]:
        # Read inputs by group index
        dim_list: List[Dict[str, Any]] = []
        total_weight = 0.0

        for pin in context.inputs:
            value = inputs.get(pin.node_id)
            if pin.group_index == 0:  # dims
                dim_list = value if isinstance(value, list) else []
            elif pin.group_index == 1:  # total_weight
                if value is not None:
                    try:
                        parsed = str(value).strip()
                        total_weight = float(parsed) if parsed else 0.0
                    except (ValueError, TypeError):
                        total_weight = 0.0

        output_node_id = context.outputs[0].node_id

        if not dim_list:
            return {output_node_id: []}

        # Check if dims already have weights
        has_existing_weights = any(
            d.get("weight", 0) != 0 for d in dim_list if isinstance(d, dict)
        )

        if has_existing_weights or total_weight == 0:
            logger.info(
                f"Passing through {len(dim_list)} dims unchanged "
                f"(existing_weights={has_existing_weights}, total_weight={total_weight})"
            )
            return {output_node_id: dim_list}

        # Distribute weight
        if cfg.method == "by_volume":
            result = self._distribute_by_volume(dim_list, total_weight)
        else:
            result = self._distribute_by_piece_count(dim_list, total_weight)

        logger.info(
            f"Distributed {total_weight} lbs across {len(result)} dims "
            f"using method={cfg.method}"
        )

        return {output_node_id: result}

    @staticmethod
    def _distribute_by_piece_count(
        dims: List[Dict[str, Any]], total_weight: float
    ) -> List[Dict[str, Any]]:
        total_pieces = sum(d.get("qty", 1) for d in dims)
        if total_pieces == 0:
            return dims

        result = []
        for d in dims:
            qty = d.get("qty", 1)
            proportion = qty / total_pieces
            result.append({
                **d,
                "weight": round(total_weight * proportion, 3),
            })
        return result

    @staticmethod
    def _distribute_by_volume(
        dims: List[Dict[str, Any]], total_weight: float
    ) -> List[Dict[str, Any]]:
        def vol(d: Dict[str, Any]) -> float:
            return (
                d.get("length", 0)
                * d.get("width", 0)
                * d.get("height", 0)
                * d.get("qty", 1)
            )

        total_volume = sum(vol(d) for d in dims)
        if total_volume == 0:
            # Fall back to piece count if all volumes are zero
            return DimWeightDistributor._distribute_by_piece_count(dims, total_weight)

        result = []
        for d in dims:
            proportion = vol(d) / total_volume
            result.append({
                **d,
                "weight": round(total_weight * proportion, 3),
            })
        return result
