"""
Email Ingestion Module

Handles automated email ingestion from configured email accounts.
"""

from .listener import IngestionListener
from .manager import IngestionManager

__all__ = ["IngestionListener", "IngestionManager"]
