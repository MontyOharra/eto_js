"""
Modules Service - Runtime operations for transformation pipeline modules
Handles module catalog queries, execution, and registry management
"""
import logging
from typing import Dict, Optional, Type, Any

from shared.types.modules import BaseModule, Module
from shared.database.repositories.module import ModuleRepository
from shared.exceptions.service import ObjectNotFoundError

from features.modules.utils.registry import ModuleRegistry

logger = logging.getLogger(__name__)


# ========== Exceptions ==========

class ModuleNotFoundError(Exception):
    """Raised when a module cannot be found"""
    pass


class ModuleLoadError(Exception):
    """Raised when a module cannot be loaded"""
    pass


class ModuleExecutionError(Exception):
    """Raised when module execution fails"""
    def __init__(self, module_id: str, error: str):
        self.module_id = module_id
        self.error = error
        super().__init__(f"Module {module_id} execution failed: {error}")


# ========== Main Service ==========

class ModulesService:
    """
    Runtime service for module operations.
    Provides module catalog access, execution, and registry management.

    Architecture:
    - Registry: In-memory class loading and caching (from utils)
    - Repository: Database persistence of module catalog
    - Service: Orchestration between registry and repository
    """

    def __init__(self, connection_manager):
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
        logger.error(f"DEBUG: ModulesService registry instance ID: {id(self._registry)}")

        # Auto-discover and register all available modules
        self._auto_discover_modules()

        logger.info("ModulesService initialized")

    def _auto_discover_modules(self):
        """
        Auto-discover and register all module classes at startup.
        Recursively scans the entire pipeline_modules directory.
        """
        try:
            logger.info("Auto-discovering modules from pipeline_modules...")

            # Just scan the entire pipeline_modules directory - no package list needed!
            self._registry.auto_discover(["pipeline_modules"])

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
        kind: Optional[str] = None,
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

    def get_module(
        self,
        module_id: str,
        version: Optional[str] = None
    ) -> Module | None:
        """
        Get detailed information about a specific module from database.

        Args:
            module_id: Module ID to retrieve
            version: Optional specific version (defaults to latest active)

        Returns:
            Module object or None if not found
        """
        try:
            if version:
                module = self.module_repository.get_by_module_ref(module_id, version)
            else:
                module = self.module_repository.get_by_id(module_id)

            if module:
                logger.debug(f"Retrieved module info for: {module_id}")
            else:
                logger.warning(f"Module not found in catalog: {module_id}")
            return module
        except ObjectNotFoundError:
            logger.warning(f"Module not found: {module_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get module info for {module_id}: {e}")
            return None

    # ========== Execution Operations ==========

    def execute_module(
        self,
        module_id: str,
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a module with given inputs and configuration.

        Args:
            module_id: Module ID to execute
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
        module_info = self.get_module(module_id)
        if not module_info:
            raise ModuleNotFoundError(f"Module {module_id} not found in catalog")

        if not module_info.is_active:
            raise ModuleLoadError(f"Module {module_id} is inactive")

        # Step 2: Get module class (from cache or dynamic load)
        module_class = self._get_module_class(module_info)

        # Step 3: Execute module
        return self._execute_module_instance(module_class, inputs, config, context)

    def _get_module_class(self, module_info: Module) -> Type[BaseModule]:
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
        module_class = self._registry.get(module_info.id)

        if not module_class and module_info.handler_name:
            # Load dynamically using handler (will be cached)
            logger.debug(f"Loading module {module_info.id} from handler: {module_info.handler_name}")
            module_class = self._registry.load_module_from_handler(module_info.handler_name)

        if not module_class:
            raise ModuleLoadError(f"Cannot load module class for {module_info.id}")

        return module_class

    def _execute_module_instance(
        self,
        module_class: Type[BaseModule],
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        context: Optional[Any]
    ) -> Dict[str, Any]:
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

    def _create_default_context(self, inputs: Dict[str, Any]) -> Any:
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

    def sync_registry_to_database(self):
        """
        Sync registered modules from registry to database.
        This should be called after module discovery to ensure database is up to date.

        Process:
        1. Get all registered modules as ModuleCreate dataclasses
        2. Upsert each to database
        """
        try:
            # Get all modules from registry as ModuleCreate dataclasses
            catalog_entries = self._registry.to_catalog_entries()

            logger.info(f"Syncing {len(catalog_entries)} modules to database...")

            synced_count = 0
            for module_create in catalog_entries:
                try:
                    # Upsert to database (repository handles all serialization)
                    self.module_repository.upsert(module_create)
                    synced_count += 1

                except Exception as e:
                    logger.error(f"Failed to sync module {module_create.id}: {e}")

            logger.info(f"Successfully synced {synced_count}/{len(catalog_entries)} modules")

        except Exception as e:
            logger.error(f"Failed to sync registry to database: {e}")

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics (registered modules, cache stats)

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
