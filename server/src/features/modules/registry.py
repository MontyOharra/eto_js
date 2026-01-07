"""
Module Registry System

Handles registration, discovery, and retrieval of module classes.
Includes the @register decorator for marking module classes.

Architecture:
- During auto-discovery: Classes are collected in _discovered_classes
- After DB sync: Registry is built with DB IDs as keys via build_from_db()
- At runtime: Lookups use integer DB ID via get()
"""
import importlib
import logging
import pkgutil
import re
from datetime import datetime
from typing import Any

from features.modules.base import BaseModule
from shared.types.modules import Module, ModuleCreate

logger = logging.getLogger(__name__)


# ========== Registration Decorator ==========

# Global pending registrations queue
# Module classes are added here by @register decorator during import
# Then consumed by ModuleRegistry during auto-discovery
_pending_registrations: list[type[BaseModule]] = []


def register(module_class: type[BaseModule]) -> type[BaseModule]:
    """
    Decorator to mark a module class for registration.

    Usage:
        from features.modules.registry import register

        @register
        class MyModule(TransformModule):
            ...

    This adds the module to a pending list that will be processed
    by ModuleRegistry during auto-discovery.

    Args:
        module_class: Module class inheriting from BaseModule

    Returns:
        The module class (for decorator pattern)
    """
    _pending_registrations.append(module_class)
    logger.debug(f"Queued module for registration: {module_class.__name__}")
    return module_class


def consume_pending_registrations(registry: 'ModuleRegistry') -> int:
    """
    Consume pending registrations and add them to a registry.
    Called by ModuleRegistry after importing each module file.

    Args:
        registry: ModuleRegistry instance to register modules into

    Returns:
        Number of modules registered
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


def clear_pending_registrations() -> None:
    """
    Clear all pending registrations without processing them.
    Useful for testing or cleanup scenarios.
    """
    global _pending_registrations
    _pending_registrations = []
    logger.debug("Cleared all pending registrations")


# ========== Security Validator ==========

class ModuleSecurityValidator:
    """Security validation for module loading."""

    ALLOWED_PACKAGES = [
        "features.modules.definitions",
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
    def validate_handler_path(cls, handler_name: str) -> tuple[bool, str]:
        """Validate a handler path is safe to load."""
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
            return False, "Module not in allowed packages"

        if not class_name.isidentifier():
            return False, f"Invalid class name: {class_name}"

        return True, "Valid"


# ========== Module Cache ==========

class ModuleCache:
    """Simple cache for dynamically loaded modules (by handler_name)."""

    def __init__(self, max_size: int = 50, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[type[BaseModule], datetime]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> type[BaseModule] | None:
        """Get module from cache."""
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

    def put(self, key: str, module_class: type[BaseModule]) -> None:
        """Add module to cache."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

        self._cache[key] = (module_class, datetime.now())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0


# ========== Module Registry ==========

class ModuleRegistry:
    """
    Singleton registry for transformation pipeline modules.
    Handles registration, discovery, and retrieval of module classes.

    Architecture:
    - _discovered_classes: Holds module classes found during auto-discovery
    - _registry: Maps DB ID (int) -> module class, built after DB sync
    - Lookups at runtime use integer DB IDs via get()
    """

    _instance: 'ModuleRegistry | None' = None
    _initialized: bool = False

    def __new__(cls) -> 'ModuleRegistry':
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize registry (only once)."""
        if not ModuleRegistry._initialized:
            # Main registry: DB ID (int) -> class (populated after DB sync)
            self._registry: dict[int, type[BaseModule]] = {}

            # Temporary holding area during auto-discovery
            self._discovered_classes: list[type[BaseModule]] = []

            # Cache for dynamically loaded modules
            self._cache = ModuleCache()

            ModuleRegistry._initialized = True
            logger.debug("ModuleRegistry initialized (singleton)")

    def register(self, module_class: type[BaseModule]) -> type[BaseModule]:
        """
        Queue a module class during auto-discovery.

        Classes are held in _discovered_classes until build_from_db() is called
        after database sync, which populates _registry with DB IDs as keys.

        Args:
            module_class: Module class inheriting from BaseModule

        Returns:
            The module class (for decorator pattern)
        """
        # Check for duplicates by (identifier, version)
        key = (module_class.identifier, module_class.version)
        for existing in self._discovered_classes:
            existing_key = (existing.identifier, existing.version)
            if existing_key == key and existing is not module_class:
                raise ValueError(
                    f"Module '{module_class.identifier}:{module_class.version}' already discovered. "
                    f"Existing: {existing.__module__}.{existing.__name__}, "
                    f"New: {module_class.__module__}.{module_class.__name__}"
                )

        if module_class not in self._discovered_classes:
            self._discovered_classes.append(module_class)
            logger.debug(f"Discovered module: {module_class.identifier}:{module_class.version} ({module_class.__name__})")

        return module_class

    def build_from_db(self, db_modules: list[Module]) -> None:
        """
        Build the registry from database records.

        Called after sync_modules() completes. Matches DB records to discovered
        classes by (identifier, version), then stores by integer DB id.

        Args:
            db_modules: List of Module domain objects from database
        """
        self._registry.clear()

        # Build temporary lookup: (identifier, version) -> class
        class_lookup: dict[tuple[str, str], type[BaseModule]] = {}
        for cls in self._discovered_classes:
            key = (cls.identifier, cls.version)
            class_lookup[key] = cls

        # Populate registry keyed by DB id
        for db_module in db_modules:
            key = (db_module.identifier, db_module.version)
            module_class = class_lookup.get(key)
            if module_class:
                self._registry[db_module.id] = module_class
            else:
                logger.warning(
                    f"DB module {db_module.identifier}:{db_module.version} (id={db_module.id}) "
                    f"not found in discovered classes"
                )

        logger.info(f"Registry built: {len(self._registry)} modules indexed by DB ID")

    def get(self, module_id: int) -> type[BaseModule] | None:
        """
        Get a module class by database ID.

        Args:
            module_id: Database primary key (int)

        Returns:
            Module class or None if not found
        """
        return self._registry.get(module_id)

    def get_all(self) -> dict[int, type[BaseModule]]:
        """
        Get all registered modules (keyed by DB id).

        Returns:
            Dictionary of db_id -> module_class
        """
        return dict(self._registry)

    def get_discovered_classes(self) -> list[type[BaseModule]]:
        """
        Get classes found during auto-discovery (for sync).

        Returns:
            List of module classes discovered during auto-discovery
        """
        return list(self._discovered_classes)

    def get_by_kind(self, kind: str) -> list[type[BaseModule]]:
        """
        Get all modules of a specific kind.

        Args:
            kind: Module kind ("transform", "logic", "comparator", "misc", "output")

        Returns:
            List of module classes of that kind
        """
        return [
            module_class
            for module_class in self._registry.values()
            if module_class.kind == kind
        ]

    def clear(self) -> None:
        """Clear all registered modules and discovered classes (useful for testing)."""
        self._registry.clear()
        self._discovered_classes.clear()
        self._cache.clear()
        logger.debug("Module registry cleared")

    def load_module_from_handler(self, handler_name: str) -> type[BaseModule] | None:
        """
        Load a module from handler_name with security validation and caching.

        This is a fallback for dynamically loading modules not in the registry.

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

    def auto_discover(self, package_paths: list[str]) -> None:
        """
        Auto-discover and import modules from specified packages (recursively).
        This will trigger the @register decorators on module classes.

        Note: After auto-discovery, call build_from_db() with DB records
        to populate the registry with integer IDs.

        Args:
            package_paths: List of package paths to scan for modules
                          e.g., ["features.modules.definitions"]
        """
        for package_path in package_paths:
            try:
                logger.info(f"Auto-discovering modules in: {package_path}")

                # Import the package
                package = importlib.import_module(package_path)

                # Recursively discover all modules
                self._discover_recursive(package, package_path)

            except ImportError as e:
                logger.warning(f"Failed to import package {package_path}: {e}")
            except Exception as e:
                logger.error(f"Error discovering modules in {package_path}: {e}")

        logger.info(f"Auto-discovery complete. {len(self._discovered_classes)} module classes found.")

    def _discover_recursive(self, package: Any, package_path: str) -> None:
        """
        Recursively discover modules in a package and all sub-packages.

        Args:
            package: Imported package object
            package_path: Package path string (e.g., "features.modules.definitions.transform")
        """
        # Get package directory
        if not hasattr(package, '__path__'):
            logger.warning(f"Package {package_path} has no __path__ attribute")
            return

        # Iterate through all items in the package
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            full_module_name = f"{package_path}.{modname}"

            try:
                # Import the module (this triggers @register decorators)
                imported_module = importlib.import_module(full_module_name)
                logger.debug(f"Imported: {full_module_name}")

                # Consume any pending registrations from this module
                count = consume_pending_registrations(self)
                if count > 0:
                    logger.debug(f"Discovered {count} modules from {full_module_name}")

                # If it's a package, recursively discover it
                if ispkg:
                    self._discover_recursive(imported_module, full_module_name)

            except Exception as e:
                logger.warning(f"Failed to import {full_module_name}: {e}")

    def to_catalog_entries(self) -> list[ModuleCreate]:
        """
        Convert discovered module classes to ModuleCreate for database sync.

        Uses _discovered_classes (not _registry) since this is called
        before build_from_db() populates the registry.

        Returns:
            List of ModuleCreate objects ready for repository
        """
        catalog_entries = []

        for module_class in self._discovered_classes:
            try:
                # Get module metadata
                meta = module_class.meta()
                config_schema = module_class.config_schema()

                # Build ModuleCreate
                entry = ModuleCreate(
                    identifier=module_class.identifier,
                    version=module_class.version,
                    name=module_class.title,
                    description=module_class.description,
                    module_kind=module_class.kind,
                    meta=meta,
                    config_schema=config_schema,
                    handler_name=f"{module_class.__module__}:{module_class.__name__}",
                    color=getattr(module_class, 'color', '#3B82F6'),
                    category=getattr(module_class, 'category', 'Processing'),
                    is_active=True
                )

                catalog_entries.append(entry)
                logger.debug(f"Converted module {module_class.identifier}:{module_class.version} to catalog entry")

            except Exception as e:
                logger.error(f"Failed to convert module {module_class.__name__} to catalog entry: {e}")

        return catalog_entries

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._cache.hits + self._cache.misses
        hit_rate = (self._cache.hits / total * 100) if total > 0 else 0

        return {
            "cache_size": len(self._cache._cache),
            "max_size": self._cache.max_size,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_hits": self._cache.hits,
            "total_misses": self._cache.misses,
            "discovered_classes": len(self._discovered_classes),
            "registered_by_id": len(self._registry),
        }
