"""
Email Filter Rules Utility

Functions for applying filter rules to emails.
Filter rules allow users to specify which emails should be processed
based on sender, subject, attachments, etc.
"""
import logging
from datetime import datetime

from shared.types.email_ingestion_configs import FilterRule
from shared.types.email_integrations import EmailMessage

logger = logging.getLogger(__name__)


def apply_filter_rules(
    emails: list[EmailMessage],
    filter_rules: list[FilterRule],
    config_id: int | None = None,
) -> list[EmailMessage]:
    """
    Apply filter rules to a list of emails.

    Filter logic uses OR between rules - an email passes if it matches ANY rule.
    If no rules are defined, all emails pass through.

    Args:
        emails: List of EmailMessage to filter
        filter_rules: List of FilterRule to apply
        config_id: Optional config ID for logging context

    Returns:
        List of emails that pass at least one filter rule
    """
    config_context = f"config {config_id}" if config_id else "filter"

    if not filter_rules or len(filter_rules) == 0:
        logger.debug(f"[{config_context}] No filter rules - processing all {len(emails)} emails")
        return emails

    filtered_emails: list[EmailMessage] = []
    logger.debug(f"[{config_context}] Applying {len(filter_rules)} filter rules to {len(emails)} emails")

    for email in emails:
        email_passes = False
        matched_rule: FilterRule | None = None

        for rule in filter_rules:
            try:
                if check_filter_rule(email, rule):
                    email_passes = True
                    matched_rule = rule
                    break
            except Exception as e:
                logger.warning(
                    f"[{config_context}] Error applying filter rule "
                    f"{rule.field} {rule.operation} '{rule.value}': {e}"
                )
                continue

        if email_passes and matched_rule:
            filtered_emails.append(email)
            subject_preview = email.subject[:40] + ('...' if len(email.subject) > 40 else '')
            logger.info(
                f"[{config_context}] PASSED: UID {email.uid} from '{email.sender_email}' "
                f"subject='{subject_preview}' "
                f"- matched rule: {matched_rule.field} {matched_rule.operation} '{matched_rule.value}'"
            )
        else:
            subject_preview = email.subject[:40] + ('...' if len(email.subject) > 40 else '')
            logger.info(
                f"[{config_context}] FILTERED OUT: UID {email.uid} from '{email.sender_email}' "
                f"subject='{subject_preview}' - no rules matched"
            )

    logger.info(
        f"[{config_context}] After filters: {len(filtered_emails)}/{len(emails)} emails passed "
        f"(filtered out {len(emails) - len(filtered_emails)})"
    )

    return filtered_emails


def check_filter_rule(email: EmailMessage, rule: FilterRule) -> bool:
    """
    Check if an email passes a single filter rule.

    Different field types require different operation handling:
    - String fields (sender_email, subject): equals, contains, starts_with, ends_with
    - Boolean field (has_attachments): equals, is
    - DateTime field (received_date): before, after, equals

    Args:
        email: EmailMessage to check
        rule: FilterRule to apply

    Returns:
        True if email passes the rule, False otherwise
    """
    # String field operations (sender_email, subject)
    if rule.field in ['sender_email', 'subject']:
        field_value = email.sender_email if rule.field == 'sender_email' else email.subject

        if rule.operation == 'equals':
            if rule.case_sensitive:
                return field_value == rule.value
            else:
                return field_value.lower() == rule.value.lower()

        elif rule.operation == 'contains':
            if rule.case_sensitive:
                return rule.value in field_value
            else:
                return rule.value.lower() in field_value.lower()

        elif rule.operation == 'starts_with':
            if rule.case_sensitive:
                return field_value.startswith(rule.value)
            else:
                return field_value.lower().startswith(rule.value.lower())

        elif rule.operation == 'ends_with':
            if rule.case_sensitive:
                return field_value.endswith(rule.value)
            else:
                return field_value.lower().endswith(rule.value.lower())

        else:
            logger.warning(
                f"Invalid operation '{rule.operation}' for string field '{rule.field}'"
            )
            return True  # Unknown operations pass by default

    # Boolean field operations (has_attachments)
    elif rule.field == 'has_attachments':
        field_value = email.has_attachments

        if rule.operation in ['equals', 'is']:
            # Convert string value to boolean
            # Accept: "true", "True", "1", "yes" as True
            # Accept: "false", "False", "0", "no" as False
            rule_bool = rule.value.lower() in ['true', '1', 'yes']
            return field_value == rule_bool
        else:
            logger.warning(
                f"Invalid operation '{rule.operation}' for boolean field '{rule.field}'. "
                f"Only 'equals' or 'is' are supported."
            )
            return True  # Unknown operations pass by default

    # DateTime field operations (received_date)
    elif rule.field == 'received_date':
        # received_date is stored as ISO string in EmailMessage
        field_value_str = email.received_date

        try:
            # Parse the email's received_date from ISO string
            field_value = datetime.fromisoformat(field_value_str.replace('Z', '+00:00'))

            # Parse the rule value as ISO datetime
            compare_date = datetime.fromisoformat(rule.value.replace('Z', '+00:00'))

            if rule.operation == 'before':
                return field_value < compare_date
            elif rule.operation == 'after':
                return field_value > compare_date
            elif rule.operation == 'equals':
                # For datetime equality, compare just the date portion
                return field_value.date() == compare_date.date()
            else:
                logger.warning(
                    f"Invalid operation '{rule.operation}' for datetime field '{rule.field}'. "
                    f"Only 'before', 'after', or 'equals' are supported."
                )
                return True  # Unknown operations pass by default

        except Exception as e:
            logger.error(
                f"Error parsing datetime value '{rule.value}' for rule: {e}. "
                f"Passing email by default."
            )
            return True  # Parsing errors pass by default

    # Unknown field
    else:
        logger.warning(f"Unknown filter field: '{rule.field}'. Passing email by default.")
        return True  # Unknown fields pass by default
