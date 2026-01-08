"""
Output Processing Feature

Processes pipeline output execution records and routes data to:
- pending_orders (for new HAWBs not in HTC)
- pending_updates (for HAWBs that exist in HTC)

This is the automated processing layer - no user interaction.
User-facing operations are handled by the order_management feature.
"""

from features.output_processing_old.service import OutputProcessingService

__all__ = ["OutputProcessingService"]
