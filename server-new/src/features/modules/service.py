"""
Modules Service - Runtime operations for transformation pipeline modules
Handles module catalog queries, execution, and registry management
"""
import logging
import re
import importlib
import pkgutil
from typing import Dict, List, Optional, Type, Any, Tuple
from datetime import datetime

from shared.types.modules import (
    BaseModule,
    Module,
    ModuleCreate,
    ModuleKind,
    AllowedModuleNodeTypes
)
from shared.database.repositories.module import ModuleRepository
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


# ========== Global Registration Hook ==========
#
# This allows module definition files to use @register decorator
# The decorator adds modules to a global pending list, which is
# then consumed by ModuleRegistry during auto-discovery

_pending_registrations: List[Type[BaseModule]] = []


def register(module_class: Type[BaseModule]) -> Type[BaseModule]:
    """
    Decorator to mark a module class for registration.

    Usage:
        @register
        class MyModule(TransformModule):
            ...

    This adds the module to a pending list that will be processed
    by ModuleRegistry during auto-discovery.
    """
    _pending_registrations.append(module_class)
    logger.debug(f"Queued module for registration: {module_class.__name__}")
    return module_class


def _consume_pending_registrations(registry: 'ModuleRegistry') -> int:
    """
    Internal function to consume pending registrations and add them to a registry.
    Returns the number of modules registered.
    """
    global _pending_registrations
    count = 0
    for module_class in _pending_registrations:
        try:
            registry.register(module_class)
            count += 1
        except Exception as e:
            logger.error(f"Failed to register {module_class.__name__}: {e}")

    # Clear the pending list
    _pending_registrations = []
    return count


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


# ========== Internal Registry Components ==========

class ModuleSecurityValidator:
    """Security validation for module loading"""

    ALLOWED_PACKAGES = [
        "features.modules.transform",
        "features.modules.action",
        "features.modules.logic",
        "features.modules.comparator",
    ]

    BLOCKED_PATTERNS = [
        r".*\.\.",  # Path traversal
        r".*__pycache__",
        r".*\.pyc",
        r".*exec.*",
        r".*eval.*",
        r".*os\.system",
        r".*subprocess",
    ]

    @classmethod
    def validate_handler_path(cls, handler_name: str) -> Tuple[bool, str]:
        """Validate a handler path is safe to load"""
        if not handler_name or ":" not in handler_name:
            return False, "Invalid handler format"

        module_path, class_name = handler_name.split(":", 1)

        # Check for blocked patterns
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern and re.match(pattern, handler_name):
                return False, f"Blocked pattern detected: {pattern}"

        # Check allowed packages
        is_allowed = any(
            module_path.startswith(pkg)
            for pkg in cls.ALLOWED_PACKAGES
            if pkg
        )

        if not is_allowed:
            return False, f"Module not in allowed packages"

        if not class_name.isidentifier():
            return False, f"Invalid class name: {class_name}"

        return True, "Valid"


class ModuleCache:
    """Simple cache for loaded modules"""

    def __init__(self, max_size: int = 50, ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[Type[BaseModule], datetime]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Type[BaseModule]]:
        """Get module from cache"""
        if key in self._cache:
            module_class, cached_at = self._cache[key]
            age = (datetime.now() - cached_at).total_seconds()
            if age < self.ttl_seconds:
                self.hits += 1
                return module_class
            else:
                del self._cache[key]

        self.misses += 1
        return None

    def put(self, key: str, module_class: Type[BaseModule]):
        """Add module to cache"""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

        self._cache[key] = (module_class, datetime.now())

    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0


class ModuleRegistry:
    """
    Registry for transformation pipeline modules
    Handles registration, discovery, and retrieval of module classes
    """

    def __init__(self):
        """Initialize registry"""
        self._registry: Dict[str, Type[BaseModule]] = {}
        self._cache = ModuleCache()
        logger.debug("ModuleRegistry initialized")

    def register(self, module_class: Type[BaseModule]) -> Type[BaseModule]:
        """
        Register a module class with the registry
        Used as a decorator on module classes

        Args:
            module_class: Module class inheriting from BaseModule

        Returns:
            The module class (for decorator pattern)

        Raises:
            ValueError: If module with same ID already registered
        """
        module_id = module_class.id

        if module_id in self._registry:
            existing = self._registry[module_id]
            if existing is not module_class:
                raise ValueError(
                    f"Module '{module_id}' already registered with different class. "
                    f"Existing: {existing.__module__}.{existing.__name__}, "
                    f"New: {module_class.__module__}.{module_class.__name__}"
                )
        else:
            self._registry[module_id] = module_class
            logger.debug(f"Registered module: {module_id} ({module_class.__name__})")

        return module_class

    def get(self, module_id: str) -> Optional[Type[BaseModule]]:
        """
        Get a module class by ID

        Args:
            module_id: Module ID to retrieve

        Returns:
            Module class or None if not found
        """
        return self._registry.get(module_id)

    def get_all(self) -> Dict[str, Type[BaseModule]]:
        """
        Get all registered modules

        Returns:
            Dictionary of module_id -> module_class
        """
        return dict(self._registry)

    def get_by_kind(self, kind: str) -> List[Type[BaseModule]]:
        """
        Get all modules of a specific kind

        Args:
            kind: Module kind ("transform", "action", "logic", "comparator")

        Returns:
            List of module classes of that kind
        """
        return [
            module_class
            for module_class in self._registry.values()
            if module_class.kind == kind
        ]

    def clear(self):
        """Clear all registered modules (useful for testing)"""
        self._registry.clear()
        self._cache.clear()
        logger.debug("Module registry cleared")

    def load_module_from_handler(self, handler_name: str) -> Optional[Type[BaseModule]]:
        """
        Load a module from handler_name with security validation and caching

        Args:
            handler_name: Module handler path (e.g., "module.path:ClassName")

        Returns:
            Module class or None if loading failed
        """
        # Check cache first
        cached_module = self._cache.get(handler_name)
        if cached_module:
            logger.debug(f"Module {handler_name} loaded from cache")
            return cached_module

        # Validate security
        is_valid, error_msg = ModuleSecurityValidator.validate_handler_path(handler_name)
        if not is_valid:
            logger.error(f"Security validation failed for {handler_name}: {error_msg}")
            return None

        try:
            # Parse handler
            module_path, class_name = handler_name.split(":", 1)

            # Import module
            module = importlib.import_module(module_path)

            # Get class
            if not hasattr(module, class_name):
                logger.error(f"Module {module_path} has no class {class_name}")
                return None

            module_class = getattr(module, class_name)

            # Validate it's a proper module
            if not issubclass(module_class, BaseModule):
                logger.error(f"{class_name} is not a valid module (must inherit from BaseModule)")
                return None

            # Cache the loaded module
            self._cache.put(handler_name, module_class)
            logger.info(f"Successfully loaded and cached module from {handler_name}")

            return module_class

        except ImportError as e:
            logger.error(f"Failed to import {module_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading module from {handler_name}: {e}")
            return None

    def resolve_module(self, module_id: str, handler_name: Optional[str] = None) -> Optional[Type[BaseModule]]:
        """
        Resolve a module using multiple strategies:
        1. Check registry (fast)
        2. Try handler_name if provided (flexible)

        Args:
            module_id: Module ID
            handler_name: Optional handler path for dynamic loading

        Returns:
            Module class or None
        """
        # Try registry first
        module_class = self.get(module_id)
        if module_class:
            return module_class

        # Try handler_name if provided
        if handler_name:
            return self.load_module_from_handler(handler_name)

        return None

    def auto_discover(self, package_paths: List[str]):
        """
        Auto-discover and import modules from specified packages
        This will trigger the @register decorators on module classes

        Args:
            package_paths: List of package paths to scan for modules
                          e.g., ["features.modules.transform", "features.modules.action"]
        """
        for package_path in package_paths:
            try:
                logger.info(f"Auto-discovering modules in: {package_path}")

                # Import the package
                package = importlib.import_module(package_path)

                # Get package directory
                if hasattr(package, '__path__'):
                    # Iterate through all modules in the package
                    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                        if not ispkg:  # Skip sub-packages
                            full_module_name = f"{package_path}.{modname}"
                            try:
                                # Import the module (this triggers @register decorators)
                                importlib.import_module(full_module_name)
                                logger.debug(f"Imported module: {full_module_name}")

                                # Consume any pending registrations from this module
                                count = _consume_pending_registrations(self)
                                if count > 0:
                                    logger.debug(f"Registered {count} modules from {full_module_name}")

                            except Exception as e:
                                logger.warning(f"Failed to import {full_module_name}: {e}")
                else:
                    logger.warning(f"Package {package_path} has no __path__ attribute")

            except ImportError as e:
                logger.warning(f"Failed to import package {package_path}: {e}")
            except Exception as e:
                logger.error(f"Error discovering modules in {package_path}: {e}")

        logger.info(f"Auto-discovery complete. {len(self._registry)} modules registered.")

    def to_catalog_entries(self) -> List[ModuleCreate]:
        """
        Convert all registered modules to ModuleCreate dataclasses for database sync

        Returns:
            List of ModuleCreate dataclasses ready for repository
        """
        catalog_entries = []

        for module_id, module_class in self._registry.items():
            try:
                # Get module metadata
                meta = module_class.meta()
                config_schema = module_class.config_schema()

                # Build ModuleCreate dataclass
                entry = ModuleCreate(
                    id=module_class.id,
                    version=getattr(module_class, 'version', '1.0.0'),  # Default version
                    name=module_class.title,
                    description=module_class.description,
                    module_kind=module_class.kind,
                    meta=meta,  # Already a ModuleMeta dataclass
                    config_schema=config_schema,  # Already a dict
                    handler_name=f"{module_class.__module__}:{module_class.__name__}",
                    color=getattr(module_class, 'color', '#3B82F6'),  # Default color
                    category=getattr(module_class, 'category', 'Processing'),  # Default category
                    is_active=True
                )

                catalog_entries.append(entry)
                logger.debug(f"Converted module {module_id} to catalog entry")

            except Exception as e:
                logger.error(f"Failed to convert module {module_id} to catalog entry: {e}")

        return catalog_entries

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._cache.hits + self._cache.misses
        hit_rate = (self._cache.hits / total * 100) if total > 0 else 0

        return {
            "cache_size": len(self._cache._cache),
            "max_size": self._cache.max_size,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_hits": self._cache.hits,
            "total_misses": self._cache.misses,
        }


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

        # Auto-discover and register all available modules
        self._auto_discover_modules()

        logger.info("ModulesService initialized")

    def _auto_discover_modules(self):
        """Auto-discover and register all module classes at startup"""
        packages_to_scan = [
            "features.modules.transform",
            "features.modules.action",
            "features.modules.logic",
            "features.modules.comparator",
        ]

        try:
            logger.info("Auto-discovering modules from packages...")
            self._registry.auto_discover(packages_to_scan)

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
