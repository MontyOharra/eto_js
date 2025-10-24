"""
Modules Service - Runtime operations for transformation pipeline modules
Handles module catalog queries and execution
"""
import logging
from typing import Dict, List, Optional, Type, Any

from shared.types import BaseModule, ModuleCatalog
from shared.database.repositories.module_catalog import ModuleCatalogRepository
from shared.utils.registry import ModuleRegistry, get_registry
from exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


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


class ModulesService:
    """
    Runtime service for module operations.
    Provides module catalog access and execution capabilities.
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
        self.module_catalog_repo = ModuleCatalogRepository(connection_manager=connection_manager)

        # Get singleton registry for class loading/caching
        self.registry = get_registry()

        # Auto-discover and register all available modules
        self._auto_discover_modules()

        logger.info("ModulesService initialized")

    def _auto_discover_modules(self):
        """Auto-discover and register all module classes at startup"""
        from shared.utils.registry import auto_discover_modules

        packages_to_scan = [
            "features.modules.transform",
            "features.modules.action",
            "features.modules.logic",
            "features.modules.comparator",
        ]

        try:
            logger.info("Auto-discovering modules from packages...")
            auto_discover_modules(packages_to_scan)

            # Log how many modules were registered
            registered_count = len(self.registry.get_all())
            logger.info(f"Auto-discovery complete: {registered_count} modules registered")
        except Exception as e:
            logger.error(f"Error during module auto-discovery: {e}")
            # Don't fail startup if auto-discovery fails
            # Modules can still be loaded from database

    def get_module_catalog(self, only_active: bool = True) -> list[ModuleCatalog]:
        """
        Get module catalog from database.

        Args:
            only_active: Whether to only include active modules

        Returns:
            List of ModuleCatalog domain objects
        """
        try:
            modules = self.module_catalog_repo.get_all(only_active=only_active)
            logger.debug(f"Retrieved {len(modules)} modules from catalog")
            return modules
        except Exception as e:
            logger.error(f"Failed to get module catalog: {e}")
            return []

    def get_module_info(self, module_id: str) -> ModuleCatalog | None:
        """
        Get detailed information about a specific module from database.

        Args:
            module_id: Module ID to retrieve

        Returns:
            ModuleCatalog object or None if not found
        """
        try:
            module = self.module_catalog_repo.get_by_id(module_id)
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
        module_info = self.get_module_info(module_id)
        if not module_info:
            raise ModuleNotFoundError(f"Module {module_id} not found in catalog")

        if not module_info.is_active:
            raise ModuleLoadError(f"Module {module_id} is inactive")

        # Step 2: Get module class (from cache or dynamic load)
        module_class = self._get_module_class(module_info)

        # Step 3: Execute module
        return self._execute_module_instance(module_class, inputs, config, context)

    def _get_module_class(self, module_info: ModuleCatalog) -> Type[BaseModule]:
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
        module_class = self.registry.get(module_info.id)

        if not module_class and module_info.handler_name:
            # Load dynamically using handler (will be cached)
            logger.debug(f"Loading module {module_info.id} from handler: {module_info.handler_name}")
            module_class = self.registry.load_module_from_handler(module_info.handler_name)

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
            outputs = instance.run(inputs, validated_config, context)
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

    def sync_catalog_to_db(self):
        """
        Sync registered modules from registry to database.
        This should be called after module discovery to ensure database is up to date.
        """
        try:
            # Get all modules from registry in catalog format
            catalog_entries = self.registry.to_catalog_format()

            logger.info(f"Syncing {len(catalog_entries)} modules to database...")

            synced_count = 0
            for entry in catalog_entries:
                try:
                    # Convert to domain object
                    from shared.types import ModuleCatalogCreate, ModuleKind, ModuleMeta

                    module_create = ModuleCatalogCreate(
                        id=entry["id"],
                        version=entry["version"],
                        name=entry["name"],
                        description=entry["description"],
                        module_kind=ModuleKind(entry["module_kind"]),
                        meta=ModuleMeta.model_validate(entry["meta"]),
                        config_schema=entry["config_schema"],
                        handler_name=entry["handler_name"],
                        color=entry["color"],
                        category=entry["category"],
                        is_active=entry["is_active"],
                    )

                    # Upsert to database
                    self.module_catalog_repo.upsert(module_create)
                    synced_count += 1

                except Exception as e:
                    logger.error(f"Failed to sync module {entry.get('id')}: {e}")

            logger.info(f"Successfully synced {synced_count}/{len(catalog_entries)} modules")

        except Exception as e:
            logger.error(f"Failed to sync catalog to database: {e}")
