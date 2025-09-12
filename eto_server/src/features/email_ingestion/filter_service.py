"""
Email Filter Service
Handles email filtering logic based on configuration
"""
import re
import logging
from typing import Dict, List, Any, Optional, Pattern
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .types import EmailData, EmailFilterRule

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Structured filter configuration"""
    sender_filters: Dict[str, List[str]]  # {"whitelist": [...], "blacklist": [...]}
    subject_filters: Dict[str, List[str]]
    attachment_filters: Dict[str, Any]
    date_filters: Dict[str, Any]
    advanced_filters: Dict[str, Any]


class EmailIngestionFilterService:
    """Handles email filtering logic based on configuration"""
    
    def __init__(self):
        self.compiled_filters: Optional[Dict] = None
        self.pattern_cache: Dict[str, Pattern] = {}  # Cache compiled regex patterns
        self.filter_stats = {
            "emails_evaluated": 0,
            "emails_matched": 0,
            "emails_rejected": 0,
            "filter_performance": {}
        }
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    
    async def evaluate_email(self, email_data: EmailData, filter_rules: List[EmailFilterRule]) -> Dict[str, Any]:
        """
        Evaluate if email matches filter criteria
        Returns: {"matches": bool, "reasons": List[str], "rejected_by": List[str]}
        """
        try:
            self.filter_stats["emails_evaluated"] += 1
            
            reasons = []
            rejected_by = []
            
            # Convert filter rules to internal format
            filter_config = self._convert_filter_rules(filter_rules)
            
            # Evaluate each filter category
            filter_results = {
                "sender": self._evaluate_sender_filters(email_data, filter_config.sender_filters),
                "subject": self._evaluate_subject_filters(email_data, filter_config.subject_filters),
                "attachments": self._evaluate_attachment_filters(email_data, filter_config.attachment_filters),
                "date": self._evaluate_date_filters(email_data, filter_config.date_filters),
                "advanced": self._evaluate_advanced_filters(email_data, filter_config.advanced_filters)
            }
            
            # Collect reasons and rejections
            for filter_name, result in filter_results.items():
                if result["passed"]:
                    if result["reason"]:
                        reasons.append(f"{filter_name}: {result['reason']}")
                else:
                    rejected_by.append(f"{filter_name}: {result['reason']}")
            
            # Overall match decision (all filters must pass)
            overall_match = all(result["passed"] for result in filter_results.values())
            
            if overall_match:
                self.filter_stats["emails_matched"] += 1
            else:
                self.filter_stats["emails_rejected"] += 1
            
            # Log filtering decision
            self._log_filter_decision(email_data, overall_match, reasons if overall_match else rejected_by)
            
            return {
                "matches": overall_match,
                "reasons": reasons,
                "rejected_by": rejected_by,
                "filter_details": filter_results
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating email filters: {e}")
            return {
                "matches": False,
                "reasons": [],
                "rejected_by": [f"Filter evaluation error: {str(e)}"],
                "filter_details": {}
            }

    def get_filter_statistics(self) -> Dict[str, Any]:
        """Get current filter statistics"""
        return self.filter_stats.copy()

    def reset_filter_statistics(self) -> None:
        """Reset filter statistics"""
        self.filter_stats = {
            "emails_evaluated": 0,
            "emails_matched": 0,
            "emails_rejected": 0,
            "filter_performance": {}
        }
        self.logger.info("Filter statistics reset")

    # === Internal Filter Methods ===
    
    def _convert_filter_rules(self, filter_rules: List[EmailFilterRule]) -> FilterConfig:
        """Convert EmailFilterRule list to internal FilterConfig format"""
        # TODO: Implement conversion from filter rules to internal format
        return FilterConfig(
            sender_filters={"whitelist": [], "blacklist": []},
            subject_filters={"whitelist": [], "blacklist": []},
            attachment_filters={"require_attachments": True, "pdf_only": True},
            date_filters={},
            advanced_filters={}
        )
    
    def _evaluate_sender_filters(self, email_data: EmailData, sender_config: Dict) -> Dict[str, Any]:
        """Evaluate sender-based filters"""
        # TODO: Implement sender filtering logic
        return {"passed": True, "reason": "Sender filter passed"}
    
    def _evaluate_subject_filters(self, email_data: EmailData, subject_config: Dict) -> Dict[str, Any]:
        """Evaluate subject-based filters"""
        # TODO: Implement subject filtering logic
        return {"passed": True, "reason": "Subject filter passed"}
    
    def _evaluate_attachment_filters(self, email_data: EmailData, attachment_config: Dict) -> Dict[str, Any]:
        """Evaluate attachment-based filters"""
        # TODO: Implement attachment filtering logic
        return {"passed": True, "reason": "Attachment filter passed"}
    
    def _evaluate_date_filters(self, email_data: EmailData, date_config: Dict) -> Dict[str, Any]:
        """Evaluate date-based filters"""
        # TODO: Implement date filtering logic
        return {"passed": True, "reason": "Date filter passed"}
    
    def _evaluate_advanced_filters(self, email_data: EmailData, advanced_config: Dict) -> Dict[str, Any]:
        """Evaluate advanced filters"""
        # TODO: Implement advanced filtering logic
        return {"passed": True, "reason": "Advanced filter passed"}
    
    def _log_filter_decision(self, email_data: EmailData, decision: bool, reasons: List[str]) -> None:
        """Log filtering decision"""
        action = "ACCEPTED" if decision else "REJECTED"
        self.logger.debug(f"Email {action}: {email_data.subject} - {'; '.join(reasons)}")