"""
Email Ingestion Service
Complete service for email configuration management, monitoring, and processing
"""
import logging
import threading
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

from shared.models.email_config import (
    EmailConfig, EmailConfigCreate, EmailConfigUpdate, EmailConfigSummary
)
from shared.models.email_integration import (
    EmailMessage, EmailAttachment, EmailAccount, EmailFolder,
    ConnectionTestResult, EmailProvider, OutlookComConfig
)
from shared.models.email import Email, EmailCreate
from shared.database.repositories.email import EmailRepository
from shared.database.repositories.email_ingestion_config import EmailIngestionConfigRepository
from shared.exceptions import ServiceError, ObjectNotFoundError

from features.email_ingestion.integrations.factory import EmailIntegrationFactory
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration
from features.email_ingestion.utils.email_listener_thread import EmailListenerThread

logger = logging.getLogger(__name__)


@dataclass
class ListenerStatus:
    """Status information for an active listener"""
    config_id: int
    email_address: str
    folder_name: str
    is_active: bool
    is_running: bool
    start_time: Optional[datetime]
    last_check_time: Optional[datetime]
    error_count: int
    emails_processed: int
    pdfs_found: int


class EmailIngestionService:
    """
    Unified service for all email ingestion functionality.
    Manages configurations, listeners, integrations, and email processing.
    """
    
    def __init__(self, connection_manager):
        """
        Initialize service with database connection
        
        Args:
            connection_manager: Database connection manager
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")
        
        self.connection_manager = connection_manager
        
        # Initialize repositories
        self.config_repository = EmailIngestionConfigRepository(connection_manager)
        self.email_repository = EmailRepository(connection_manager)
        
        # Active integrations and listeners
        self.active_integrations: Dict[int, BaseEmailIntegration] = {}
        self.active_listeners: Dict[int, EmailListenerThread] = {}
        
        # Thread safety
        self.lock = threading.RLock()
        
        logger.info("EmailIngestionService initialized")
    
    # ========== Account/Folder Discovery ==========
    
    def discover_email_accounts(self, provider_type: str = "outlook_com") -> List[EmailAccount]:
        """
        Discover available email accounts for the specified provider
        
        Args:
            provider_type: Email provider type (outlook_com, gmail_api, etc.)
            
        Returns:
            List of discovered email accounts
        """
        try:
            logger.info(f"Discovering email accounts for provider: {provider_type}")
            
            # Create temporary integration for discovery
            if provider_type == EmailProvider.OUTLOOK_COM.value:
                config = OutlookComConfig(
                    provider_type=EmailProvider.OUTLOOK_COM,
                    account_identifier=None
                )
                integration = EmailIntegrationFactory.create_integration(config)
                
                # Discover accounts (doesn't require connection)
                accounts = integration.discover_accounts()
                
                logger.info(f"Discovered {len(accounts)} accounts")
                return accounts
            
            else:
                logger.warning(f"Provider {provider_type} not yet supported for discovery")
                return []
                
        except Exception as e:
            logger.error(f"Error discovering email accounts: {e}")
            raise ServiceError(f"Failed to discover accounts: {str(e)}")
    
    def discover_folders(self, email_address: str, provider_type: str = "outlook_com") -> List[EmailFolder]:
        """
        Discover folders for a specific email account
        
        Args:
            email_address: Email address to discover folders for
            provider_type: Email provider type (defaults to outlook_com)
            
        Returns:
            List of discovered folders
        """
        try:
            logger.info(f"Discovering folders for {email_address} on {provider_type}")
            
            # Create temporary integration
            if provider_type == EmailProvider.OUTLOOK_COM.value or provider_type == "outlook_com":
                config = OutlookComConfig(
                    provider_type=EmailProvider.OUTLOOK_COM,
                    account_identifier=email_address
                )
                integration = EmailIntegrationFactory.create_integration(config)
                
                # Connect temporarily for folder discovery
                if integration.connect(email_address):
                    try:
                        folders = integration.discover_folders(email_address)
                        logger.info(f"Discovered {len(folders)} folders")
                        return folders
                    finally:
                        integration.disconnect()
                else:
                    raise ServiceError("Failed to connect for folder discovery")
            
            else:
                logger.warning(f"Provider {provider_type} not yet supported")
                return []
                
        except Exception as e:
            logger.error(f"Error discovering folders: {e}")
            raise ServiceError(f"Failed to discover folders: {str(e)}")
    
    def test_connection_for_new_config(self, email_address: str, folder_name: str, provider_type: str = "outlook_com") -> ConnectionTestResult:
        """
        Test connection for a new config before creating it
        
        Args:
            email_address: Email account to test
            folder_name: Folder to test access to
            provider_type: Email provider type (defaults to outlook_com)
            
        Returns:
            ConnectionTestResult with success status and error message if failed
        """
        try:
            logger.info(f"Testing connection for {email_address}/{folder_name}")
            
            # Create temporary integration
            if provider_type == EmailProvider.OUTLOOK_COM.value or provider_type == "outlook_com":
                config = OutlookComConfig(
                    provider_type=EmailProvider.OUTLOOK_COM,
                    account_identifier=email_address,
                    default_folder=folder_name
                )
                integration = EmailIntegrationFactory.create_integration(config)
                
                # Test connection
                result = integration.test_connection()
                
                # Additional check: try to connect and access the folder
                if result.success:
                    if integration.connect(email_address):
                        try:
                            # Verify folder exists by trying to discover it
                            folders = integration.discover_folders(email_address)
                            folder_names = [f.name for f in folders]
                            
                            if folder_name not in folder_names:
                                result = ConnectionTestResult(
                                    success=False,
                                    error=f"Folder '{folder_name}' not found. Available folders: {', '.join(folder_names)}"
                                )
                            else:
                                logger.info(f"Successfully verified access to {email_address}/{folder_name}")
                        finally:
                            integration.disconnect()
                    else:
                        result = ConnectionTestResult(
                            success=False,
                            error="Failed to connect to email account"
                        )
                
                return result
            
            else:
                return ConnectionTestResult(
                    success=False,
                    error=f"Provider {provider_type} not yet supported"
                )
                
        except Exception as e:
            logger.error(f"Error testing connection for {email_address}/{folder_name}: {e}")
            return ConnectionTestResult(
                success=False,
                error=str(e)
            )
    
    # ========== Configuration Management ==========
    
    def create_config(self, config_create: EmailConfigCreate) -> EmailConfig:
        """Create new email configuration"""
        try:
            # Test connection and verify folder exists
            test_result = self.test_connection_for_new_config(
                email_address=config_create.email_address,
                folder_name=config_create.folder_name
            )
            if not test_result.success:
                raise ServiceError(f"Connection test failed: {test_result.error}")
            
            # Create config in database
            config = self.config_repository.create(config_create)
            logger.info(f"Created email config {config.id}: {config.name}")
            return config
            
        except Exception as e:
            logger.error(f"Error creating config: {e}")
            raise
    
    def get_config(self, config_id: int) -> Optional[EmailConfig]:
        """Get specific configuration"""
        config = self.config_repository.get_by_id(config_id)
        return config
    
    def update_config(self, config_id: int, updates: EmailConfigUpdate) -> EmailConfig:
        """
        Update configuration
        If config is active, restart listener with new settings
        """
        try:
            # Check if listener is active
            was_active = config_id in self.active_listeners
            
            # Stop listener if active
            if was_active:
                self.deactivate_config(config_id)
            
            # Update config
            config = self.config_repository.update(config_id, updates)
            logger.info(f"Updated config {config_id}")
            
            # Restart if was active
            if was_active and config.is_active:
                self.activate_config(config_id)
            
            return config
            
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating config {config_id}: {e}")
            raise
    
    def delete_config(self, config_id: int) -> EmailConfig:
        """Delete configuration (stops listener first if active)"""
        try:
            # Stop listener if active
            if config_id in self.active_listeners:
                self.deactivate_config(config_id)
            
            # Delete from database
            result = self.config_repository.delete(config_id)
            logger.info(f"Deleted config {config_id}")
            return result
            
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting config {config_id}: {e}")
            raise
    
    def list_configs(self) -> List[EmailConfig]:
        """List all configurations"""
        return self.config_repository.get_all()
    
    def list_config_summaries(self) -> List[EmailConfigSummary]:
        """List configuration summaries for UI"""
        return self.config_repository.get_all_summaries()
    
    # ========== Listener Management ==========
    
    def activate_config(self, config_id: int) -> EmailConfig:
        """
        Activate email monitoring for a configuration
        
        Args:
            config_id: Configuration to activate
            
        Returns:
            True if successfully activated
        """
        with self.lock:
            try:
                config = self.config_repository.get_by_id(config_id)
                if not config:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                  
                # Check if already active
                if config_id in self.active_listeners:
                    logger.warning(f"Config {config_id} is already active")
                    return config
                
                logger.info(f"Activating config {config_id}: {config.name}")
                
                # Create integration
                integration_config = OutlookComConfig(
                    provider_type=EmailProvider.OUTLOOK_COM,
                    account_identifier=config.email_address,
                    default_folder=config.folder_name
                )
                integration = EmailIntegrationFactory.create_integration(integration_config)
                
                # Connect integration
                if not integration.connect(config.email_address):
                    raise ServiceError("Failed to connect email integration")
                
                # Create process callback bound to this config
                process_callback = partial(self.process_email, config_id)
                
                # Create and start listener thread
                listener = EmailListenerThread(
                    config=config,
                    integration=integration,
                    process_callback=process_callback
                )
                listener.start()
                
                # Store references
                self.active_integrations[config_id] = integration
                self.active_listeners[config_id] = listener
                
                # Update config status
                config = self.config_repository.activate(
                    config_id, 
                    activation_time=datetime.now(timezone.utc)
                )
                
                logger.info(f"Successfully activated config {config_id}")
                return config
                
            except Exception as e:
                logger.error(f"Error activating config {config_id}: {e}")
                # Clean up on failure
                if config_id in self.active_integrations:
                    self.active_integrations[config_id].disconnect()
                    del self.active_integrations[config_id]
                if config_id in self.active_listeners:
                    del self.active_listeners[config_id]
                raise ServiceError(f"Failed to activate config: {str(e)}")
    
    def stop_config_listeners(self, config_id: int) -> bool:
        """
        Stop listeners and integrations for a config WITHOUT changing database status
        Used during app shutdown to preserve config state for startup recovery

        Args:
            config_id: Configuration to stop listeners for

        Returns:
            True if successfully stopped
        """
        with self.lock:
            try:
                logger.info(f"Stopping listeners for config {config_id} (preserving config status)")

                # Stop listener thread
                if config_id in self.active_listeners:
                    listener = self.active_listeners[config_id]
                    listener.stop()
                    listener.join(timeout=5.0)  # Wait up to 5 seconds
                    del self.active_listeners[config_id]
                    logger.debug(f"Stopped listener thread for config {config_id}")

                # Disconnect integration
                if config_id in self.active_integrations:
                    integration = self.active_integrations[config_id]
                    integration.disconnect()
                    del self.active_integrations[config_id]
                    logger.debug(f"Disconnected integration for config {config_id}")

                # DO NOT call self.config_repository.deactivate() - preserve DB status

                logger.info(f"Successfully stopped listeners for config {config_id} (config remains active in DB)")
                return True

            except Exception as e:
                logger.error(f"Error stopping listeners for config {config_id}: {e}")
                raise ServiceError(f"Failed to stop config listeners: {str(e)}")

    def deactivate_config(self, config_id: int) -> bool:
        """
        Deactivate email monitoring for a configuration (user-initiated)
        Stops runtime resources AND changes database status to inactive

        Args:
            config_id: Configuration to deactivate

        Returns:
            True if successfully deactivated
        """
        with self.lock:
            try:
                logger.info(f"Deactivating config {config_id} (user-initiated - will change DB status)")

                # Stop listener thread
                if config_id in self.active_listeners:
                    listener = self.active_listeners[config_id]
                    listener.stop()
                    listener.join(timeout=5.0)  # Wait up to 5 seconds
                    del self.active_listeners[config_id]

                # Disconnect integration
                if config_id in self.active_integrations:
                    integration = self.active_integrations[config_id]
                    integration.disconnect()
                    del self.active_integrations[config_id]

                # Update config status in database (user-initiated deactivation)
                self.config_repository.deactivate(config_id)

                logger.info(f"Successfully deactivated config {config_id} (config marked inactive in DB)")
                return True

            except Exception as e:
                logger.error(f"Error deactivating config {config_id}: {e}")
                raise ServiceError(f"Failed to deactivate config: {str(e)}")
    
    def get_active_listeners(self) -> Dict[int, ListenerStatus]:
        """Get status of all active listeners"""
        with self.lock:
            statuses = {}
            
            for config_id, listener in self.active_listeners.items():
                config = self.config_repository.get_by_id(config_id)
                if config:
                    statuses[config_id] = ListenerStatus(
                        config_id=config_id,
                        email_address=config.email_address,
                        folder_name=config.folder_name,
                        is_active=config.is_active,
                        is_running=listener.is_alive(),
                        start_time=config.activated_at,
                        last_check_time=config.last_check_time,
                        error_count=listener.error_count,
                        emails_processed=config.total_emails_processed,
                        pdfs_found=config.total_pdfs_found
                    )
            
            return statuses
    
    # ========== Email Processing ==========
    
    def process_email(self, config_id: int, email_msg: EmailMessage, attachments: List[EmailAttachment]):
        """
        Process an email retrieved by a listener
        
        Args:
            config_id: Configuration that retrieved this email
            email_msg: Email message from integration
            attachments: List of attachments
        """
        try:
            # Check if already processed
            if self.email_repository.exists_by_message_id(config_id, email_msg.message_id):
                logger.debug(f"Email {email_msg.message_id} already processed for config {config_id}")
                return
            
            logger.info(f"Processing email: {email_msg.subject} from {email_msg.sender_email}")
            
            # Count PDFs
            pdf_count = sum(1 for a in attachments 
                          if a.content_type == "application/pdf" or a.filename.lower().endswith('.pdf'))
            
            # Create email record using Pydantic model
            email_create = EmailCreate(
                config_id=config_id,
                message_id=email_msg.message_id,
                subject=email_msg.subject,
                sender_email=email_msg.sender_email,
                sender_name=email_msg.sender_name,
                received_date=email_msg.received_date,
                folder_name=email_msg.folder_name,
                has_pdf_attachments=pdf_count > 0,
                attachment_count=len(attachments),
                pdf_count=pdf_count,
                body_preview=email_msg.body_preview
            )
            
            # Save email to database
            email_record = self.email_repository.create(email_create)
            
            # Process PDF attachments
            for attachment in attachments:
                if attachment.content_type == "application/pdf" or attachment.filename.lower().endswith('.pdf'):
                    try:
                        self._process_pdf_attachment(email_record.id, attachment)
                    except Exception as e:
                        logger.error(f"Error processing PDF {attachment.filename}: {e}")
            
            # Update statistics
            self.config_repository.update_progress(
                config_id,
                current_time=datetime.now(timezone.utc),
                emails_processed=1,
                pdfs_found=pdf_count
            )
            
            logger.info(f"Successfully processed email with {pdf_count} PDFs")
            
        except Exception as e:
            logger.error(f"Error processing email {email_msg.message_id}: {e}")
            # Record error but don't stop processing
            try:
                self.config_repository.record_error(config_id, str(e))
            except:
                pass
    
    def _process_pdf_attachment(self, email_id: int, attachment: EmailAttachment):
        """
        Process a PDF attachment through the complete pipeline

        Args:
            email_id: Database ID of the email
            attachment: PDF attachment to process
        """
        try:
            logger.info(f"Processing PDF: {attachment.filename} ({attachment.size_bytes} bytes)")

            # Step 1: Store PDF using PDF processing service
            from shared.services import get_pdf_processing_service
            pdf_service = get_pdf_processing_service()

            # Store PDF and get file record
            pdf_file = pdf_service.store_pdf(
                file_content=attachment.content,
                original_filename=attachment.filename,
                email_id=email_id
            )

            logger.info(f"PDF stored successfully: {pdf_file.id}")

            # Step 2: Trigger ETO processing pipeline
            from shared.services import get_eto_processing_service
            eto_service = get_eto_processing_service()

            # Start ETO processing for the stored PDF
            eto_run = eto_service.process_pdf(pdf_file.id)

            logger.info(f"ETO processing initiated for PDF {pdf_file.id}, ETO run: {eto_run.id}, status: {eto_run.status}")

            # Log success metrics
            if eto_run.status == "success":
                logger.info(f"PDF attachment successfully processed end-to-end: {attachment.filename}")
            elif eto_run.status == "needs_template":
                logger.warning(f"PDF requires manual template assignment: {attachment.filename}")
            elif eto_run.status == "failure":
                logger.error(f"PDF processing failed: {attachment.filename}, error: {eto_run.error_message}")

        except Exception as e:
            logger.error(f"Failed to process PDF attachment {attachment.filename}: {e}")
            # Don't re-raise - email processing should continue even if PDF processing fails
    
    # ========== Query Methods ==========
    
    def get_processed_emails(self, config_id: int, limit: int = 100) -> List[Email]:
        """Get emails processed by a specific configuration"""
        return self.email_repository.get_by_config(config_id, limit)
    
    def get_processing_statistics(self, config_id: int) -> Dict[str, Any]:
        """Get processing statistics for a configuration"""
        config = self.config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError('EmailConfig', config_id)
        
        return {
            "config_id": config_id,
            "name": config.name,
            "is_active": config.is_active,
            "is_running": config_id in self.active_listeners,
            "total_emails_processed": config.total_emails_processed,
            "total_pdfs_found": config.total_pdfs_found,
            "last_check_time": config.last_check_time,
            "activated_at": config.activated_at,
            "last_error": config.last_error_message,
            "last_error_at": config.last_error_at
        }
    
    # ========== Service Lifecycle ==========
    
    def startup_recovery(self):
        """
        Recover active configurations on service startup
        Called when the application starts
        """
        try:
            logger.info("Starting email ingestion service recovery")
            
            # Get all active configs
            active_configs = self.config_repository.get_active_configs()
            
            if not active_configs:
                logger.info("No active email configurations to recover")
                return
            
            logger.info(f"Found {len(active_configs)} active configurations to recover")
            
            # Try to restart each one
            for config in active_configs:
                try:
                    logger.info(f"Recovering config {config.id}: {config.name}")
                    self.activate_config(config.id)
                except Exception as e:
                    logger.error(f"Failed to recover config {config.id}: {e}")
                    # Mark as inactive if we can't recover
                    try:
                        self.config_repository.deactivate(config.id)
                    except:
                        pass
            
            logger.info("Email ingestion service recovery complete")
            
        except Exception as e:
            logger.error(f"Error during startup recovery: {e}")

    def is_healthy(self) -> bool:
        """
        Check if the email ingestion service is healthy

        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Check if we can access the database
            with self.connection_manager.session_scope() as session:
                session.execute("SELECT 1")

            # Check if repositories are accessible
            self.email_repository.count_by_config(1)  # Test query

            return True
        except Exception as e:
            logger.error(f"Email ingestion service health check failed: {e}")
            return False

    def stop_all_listeners(self):
        """
        Stop all active listeners without changing config database status
        Used during app shutdown to preserve config states for startup recovery
        """
        logger.info("Stopping all email ingestion listeners (preserving config states)")

        with self.lock:
            # Get list of active config IDs to avoid modifying dict during iteration
            active_config_ids = list(self.active_listeners.keys())

            if not active_config_ids:
                logger.info("No active listeners to stop")
                return

            logger.info(f"Stopping listeners for {len(active_config_ids)} configurations")

            # Stop listeners for each config without changing DB status
            for config_id in active_config_ids:
                try:
                    self.stop_config_listeners(config_id)
                except Exception as e:
                    logger.error(f"Error stopping listeners for config {config_id}: {e}")
                    # Continue stopping other listeners even if one fails

        logger.info("All email ingestion listeners stopped (configs remain active in database)")

    def shutdown(self):
        """
        Gracefully shutdown all listeners while preserving config database status
        Called when the application is stopping
        """
        logger.info("Shutting down email ingestion service")

        # Stop all listeners without changing database config status
        self.stop_all_listeners()

        logger.info("Email ingestion service shutdown complete")