"""
Email Ingestion Service
Runtime orchestration for multiple email configurations
"""
import logging
import threading
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared.models.email_config import EmailConfig
from shared.exceptions import ServiceError
from features.email_configs.service import EmailConfigService
from features.email_ingestion.email_listener import EmailListenerThread
from shared.database.repositories.email import EmailRepository

logger = logging.getLogger(__name__)


@dataclass
class EmailListener:
    """Container for managing an email listener thread"""
    config: EmailConfig
    thread: EmailListenerThread
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_check: Optional[datetime] = None
    error_count: int = 0
    status: str = "initializing"


class EmailIngestionService:
    """Service for managing multiple concurrent email listeners"""
    
    def __init__(self, 
                 config_service: EmailConfigService,
                 email_repository: EmailRepository):
        self.config_service = config_service
        self.email_repository = email_repository
        
        # Thread-safe listener management
        self.listeners: Dict[int, EmailListener] = {}
        self.listeners_lock = threading.RLock()
        
        # Service state
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        logger.info("EmailIngestionService initialized")
    
    def startup_recovery(self):
        """Resume monitoring for all active configs on service startup"""
        try:
            logger.info("Starting email ingestion service recovery...")
            self.is_running = True
            
            # Get all active configs
            active_configs = self.config_service.list_configs(is_active=True)
            
            if not active_configs:
                logger.info("No active configurations to recover")
                return
            
            # Resume monitoring for each active config
            for config in active_configs:
                try:
                    # Check if config has been activated before (has progress tracking)
                    if config.last_check_time:
                        logger.info(f"Resuming monitoring for config {config.id} "
                                   f"(last check: {config.last_check_time})")
                    else:
                        logger.info(f"Starting fresh monitoring for config {config.id}")
                    
                    # Start listener
                    self._start_listener(config)
                    
                except Exception as e:
                    logger.error(f"Failed to recover config {config.id}: {e}")
                    # Continue with other configs
            
            logger.info(f"Recovery complete: {len(self.listeners)} listeners active")
            
        except Exception as e:
            logger.error(f"Failed to perform startup recovery: {e}")
            raise ServiceError(f"Startup recovery failed: {e}") from e
    
    def shutdown(self):
        """Gracefully shutdown all listeners"""
        logger.info("Shutting down email ingestion service...")
        self.is_running = False
        self.shutdown_event.set()
        
        with self.listeners_lock:
            # Stop all listeners
            for config_id, listener in list(self.listeners.items()):
                try:
                    logger.info(f"Stopping listener for config {config_id}")
                    listener.thread.stop()
                    listener.thread.join(timeout=5)
                except Exception as e:
                    logger.error(f"Error stopping listener {config_id}: {e}")
            
            self.listeners.clear()
        
        logger.info("Email ingestion service shutdown complete")
    
    def activate_config(self, config: EmailConfig):
        """Activate email monitoring for a configuration"""
        if not self.is_running:
            raise ServiceError("Email ingestion service is not running")
        
        with self.listeners_lock:
            # Check if already active
            if config.id in self.listeners:
                logger.warning(f"Config {config.id} is already active")
                return
            
            # Start listener (config already has progress tracking from activation)
            self._start_listener(config)
            logger.info(f"Activated monitoring for config {config.id}")
    
    def deactivate_config(self, config_id: int):
        """Deactivate email monitoring and delete cursor for fresh start"""
        with self.listeners_lock:
            # Stop listener if running
            if config_id in self.listeners:
                listener = self.listeners[config_id]
                try:
                    logger.info(f"Stopping listener for config {config_id}")
                    listener.thread.stop()
                    listener.thread.join(timeout=5)
                except Exception as e:
                    logger.error(f"Error stopping listener {config_id}: {e}")
                finally:
                    del self.listeners[config_id]
            
            # Progress will be cleared when config is deactivated via config_service
            
            logger.info(f"Deactivated monitoring for config {config_id}")
    
    def _start_listener(self, config: EmailConfig):
        """Internal method to start a listener thread"""
        try:
            # Create listener thread
            thread = EmailListenerThread(
                config=config,
                config_service=self.config_service,
                email_repository=self.email_repository,
                check_interval=config.poll_interval_seconds
            )
            
            # Create listener container
            listener = EmailListener(
                config=config,
                thread=thread,
                status="starting"
            )
            
            # Start thread
            thread.start()
            listener.status = "running"
            
            # Store listener
            self.listeners[config.id] = listener
            
            logger.info(f"Started listener for config {config.id}")
            
        except Exception as e:
            logger.error(f"Failed to start listener for config {config.id}: {e}")
            raise ServiceError(f"Failed to start listener: {e}") from e
    
    def get_status(self, config_id: int) -> dict:
        """Get status of a specific configuration's monitoring"""
        with self.listeners_lock:
            if config_id not in self.listeners:
                # Check if config exists and return progress stats
                config = self.config_service.get_config(config_id)
                if config:
                    return {
                        "is_active": config.is_active,
                        "status": "inactive" if not config.is_active else "stopped",
                        "emails_processed": config.total_emails_processed,
                        "pdfs_found": config.total_pdfs_found,
                        "last_check_time": config.last_check_time
                    }
                return {
                    "is_active": False,
                    "status": "not_found"
                }
            
            listener = self.listeners[config_id]
            config = listener.config
            
            return {
                "is_active": True,
                "status": listener.status,
                "start_time": listener.start_time,
                "last_check": listener.last_check,
                "error_count": listener.error_count,
                "thread_alive": listener.thread.is_alive(),
                "emails_processed": config.total_emails_processed,
                "pdfs_found": config.total_pdfs_found,
                "last_check_time": config.last_check_time
            }
    
    def get_all_status(self) -> dict:
        """Get status of all configurations"""
        with self.listeners_lock:
            status = {
                "service_running": self.is_running,
                "active_listeners": len(self.listeners),
                "configs": {}
            }
            
            # Get all configs
            all_configs = self.config_service.list_configs()
            
            for config in all_configs:
                status["configs"][config.id] = self.get_status(config.id)
            
            return status
    
    def refresh_config(self, config_id: int):
        """Refresh a configuration if its settings have changed"""
        with self.listeners_lock:
            # Get updated config
            config = self.config_service.get_config(config_id)
            if not config:
                logger.warning(f"Config {config_id} not found")
                return
            
            # If active and running, restart with new settings
            if config.is_active and config_id in self.listeners:
                logger.info(f"Refreshing listener for config {config_id}")
                
                # Stop current listener
                listener = self.listeners[config_id]
                listener.thread.stop()
                listener.thread.join(timeout=5)
                del self.listeners[config_id]
                
                # Start with new settings
                self._start_listener(config)
            elif config.is_active and config_id not in self.listeners:
                # Config was activated but listener not running
                logger.info(f"Starting listener for newly activated config {config_id}")
                self.activate_config(config)
            elif not config.is_active and config_id in self.listeners:
                # Config was deactivated but listener still running
                logger.info(f"Stopping listener for deactivated config {config_id}")
                self.deactivate_config(config_id)