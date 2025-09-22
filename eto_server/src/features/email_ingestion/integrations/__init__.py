"""
Email Integrations
Provider-specific email integration implementations
"""
from .base_integration import BaseEmailIntegration
from .outlook_com import OutlookComIntegration
from .factory import EmailIntegrationFactory

# Keep old service for backward compatibility during migration
from .outlook_com_service_old import OutlookComService

__all__ = [
    'BaseEmailIntegration',
    'OutlookComIntegration',
    'EmailIntegrationFactory',
    'OutlookComService',  # Deprecated - use OutlookComIntegration
]