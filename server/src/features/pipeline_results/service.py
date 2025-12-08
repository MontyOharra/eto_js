"""
Pipeline Result Service

Service for executing output modules after pipeline execution completes.
Handles order creation/updates via output definitions.
Also manages output channel type catalog sync.
"""

from typing import Any, Dict, TYPE_CHECKING

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError
from shared.database.data_database_manager import DataDatabaseManager
from shared.database.repositories import OutputChannelTypeRepository
from shared.types.output_channels import OutputChannelTypeCreate

from features.pipeline_results.helpers.orders import OrderHelpers
from features.pipeline_results.output_definitions.base import OutputDefinitionBase
from features.pipeline_results.output_definitions.test_output import TestOutputDefinition
from features.pipeline_results.output_channels import OUTPUT_CHANNEL_DEFINITIONS

if TYPE_CHECKING:
    from shared.database.connection import DatabaseConnectionManager

logger = get_logger(__name__)


class PipelineResultService:
    """
    Service for processing pipeline output results.

    Responsible for:
    - Executing order creation via output definitions
    - Executing order updates via output definitions
    - Providing order helpers to output definitions

    The EtoRunsService orchestrates when to call these methods and handles
    all ETO database persistence.
    """

    # ==================== Dependencies ====================

    _connection_manager: 'DatabaseConnectionManager'
    _data_database_manager: DataDatabaseManager
    _database_name: str
    _order_helpers: OrderHelpers

    # ==================== Initialization ====================

    def __init__(
        self,
        connection_manager: 'DatabaseConnectionManager',
        data_database_manager: DataDatabaseManager,
        database_name: str = "htc_300_db"
    ) -> None:
        """
        Initialize the service.

        Args:
            connection_manager: DatabaseConnectionManager for ETO database access
            data_database_manager: DataDatabaseManager for business database access
            database_name: Name of the database containing order tables
        """
        logger.debug("Initializing PipelineResultService...")

        self._connection_manager = connection_manager
        self._data_database_manager = data_database_manager
        self._database_name = database_name

        # Create order helpers instance
        self._order_helpers = OrderHelpers(data_database_manager, database_name)

        # Registry of output definitions by module_id
        self._definitions: Dict[str, OutputDefinitionBase] = {}

        # Register built-in output definitions
        self._register_builtin_definitions()

        logger.info("PipelineResultService initialized successfully")

    def _register_builtin_definitions(self) -> None:
        """Register all built-in output definitions."""
        # Test output module (for testing the output execution system)
        self.register_definition("test_output", TestOutputDefinition())

    # ==================== Public API ====================

    def register_definition(self, module_id: str, definition: OutputDefinitionBase) -> None:
        """
        Register an output definition for a module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            definition: The definition instance that handles order creation/update
        """
        self._definitions[module_id] = definition
        logger.debug(f"Registered output definition for module: {module_id}")

    def create_order(
        self,
        module_id: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute order creation for the given module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            input_data: Data collected from pipeline execution

        Returns:
            Dict containing order_number, hawb, and other result data

        Raises:
            OutputExecutionError: If module not found or order creation fails
        """
        definition = self._get_definition(module_id)

        logger.info(f"Creating order via {module_id} for HAWB: {input_data.get('hawb')}")

        # Execute order creation
        result = definition.create_order(input_data, self._order_helpers)

        logger.info(f"Order created: {result.get('order_number')}")
        return result

    def update_order(
        self,
        module_id: str,
        input_data: Dict[str, Any],
        existing_order_number: int,
    ) -> Dict[str, Any]:
        """
        Execute order update for the given module.

        Args:
            module_id: The output module ID (e.g., "basic_order_output")
            input_data: Data collected from pipeline execution
            existing_order_number: The order number to update

        Returns:
            Dict containing order_number, hawb, fields_updated, and other result data

        Raises:
            OutputExecutionError: If module not found or order update fails
        """
        definition = self._get_definition(module_id)

        logger.info(f"Updating order {existing_order_number} via {module_id}")

        # Execute order update
        result = definition.update_order(input_data, existing_order_number, self._order_helpers)

        logger.info(f"Order updated: {result.get('order_number')}, fields: {result.get('fields_updated')}")
        return result

    # ==================== Properties ====================

    @property
    def order_helpers(self) -> OrderHelpers:
        """Get the order helpers instance."""
        return self._order_helpers

    # ==================== Private Methods ====================

    def _get_definition(self, module_id: str) -> OutputDefinitionBase:
        """Get output definition by module ID."""
        definition = self._definitions.get(module_id)
        if not definition:
            raise OutputExecutionError(f"No output definition registered for module: {module_id}")
        return definition

    # ==================== Output Channel Sync ====================

    def sync_output_channel_types(self) -> Dict[str, Any]:
        """
        Sync output channel type definitions to the database.

        Reads static definitions from OUTPUT_CHANNEL_DEFINITIONS and
        upserts each into the output_channel_types table.

        Returns:
            Dict with sync statistics:
                - total: number of definitions processed
                - created: number of new records created
                - updated: number of existing records updated
                - channel_names: list of all channel names synced
        """
        logger.info("Starting output channel types sync...")

        repo = OutputChannelTypeRepository(connection_manager=self._connection_manager)

        created = 0
        updated = 0
        channel_names = []

        for definition in OUTPUT_CHANNEL_DEFINITIONS:
            # Convert definition to create dataclass
            channel_create = OutputChannelTypeCreate(
                name=definition.name,
                label=definition.label,
                data_type=definition.data_type,
                is_required=definition.is_required,
                category=definition.category,
                description=definition.description,
            )

            # Check if exists to track created vs updated
            existing = repo.get_by_name(definition.name)

            # Upsert the channel type
            repo.upsert(channel_create)

            if existing:
                updated += 1
            else:
                created += 1

            channel_names.append(definition.name)

        logger.info(f"Output channel types sync complete: {created} created, {updated} updated")

        return {
            "total": len(OUTPUT_CHANNEL_DEFINITIONS),
            "created": created,
            "updated": updated,
            "channel_names": channel_names,
        }
