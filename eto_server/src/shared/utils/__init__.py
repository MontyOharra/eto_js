"""
Shared Utilities Package
Common utility functions and helpers for the ETO server
"""

from .storage_config import (
    get_default_storage_path,
    get_portable_storage_path,
    get_development_storage_path,
    get_storage_configuration,
    setup_first_run_storage,
    validate_storage_path,
    is_development_mode,
    get_fallback_storage
)

__all__ = [
    'get_default_storage_path',
    'get_portable_storage_path', 
    'get_development_storage_path',
    'get_storage_configuration',
    'setup_first_run_storage',
    'validate_storage_path',
    'is_development_mode',
    'get_fallback_storage'
]