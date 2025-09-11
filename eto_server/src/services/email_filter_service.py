"""
Email Filter Service
Handles email filtering logic based on configuration
"""
import re
import logging
from typing import Dict, List, Any, Optional, Pattern
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .email_types import EmailData

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Structured filter configuration"""
    sender_filters: Dict[str, List[str]]  # {"whitelist": [...], "blacklist": [...]}
    subject_filters: Dict[str, List[str]]
    attachment_filters: Dict[str, Any]
    date_filters: Dict[str, Any]
    advanced_filters: Dict[str, Any]



class EmailFilterService:
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

    # === Configuration Loading ===
    
    async def load_configuration(self, filter_config: Any) -> None:
        """Load and compile filter configuration"""
        try:
            self.logger.info("Loading email filter configuration")
            
            # Convert the config to the expected format if needed
            if hasattr(filter_config, 'rules'):
                # This is a FilterConfig from email_config_service
                config_dict = {
                    "sender_filters": {"whitelist": [], "blacklist": []},
                    "subject_filters": {"whitelist": [], "blacklist": []},
                    "attachment_filters": {
                        "require_attachments": getattr(filter_config, 'require_attachments', True),
                        "pdf_only": getattr(filter_config, 'pdf_only', True),
                        "enabled": getattr(filter_config, 'enabled', True)
                    },
                    "date_filters": {},
                    "advanced_filters": {}
                }
                
                # Convert rules to the appropriate filter categories
                for rule in filter_config.rules:
                    rule_type = rule.type
                    pattern = rule.pattern
                    operation = getattr(rule, 'operation', 'contains')
                    
                    if rule_type == "sender":
                        if operation == "contains" or operation == "equals":
                            config_dict["sender_filters"]["whitelist"].append(pattern)
                    elif rule_type == "subject":
                        if operation == "contains" or operation == "equals":
                            config_dict["subject_filters"]["whitelist"].append(pattern)
                    elif rule_type == "attachment":
                        config_dict["attachment_filters"][pattern] = True
                
                # Compile filters
                await self.compile_filters(self._parse_filter_config(config_dict))
                
            else:
                # Assume it's already in the right format
                await self.compile_filters(filter_config)
                
            self.logger.info("Filter configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading filter configuration: {e}")
            raise

    # === High-Level API Methods ===
    
    async def evaluate_email(self, email_data: EmailData, filter_config: FilterConfig) -> Dict[str, Any]:
        """
        Evaluate if email matches filter criteria
        Returns: {"matches": bool, "reasons": List[str], "rejected_by": List[str]}
        """
        try:
            self.filter_stats["emails_evaluated"] += 1
            
            reasons = []
            rejected_by = []
            
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
            logger.error(f"Error evaluating email filters: {e}")
            return {
                "matches": False,
                "reasons": [],
                "rejected_by": [f"Filter error: {str(e)}"],
                "filter_details": {}
            }
    
    async def compile_filters(self, filter_config: FilterConfig) -> Dict[str, Any]:
        """Pre-compile filters for performance optimization"""
        try:
            logger.info("Compiling email filters for performance optimization")
            
            compiled = {
                "sender_patterns": {},
                "subject_patterns": {},
                "compilation_time": datetime.now(timezone.utc),
                "pattern_count": 0
            }
            
            # Compile sender patterns
            for filter_type, patterns in filter_config.sender_filters.items():
                compiled["sender_patterns"][filter_type] = []
                for pattern in patterns:
                    compiled_pattern = self._compile_pattern(pattern)
                    compiled["sender_patterns"][filter_type].append(compiled_pattern)
                    compiled["pattern_count"] += 1
            
            # Compile subject patterns
            for filter_type, patterns in filter_config.subject_filters.items():
                compiled["subject_patterns"][filter_type] = []
                for pattern in patterns:
                    compiled_pattern = self._compile_pattern(pattern)
                    compiled["subject_patterns"][filter_type].append(compiled_pattern)
                    compiled["pattern_count"] += 1
            
            self.compiled_filters = compiled
            logger.info(f"Compiled {compiled['pattern_count']} filter patterns successfully")
            
            return {
                "success": True,
                "pattern_count": compiled["pattern_count"],
                "compilation_time": compiled["compilation_time"]
            }
            
        except Exception as e:
            logger.error(f"Error compiling filters: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_filter_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate filter configuration structure and values
        Returns: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        
        try:
            # Parse configuration
            filter_config = self._parse_filter_config(config_dict)
            
            # Validate sender filters
            if filter_config.sender_filters:
                sender_errors = self._validate_pattern_filters(filter_config.sender_filters, "sender")
                errors.extend(sender_errors)
            
            # Validate subject filters
            if filter_config.subject_filters:
                subject_errors = self._validate_pattern_filters(filter_config.subject_filters, "subject")
                errors.extend(subject_errors)
            
            # Validate attachment filters
            if filter_config.attachment_filters:
                attachment_errors = self._validate_attachment_config(filter_config.attachment_filters)
                errors.extend(attachment_errors)
            
            # Validate date filters
            if filter_config.date_filters:
                date_errors = self._validate_date_config(filter_config.date_filters)
                errors.extend(date_errors)
            
            # Check for potential performance issues
            pattern_count = 0
            for patterns in filter_config.sender_filters.values():
                pattern_count += len(patterns)
            for patterns in filter_config.subject_filters.values():
                pattern_count += len(patterns)
            
            if pattern_count > 50:
                warnings.append(f"Large number of patterns ({pattern_count}) may impact performance")
            
            is_valid = len(errors) == 0
            
            return {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "pattern_count": pattern_count
            }
            
        except Exception as e:
            logger.error(f"Error validating filter configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Configuration validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def get_filter_statistics(self) -> Dict[str, Any]:
        """Get filter performance statistics"""
        try:
            total_evaluated = self.filter_stats["emails_evaluated"]
            match_rate = (self.filter_stats["emails_matched"] / total_evaluated * 100) if total_evaluated > 0 else 0
            reject_rate = (self.filter_stats["emails_rejected"] / total_evaluated * 100) if total_evaluated > 0 else 0
            
            return {
                "emails_evaluated": total_evaluated,
                "emails_matched": self.filter_stats["emails_matched"],
                "emails_rejected": self.filter_stats["emails_rejected"],
                "match_rate_percent": round(match_rate, 2),
                "reject_rate_percent": round(reject_rate, 2),
                "cached_patterns": len(self.pattern_cache),
                "compiled_filters_active": self.compiled_filters is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting filter statistics: {e}")
            return {"error": str(e)}
    
    def reset_filter_statistics(self) -> None:
        """Reset performance statistics"""
        self.filter_stats = {
            "emails_evaluated": 0,
            "emails_matched": 0,
            "emails_rejected": 0,
            "filter_performance": {}
        }
        logger.info("Filter statistics reset")

    # === Filter Evaluation Methods ===
    
    def _evaluate_sender_filters(self, email_data: EmailData, sender_config: Dict) -> Dict[str, Any]:
        """Evaluate sender-based filters"""
        try:
            if not sender_config:
                return {"passed": True, "reason": "No sender filters configured"}
            
            sender_email = email_data.sender_email.lower()
            
            # Check blacklist first (takes precedence)
            if "blacklist" in sender_config:
                for pattern in sender_config["blacklist"]:
                    if self._match_patterns(sender_email, [pattern], case_sensitive=False):
                        return {"passed": False, "reason": f"Sender '{sender_email}' matches blacklist pattern '{pattern}'"}
            
            # Check whitelist
            if "whitelist" in sender_config:
                whitelist_patterns = sender_config["whitelist"]
                if whitelist_patterns:  # Only check if whitelist is not empty
                    for pattern in whitelist_patterns:
                        if self._match_patterns(sender_email, [pattern], case_sensitive=False):
                            return {"passed": True, "reason": f"Sender '{sender_email}' matches whitelist pattern '{pattern}'"}
                    # If whitelist exists but no match, reject
                    return {"passed": False, "reason": f"Sender '{sender_email}' does not match any whitelist patterns"}
            
            return {"passed": True, "reason": "Sender filters passed"}
            
        except Exception as e:
            logger.error(f"Error evaluating sender filters: {e}")
            return {"passed": False, "reason": f"Sender filter error: {str(e)}"}
    
    def _evaluate_subject_filters(self, email_data: EmailData, subject_config: Dict) -> Dict[str, Any]:
        """Evaluate subject-based filters"""
        try:
            if not subject_config:
                return {"passed": True, "reason": "No subject filters configured"}
            
            subject = email_data.subject or ""
            
            # Check required patterns
            if "required" in subject_config:
                required_patterns = subject_config["required"]
                if required_patterns:  # Only check if required patterns exist
                    for pattern in required_patterns:
                        if not self._match_patterns(subject, [pattern], case_sensitive=False):
                            return {"passed": False, "reason": f"Subject missing required pattern '{pattern}'"}
                    return {"passed": True, "reason": f"Subject contains all required patterns"}
            
            # Check blacklist patterns
            if "blacklist" in subject_config:
                for pattern in subject_config["blacklist"]:
                    if self._match_patterns(subject, [pattern], case_sensitive=False):
                        return {"passed": False, "reason": f"Subject matches blacklisted pattern '{pattern}'"}
            
            return {"passed": True, "reason": "Subject filters passed"}
            
        except Exception as e:
            logger.error(f"Error evaluating subject filters: {e}")
            return {"passed": False, "reason": f"Subject filter error: {str(e)}"}
    
    def _evaluate_attachment_filters(self, email_data: EmailData, attachment_config: Dict) -> Dict[str, Any]:
        """Evaluate attachment-based filters"""
        try:
            if not attachment_config:
                return {"passed": True, "reason": "No attachment filters configured"}
            
            # Check if attachments are required
            if attachment_config.get("require_attachments", False):
                if not email_data.has_attachments:
                    return {"passed": False, "reason": "Email must have attachments"}
            
            # Check if PDF attachments are required
            if attachment_config.get("require_pdf", False):
                if not email_data.has_pdf_attachments:
                    return {"passed": False, "reason": "Email must have PDF attachments"}
            
            # Check minimum attachment count
            min_attachments = attachment_config.get("min_attachments")
            if min_attachments is not None and email_data.attachment_count < min_attachments:
                return {"passed": False, "reason": f"Email must have at least {min_attachments} attachments (has {email_data.attachment_count})"}
            
            # Check maximum attachment count
            max_attachments = attachment_config.get("max_attachments")
            if max_attachments is not None and email_data.attachment_count > max_attachments:
                return {"passed": False, "reason": f"Email must have at most {max_attachments} attachments (has {email_data.attachment_count})"}
            
            # Check filename patterns
            filename_patterns = attachment_config.get("filename_patterns", [])
            if filename_patterns and email_data.attachment_filenames:
                pattern_matched = False
                for filename in email_data.attachment_filenames:
                    if self._match_patterns(filename.lower(), filename_patterns, case_sensitive=False):
                        pattern_matched = True
                        break
                
                if not pattern_matched:
                    return {"passed": False, "reason": f"No attachments match filename patterns: {filename_patterns}"}
            
            return {"passed": True, "reason": "Attachment filters passed"}
            
        except Exception as e:
            logger.error(f"Error evaluating attachment filters: {e}")
            return {"passed": False, "reason": f"Attachment filter error: {str(e)}"}
    
    def _evaluate_date_filters(self, email_data: EmailData, date_config: Dict) -> Dict[str, Any]:
        """Evaluate date-based filters"""
        try:
            if not date_config or not date_config.get("enabled", False):
                return {"passed": True, "reason": "No date filters configured"}
            
            current_time = datetime.now(timezone.utc)
            received_time = email_data.received_time
            
            # Convert to naive datetime for comparison if needed
            if hasattr(received_time, 'replace') and received_time.tzinfo is not None:
                received_time = received_time.replace(tzinfo=None)
            if hasattr(current_time, 'replace') and current_time.tzinfo is not None:
                current_time = current_time.replace(tzinfo=None)
            
            # Check hours back limit
            hours_back = date_config.get("hours_back")
            if hours_back is not None:
                cutoff_time = current_time - timedelta(hours=hours_back)
                if received_time < cutoff_time:
                    return {"passed": False, "reason": f"Email is older than {hours_back} hours"}
            
            # Check weekend exclusion
            if date_config.get("exclude_weekends", False):
                if received_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    return {"passed": False, "reason": "Email received on weekend (excluded)"}
            
            # Check business hours (assuming 9 AM to 5 PM)
            if date_config.get("business_hours_only", False):
                if received_time.hour < 9 or received_time.hour >= 17:
                    return {"passed": False, "reason": "Email received outside business hours"}
            
            return {"passed": True, "reason": "Date filters passed"}
            
        except Exception as e:
            logger.error(f"Error evaluating date filters: {e}")
            return {"passed": False, "reason": f"Date filter error: {str(e)}"}
    
    def _evaluate_advanced_filters(self, email_data: EmailData, advanced_config: Dict) -> Dict[str, Any]:
        """Evaluate advanced filters (body content, priority, etc.)"""
        try:
            if not advanced_config:
                return {"passed": True, "reason": "No advanced filters configured"}
            
            # Check body keywords
            body_keywords = advanced_config.get("body_keywords", [])
            if body_keywords and email_data.body_preview:
                body_lower = email_data.body_preview.lower()
                for keyword in body_keywords:
                    if keyword.lower() in body_lower:
                        return {"passed": True, "reason": f"Body contains keyword '{keyword}'"}
                
                return {"passed": False, "reason": f"Body does not contain any required keywords: {body_keywords}"}
            
            # Note: Other advanced filters like auto-reply detection, priority filtering
            # would require additional email metadata that we don't currently have
            
            return {"passed": True, "reason": "Advanced filters passed"}
            
        except Exception as e:
            logger.error(f"Error evaluating advanced filters: {e}")
            return {"passed": False, "reason": f"Advanced filter error: {str(e)}"}

    # === Helper Methods ===
    
    def _match_patterns(self, text: str, patterns: List[str], case_sensitive: bool = False) -> bool:
        """Match text against list of patterns (supports wildcards)"""
        try:
            if not patterns or not text:
                return False
            
            for pattern in patterns:
                compiled_pattern = self._compile_pattern(pattern)
                flags = 0 if case_sensitive else re.IGNORECASE
                
                if compiled_pattern.search(text):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error matching patterns: {e}")
            return False
    
    def _compile_pattern(self, pattern: str) -> Pattern:
        """Compile pattern string to regex with wildcard support"""
        try:
            # Check cache first
            if pattern in self.pattern_cache:
                return self.pattern_cache[pattern]
            
            # Convert wildcard pattern to regex
            # Escape special regex characters except * and ?
            escaped = re.escape(pattern)
            # Replace escaped wildcards with regex equivalents
            regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
            
            # Compile and cache
            compiled = re.compile(regex_pattern, re.IGNORECASE)
            self.pattern_cache[pattern] = compiled
            
            return compiled
            
        except Exception as e:
            logger.error(f"Error compiling pattern '{pattern}': {e}")
            # Return a pattern that never matches
            return re.compile(r'(?!.*)', re.IGNORECASE)
    
    def _parse_filter_config(self, config_dict: Dict[str, Any]) -> FilterConfig:
        """Parse dictionary configuration to FilterConfig dataclass"""
        try:
            filters = config_dict.get("filters", {})
            
            return FilterConfig(
                sender_filters=filters.get("sender", {}),
                subject_filters=filters.get("subject", {}),
                attachment_filters=filters.get("attachments", {}),
                date_filters=filters.get("date_range", {}),
                advanced_filters=filters.get("advanced", {})
            )
            
        except Exception as e:
            logger.error(f"Error parsing filter configuration: {e}")
            # Return empty configuration
            return FilterConfig(
                sender_filters={},
                subject_filters={},
                attachment_filters={},
                date_filters={},
                advanced_filters={}
            )
    
    def _validate_pattern_filters(self, pattern_filters: Dict[str, List[str]], filter_type: str) -> List[str]:
        """Validate pattern-based filters"""
        errors = []
        
        try:
            for filter_subtype, patterns in pattern_filters.items():
                if not isinstance(patterns, list):
                    errors.append(f"{filter_type}.{filter_subtype} must be a list")
                    continue
                
                for i, pattern in enumerate(patterns):
                    if not isinstance(pattern, str):
                        errors.append(f"{filter_type}.{filter_subtype}[{i}] must be a string")
                        continue
                    
                    # Try to compile pattern to check for regex errors
                    try:
                        self._compile_pattern(pattern)
                    except Exception as pattern_error:
                        errors.append(f"{filter_type}.{filter_subtype}[{i}] invalid pattern '{pattern}': {pattern_error}")
            
        except Exception as e:
            errors.append(f"Error validating {filter_type} filters: {str(e)}")
        
        return errors
    
    def _validate_attachment_config(self, attachment_config: Dict[str, Any]) -> List[str]:
        """Validate attachment configuration"""
        errors = []
        
        try:
            # Validate boolean flags
            boolean_fields = ["require_attachments", "require_pdf"]
            for field in boolean_fields:
                if field in attachment_config and not isinstance(attachment_config[field], bool):
                    errors.append(f"attachments.{field} must be a boolean")
            
            # Validate numeric fields
            numeric_fields = ["min_attachments", "max_attachments", "min_file_size_kb"]
            for field in numeric_fields:
                if field in attachment_config:
                    value = attachment_config[field]
                    if not isinstance(value, int) or value < 0:
                        errors.append(f"attachments.{field} must be a non-negative integer")
            
            # Validate min <= max
            min_attachments = attachment_config.get("min_attachments")
            max_attachments = attachment_config.get("max_attachments")
            if (min_attachments is not None and max_attachments is not None and 
                min_attachments > max_attachments):
                errors.append("attachments.min_attachments cannot be greater than max_attachments")
            
        except Exception as e:
            errors.append(f"Error validating attachment configuration: {str(e)}")
        
        return errors
    
    def _validate_date_config(self, date_config: Dict[str, Any]) -> List[str]:
        """Validate date configuration"""
        errors = []
        
        try:
            # Validate boolean flags
            boolean_fields = ["enabled", "exclude_weekends", "business_hours_only"]
            for field in boolean_fields:
                if field in date_config and not isinstance(date_config[field], bool):
                    errors.append(f"date_range.{field} must be a boolean")
            
            # Validate numeric fields
            if "hours_back" in date_config:
                hours_back = date_config["hours_back"]
                if not isinstance(hours_back, int) or hours_back < 0:
                    errors.append("date_range.hours_back must be a non-negative integer")
                elif hours_back > 8760:  # More than 1 year
                    errors.append("date_range.hours_back should not exceed 8760 hours (1 year)")
            
        except Exception as e:
            errors.append(f"Error validating date configuration: {str(e)}")
        
        return errors
    
    def _log_filter_decision(self, email_data: EmailData, decision: bool, reasons: List[str]) -> None:
        """Log filtering decisions for debugging"""
        try:
            decision_text = "ACCEPTED" if decision else "REJECTED"
            reason_text = "; ".join(reasons) if reasons else "No specific reasons"
            
            logger.debug(f"Filter decision: {decision_text} - Email: '{email_data.subject}' from {email_data.sender_email} - Reasons: {reason_text}")
            
        except Exception as e:
            logger.error(f"Error logging filter decision: {e}")