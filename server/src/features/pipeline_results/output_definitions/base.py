"""
Output Definition Base Class

Abstract base class that all output module definitions must implement.
Defines the contract for order creation/update and email templates.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class OutputDefinitionBase(ABC):
    """
    Base class for output module definitions.

    Each output module (e.g., basic_order_output) has a corresponding definition
    that implements the actual order creation/update logic.

    Implementations must:
    1. Define email templates for create and update confirmations
    2. Implement create_order() for new orders
    3. Implement update_order() for existing orders
    """

    # Email templates - subclasses must define these
    # Templates use {placeholder} format for string interpolation
    # Available placeholders: all input_data fields + order_number, hawb, etc.
    email_subject_create: str
    email_subject_update: str
    email_body_create: str
    email_body_update: str

    @abstractmethod
    def create_order(
        self,
        input_data: Dict[str, Any],
        helpers: Any
    ) -> Dict[str, Any]:
        """
        Create a new order from the pipeline output data.

        Args:
            input_data: Data collected from pipeline execution (e.g., hawb, customer_id, times, addresses)
            helpers: Helper utilities for order operations, address resolution, etc.

        Returns:
            Dict containing at minimum:
            {
                "order_number": int,
                "hawb": str,
                ... additional fields for result storage and email templates
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
        helpers: Any
    ) -> Dict[str, Any]:
        """
        Update an existing order with new data from pipeline output.

        Args:
            input_data: Data collected from pipeline execution
            existing_order_number: The order number to update
            helpers: Helper utilities for order operations, address resolution, etc.

        Returns:
            Dict containing at minimum:
            {
                "order_number": int,
                "hawb": str,
                "fields_updated": list[str],  # Which fields were changed
                ... additional fields for result storage and email templates
            }

        Raises:
            OutputExecutionError: If order update fails
        """
        pass
