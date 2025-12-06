"""
Email Utilities

Helper functions for email processing.
"""
from .filter_rules import apply_filter_rules, check_filter_rule
from .deduplication import filter_duplicate_emails

__all__ = [
    "apply_filter_rules",
    "check_filter_rule",
    "filter_duplicate_emails",
]
