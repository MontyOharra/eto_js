"""
Modules Service - Runtime operations for transformation pipeline modules

Handles module catalog queries, execution, and registry management.
"""
import logging
from typing import Any

from features.modules.base import BaseModule
from features.modules.output_channel_definitions import OUTPUT_CHANNEL_DEFINITIONS
from features.modules.registry import ModuleRegistry
from shared.database.repositories import OutputChannelTypeRepository
from shared.database.repositories.module import ModuleRepository
from shared.exceptions.service import ObjectNotFoundError
from shared.types.modules import Module
from shared.types.output_channels import OutputChannelType

logger = logging.getLogger(__name__)


# ========== Exceptions ==========

class ModuleNotFoundError(Exception):
    """Raised when a module cannot be found."""
    pass


class ModuleLoadError(Exception):
    """Raised when a module cannot be loaded."""
    pass


class ModuleExecutionError(Exception):
    """Raised when module execution fails."""
    def __init__(self, identifier: str, error: str):
        self.identifier = identifier
        self.error = error
        super().__init__(f"Module {identifier} execution failed: {error}")


# ========== Main Service ==========

class ModulesService:
    """
    Runtime service for module operations.
    Provides module catalog access, execution, and registry management.

    Architecture:
    - Registry: In-memory class loading and caching
    - Repository: Database persistence of module catalog
    - Service: Orchestration between registry and repository
    """

    def __init__(self, connection_manager) -> None:
        """
        Initialize service with database connection.

        Args:
            connection_manager: Database connection manager
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.module_repository = ModuleRepository(connection_manager=connection_manager)

        # Create internal registry instance (not singleton)
        self._registry = ModuleRegistry()
        logger.debug(f"ModulesService registry instance ID: {id(self._registry)}")

        # Auto-discover and register all available modules
        self._auto_discover_modules()

        logger.info("ModulesService initialized")

    def _auto_discover_modules(self) -> None:
        """
        Auto-discover and register all module classes at startup.
        Recursively scans the features/modules/definitions directory.
        """
        try:
            logger.info("Auto-discovering modules from features.modules.definitions...")

            # Scan the definitions directory within the modules feature
            self._registry.auto_discover(["features.modules.definitions"])

            # Log how many modules were registered
            registered_count = len(self._registry.get_all())
            logger.info(f"Auto-discovery complete: {registered_count} modules registered")
        except Exception as e:
            logger.error(f"Error during module auto-discovery: {e}")
            # Don't fail startup if auto-discovery fails
            # Modules can still be loaded from database

    # ========== Public API - Catalog Operations ==========

    def list_modules(
        self,
        kind: str | None = None,
        only_active: bool = True
    ) -> list[Module]:
        """
        Get module catalog from database.

        Args:
            kind: Optional filter by module kind
            only_active: Whether to only include active modules

        Returns:
            List of Module domain objects
        """
        try:
            if kind:
                modules = self.module_repository.get_by_kind(kind, only_active=only_active)
            else:
                modules = self.module_repository.get_all(only_active=only_active)

            logger.debug(f"Retrieved {len(modules)} modules from catalog")
            return modules
        except Exception as e:
            logger.error(f"Failed to get module catalog: {e}")
            return []

    def list_latest_modules(self, only_active: bool = True) -> list[Module]:
        """
        Get latest version of each module for frontend catalog display.

        Returns only one entry per module identifier (the highest version),
        suitable for the module pane where users select modules to add.

        Args:
            only_active: Whether to only include active modules

        Returns:
            List of Module domain objects (one per identifier, latest version)
        """
        try:
            modules = self.module_repository.get_latest_versions(only_active=only_active)
            logger.debug(f"Retrieved {len(modules)} latest module versions")
            return modules
        except Exception as e:
            logger.error(f"Failed to get latest module versions: {e}")
            return []

    def get_module_by_id(self, id: int) -> Module | None:
        """
        Get module by primary key (int).

        Args:
            id: Module primary key

        Returns:
            Module object or None if not found
        """
        try:
            module = self.module_repository.get_by_id(id)
            if module:
                logger.debug(f"Retrieved module by id={id}: {module.identifier}")
            else:
                logger.warning(f"Module not found: id={id}")
            return module
        except Exception as e:
            logger.error(f"Failed to get module by id={id}: {e}")
            return None

    def get_module(
        self,
        identifier: str,
        version: str | None = None
    ) -> Module | None:
        """
        Get detailed information about a specific module from database.

        Args:
            identifier: Module identifier (e.g., "text_cleaner")
            version: Optional specific version (defaults to latest active)

        Returns:
            Module object or None if not found
        """
        try:
            if version:
                module = self.module_repository.get_by_identifier_version(identifier, version)
            else:
                module = self.module_repository.get_by_identifier(identifier)

            if module:
                logger.debug(f"Retrieved module info for: {identifier}")
            else:
                logger.warning(f"Module not found in catalog: {identifier}")
            return module
        except ObjectNotFoundError:
            logger.warning(f"Module not found: {identifier}")
            return None
        except Exception as e:
            logger.error(f"Failed to get module info for {identifier}: {e}")
            return None

    # ========== Execution Operations ==========

    def execute_module(
        self,
        identifier: str,
        inputs: dict[str, Any],
        config: dict[str, Any],
        context: Any | None = None
    ) -> dict[str, Any]:
        """
        Execute a module with given inputs and configuration.

        Args:
            identifier: Module identifier to execute
            inputs: Input values keyed by node ID
            config: Configuration values
            context: Optional execution context

        Returns:
            Output values from module execution

        Raises:
            ModuleNotFoundError: If module not found in catalog
            ModuleLoadError: If module class cannot be loaded
            ModuleExecutionError: If module execution fails
        """
        # Step 1: Get module metadata from database
        module_info = self.get_module(identifier)
        if not module_info:
            raise ModuleNotFoundError(f"Module {identifier} not found in catalog")

        if not module_info.is_active:
            raise ModuleLoadError(f"Module {identifier} is inactive")

        # Step 2: Get module class (from cache or dynamic load)
        module_class = self._get_module_class(module_info)

        # Step 3: Execute module
        return self._execute_module_instance(module_class, inputs, config, context)

    def _get_module_class(self, module_info: Module) -> type[BaseModule]:
        """
        Get module class from registry, loading if needed.

        Args:
            module_info: Module catalog entry

        Returns:
            Module class

        Raises:
            ModuleLoadError: If module cannot be loaded
        """
        # Try registry first (fast path - may be cached)
        # Registry uses identifier (string), not id (int)
        module_class = self._registry.get(module_info.identifier)

        if not module_class and module_info.handler_name:
            # Load dynamically using handler (will be cached)
            logger.debug(f"Loading module {module_info.identifier} from handler: {module_info.handler_name}")
            module_class = self._registry.load_module_from_handler(module_info.handler_name)

        if not module_class:
            raise ModuleLoadError(f"Cannot load module class for {module_info.identifier}")

        return module_class

    def _execute_module_instance(
        self,
        module_class: type[BaseModule],
        inputs: dict[str, Any],
        config: dict[str, Any],
        context: Any | None
    ) -> dict[str, Any]:
        """
        Execute a module instance with validation.

        Args:
            module_class: Module class to instantiate and execute
            inputs: Input values
            config: Configuration values
            context: Execution context

        Returns:
            Output values from module

        Raises:
            ModuleExecutionError: If execution fails
        """
        try:
            # Create module instance
            instance = module_class()

            # Validate and parse configuration
            validated_config = module_class.ConfigModel(**config)

            # Prepare context if needed
            if context is None:
                context = self._create_default_context(inputs)

            # Execute module
            logger.debug(f"Executing module {module_class.id} with {len(inputs)} inputs")
            outputs = instance.run(inputs, validated_config.model_dump(), context)
            logger.debug(f"Module {module_class.id} produced {len(outputs) if outputs else 0} outputs")

            return outputs or {}

        except Exception as e:
            logger.error(f"Module {module_class.id} execution failed: {e}")
            raise ModuleExecutionError(module_class.id, str(e))

    def _create_default_context(self, inputs: dict[str, Any]) -> Any:
        """
        Create a default execution context for modules.

        Args:
            inputs: Input values

        Returns:
            Context object with basic structure
        """
        return type('Context', (), {
            'instance_ordered_inputs': list(inputs.items()),
            'instance_ordered_outputs': []
        })()

    # ========== Registry Sync Operations ==========

    def rediscover_modules(self) -> int:
        """
        Re-scan the codebase for module definitions.

        Clears the current registry and re-runs auto-discovery to pick up
        any new modules or versions that were added.

        Returns:
            Number of modules discovered
        """
        logger.info("Re-discovering modules...")

        # Clear existing registry
        self._registry.clear()

        # Re-run auto-discovery
        self._auto_discover_modules()

        count = len(self._registry.get_all())
        logger.info(f"Re-discovery complete: {count} modules found")

        return count

    def sync_modules(self, refresh: bool = False) -> dict[str, Any]:
        """
        Sync module definitions to database with detailed results.

        This is the main entry point for module syncing, used by both
        startup and the admin API endpoint.

        Args:
            refresh: If True, re-scan codebase for new modules before syncing

        Returns:
            Dict with sync results:
                - success: bool
                - modules_discovered: int
                - modules_synced: int
                - modules_failed: int
                - results: list of per-module results
                - message: str
        """
        results: list[dict[str, Any]] = []
        synced_count = 0
        failed_count = 0

        try:
            # Step 1: Optionally re-discover modules
            if refresh:
                self.rediscover_modules()

            # Step 2: Get all registered modules as ModuleCreate objects
            catalog_entries = self._registry.to_catalog_entries()

            if not catalog_entries:
                logger.warning("No modules found to sync")
                return {
                    "success": True,
                    "modules_discovered": 0,
                    "modules_synced": 0,
                    "modules_failed": 0,
                    "results": [],
                    "message": "No modules found to sync. Check module packages and decorators."
                }

            # Build set of module refs (identifier, version) from registry
            registry_refs = {(m.identifier, m.version) for m in catalog_entries}

            logger.info(f"Syncing {len(catalog_entries)} modules to database...")

            # Step 3: Sync each module and track results
            for module_create in catalog_entries:
                try:
                    self.module_repository.upsert(module_create)
                    synced_count += 1

                    results.append({
                        "id": module_create.identifier,
                        "name": module_create.name,
                        "status": "success",
                        "message": None
                    })
                    logger.debug(f"Synced module: {module_create.identifier}")

                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)

                    results.append({
                        "id": module_create.identifier,
                        "name": module_create.name,
                        "status": "error",
                        "message": error_msg
                    })
                    logger.error(f"Failed to sync module {module_create.identifier}: {e}")

            # Step 4: Soft-delete modules no longer in registry
            db_modules = self.module_repository.get_all(only_active=True)
            removed_count = 0

            for db_module in db_modules:
                db_ref = (db_module.identifier, db_module.version)
                if db_ref not in registry_refs:
                    try:
                        self.module_repository.delete(db_module.id)
                        removed_count += 1
                        logger.info(f"Deactivated obsolete module: {db_module.identifier}:{db_module.version}")
                    except Exception as e:
                        logger.error(f"Failed to deactivate obsolete module {db_module.identifier}: {e}")

            if removed_count > 0:
                logger.info(f"Deactivated {removed_count} obsolete modules")

            # Build response
            success = failed_count == 0
            message = f"Successfully synced {synced_count} modules"
            if failed_count > 0:
                message += f", {failed_count} failed"
            if removed_count > 0:
                message += f", {removed_count} deactivated"

            logger.info(message)

            return {
                "success": success,
                "modules_discovered": len(catalog_entries),
                "modules_synced": synced_count,
                "modules_failed": failed_count,
                "results": results,
                "message": message
            }

        except Exception as e:
            logger.error(f"Fatal error during module sync: {e}")
            return {
                "success": False,
                "modules_discovered": 0,
                "modules_synced": synced_count,
                "modules_failed": failed_count,
                "results": results,
                "message": f"Fatal error: {str(e)}"
            }

    def sync_registry_to_database(self) -> None:
        """
        Sync registered modules from registry to database.

        Simple wrapper for startup use - calls sync_modules without refresh.
        For detailed results, use sync_modules() directly.
        """
        self.sync_modules(refresh=False)

    def get_registry_stats(self) -> dict[str, Any]:
        """
        Get registry statistics (registered modules, cache stats).

        Returns:
            Dictionary with registry statistics
        """
        registered_modules = self._registry.get_all()
        cache_stats = self._registry.get_cache_stats()

        return {
            "registered_count": len(registered_modules),
            "registered_modules": list(registered_modules.keys()),
            "cache_stats": cache_stats
        }

    # ========== Output Channel Operations ==========

    def list_output_channel_types(self) -> list[OutputChannelType]:
        """
        Get all output channel type definitions from database.

        Returns the catalog of available output channel types that can be
        placed in pipelines to collect data for the pending orders system.

        Returns:
            List of OutputChannelType domain objects
        """
        try:
            repo = OutputChannelTypeRepository(connection_manager=self.connection_manager)
            channels = repo.get_all()
            logger.debug(f"Retrieved {len(channels)} output channel types")
            return channels
        except Exception as e:
            logger.error(f"Failed to get output channel types: {e}")
            return []

    def sync_output_channel_types(self) -> dict[str, Any]:
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

        repo = OutputChannelTypeRepository(connection_manager=self.connection_manager)

        created = 0
        updated = 0
        channel_names = []

        for definition in OUTPUT_CHANNEL_DEFINITIONS:
            # Check if exists to track created vs updated
            existing = repo.get_by_name(definition.name)

            # Upsert the channel type (definition is already OutputChannelTypeCreate)
            repo.upsert(definition)

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
