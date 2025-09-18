"""
API Package
Flask REST API layer for the Unified ETO Server
"""
from .blueprints import (
    health_bp,
    email_ingestion_bp,
    eto_processing_bp,
    eto_service_bp
)

# Export all blueprints for easy registration
BLUEPRINTS = [
    health_bp,
    email_ingestion_bp,
    eto_processing_bp,
    eto_service_bp
]

__all__ = [
    'BLUEPRINTS',
    'health_bp',
    'email_ingestion_bp',
    'eto_processing_bp',
    'eto_service_bp'
]