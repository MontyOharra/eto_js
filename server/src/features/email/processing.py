"""
Email Processing Handler

Handles the processing of incoming emails after they pass filter rules and deduplication.
Orchestrates:
1. Downloading PDF attachments
2. Storing PDFs via PdfFilesService
3. Recording email in database (for deduplication)
4. Creating ETO runs for each PDF
"""
import logging
from datetime import datetime

from shared.database.repositories.email import EmailRepository
from shared.types.email import EmailCreate
from shared.types.email_ingestion_configs import EmailIngestionConfig
from features.email.integrations.base_integration import BaseEmailIntegration
from shared.types.email_integrations import EmailMessage
from features.pdf_files.service import PdfFilesService
from features.eto_runs.service import EtoRunsService

logger = logging.getLogger(__name__)


class EmailProcessingHandler:
    """
    Processes emails that have passed filter rules and deduplication.

    For each email:
    1. Downloads PDF attachments from the email server
    2. Stores each PDF (with hash deduplication)
    3. Creates an email record in the database
    4. Creates an ETO run for each PDF

    This handler is called by the poller's on_emails_received callback.
    """

    def __init__(
        self,
        email_repository: EmailRepository,
        pdf_files_service: PdfFilesService,
        eto_runs_service: EtoRunsService,
    ):
        """
        Initialize the email processing handler.

        Args:
            email_repository: Repository for storing email records
            pdf_files_service: Service for storing PDF files
            eto_runs_service: Service for creating ETO runs
        """
        self.email_repository = email_repository
        self.pdf_files_service = pdf_files_service
        self.eto_runs_service = eto_runs_service

    def process_emails(
        self,
        config: EmailIngestionConfig,
        emails: list[EmailMessage],
        integration: BaseEmailIntegration,
    ) -> None:
        """
        Process a batch of emails from the poller.

        Args:
            config: The ingestion config that received these emails
            emails: List of emails that passed filter rules and deduplication
            integration: The email integration to use for downloading attachments
        """
        logger.info(f"[PROCESSING] Starting to process {len(emails)} email(s) for config {config.id}")

        for email_msg in emails:
            try:
                self._process_single_email(config, email_msg, integration)
            except Exception as e:
                logger.error(
                    f"[PROCESSING] Failed to process email UID {email_msg.uid} "
                    f"(message_id={email_msg.message_id[:30]}...): {e}",
                    exc_info=True
                )
                # Continue processing other emails

        logger.info(f"[PROCESSING] Completed processing {len(emails)} email(s) for config {config.id}")

    def _process_single_email(
        self,
        config: EmailIngestionConfig,
        email_msg: EmailMessage,
        integration: BaseEmailIntegration,
    ) -> None:
        """
        Process a single email.

        Steps:
        1. Download PDF attachments
        2. Store each PDF and create ETO runs
        3. Create email record in database

        Args:
            config: The ingestion config
            email_msg: The email message to process
            integration: The email integration for downloading attachments
        """
        subject_preview = email_msg.subject[:50] + ('...' if len(email_msg.subject) > 50 else '')
        logger.info(
            f"[PROCESSING] Processing email UID {email_msg.uid}: "
            f"'{subject_preview}' from {email_msg.sender_email}"
        )

        # Step 1: Download PDF attachments
        if not email_msg.has_attachments:
            logger.info(f"[PROCESSING] Email UID {email_msg.uid} has no attachments, skipping PDF download")
            pdf_attachments = []
        else:
            pdf_attachments = integration.get_attachments(
                folder_name=config.folder_name,
                uid=email_msg.uid,
                file_extensions=[".pdf"],
            )
            logger.info(f"[PROCESSING] Downloaded {len(pdf_attachments)} PDF attachment(s) from email UID {email_msg.uid}")

        # Step 2: Store PDFs and create ETO runs
        pdf_count = 0
        email_record_id = None

        # We need to create the email record first to link ETO runs to it
        # But we want the PDF count for the record, so we process PDFs first to count them
        stored_pdfs = []

        for attachment in pdf_attachments:
            try:
                logger.info(f"[PROCESSING] Storing PDF: '{attachment.filename}' ({len(attachment.data)} bytes)")

                pdf_file = self.pdf_files_service.store_pdf(
                    file_bytes=attachment.data,
                    filename=attachment.filename,
                )

                stored_pdfs.append(pdf_file)
                pdf_count += 1

                logger.info(
                    f"[PROCESSING] Stored PDF '{attachment.filename}' as pdf_id={pdf_file.id} "
                    f"(hash={pdf_file.file_hash[:16]}...)"
                )

            except Exception as e:
                logger.error(f"[PROCESSING] Failed to store PDF '{attachment.filename}': {e}")
                # Continue with other attachments

        # Step 3: Create email record
        try:
            email_record = self.email_repository.create(EmailCreate(
                account_id=config.account_id,
                ingestion_config_id=config.id,
                message_id=email_msg.message_id,
                sender_email=email_msg.sender_email,
                sender_name=email_msg.sender_name,
                subject=email_msg.subject,
                received_date=datetime.fromisoformat(email_msg.received_date),
                folder_name=email_msg.folder_name,
                has_pdf_attachments=pdf_count > 0,
                attachment_count=email_msg.attachment_count,
                pdf_count=pdf_count,
            ))
            email_record_id = email_record.id

            logger.info(
                f"[PROCESSING] Created email record id={email_record_id} "
                f"for message_id={email_msg.message_id[:30]}..."
            )

        except Exception as e:
            logger.error(f"[PROCESSING] Failed to create email record: {e}")
            # Even if email record fails, we've already stored PDFs
            # They just won't be linked to an email

        # Step 4: Create ETO runs for each stored PDF
        for pdf_file in stored_pdfs:
            try:
                eto_run = self.eto_runs_service.create_run(
                    pdf_file_id=pdf_file.id,
                    source_type='email',
                    source_email_id=email_record_id,
                )

                logger.info(
                    f"[PROCESSING] Created ETO run id={eto_run.id} for PDF '{pdf_file.original_filename}' "
                    f"(pdf_id={pdf_file.id}, email_id={email_record_id})"
                )

            except Exception as e:
                logger.error(
                    f"[PROCESSING] Failed to create ETO run for PDF {pdf_file.id}: {e}"
                )
                # Continue with other PDFs

        logger.info(
            f"[PROCESSING] Completed email UID {email_msg.uid}: "
            f"{pdf_count} PDF(s) stored, {len(stored_pdfs)} ETO run(s) created"
        )
