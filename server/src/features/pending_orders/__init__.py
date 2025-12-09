"""
Pending Orders Feature

Handles processing of output channel data from pipeline executions,
routing to pending orders or pending updates based on HAWB existence in HTC.
"""

from .service import PendingOrdersService

__all__ = ['PendingOrdersService']
