"""
HTC Integration Feature

Provides all database operations for the HTC Access database.
This is the single point of access for HTC order operations.

Used by:
- OutputProcessingService: To check if orders exist in HTC
- OrderManagementService: To create/update orders in HTC

All HTC database connectivity and queries are centralized here.
"""

from features.htc_integration.service import HtcIntegrationService

__all__ = ["HtcIntegrationService"]
