"""
Shared Utilities Package
Common utility functions and helpers for the ETO server
"""

from .storage_config import get_storage_configuration, get_fallback_storage

__all__ = [
    'get_storage_configuration',
    'get_fallback_storage',
]