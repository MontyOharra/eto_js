"""
Shared Utilities Package
Common utility functions and helpers for the ETO server
"""

from .storage_config import get_storage_configuration, get_fallback_storage
from ..services.service_container import (
  ServiceContainer, get_pdf_processing_service, get_email_ingestion_service, 
  get_eto_processing_service, get_pdf_template_service, get_connection_manager, 
  is_service_container_initialized
)

__all__ = [
    'get_storage_configuration',
    'get_fallback_storage',
    'ServiceContainer',
    'get_pdf_processing_service',
    'get_email_ingestion_service',
    'get_eto_processing_service',
    'get_pdf_template_service',
    'get_connection_manager',
    'is_service_container_initialized'
]