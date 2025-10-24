"""
Module Registry System
Singleton registry for module registration and discovery
"""
import logging
import time
import re
from typing import Dict, Type, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import importlib
import pkgutil

from shared.types import BaseModule

logger = logging.getLogger(__name__)


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


class ModuleRegistry:
    """
    Singleton registry for transformation pipeline modules
    Handles registration, discovery, and retrieval of module classes
    """

    _instance: Optional['ModuleRegistry'] = None
    _initialized: bool = False

    def __new__(cls) -> 'ModuleRegistry':
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry (only once)"""
        if not self._initialized:
            self._registry: Dict[str, Type[BaseModule]] = {}
            self._cache = ModuleCache()
            self._initialized = True
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
            kind: Module kind ("transform", "action", or "logic")

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
        self._cache = ModuleCache()  # Reset cache too
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
                            except Exception as e:
                                logger.warning(f"Failed to import {full_module_name}: {e}")
                else:
                    logger.warning(f"Package {package_path} has no __path__ attribute")

            except ImportError as e:
                logger.warning(f"Failed to import package {package_path}: {e}")
            except Exception as e:
                logger.error(f"Error discovering modules in {package_path}: {e}")

        logger.info(f"Auto-discovery complete. {len(self._registry)} modules registered.")

    def to_catalog_format(self) -> List[Dict]:
        """
        Convert all registered modules to catalog format for database

        Returns:
            List of dictionaries ready for database insertion
        """
        catalog_entries = []

        for module_id, module_class in self._registry.items():
            try:
                # Get module metadata
                meta = module_class.meta()
                config_schema = module_class.config_schema()

                # Build catalog entry
                entry = {
                    "id": module_class.id,
                    "version": getattr(module_class, 'version', '1.0.0'),  # Default version
                    "name": module_class.title,
                    "description": module_class.description,
                    "module_kind": module_class.kind,
                    "meta": meta.to_dict(),  # Convert to dict
                    "config_schema": config_schema,
                    "handler_name": f"{module_class.__module__}:{module_class.__name__}",
                    "color": getattr(module_class, 'color', '#3B82F6'),  # Default color
                    "category": getattr(module_class, 'category', 'Processing'),  # Default category
                    "is_active": True
                }

                catalog_entries.append(entry)
                logger.debug(f"Converted module {module_id} to catalog format")

            except Exception as e:
                logger.error(f"Failed to convert module {module_id} to catalog format: {e}")

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


# Singleton instance
_registry = ModuleRegistry()

# Convenience functions for module access
def register(module_class: Type[BaseModule]) -> Type[BaseModule]:
    """
    Decorator to register a module class

    Usage:
        @register
        class MyModule(TransformModule):
            ...
    """
    return _registry.register(module_class)


def get_registry() -> ModuleRegistry:
    """Get the singleton registry instance"""
    return _registry


def get_module(module_id: str) -> Optional[Type[BaseModule]]:
    """Get a module class by ID"""
    return _registry.get(module_id)


def get_all_modules() -> Dict[str, Type[BaseModule]]:
    """Get all registered modules"""
    return _registry.get_all()


def auto_discover_modules(package_paths: List[str]):
    """Auto-discover modules from specified packages"""
    _registry.auto_discover(package_paths)


def clear_registry():
    """Clear the registry (useful for testing)"""
    _registry.clear()
