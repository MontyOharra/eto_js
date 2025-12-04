"""
Test Output Definition

Implementation for the test_output module.
Used for testing the output execution system.
"""

from typing import Any, Dict

from shared.logging import get_logger
from features.pipeline_results.output_definitions.base import OutputDefinitionBase
from features.pipeline_results.helpers.orders import OrderHelpers

logger = get_logger(__name__)


class TestOutputDefinition(OutputDefinitionBase):
    """
    Output definition for the test_output module.

    This is a simple test implementation that:
    - Generates a new order number
    - Logs the order number and HAWB (test_value input)
    - Does NOT actually create any order in the database

    Used for validating the output execution pipeline works correctly.
    """

    def create_order(
        self,
        input_data: Dict[str, Any],
        helpers: OrderHelpers
    ) -> Dict[str, Any]:
        """
        Test order creation - generates order number and logs without creating actual order.

        Args:
            input_data: Data from pipeline execution, contains "test_value" as HAWB
            helpers: OrderHelpers instance for database operations

        Returns:
            Dict with order_number and hawb
        """
        # Get the test_value input (treated as HAWB for testing)
        hawb = input_data.get("test_value", "")

        # Generate a new order number (this DOES write to LON and OIW tables)
        order_number = helpers.generate_next_order_number()

        # Log the results
        logger.info("=" * 60)
        logger.info("[TEST OUTPUT] Order creation test")
        logger.info(f"[TEST OUTPUT] HAWB: {hawb}")
        logger.info(f"[TEST OUTPUT] Generated Order Number: {order_number}")
        logger.info("[TEST OUTPUT] NOTE: No actual order was created in the orders table")
        logger.info("=" * 60)

        return {
            "order_number": order_number,
            "hawb": hawb,
        }

    def update_order(
        self,
        input_data: Dict[str, Any],
        existing_order_number: int,
        helpers: OrderHelpers
    ) -> Dict[str, Any]:
        """
        Test order update - not implemented for test module.

        Args:
            input_data: Data from pipeline execution
            existing_order_number: The order number to update
            helpers: OrderHelpers instance

        Returns:
            Dict with order_number, hawb, and empty fields_updated
        """
        hawb = input_data.get("test_value", "")

        logger.info("=" * 60)
        logger.info("[TEST OUTPUT] Order update test (no-op)")
        logger.info(f"[TEST OUTPUT] HAWB: {hawb}")
        logger.info(f"[TEST OUTPUT] Existing Order Number: {existing_order_number}")
        logger.info("[TEST OUTPUT] NOTE: No actual order was updated")
        logger.info("=" * 60)

        return {
            "order_number": float(existing_order_number),
            "hawb": hawb,
            "fields_updated": [],
        }
