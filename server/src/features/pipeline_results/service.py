"""
Pipeline Result Service

Service for executing output modules after pipeline execution completes.
Handles HAWB checking, order creation/updates, and confirmation emails.
"""

import logging
from typing import Any, Dict, Optional

from shared.exceptions import OutputExecutionError
from features.pipeline_results.output_definitions.base import OutputDefinitionBase

logger = logging.getLogger(__name__)


class PipelineResultService:
    """
    Service for processing pipeline output results.

    Responsible for:
    - Checking HAWB existence in orders database
    - Executing order creation via output definitions
    - Executing order updates via output definitions
    - Sending confirmation emails

    The EtoRunsService orchestrates when to call these methods and handles
    all ETO database persistence.
    """

    def __init__(self, helpers: Any):
        """
        Initialize the service.

        Args:
            helpers: Helper utilities container with order, address, and email helpers
        """
        self._helpers = helpers

        # Registry of output definitions by module_id
        # Definitions are registered here as they are implemented
        self._definitions: Dict[str, OutputDefinitionBase] = {}

    def register_definition(self, module_id: str, definition: OutputDefinitionBase) -> None:
        """
        Register an output definition for a module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            definition: The definition instance that handles order creation/update
        """
        self._definitions[module_id] = definition
        logger.debug(f"Registered output definition for module: {module_id}")

    def check_hawb(self, hawb: str) -> Dict[str, Any]:
        """
        Check if HAWB exists in the orders database.

        Used by EtoRunsService to determine if this is a create or update flow.

        Args:
            hawb: House Air Waybill number to check

        Returns:
            Dict with:
            - count: Number of orders found with this HAWB
            - existing_order: Full order data if count == 1, None otherwise
            - error: "multiple_hawb" if count > 1, None otherwise
        """
        orders = self._helpers.order.find_orders_by_hawb(hawb)
        count = len(orders)

        if count == 0:
            return {"count": 0, "existing_order": None, "error": None}
        elif count == 1:
            order_number = orders[0]["order_number"]
            existing_order = self._helpers.order.get_order_details(order_number)
            return {"count": 1, "existing_order": existing_order, "error": None}
        else:
            return {"count": count, "existing_order": None, "error": "multiple_hawb"}

    def create_order(
        self,
        module_id: str,
        input_data: Dict[str, Any],
        source_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute order creation for the given module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            input_data: Data collected from pipeline execution
            source_email: Email address to send confirmation to (None if manual upload)

        Returns:
            Dict containing order_number, hawb, and other result data

        Raises:
            OutputExecutionError: If module not found or order creation fails
        """
        definition = self._get_definition(module_id)

        logger.info(f"Creating order via {module_id} for HAWB: {input_data.get('hawb')}")

        # Execute order creation
        result = definition.create_order(input_data, self._helpers)

        # Send confirmation email if source email provided
        if source_email:
            self._send_email(
                definition=definition,
                action="create",
                input_data=input_data,
                result=result,
                to_address=source_email
            )

        logger.info(f"Order created: {result.get('order_number')}")
        return result

    def update_order(
        self,
        module_id: str,
        input_data: Dict[str, Any],
        existing_order_number: int,
        source_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute order update for the given module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            input_data: Data collected from pipeline execution
            existing_order_number: The order number to update
            source_email: Email address to send confirmation to (None if manual upload)

        Returns:
            Dict containing order_number, hawb, fields_updated, and other result data

        Raises:
            OutputExecutionError: If module not found or order update fails
        """
        definition = self._get_definition(module_id)

        logger.info(f"Updating order {existing_order_number} via {module_id}")

        # Execute order update
        result = definition.update_order(input_data, existing_order_number, self._helpers)

        # Send confirmation email if source email provided
        if source_email:
            self._send_email(
                definition=definition,
                action="update",
                input_data=input_data,
                result=result,
                to_address=source_email
            )

        logger.info(f"Order updated: {result.get('order_number')}, fields: {result.get('fields_updated')}")
        return result

    def _get_definition(self, module_id: str) -> OutputDefinitionBase:
        """Get output definition by module ID."""
        definition = self._definitions.get(module_id)
        if not definition:
            raise OutputExecutionError(f"No output definition registered for module: {module_id}")
        return definition

    def _send_email(
        self,
        definition: OutputDefinitionBase,
        action: str,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
        to_address: str
    ) -> None:
        """
        Send confirmation email using the definition's templates.

        Args:
            definition: The output definition with email templates
            action: "create" or "update"
            input_data: Pipeline output data
            result: Order creation/update result
            to_address: Recipient email address
        """
        try:
            # Merge data for template interpolation
            template_data = {**input_data, **result}

            # Select template based on action
            if action == "create":
                subject = definition.email_subject_create.format(**template_data)
                body = definition.email_body_create.format(**template_data)
            else:
                subject = definition.email_subject_update.format(**template_data)
                body = definition.email_body_update.format(**template_data)

            self._helpers.email.send(to_address, subject, body)
            logger.info(f"Confirmation email sent to {to_address}")

        except Exception as e:
            # Log but don't fail the order operation for email errors
            logger.error(f"Failed to send confirmation email: {e}")
