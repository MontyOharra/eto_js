"""
Email Ingestion Service
Main orchestrator for email processing with automatic startup and downtime recovery
"""
import asyncio
import logging
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from .outlook_connection_service import OutlookConnectionService
from .email_filter_service import EmailFilterService
from .email_types import EmailConnectionConfig, EmailData
from .email_cursor_service import EmailCursorService
from .email_config_service import EmailConfigService, ConfigurationData
from ..database import get_connection_manager
from ..database.repositories import EmailConfigRepository, CursorRepository

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Email ingestion statistics"""
    emails_processed: int = 0
    emails_filtered: int = 0
    pdfs_extracted: int = 0
    processing_errors: int = 0
    last_processed_at: Optional[datetime] = None
    uptime_seconds: int = 0
    reconnections: int = 0


@dataclass
class ServiceHealth:
    """Service health status"""
    is_running: bool = False
    is_connected: bool = False
    configuration_loaded: bool = False
    last_error: Optional[str] = None
    stats: IngestionStats = field(default_factory=IngestionStats)


class EmailIngestionService:
    """Main orchestrator for email processing with automatic startup and downtime recovery"""
    
    def __init__(self):        
        # Database access
        self.connection_manager = get_connection_manager()
        assert self.connection_manager is not None
        
        self.config_repo = EmailConfigRepository(self.connection_manager)
        self.cursor_repo = CursorRepository(self.connection_manager)
        
        # Core services
        self.connection_service = OutlookConnectionService()
        self.filter_service = EmailFilterService()
        
        # Initialize services with repository dependencies
        self.cursor_service = EmailCursorService(self.cursor_repo)
        self.config_service = EmailConfigService()
        
        # Service state
        self.is_running = False
        self.is_stopping = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.current_config: Optional[ConfigurationData] = None
        
        # Statistics and health
        self.stats = IngestionStats()
        self.start_time: Optional[datetime] = None
        self.last_health_check = datetime.now(timezone.utc)
        
        # Thread safety
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)


    # === Service Health and Status ===
    async def get_health_status(self) -> ServiceHealth:
        """Get comprehensive service health status"""
        try:
            # Update uptime
            if self.start_time and self.is_running:
                uptime_delta = datetime.now(timezone.utc) - self.start_time
                self.stats.uptime_seconds = int(uptime_delta.total_seconds())
            
            # Check connection health
            connection_status = await self.connection_service.get_connection_status()
            
            return ServiceHealth(
                is_running=self.is_running,
                is_connected=connection_status.is_connected,
                configuration_loaded=self.current_config is not None,
                last_error=connection_status.last_error,
                stats=self.stats
            )
        
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return ServiceHealth(
                is_running=self.is_running,
                is_connected=False,
                configuration_loaded=False,
                last_error=str(e),
                stats=self.stats
            )
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed service status including configuration and statistics"""
        try:
            health = await self.get_health_status()
            
            connection_status = await self.connection_service.get_connection_status()
            
            status = {
                "service": {
                    "is_running": health.is_running,
                    "uptime_minutes": self._get_uptime_minutes(),
                    "last_health_check": self.last_health_check
                },
                "connection": {
                    "is_connected": health.is_connected,
                    "email_address": connection_status.email_address,
                    "folder_name": connection_status.folder_name,
                    "inbox_count": connection_status.inbox_count,
                    "last_error": connection_status.last_error
                },
                "statistics": {
                    "emails_processed": health.stats.emails_processed,
                    "emails_filtered": health.stats.emails_filtered,
                    "pdfs_extracted": health.stats.pdfs_extracted,
                    "processing_errors": health.stats.processing_errors,
                    "reconnections": health.stats.reconnections,
                    "last_processed_at": health.stats.last_processed_at
                }
            }
            
            # Add configuration info if loaded
            if self.current_config:
                status["configuration"] = {
                    "filter_name": self.current_config.filters.name,
                    "polling_interval": self.current_config.connection.polling_interval,
                    "auto_reconnect": self.current_config.monitoring.auto_reconnect,
                    "rule_count": len(self.current_config.filters.rules)
                }
            
            return status
        
        except Exception as e:
            self.logger.error(f"Error getting detailed status: {e}")
            return {"error": str(e)}


    # === High-Level Service Lifecycle ===
    
    async def start_service(self) -> Dict[str, Any]:
        """Start the email ingestion service with automatic configuration loading"""
        try:
            with self._lock:
                if self.is_running:
                    return {
                        "success": True,
                        "message": "Service is already running",
                        "status": await self.get_health_status()
                    }
                
                self.logger.info("Starting Email Ingestion Service")
                
                self.current_config = self.config_service.get_active_configuration()
                assert self.current_config is not None
                
                # Initialize services with configuration
                await self._initialize_services()
                
                connection_status = await self.connection_service.get_connection_status()
                
                # Connect to Outlook
                if not connection_status.is_connected:
                    raise Exception(f"Failed to connect to Outlook: {connection_status.last_error}")
                
                # Start monitoring thread
                self.is_running = True
                self.is_stopping = False
                self.start_time = datetime.now(timezone.utc)
                self.stats = IngestionStats()
                
                self.monitoring_thread = threading.Thread(
                    target=self._run_monitoring_loop,
                    name="EmailIngestionMonitoring",
                    daemon=True
                )
                self.monitoring_thread.start()
                
                # Process any backlog from downtime
                await self._process_downtime_backlog()
                
                self.logger.info("Email Ingestion Service started successfully")
                
                
                return {
                    "success": True,
                    "message": "Service started successfully",
                    "configuration": {
                        "email_address": connection_status.email_address,
                        "folder_name": connection_status.folder_name,
                        "filter_name": self.current_config.filters.name
                    },
                    "connection_status": {
                        "is_connected": connection_status.is_connected,
                        "inbox_count": connection_status.inbox_count
                    }
                }
        
        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            await self._cleanup_on_error()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start service"
            }
    
    async def stop_service(self) -> Dict[str, Any]:
        """Stop the email ingestion service gracefully"""
        try:
            with self._lock:
                if not self.is_running:
                    return {
                        "success": True,
                        "message": "Service is not running"
                    }
                
                self.logger.info("Stopping Email Ingestion Service")
                
                # Signal monitoring thread to stop
                self.is_stopping = True
                self.is_running = False
                
                # Wait for monitoring thread to finish
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=10.0)
                    if self.monitoring_thread.is_alive():
                        self.logger.warning("Monitoring thread did not stop gracefully")
                
                # Disconnect from Outlook
                await self.connection_service.disconnect()
                
                # Update final cursor state
                if self.current_config:
                    await self._update_cursor_state()
                
                self.logger.info("Email Ingestion Service stopped")
                
                return {
                    "success": True,
                    "message": "Service stopped successfully",
                    "final_stats": {
                        "emails_processed": self.stats.emails_processed,
                        "uptime_minutes": self._get_uptime_minutes()
                    }
                }
        
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error occurred while stopping service"
            }
    
    async def restart_service(self) -> Dict[str, Any]:
        """Restart the email ingestion service"""
        try:
            self.logger.info("Restarting Email Ingestion Service")
            
            # Stop current service
            stop_result = await self.stop_service()
            if not stop_result["success"]:
                return stop_result
            
            # Wait a moment for cleanup
            await asyncio.sleep(2)
            
            # Start service again
            start_result = await self.start_service()
            
            if start_result["success"]:
                self.stats.reconnections += 1
                self.logger.info("Email Ingestion Service restarted successfully")
            
            return start_result
        
        except Exception as e:
            self.logger.error(f"Error restarting service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to restart service"
            }

    # === Configuration Management ===
    
    async def reload_configuration(self) -> Dict[str, Any]:
        """Reload active configuration without restarting service"""
        try:
            self.logger.info("Reloading email ingestion configuration")
            
            # Load new configuration
            new_config = self.config_service.get_active_configuration()
            if not new_config:
                raise Exception("No active configuration found")
            
            # Check if connection settings changed
            connection_changed = (
                not self.current_config or
                new_config.connection.email_address != self.current_config.connection.email_address or
                new_config.connection.folder_name != self.current_config.connection.folder_name
            )
            
            # Update configuration
            old_config = self.current_config
            self.current_config = new_config
            
            # Reinitialize filter service with new rules
            await self.filter_service.load_configuration(self.current_config.filters)
            
            # Reconnect if connection settings changed
            if connection_changed and self.is_running:
                self.logger.info("Connection settings changed, reconnecting...")
                
                connection_config = EmailConnectionConfig(
                    email_address=new_config.connection.email_address,
                    folder_name=new_config.connection.folder_name
                )
                
                await self.connection_service.disconnect()
                connection_status = await self.connection_service.connect(connection_config)
                
                if not connection_status.is_connected:
                    # Rollback configuration on connection failure
                    self.current_config = old_config
                    if old_config:
                        await self.filter_service.load_configuration(old_config.filters)
                    raise Exception(f"Failed to reconnect with new settings: {connection_status.last_error}")
            
            self.logger.info("Configuration reloaded successfully")
            
            return {
                "success": True,
                "message": "Configuration reloaded successfully",
                "connection_changed": connection_changed,
                "filter_name": new_config.filters.name
            }
        
        except Exception as e:
            self.logger.error(f"Error reloading configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to reload configuration"
            }

    # === Private Implementation Methods ===
    
    async def _initialize_services(self) -> None:
        """Initialize all sub-services with current configuration"""
                
        if not self.current_config:
            raise Exception("No configuration loaded")
        
        # Create connection config once for both services
        connection_config = EmailConnectionConfig(
            email_address=self.current_config.connection.email_address,
            folder_name=self.current_config.connection.folder_name
        )
        
        await self.filter_service.load_configuration(self.current_config.filters)
        await self.cursor_service.initialize_cursor(connection_config)
        await self.connection_service.connect(connection_config)
        
        self.logger.debug("Sub-services initialized with current configuration")

    
    def _run_monitoring_loop(self) -> None:
        """Main monitoring loop (runs in separate thread)"""
        self.logger.info("Email monitoring loop started")
        
        try:
            while not self.is_stopping:
                try:
                    # Run async monitoring cycle
                    asyncio.run(self._monitoring_cycle())
                    
                    # Update health check time
                    self.last_health_check = datetime.now(timezone.utc)
                    
                    # Wait for next polling cycle
                    if self.current_config:
                        polling_interval = self.current_config.connection.polling_interval
                    else:
                        polling_interval = 60  # Default fallback
                    
                    for _ in range(polling_interval):
                        if self.is_stopping:
                            break
                        time.sleep(1)
                
                except Exception as cycle_error:
                    self.logger.error(f"Error in monitoring cycle: {cycle_error}")
                    self.stats.processing_errors += 1
                    
                    # Try to recover from errors
                    if self.current_config and self.current_config.monitoring.auto_reconnect:
                        asyncio.run(self._attempt_recovery())
                    else:
                        time.sleep(30)  # Wait before retrying
        
        except Exception as loop_error:
            self.logger.error(f"Fatal error in monitoring loop: {loop_error}")
        
        finally:
            self.logger.info("Email monitoring loop stopped")
    
    async def _monitoring_cycle(self) -> None:
        """Single monitoring cycle - check for new emails and process them"""
        try:
            if not self.current_config or not self.is_running:
                return
            
            # Get current Outlook folder
            folder = self.connection_service.get_current_folder()
            if not folder:
                self.logger.warning("No current folder available, attempting reconnection")
                await self._attempt_recovery()
                return
            
            # Get cursor state to determine what emails to process
            cursor_state = await self.cursor_service.get_cursor_state(
                email_address=self.current_config.connection.email_address or "default",
                folder=self.current_config.connection.folder_name
            )
            
            # Process emails since last cursor position
            emails_processed = await self._process_new_emails(folder, cursor_state)
            
            # Update statistics
            self.stats.emails_processed += emails_processed
            if emails_processed > 0:
                self.stats.last_processed_at = datetime.now(timezone.utc)
                
                # Update cursor state and database statistics
                await self._update_cursor_state()
                await self._update_processing_statistics(emails_processed)
        
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            raise
    
    async def _process_new_emails(self, folder, cursor_state: Dict[str, Any]) -> int:
        """Process new emails based on cursor state"""
        try:
            if not self.current_config:
                return 0
            
            processed_count = 0
            last_processed_time = cursor_state.get("last_processed_at")
            
            # Get emails from Outlook folder
            # Note: This is a simplified implementation - in practice, you'd need
            # to implement proper Outlook COM email iteration based on the cursor
            items = folder.Items
            items.Sort("[ReceivedTime]", True)  # Sort by received time, newest first
            
            # Process recent emails (limited batch to avoid performance issues)
            batch_size = 50
            for i in range(min(batch_size, items.Count)):
                try:
                    email_item = items.Item(i + 1)
                    
                    # Check if we've already processed this email based on cursor
                    email_received_time = email_item.ReceivedTime
                    if last_processed_time and email_received_time <= last_processed_time:
                        break  # We've reached emails we've already processed
                    
                    # Convert Outlook email to our EmailData format
                    email_data = self._convert_outlook_email(email_item)
                    
                    # Apply filters
                    filter_result = await self.filter_service.evaluate_email(
                        email_data, self.current_config.filters
                    )
                    
                    self.stats.emails_filtered += 1
                    
                    if filter_result["matches"]:
                        # Process email (extract PDFs, create ETO run, etc.)
                        success = await self._process_matching_email(email_item, email_data, filter_result)
                        if success:
                            processed_count += 1
                            pdf_count = len([f for f in email_data.attachment_filenames if f.lower().endswith('.pdf')])
                            self.stats.pdfs_extracted += pdf_count
                    
                except Exception as email_error:
                    self.logger.error(f"Error processing individual email: {email_error}")
                    self.stats.processing_errors += 1
                    continue
            
            return processed_count
        
        except Exception as e:
            self.logger.error(f"Error processing new emails: {e}")
            return 0
    
    def _convert_outlook_email(self, email_item) -> EmailData:
        """Convert Outlook email item to EmailData format"""
        try:
            # Extract attachments
            attachments = []
            if email_item.Attachments.Count > 0:
                for i in range(email_item.Attachments.Count):
                    attachment = email_item.Attachments.Item(i + 1)
                    attachments.append({
                        "filename": attachment.FileName,
                        "size": attachment.Size,
                        "content_type": "application/pdf" if attachment.FileName.lower().endswith('.pdf') else "unknown"
                    })
            
            # Process attachment info
            attachment_filenames = [att["filename"] for att in attachments]
            has_pdf_attachments = any(filename.lower().endswith('.pdf') for filename in attachment_filenames)
            
            return EmailData(
                subject=email_item.Subject or "",
                sender_email=email_item.SenderEmailAddress or "unknown",
                sender_name=email_item.SenderName,
                received_time=email_item.ReceivedTime,
                has_attachments=len(attachments) > 0,
                attachment_count=len(attachments),
                attachment_filenames=attachment_filenames,
                has_pdf_attachments=has_pdf_attachments,
                body_preview=email_item.Body[:200] if email_item.Body else None
            )
        
        except Exception as e:
            self.logger.error(f"Error converting Outlook email: {e}")
            # Return minimal EmailData on error
            return EmailData(
                subject="error",
                sender_email="unknown",
                sender_name=None,
                received_time=datetime.now(timezone.utc),
                has_attachments=False,
                attachment_count=0,
                attachment_filenames=[],
                has_pdf_attachments=False,
                body_preview=None
            )
    
    async def _process_matching_email(self, email_item, email_data: EmailData, filter_result: Dict[str, Any]) -> bool:
        """Process an email that matches filters (extract PDFs, create ETO run)"""
        try:
            self.logger.info(f"Processing matching email: {email_data.subject}")
            
            # This is where you'd integrate with the PDF extraction and ETO run creation
            # For now, we'll just log the processing
            
            if email_data.has_pdf_attachments:
                pdf_filenames = [f for f in email_data.attachment_filenames if f.lower().endswith('.pdf')]
                self.logger.info(f"Found {len(pdf_filenames)} PDF attachments to process")
                
                # Here you would:
                # 1. Save PDF attachments to storage
                # 2. Create ETO run record
                # 3. Trigger PDF processing pipeline
                # 4. Update email cursor with processed email info
                
                # For now, simulate processing
                await asyncio.sleep(0.1)  # Simulate processing time
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error processing matching email: {e}")
            return False
    
    async def _process_downtime_backlog(self) -> None:
        """Process any emails missed during service downtime"""
        try:
            if not self.current_config:
                return
            
            self.logger.info("Checking for emails missed during downtime")
            
            # Get backlog processing scope
            backlog_scope = await self.cursor_service.get_backlog_scope(
                email_address=self.current_config.connection.email_address or "default",
                folder=self.current_config.connection.folder_name,
                max_hours_back=self.current_config.connection.max_hours_back
            )
            
            if backlog_scope:
                start_time, end_time = backlog_scope
                self.logger.info(f"Processing backlog from {start_time} to {end_time}")
                
                # This would implement backlog processing logic
                # For now, we'll just update the cursor to current time
                await self.cursor_service.update_cursor_state(
                    email_address=self.current_config.connection.email_address or "default",
                    folder=self.current_config.connection.folder_name,
                    last_processed_at=datetime.now(timezone.utc),
                    processed_count=0,
                    last_email_id=None
                )
            else:
                self.logger.info("No backlog processing needed")
        
        except Exception as e:
            self.logger.error(f"Error processing downtime backlog: {e}")
    
    async def _attempt_recovery(self) -> bool:
        """Attempt to recover from connection errors"""
        try:
            if not self.current_config or not self.current_config.monitoring.auto_reconnect:
                return False
            
            self.logger.info("Attempting service recovery")
            
            max_attempts = self.current_config.monitoring.max_reconnect_attempts
            
            for attempt in range(max_attempts):
                try:
                    # Try to reconnect to Outlook
                    success = await self.connection_service.reconnect()
                    if success:
                        self.stats.reconnections += 1
                        self.logger.info(f"Service recovery successful (attempt {attempt + 1})")
                        return True
                
                except Exception as reconnect_error:
                    self.logger.warning(f"Recovery attempt {attempt + 1} failed: {reconnect_error}")
                
                if attempt < max_attempts - 1:
                    wait_time = min(30, 5 * (attempt + 1))  # Progressive backoff
                    await asyncio.sleep(wait_time)
            
            self.logger.error(f"Service recovery failed after {max_attempts} attempts")
            return False
        
        except Exception as e:
            self.logger.error(f"Error during recovery attempt: {e}")
            return False
    
    async def _update_cursor_state(self) -> None:
        """Update cursor state with latest processing information"""
        try:
            if not self.current_config:
                return
            
            await self.cursor_service.update_cursor_state(
                email_address=self.current_config.connection.email_address or "default",
                folder=self.current_config.connection.folder_name,
                last_processed_at=datetime.now(timezone.utc),
                processed_count=self.stats.emails_processed,
                last_email_id=None  # Would be set to actual last processed email ID
            )
        
        except Exception as e:
            self.logger.error(f"Error updating cursor state: {e}")
    
    async def _update_processing_statistics(self, processed_count: int) -> None:
        """Update database processing statistics"""
        try:
            async with self.connection_manager.get_session() as session:
                await self.config_repo.increment_processing_stats(
                    session, processed_count, datetime.now(timezone.utc)
                )
        
        except Exception as e:
            self.logger.error(f"Error updating processing statistics: {e}")
    
    async def _cleanup_on_error(self) -> None:
        """Clean up resources when service fails to start"""
        try:
            self.is_running = False
            self.is_stopping = True
            await self.connection_service.disconnect()
        except:
            pass  # Ignore cleanup errors
    
    def _get_uptime_minutes(self) -> int:
        """Get service uptime in minutes"""
        if not self.start_time:
            return 0
        
        uptime_delta = datetime.now(timezone.utc) - self.start_time
        return int(uptime_delta.total_seconds() / 60)