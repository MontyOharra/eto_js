"""
API Package
Flask REST API layer for the Unified ETO Server
"""
from .blueprints import (
    health_bp,
    email_config_bp,
    eto_processing_bp
)

# Export all blueprints for easy registration
BLUEPRINTS = [
    health_bp,
    email_config_bp,
    eto_processing_bp
]

__all__ = [
    'BLUEPRINTS',
    'health_bp',
    'email_config_bp',
    'eto_processing_bp'
]