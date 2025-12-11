"""
HTC Integration Feature

Provides all database operations for the HTC Access database.
This is the single point of access for HTC order operations.

Used by:
- OutputProcessingService: To check if orders exist in HTC
- OrderManagementService: To create/update orders in HTC

All HTC database connectivity and queries are centralized here.

Architecture:
    HtcIntegrationService - Main facade/orchestrator
        ├── HtcLookupUtils   - Customer, address, order lookups
        ├── HtcAddressUtils  - Address parsing, normalization, creation
        └── HtcOrderUtils    - Order number generation, creation, updates
"""

from features.htc_integration.service import (
    HtcIntegrationService,
    HtcOrderDetails,
    AddressInfo,
    CustomerInfo,
    PreparedOrderData,
)

# Utility classes (for direct use if needed)
from features.htc_integration.lookup_utils import HtcLookupUtils
from features.htc_integration.address_utils import HtcAddressUtils
from features.htc_integration.order_utils import HtcOrderUtils

__all__ = [
    # Main service
    "HtcIntegrationService",
    # Data types
    "HtcOrderDetails",
    "AddressInfo",
    "CustomerInfo",
    "PreparedOrderData",
    # Utility classes
    "HtcLookupUtils",
    "HtcAddressUtils",
    "HtcOrderUtils",
]
