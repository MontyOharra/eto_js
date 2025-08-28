"""
Service Health Monitor
Monitors critical services and provides automatic restart capability
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RESTARTING = "restarting"
    FAILED = "failed"
    STOPPED = "stopped"

class ServiceMonitor:
    """Monitors service health and provides automatic recovery"""
    
    def __init__(self, check_interval: int = 30):
        self.services = {}  # service_name -> service_instance
        self.health_checks = {}  # service_name -> health_check_function
        self.restart_functions = {}  # service_name -> restart_function
        self.service_status = {}  # service_name -> ServiceStatus
        self.last_health_check = {}  # service_name -> datetime
        self.failure_counts = {}  # service_name -> int
        self.last_failure_time = {}  # service_name -> datetime
        
        self.check_interval = check_interval  # seconds
        self.monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        
        # Configuration
        self.max_failures = 3  # Max failures before marking as failed
        self.failure_reset_time = 300  # Reset failure count after 5 minutes
        self.restart_backoff_base = 30  # Base backoff time for restarts
        self.max_restart_backoff = 300  # Maximum backoff time
    
    def register_service(self, 
                        name: str, 
                        service_instance: Any,
                        health_check_func: Callable[[], bool],
                        restart_func: Optional[Callable[[], bool]] = None):
        """
        Register a service for health monitoring
        
        Args:
            name: Service name for identification
            service_instance: The service instance to monitor
            health_check_func: Function that returns True if service is healthy
            restart_func: Optional function to restart the service, returns True on success
        """
        with self._lock:
            self.services[name] = service_instance
            self.health_checks[name] = health_check_func
            if restart_func:
                self.restart_functions[name] = restart_func
            self.service_status[name] = ServiceStatus.HEALTHY
            self.failure_counts[name] = 0
            self.last_health_check[name] = datetime.now()
            
        logger.info(f"Registered service '{name}' for health monitoring")
    
    def unregister_service(self, name: str):
        """Unregister a service from monitoring"""
        with self._lock:
            if name in self.services:
                del self.services[name]
                del self.health_checks[name]
                if name in self.restart_functions:
                    del self.restart_functions[name]
                if name in self.service_status:
                    del self.service_status[name]
                if name in self.failure_counts:
                    del self.failure_counts[name]
                if name in self.last_health_check:
                    del self.last_health_check[name]
                if name in self.last_failure_time:
                    del self.last_failure_time[name]
                    
        logger.info(f"Unregistered service '{name}' from health monitoring")
    
    def start_monitoring(self):
        """Start the health monitoring loop"""
        with self._lock:
            if self.monitoring:
                logger.warning("Service monitor is already running")
                return
            
            if not self.services:
                logger.warning("No services registered for monitoring")
                return
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
        logger.info(f"Service monitor started - monitoring {len(self.services)} services")
    
    def stop_monitoring(self):
        """Stop the health monitoring loop"""
        with self._lock:
            if not self.monitoring:
                return
            
            self.monitoring = False
            monitor_thread = self.monitor_thread
        
        # Wait for monitoring thread to finish
        if monitor_thread and monitor_thread.is_alive():
            logger.info("Stopping service monitor...")
            monitor_thread.join(timeout=10)
            
            if monitor_thread.is_alive():
                logger.warning("Service monitor thread did not stop within timeout")
            else:
                logger.info("Service monitor stopped")
        
        with self._lock:
            self.monitor_thread = None
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Service monitoring loop started")
        
        while self.monitoring:
            try:
                self._check_all_services()
                
                # Sleep in small chunks to allow for quick shutdown
                for _ in range(self.check_interval):
                    if not self.monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in service monitoring loop: {e}")
                if self.monitoring:
                    time.sleep(5)  # Brief pause on error
        
        logger.info("Service monitoring loop stopped")
    
    def _check_all_services(self):
        """Check health of all registered services"""
        current_time = datetime.now()
        
        # Create a copy to avoid holding the lock too long
        with self._lock:
            services_to_check = list(self.services.keys())
        
        for service_name in services_to_check:
            if not self.monitoring:
                break
                
            try:
                self._check_service_health(service_name, current_time)
            except Exception as e:
                logger.error(f"Error checking health of service '{service_name}': {e}")
                self._mark_service_unhealthy(service_name, str(e))
    
    def _check_service_health(self, service_name: str, current_time: datetime):
        """Check health of a specific service"""
        if service_name not in self.health_checks:
            return
        
        try:
            is_healthy = self.health_checks[service_name]()
            
            with self._lock:
                self.last_health_check[service_name] = current_time
                
                if is_healthy:
                    # Service is healthy
                    if self.service_status[service_name] != ServiceStatus.HEALTHY:
                        logger.info(f"Service '{service_name}' recovered - status: healthy")
                        self.service_status[service_name] = ServiceStatus.HEALTHY
                        
                        # Reset failure count on recovery
                        self.failure_counts[service_name] = 0
                        if service_name in self.last_failure_time:
                            del self.last_failure_time[service_name]
                else:
                    # Service is unhealthy
                    self._mark_service_unhealthy(service_name, "Health check returned False")
                    
        except Exception as e:
            logger.error(f"Health check failed for service '{service_name}': {e}")
            self._mark_service_unhealthy(service_name, f"Health check exception: {str(e)}")
    
    def _mark_service_unhealthy(self, service_name: str, reason: str):
        """Mark a service as unhealthy and handle failure logic"""
        current_time = datetime.now()
        
        with self._lock:
            # Reset failure count if enough time has passed since last failure
            if (service_name in self.last_failure_time and 
                current_time - self.last_failure_time[service_name] > timedelta(seconds=self.failure_reset_time)):
                self.failure_counts[service_name] = 0
            
            self.failure_counts[service_name] += 1
            self.last_failure_time[service_name] = current_time
            
            failure_count = self.failure_counts[service_name]
            
            if failure_count >= self.max_failures:
                # Too many failures - mark as failed
                if self.service_status[service_name] != ServiceStatus.FAILED:
                    logger.error(f"Service '{service_name}' marked as failed after {failure_count} failures. Last reason: {reason}")
                    self.service_status[service_name] = ServiceStatus.FAILED
            else:
                # Mark as unhealthy and attempt restart
                if self.service_status[service_name] != ServiceStatus.UNHEALTHY:
                    logger.warning(f"Service '{service_name}' marked as unhealthy ({failure_count}/{self.max_failures}). Reason: {reason}")
                    self.service_status[service_name] = ServiceStatus.UNHEALTHY
                    
                # Attempt restart if restart function is available
                if service_name in self.restart_functions:
                    self._attempt_service_restart(service_name)
    
    def _attempt_service_restart(self, service_name: str):
        """Attempt to restart a failed service"""
        if service_name not in self.restart_functions:
            logger.warning(f"No restart function available for service '{service_name}'")
            return
        
        with self._lock:
            if self.service_status[service_name] == ServiceStatus.RESTARTING:
                logger.debug(f"Service '{service_name}' is already being restarted")
                return
            
            self.service_status[service_name] = ServiceStatus.RESTARTING
            failure_count = self.failure_counts[service_name]
        
        # Calculate backoff time (exponential backoff)
        backoff_time = min(
            self.restart_backoff_base * (2 ** (failure_count - 1)),
            self.max_restart_backoff
        )
        
        logger.info(f"Attempting to restart service '{service_name}' (attempt {failure_count}) after {backoff_time}s backoff")
        
        # Sleep for backoff time
        for _ in range(backoff_time):
            if not self.monitoring:
                return
            time.sleep(1)
        
        try:
            # Attempt restart
            restart_successful = self.restart_functions[service_name]()
            
            if restart_successful:
                logger.info(f"Successfully restarted service '{service_name}'")
                with self._lock:
                    self.service_status[service_name] = ServiceStatus.HEALTHY
                    # Don't reset failure count yet - let health check confirm recovery
            else:
                logger.error(f"Failed to restart service '{service_name}' - restart function returned False")
                with self._lock:
                    self.service_status[service_name] = ServiceStatus.UNHEALTHY
                    
        except Exception as e:
            logger.error(f"Exception during restart of service '{service_name}': {e}")
            with self._lock:
                self.service_status[service_name] = ServiceStatus.UNHEALTHY
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific service"""
        with self._lock:
            if service_name not in self.services:
                return {"error": f"Service '{service_name}' not registered"}
            
            return {
                "name": service_name,
                "status": self.service_status[service_name].value,
                "failure_count": self.failure_counts[service_name],
                "last_health_check": self.last_health_check[service_name].isoformat() if service_name in self.last_health_check else None,
                "last_failure_time": self.last_failure_time[service_name].isoformat() if service_name in self.last_failure_time else None,
                "has_restart_function": service_name in self.restart_functions
            }
    
    def get_all_services_status(self) -> Dict[str, Any]:
        """Get status of all monitored services"""
        with self._lock:
            services_status = {}
            for service_name in self.services.keys():
                services_status[service_name] = {
                    "status": self.service_status[service_name].value,
                    "failure_count": self.failure_counts[service_name],
                    "last_health_check": self.last_health_check[service_name].isoformat() if service_name in self.last_health_check else None,
                    "has_restart_function": service_name in self.restart_functions
                }
            
            return {
                "monitoring": self.monitoring,
                "total_services": len(self.services),
                "services": services_status,
                "check_interval": self.check_interval
            }
    
    def force_restart_service(self, service_name: str) -> bool:
        """Manually force restart of a service"""
        if service_name not in self.services:
            logger.error(f"Cannot restart - service '{service_name}' not registered")
            return False
        
        if service_name not in self.restart_functions:
            logger.error(f"Cannot restart - no restart function for service '{service_name}'")
            return False
        
        logger.info(f"Forcing restart of service '{service_name}'")
        
        try:
            with self._lock:
                self.service_status[service_name] = ServiceStatus.RESTARTING
            
            restart_successful = self.restart_functions[service_name]()
            
            with self._lock:
                if restart_successful:
                    self.service_status[service_name] = ServiceStatus.HEALTHY
                    self.failure_counts[service_name] = 0  # Reset failure count on manual restart
                    if service_name in self.last_failure_time:
                        del self.last_failure_time[service_name]
                    logger.info(f"Manual restart of service '{service_name}' successful")
                else:
                    self.service_status[service_name] = ServiceStatus.FAILED
                    logger.error(f"Manual restart of service '{service_name}' failed")
            
            return restart_successful
            
        except Exception as e:
            logger.error(f"Exception during manual restart of service '{service_name}': {e}")
            with self._lock:
                self.service_status[service_name] = ServiceStatus.FAILED
            return False

# Global service monitor instance
service_monitor = ServiceMonitor()

def get_service_monitor():
    """Get the global service monitor instance"""
    return service_monitor