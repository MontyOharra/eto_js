"""
Create Order Action Module
Testing order creation in HTC database test table
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel
from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class CreateOrderConfig(BaseModel):
    """Configuration for create order action - no config for now"""
    pass


@register
class CreateOrder(ActionModule):
    """
    Action module that creates a test record in the HTC database.

    For testing purposes - inserts hawb and search_text values into the test table.
    """

    id = "create_order"
    version = "1.0.0"
    title = "Create Order"
    description = "Creates a test record in the HTC database test table"
    category = "Database"
    color = "#DC2626"  # Dark red (Tailwind red-600)

    ConfigModel = CreateOrderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="hawb",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="search_text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ]),
                outputs=IOSideShape(nodes=[])  # Actions typically have no outputs
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: CreateOrderConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the create order action.

        Inserts hawb and search_text values into the test table in htc_db.

        Args:
            inputs: Dictionary with input values (hawb, search_text)
            cfg: Configuration (empty for now)
            context: Execution context with services

        Returns:
            Empty dict (actions don't produce outputs)
        """
        if not context or not context.services:
            raise RuntimeError("CreateOrder requires service container access")

        # Get input values by matching context input nodes to inputs dict
        hawb_input = next(node for node in context.inputs if node.group_index == 0)
        search_text_input = next(node for node in context.inputs if node.group_index == 1)
        
        hawb = inputs[hawb_input.node_id]
        search_text = inputs[search_text_input.node_id]

        logger.info(f"[CREATE ORDER] Creating test record with HAWB: {hawb}, search_text: {search_text}")

        # Get the HTC database connection
        try:
            htc_db = context.services.get_connection('htc_db')
            logger.info("[CREATE ORDER] Successfully accessed htc_db connection")
        except ValueError as e:
            logger.error(f"[CREATE ORDER] Failed to access htc_db: {e}")
            raise RuntimeError(
                "HTC database not configured. "
                "Set HTC_DB_CONNECTION_STRING in .env file to enable order creation."
            ) from e

        # Create test record in database
        try:
            with htc_db.cursor() as cursor:
                logger.info("[CREATE ORDER] Executing INSERT into test table...")

                # Insert test record
                cursor.execute(
                    """
                    INSERT INTO test (hawb, search_text)
                    VALUES (?, ?)
                    """,
                    (hawb, search_text)
                )

                logger.info(f"[CREATE ORDER] Test record created successfully with HAWB: {hawb}, search_text: {search_text}")

        except Exception as e:
            logger.error(f"[CREATE ORDER] Database operation failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create test record: {e}") from e

        # Actions return empty dict
        return {}
