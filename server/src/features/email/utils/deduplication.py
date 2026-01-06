"""
Email Deduplication Utility

Filters out emails that have already been processed for an account.
Uses Message-ID for deduplication - same Message-ID on same account = same email.
"""
import logging

from shared.database.repositories.email import EmailRepository
from shared.types.email_integrations import EmailMessage

logger = logging.getLogger(__name__)


def filter_duplicate_emails(
    emails: list[EmailMessage],
    account_id: int,
    email_repository: EmailRepository,
    config_id: int | None = None,
) -> list[EmailMessage]:
    """
    Filter out emails that have already been processed for this account.

    Uses batch query for efficiency when checking multiple emails.

    Args:
        emails: List of EmailMessage to check
        account_id: Email account ID (for per-account deduplication)
        email_repository: Repository for checking existing emails
        config_id: Optional config ID for logging context

    Returns:
        List of emails that have NOT been processed yet (new emails)
    """
    config_context = f"config {config_id}" if config_id else "dedup"

    if not emails:
        return []

    # Extract message IDs for batch lookup
    message_ids = [email.message_id for email in emails if email.message_id]

    if not message_ids:
        logger.warning(f"[{config_context}] No valid message IDs found in {len(emails)} emails")
        return emails

    # Batch check which already exist
    existing_ids = email_repository.get_existing_message_ids(account_id, message_ids)

    if not existing_ids:
        logger.debug(f"[{config_context}] No duplicates found - all {len(emails)} emails are new")
        return emails

    # Filter out duplicates
    new_emails: list[EmailMessage] = []
    duplicate_count = 0

    for email in emails:
        if email.message_id in existing_ids:
            duplicate_count += 1
            logger.info(
                f"[{config_context}] DUPLICATE: UID {email.uid} message_id='{email.message_id[:40]}...' "
                f"already processed for account {account_id}"
            )
        else:
            new_emails.append(email)

    logger.info(
        f"[{config_context}] Deduplication: {len(new_emails)}/{len(emails)} emails are new "
        f"({duplicate_count} duplicates filtered)"
    )

    return new_emails
