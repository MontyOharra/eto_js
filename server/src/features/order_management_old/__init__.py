"""
Order Management Feature

User-facing operations for managing pending orders and updates.
Provides functionality for:
- Viewing pending orders and updates
- Resolving field conflicts
- Approving/rejecting pending orders (creates in HTC)
- Approving/rejecting pending updates (updates in HTC)

This is the user interaction layer - all read/write operations triggered by users.
Automated processing is handled by the output_processing feature.
"""

from features.order_management_old.service import OrderManagementService

__all__ = ["OrderManagementService"]
