"""
ETO Service Management API Schemas
Request/response models for ETO service control and monitoring endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from api.schemas.common import APIResponse

# === Service Status & Health Schemas ===

class WorkerConfiguration(BaseModel):
    """ETO processing worker configuration"""
    poll_interval_seconds: int = Field(..., ge=1, description="Polling interval in seconds")
    batch_size: int = Field(..., ge=1, le=100, description="Maximum runs to process per batch")
    max_concurrent_runs: int = Field(..., ge=1, description="Maximum concurrent processing")
    timeout_seconds: int = Field(..., ge=60, description="Processing timeout per run")


class WorkerStatus(BaseModel):
    """Current worker status information"""
    is_running: bool
    worker_thread_id: Optional[str] = None
    started_at: Optional[datetime] = None
    uptime_seconds: Optional[int] = None
    last_poll_at: Optional[datetime] = None
    current_batch_size: int = 0
    runs_processed_total: int = 0
    runs_processed_session: int = 0


class ServiceHealth(BaseModel):
    """Overall service health status"""
    status: Literal["healthy", "degraded", "unhealthy", "stopped"]
    database_connected: bool
    queue_accessible: bool
    last_successful_processing: Optional[datetime] = None
    error_count_last_hour: int = 0
    warning_count_last_hour: int = 0


class EtoServiceStatus(BaseModel):
    """Complete ETO service status"""
    service_name: str = "ETO Processing Service"
    version: str = "1.0.0"

    # Overall health
    health: ServiceHealth

    # Worker information
    worker: WorkerStatus
    configuration: WorkerConfiguration

    # Current processing state
    pending_runs: int = 0
    processing_runs: int = 0
    failed_runs_last_hour: int = 0

    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Timestamps
    status_timestamp: datetime
    last_restart: Optional[datetime] = None


class EtoServiceStatusResponse(APIResponse):
    """Response for ETO service status"""
    data: Optional[EtoServiceStatus] = None


# === Service Metrics Schemas ===

class ProcessingMetrics(BaseModel):
    """Processing performance metrics"""
    # Throughput metrics
    runs_per_hour_avg: float = 0.0
    runs_per_hour_peak: float = 0.0
    processing_rate_trend: Literal["increasing", "stable", "decreasing"] = "stable"

    # Performance metrics
    avg_processing_time_ms: Optional[int] = None
    median_processing_time_ms: Optional[int] = None
    p95_processing_time_ms: Optional[int] = None
    p99_processing_time_ms: Optional[int] = None

    # Success metrics
    success_rate_24h: float = Field(..., ge=0.0, le=1.0)
    success_rate_7d: float = Field(..., ge=0.0, le=1.0)
    success_rate_30d: float = Field(..., ge=0.0, le=1.0)


class ErrorMetrics(BaseModel):
    """Error tracking metrics"""
    total_errors_24h: int = 0
    total_errors_7d: int = 0
    total_errors_30d: int = 0

    # Error breakdown by type
    template_matching_errors: int = 0
    data_extraction_errors: int = 0
    transformation_errors: int = 0
    pipeline_errors: int = 0

    # Most common errors
    most_frequent_errors: List[Dict[str, Any]] = []


class QueueMetrics(BaseModel):
    """Processing queue metrics"""
    pending_runs: int = 0
    processing_runs: int = 0
    queue_depth_trend: Literal["growing", "stable", "shrinking"] = "stable"
    avg_queue_wait_time_ms: Optional[int] = None
    longest_waiting_run_age_ms: Optional[int] = None


class ResourceMetrics(BaseModel):
    """System resource usage metrics"""
    memory_usage_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cpu_peak_percent: float = 0.0

    # Database metrics
    db_connection_pool_size: int = 0
    db_active_connections: int = 0
    db_query_avg_time_ms: Optional[float] = None


class EtoServiceMetrics(BaseModel):
    """Comprehensive ETO service metrics"""
    collection_timestamp: datetime
    collection_period_hours: int = 24

    # Core metrics
    processing: ProcessingMetrics
    errors: ErrorMetrics
    queue: QueueMetrics
    resources: ResourceMetrics

    # Service uptime
    service_uptime_hours: float = 0.0
    total_restarts: int = 0
    last_restart_reason: Optional[str] = None


class EtoServiceMetricsResponse(APIResponse):
    """Response for ETO service metrics"""
    data: Optional[EtoServiceMetrics] = None


# === Service Control Schemas ===

class StartServiceRequest(BaseModel):
    """Request to start ETO processing service"""
    poll_interval: Optional[int] = Field(None, ge=1, le=300, description="Polling interval in seconds")
    batch_size: Optional[int] = Field(None, ge=1, le=100, description="Batch size for processing")
    force_restart: bool = Field(False, description="Force restart if already running")


class StartServiceResponse(APIResponse):
    """Response for starting ETO service"""
    service_started: bool = False
    was_already_running: bool = False
    worker_thread_id: str = ""
    configuration: Optional[WorkerConfiguration] = None


class StopServiceRequest(BaseModel):
    """Request to stop ETO processing service"""
    graceful: bool = Field(True, description="Wait for current processing to complete")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Maximum wait time for graceful stop")
    force: bool = Field(False, description="Force stop immediately")


class StopServiceResponse(APIResponse):
    """Response for stopping ETO service"""
    service_stopped: bool = False
    was_running: bool = False
    graceful_shutdown: bool = False
    pending_runs_interrupted: int = 0
    stop_duration_seconds: float = 0.0


class RestartServiceRequest(BaseModel):
    """Request to restart ETO processing service"""
    graceful: bool = Field(True, description="Graceful restart")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Stop timeout")
    new_poll_interval: Optional[int] = Field(None, ge=1, le=300, description="New polling interval")
    new_batch_size: Optional[int] = Field(None, ge=1, le=100, description="New batch size")
    reason: Optional[str] = Field(None, description="Reason for restart")


class RestartServiceResponse(APIResponse):
    """Response for restarting ETO service"""
    service_restarted: bool = False
    stop_duration_seconds: float = 0.0
    start_duration_seconds: float = 0.0
    configuration_changed: bool = False
    new_worker_thread_id: str = ""


# === Worker Information Schemas ===

class ThreadInfo(BaseModel):
    """Thread information for the worker"""
    thread_id: str
    thread_name: str
    is_alive: bool
    is_daemon: bool
    started_at: datetime


class ProcessingState(BaseModel):
    """Current processing state details"""
    current_run_id: Optional[int] = None
    current_step: Optional[str] = None
    step_started_at: Optional[datetime] = None
    runs_in_current_batch: List[int] = []
    batch_started_at: Optional[datetime] = None


class PerformanceStats(BaseModel):
    """Worker performance statistics"""
    runs_processed_this_session: int = 0
    avg_runs_per_minute: float = 0.0
    fastest_run_time_ms: Optional[int] = None
    slowest_run_time_ms: Optional[int] = None
    last_error_at: Optional[datetime] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0


class WorkerInfo(BaseModel):
    """Detailed worker information"""
    # Thread details
    thread: ThreadInfo

    # Configuration
    configuration: WorkerConfiguration

    # Current state
    processing_state: ProcessingState

    # Performance
    performance: PerformanceStats

    # Health indicators
    last_heartbeat: datetime
    health_check_interval_seconds: int = 30
    is_responsive: bool = True

    # System info
    process_id: int
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class WorkerInfoResponse(APIResponse):
    """Response for detailed worker information"""
    data: Optional[WorkerInfo] = None


# === Service Configuration Schemas ===

class UpdateConfigurationRequest(BaseModel):
    """Request to update service configuration"""
    poll_interval: Optional[int] = Field(None, ge=1, le=300)
    batch_size: Optional[int] = Field(None, ge=1, le=100)
    max_concurrent_runs: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=60, le=3600)
    restart_required: bool = Field(False, description="Restart service with new config")


class UpdateConfigurationResponse(APIResponse):
    """Response for configuration update"""
    configuration_updated: bool = False
    restart_required: bool = False
    old_configuration: Optional[WorkerConfiguration] = None
    new_configuration: Optional[WorkerConfiguration] = None
    changes_applied: List[str] = Field(default_factory=list)


# === Health Check Schemas ===

class HealthCheckDetail(BaseModel):
    """Individual health check result"""
    check_name: str
    status: Literal["pass", "warn", "fail"]
    response_time_ms: Optional[int] = None
    message: Optional[str] = None
    last_checked: datetime


class ComprehensiveHealthCheck(BaseModel):
    """Comprehensive service health check"""
    overall_status: Literal["healthy", "degraded", "unhealthy"]
    checks: List[HealthCheckDetail]

    # Summary metrics
    total_checks: int
    passed_checks: int
    warning_checks: int
    failed_checks: int

    # Service readiness
    ready_for_processing: bool
    ready_for_traffic: bool

    check_timestamp: datetime


class HealthCheckResponse(APIResponse):
    """Response for comprehensive health check"""
    data: Optional[ComprehensiveHealthCheck] = None