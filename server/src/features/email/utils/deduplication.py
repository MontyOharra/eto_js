"""
Email Deduplication Utility

Filters out emails that have already been processed for an account.
Uses Message-ID for deduplication - same Message-ID on same account = same email.
"""
import logging

from shared.types.email_integrations import EmailMessage

logger = logging.getLogger(__name__)


def filter_duplicate_emails(
    emails: list[EmailMessage],
    existing_message_ids: set[str],
    context: str | None = None,
) -> list[EmailMessage]:
    """
    Filter out emails that have already been processed.

    Args:
        emails: List of EmailMessage to check
        existing_message_ids: Set of message IDs that have already been processed
        context: Optional context string for logging (e.g., "config 123")

    Returns:
        List of emails that have NOT been processed yet (new emails)
    """
    log_context = f"[{context}] " if context else ""

    if not emails:
        return []

    if not existing_message_ids:
        logger.debug(f"{log_context}No existing message IDs - all {len(emails)} emails are new")
        return emails

    # Filter out duplicates
    new_emails: list[EmailMessage] = []
    duplicate_count = 0

    for email in emails:
        if email.message_id in existing_message_ids:
            duplicate_count += 1
            message_id_preview = email.message_id[:40] + ('...' if len(email.message_id) > 40 else '')
            logger.info(f"{log_context}DUPLICATE: UID {email.uid} message_id='{message_id_preview}'")
        else:
            new_emails.append(email)

    logger.info(
        f"{log_context}Deduplication: {len(new_emails)}/{len(emails)} emails are new "
        f"({duplicate_count} duplicates filtered)"
    )

    return new_emails
