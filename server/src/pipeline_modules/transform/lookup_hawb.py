"""
Lookup HAWB Transform Module
Queries the HTC database test table to find hawb by search_text
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel
from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class LookupHawbConfig(BaseModel):
    """Configuration for lookup hawb transform - no config for now"""
    pass


@register
class LookupHawb(TransformModule):
    """
    Transform module that looks up a hawb from the HTC database test table.

    Executes a WHERE query on the test table using search_text and returns the hawb.
    """

    id = "lookup_hawb"
    version = "1.0.0"
    title = "Lookup HAWB"
    description = "Queries the test table to find hawb by search_text"
    category = "Database"
    color = "#3B82F6"  # Blue

    ConfigModel = LookupHawbConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="search_text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="hawb",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: LookupHawbConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Execute the lookup hawb transform.

        Queries the test table WHERE search_text matches the input value.

        Args:
            inputs: Dictionary with input values (search_text)
            cfg: Configuration (empty for now)
            context: Execution context with I/O metadata
            services: Service container for database access

        Returns:
            Dictionary with output: {"hawb": found_hawb_value}
        """
        if not services:
            raise RuntimeError("LookupHawb requires service container access")

        # Get input value by group_index (order in meta definition)
        # group_index 0 = search_text (first and only input NodeGroup)
        search_text_input = next(node for node in context.inputs if node.group_index == 0)
        search_text = inputs[search_text_input.node_id]

        logger.info(f"[LOOKUP HAWB] Querying test table for search_text: {search_text}")

        # Get the HTC database connection
        try:
            htc_db = services.get_connection('htc_db')
            logger.info("[LOOKUP HAWB] Successfully accessed htc_db connection")
        except ValueError as e:
            logger.error(f"[LOOKUP HAWB] Failed to access htc_db: {e}")
            raise RuntimeError(
                "HTC database not configured. "
                "Set HTC_DB_CONNECTION_STRING in .env file to enable database queries."
            ) from e

        # Query database for hawb
        try:
            with htc_db.cursor() as cursor:
                logger.info("[LOOKUP HAWB] Executing SELECT query on test table...")

                # Query for matching record
                cursor.execute(
                    """
                    SELECT hawb
                    FROM test
                    WHERE search_text = ?
                    """,
                    (search_text,)
                )

                row = cursor.fetchone()

                if not row:
                    raise RuntimeError(f"No record found in test table with search_text: {search_text}")

                hawb = row[0]
                logger.info(f"[LOOKUP HAWB] Found HAWB: {hawb} for search_text: {search_text}")

        except Exception as e:
            logger.error(f"[LOOKUP HAWB] Database operation failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to lookup hawb: {e}") from e

        # Get output node by group_index
        # group_index 0 = hawb (first and only output NodeGroup)
        output_pin = next(node for node in context.outputs if node.group_index == 0)

        return {
            output_pin.node_id: hawb
        }
