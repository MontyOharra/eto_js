"""
Module Registration Decorators
Global decorator system for marking module classes for registration
"""
import logging
from typing import Type, List

from shared.types.modules import BaseModule

logger = logging.getLogger(__name__)


# Global pending registrations queue
# Module classes are added here by @register decorator during import
# Then consumed by ModuleRegistry during auto-discovery
_pending_registrations: List[Type[BaseModule]] = []


def register(module_class: Type[BaseModule]) -> Type[BaseModule]:
    """
    Decorator to mark a module class for registration.

    Usage:
        from features.modules.utils.decorators import register

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
    Internal function to consume pending registrations and add them to a registry.
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


def clear_pending_registrations():
    """
    Clear all pending registrations without processing them.
    Useful for testing or cleanup scenarios.
    """
    global _pending_registrations
    _pending_registrations = []
    logger.debug("Cleared all pending registrations")
