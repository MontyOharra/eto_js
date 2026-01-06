"""
Customer Picker Output Module
Provides a dropdown to select a customer and outputs the customer ID
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class CustomerPickerConfig(BaseModel):
    """Configuration for Customer Picker"""
    customer_name: str = Field(
        default="",
        description="Select customer from the list"
    )


@register
class CustomerPicker(MiscModule):
    """
    Customer Picker module
    Output-only module that provides a dropdown to select a customer
    Returns the selected customer's ID
    """

    # Class metadata
    id = "customer_picker"
    version = "1.0.0"
    title = "Customer Picker"
    description = "Select a customer from dropdown and output customer ID"
    category = "Database"
    color = "#EAB308"  # Yellow

    # Configuration model
    ConfigModel = CustomerPickerConfig

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Generate config schema with dynamic customer dropdown.

        Queries the Customers table and injects customer names as enum options
        for the frontend to render as a dropdown.
        """
        # Get base schema from Pydantic model
        schema = cls.ConfigModel.model_json_schema()

        # Try to inject available customers from database
        try:
            from shared.services.service_container import ServiceContainer

            if ServiceContainer.is_initialized():
                # Get database connection
                access_db_manager = ServiceContainer._access_database_manager
                if not access_db_manager:
                    logger.warning("AccessDatabaseManager not available")
                    return schema

                connection = access_db_manager.get_connection("htc_300")

                # Query active customers, ordered by name
                sql = """
                SELECT CustomerID, Customer
                FROM [HTC300_G030_T010 Customers]
                WHERE Cus_Status = True
                ORDER BY Customer
                """

                logger.debug("Fetching customer list for dropdown")

                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    rows = cursor.fetchall()

                if rows:
                    # Extract customer names for dropdown options
                    customer_options = [row[1] for row in rows if row[1]]  # row[1] is Customer name

                    # Inject as enum for dropdown rendering
                    schema['properties']['customer_name']['enum'] = customer_options

                    logger.info(f"Injected {len(customer_options)} customers into dropdown")

                    # Set default to first customer if current default is empty
                    if not schema['properties']['customer_name'].get('default') and customer_options:
                        schema['properties']['customer_name']['default'] = customer_options[0]
                else:
                    logger.warning("No active customers found in database")

            else:
                logger.warning("ServiceContainer not initialized - cannot inject customers")

        except Exception as e:
            logger.error(f"Could not inject customer options into schema: {e}")
            # Schema will still work, just won't have dropdown options

        return schema

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[]  # No inputs - output only module
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="customer_id",
                            typing=NodeTypeRule(allowed_types=["int"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="customer_name",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: CustomerPickerConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute customer picker - looks up customer ID by name

        Args:
            inputs: Empty dictionary (no inputs for this module)
            cfg: Validated configuration with selected customer_name
            context: Execution context with ordered outputs
            services: AccessDatabaseManager for database access

        Returns:
            Dictionary with customer_id and customer_name outputs
        """
        # Validate services
        if services is None:
            raise ValueError("AccessDatabaseManager services required for customer_picker")

        # Validate that a customer was selected
        if not cfg.customer_name:
            raise ValueError("No customer selected. Please select a customer from the dropdown.")

        logger.info(f"Looking up customer ID for: '{cfg.customer_name}'")

        # Get database connection
        try:
            connection = services.get_connection("htc_300")
        except Exception as e:
            logger.error(f"Failed to get database connection 'htc_300': {e}")
            raise ValueError(f"Could not connect to database: {e}")

        # Query for customer ID by name
        sql = """
        SELECT CustomerID, Customer
        FROM [HTC300_G030_T010 Customers]
        WHERE Customer = ? AND Cus_Status = True
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (cfg.customer_name,))
                row = cursor.fetchone()
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise ValueError(f"Database query failed: {e}")

        # Handle customer not found
        if row is None:
            logger.error(f"Customer '{cfg.customer_name}' not found in database")
            raise ValueError(
                f"Customer '{cfg.customer_name}' not found in database. "
                f"The customer may have been deactivated or deleted."
            )

        customer_id = row[0]
        customer_name = row[1]

        logger.info(f"Found customer: '{customer_name}' (ID: {customer_id})")

        # Get output node IDs
        customer_id_output = context.outputs[0].node_id
        customer_name_output = context.outputs[1].node_id

        return {
            customer_id_output: int(customer_id),
            customer_name_output: customer_name
        }
