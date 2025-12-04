"""
Output Definition Base Class

Abstract base class that all output module definitions must implement.
Defines the contract for order creation/update.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from features.pipeline_results.helpers.orders import OrderHelpers


class OutputDefinitionBase(ABC):
    """
    Base class for output module definitions.

    Each output module (e.g., basic_order_output) has a corresponding definition
    that implements the actual order creation/update logic.

    Implementations must:
    1. Implement create_order() for new orders
    2. Implement update_order() for existing orders
    """

    @abstractmethod
    def create_order(
        self,
        input_data: Dict[str, Any],
        helpers: "OrderHelpers"
    ) -> Dict[str, Any]:
        """
        Create a new order from the pipeline output data.

        Args:
            input_data: Data collected from pipeline execution (e.g., hawb, customer_id, times, addresses)
            helpers: OrderHelpers instance for database operations (e.g., generate_next_order_number)

        Returns:
            Dict containing at minimum:
            {
                "order_number": float,
                "hawb": str,
                ... additional fields for result storage
            }

        Raises:
            OutputExecutionError: If order creation fails
        """
        pass

    @abstractmethod
    def update_order(
        self,
        input_data: Dict[str, Any],
        existing_order_number: int,
        helpers: "OrderHelpers"
    ) -> Dict[str, Any]:
        """
        Update an existing order with new data from pipeline output.

        Args:
            input_data: Data collected from pipeline execution
            existing_order_number: The order number to update
            helpers: OrderHelpers instance for database operations

        Returns:
            Dict containing at minimum:
            {
                "order_number": float,
                "hawb": str,
                "fields_updated": list[str],  # Which fields were changed
                ... additional fields for result storage
            }

        Raises:
            OutputExecutionError: If order update fails
        """
        pass
