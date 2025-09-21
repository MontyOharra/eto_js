"""
Email Config FastAPI Router
REST endpoints for email ingestion configuration management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from features.email_ingestion.config_service import EmailIngestionConfigService
from shared.database.repositories import EmailIngestionConfigRepository
from shared.exceptions import ObjectNotFoundError
from shared.models.email_config import (
    EmailConfig,
    EmailConfigSummary,
    EmailConfigStats
)
from api.schemas.email_config import (
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfigActivateRequest,
    EmailConfigActivateResponse
)
from api.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/email_configs",
    tags=["Email Configs"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get("/",
            response_model=List[EmailConfigSummary],
            summary="List all email configurations",
            description="Get a list of all email configurations with summary information")
def list_email_configs(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_running: Optional[bool] = Query(None, description="Filter by running status"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of configs to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of configs to skip"),
    include_stats: bool = Query(False, description="Include processing statistics")
) -> List[EmailConfigSummary]:
    """
    Get list of email configurations
    
    - **is_active**: Filter by active status (optional)
    - **is_running**: Filter by running status (optional)
    - **limit**: Maximum number of results (optional, max 100)
    - **offset**: Number of results to skip (optional, default 0)
    - **include_stats**: Include processing statistics (optional, default false)
    """
    try:
        config_service = get_email_config_service()
        configs = config_service.list_configs()
        
        # Apply filtering
        if is_active is not None:
            configs = [c for c in configs if c.is_active == is_active]
        if is_running is not None:
            configs = [c for c in configs if c.is_running == is_running]
        
        # Apply pagination
        if offset:
            configs = configs[offset:]
        if limit:
            configs = configs[:limit]
        
        # Convert to summary format
        summaries = []
        for config in configs:
            summary = EmailConfigSummary(
                id=config.id,
                name=config.name,
                email_address=config.email_address or "default",
                folder_name=config.folder_name,
                is_active=config.is_active,
                is_running=config.is_running,
                emails_processed=config.emails_processed,
                pdfs_found=config.pdfs_found,
                filter_rule_count=len(config.filter_rules),
                last_used_at=config.last_used_at,
                created_at=config.created_at
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.exception(f"Error listing email configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configurations"
        )


@router.get("/{config_id}",
            response_model=EmailConfig,
            summary="Get email configuration by ID",
            description="Get detailed information about a specific email configuration")
def get_email_config(config_id: int) -> EmailConfig:
    """
    Get email configuration by ID
    
    - **config_id**: Configuration ID (required)
    """
    try:
        config_service = get_email_config_service()
        config = config_service.get_config(config_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration with ID {config_id} not found"
            )
        
        # Convert domain object to Pydantic model
        return EmailConfig(
            id=config.id,
            name=config.name,
            description=config.description,
            email_address=config.email_address or "default",
            folder_name=config.folder_name,
            filter_rules=[
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in config.filter_rules
            ],
            monitoring={
                "poll_interval_seconds": config.poll_interval_seconds,
                "max_backlog_hours": config.max_backlog_hours,
                "error_retry_attempts": config.error_retry_attempts
            },
            is_active=config.is_active,
            is_running=config.is_running,
            emails_processed=config.emails_processed,
            pdfs_found=config.pdfs_found,
            last_error_message=config.last_error_message,
            last_error_at=config.last_error_at,
            created_by=getattr(config, 'created_by', 'system'),
            created_at=config.created_at,
            updated_at=config.updated_at,
            last_used_at=config.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configuration"
        )


@router.post("/",
             response_model=EmailConfig,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new email configuration",
             description="Create a new email configuration with filter rules and monitoring settings")
def create_email_config(config_create: EmailConfigCreate) -> EmailConfig:
    """
    Create a new email configuration
    
    - **name**: Configuration name (required)
    - **description**: Configuration description (optional)
    - **email_address**: Email address to monitor (required)
    - **folder_name**: Email folder name (required)
    - **filter_rules**: Email filter rules (optional)
    - **monitoring**: Monitoring settings (optional, uses defaults)
    - **created_by**: User who created the configuration (required)
    """
    try:
        config_service = get_email_config_service()
        
        # Convert Pydantic models to domain objects
        from shared.domain.email_ingestion import EmailFilterRule
        filter_rules = [
            EmailFilterRule(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            )
            for rule in config_create.filter_rules
        ]
        
        created_config = config_service.create_config(
            name=config_create.name,
            description=config_create.description,
            email_address=config_create.email_address,
            folder_name=config_create.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=config_create.monitoring.poll_interval_seconds,
            max_backlog_hours=config_create.monitoring.max_backlog_hours,
            error_retry_attempts=config_create.monitoring.error_retry_attempts
        )
        
        # Convert back to Pydantic model
        return EmailConfig(
            id=created_config.id,
            name=created_config.name,
            description=created_config.description,
            email_address=created_config.email_address or "default",
            folder_name=created_config.folder_name,
            filter_rules=[
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in created_config.filter_rules
            ],
            monitoring={
                "poll_interval_seconds": created_config.poll_interval_seconds,
                "max_backlog_hours": created_config.max_backlog_hours,
                "error_retry_attempts": created_config.error_retry_attempts
            },
            is_active=created_config.is_active,
            is_running=created_config.is_running,
            emails_processed=created_config.emails_processed,
            pdfs_found=created_config.pdfs_found,
            last_error_message=created_config.last_error_message,
            last_error_at=created_config.last_error_at,
            created_by=config_create.created_by,
            created_at=created_config.created_at,
            updated_at=created_config.updated_at,
            last_used_at=created_config.last_used_at
        )
        
    except Exception as e:
        logger.exception(f"Error creating email config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email configuration"
        )


@router.patch("/{config_id}",
              response_model=EmailConfig,
              summary="Update email configuration",
              description="Update filter rules and monitoring settings for an existing email configuration")
def update_email_config(config_id: int, config_update: EmailConfigUpdate) -> EmailConfig:
    """
    Update email configuration
    
    - **config_id**: Configuration ID (required)
    - **description**: Configuration description (optional)
    - **filter_rules**: Email filter rules (optional)
    - **monitoring**: Monitoring settings (optional)
    
    Note: email_address and folder_name cannot be updated after creation
    """
    try:
        config_service = get_email_config_service()
        
        # Get current config
        current_config = config_service.get_config(config_id)
        if not current_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration with ID {config_id} not found"
            )
        
        # Create updated config object
        from shared.domain.email_ingestion import EmailFilterRule, EmailIngestionConfig
        
        # Use current values as defaults, override with provided updates
        filter_rules = current_config.filter_rules
        if config_update.filter_rules is not None:
            filter_rules = [
                EmailFilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                )
                for rule in config_update.filter_rules
            ]
        
        monitoring = {
            "poll_interval_seconds": current_config.poll_interval_seconds,
            "max_backlog_hours": current_config.max_backlog_hours,
            "error_retry_attempts": current_config.error_retry_attempts
        }
        if config_update.monitoring is not None:
            monitoring.update({
                "poll_interval_seconds": config_update.monitoring.poll_interval_seconds,
                "max_backlog_hours": config_update.monitoring.max_backlog_hours,
                "error_retry_attempts": config_update.monitoring.error_retry_attempts
            })
        
        updated_config_obj = EmailIngestionConfig(
            id=current_config.id,
            name=current_config.name,
            description=config_update.description if config_update.description is not None else current_config.description,
            email_address=current_config.email_address,
            folder_name=current_config.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=monitoring["poll_interval_seconds"],
            max_backlog_hours=monitoring["max_backlog_hours"],
            error_retry_attempts=monitoring["error_retry_attempts"],
            is_active=current_config.is_active,
            is_running=current_config.is_running,
            last_used_at=current_config.last_used_at,
            emails_processed=current_config.emails_processed,
            pdfs_found=current_config.pdfs_found,
            last_error_message=current_config.last_error_message,
            last_error_at=current_config.last_error_at,
            created_at=current_config.created_at,
            updated_at=current_config.updated_at
        )
        
        updated_config = config_service.update_config(config_id, updated_config_obj)
        
        # Convert back to Pydantic model
        return EmailConfig(
            id=updated_config.id,
            name=updated_config.name,
            description=updated_config.description,
            email_address=updated_config.email_address or "default",
            folder_name=updated_config.folder_name,
            filter_rules=[
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in updated_config.filter_rules
            ],
            monitoring={
                "poll_interval_seconds": updated_config.poll_interval_seconds,
                "max_backlog_hours": updated_config.max_backlog_hours,
                "error_retry_attempts": updated_config.error_retry_attempts
            },
            is_active=updated_config.is_active,
            is_running=updated_config.is_running,
            emails_processed=updated_config.emails_processed,
            pdfs_found=updated_config.pdfs_found,
            last_error_message=updated_config.last_error_message,
            last_error_at=updated_config.last_error_at,
            created_by=getattr(updated_config, 'created_by', 'system'),
            created_at=updated_config.created_at,
            updated_at=updated_config.updated_at,
            last_used_at=updated_config.last_used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email configuration"
        )


@router.patch("/{config_id}/activate",
              response_model=EmailConfigActivateResponse,
              summary="Activate or deactivate email configuration",
              description="Activate or deactivate an email configuration (only one can be active at a time)")
def activate_email_config(config_id: int, activate_request: EmailConfigActivateRequest) -> EmailConfigActivateResponse:
    """
    Activate or deactivate email configuration
    
    - **config_id**: Configuration ID (required)
    - **is_active**: Whether to activate or deactivate (required)
    
    Note: Only one configuration can be active at a time. Activating a config will deactivate all others.
    """
    try:
        config_service = get_email_config_service()
        
        if activate_request.is_active:
            # Activate this config (deactivates all others)
            updated_config = config_service.activate_config(config_id)
            message = f"Configuration '{updated_config.name}' has been activated"
        else:
            # For deactivation, we need to update the config directly
            # Since there's no deactivate method, we'll use the repository
            current_config = config_service.get_config(config_id)
            if not current_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Email configuration with ID {config_id} not found"
                )
            
            # Update is_active to False - this would need to be implemented in the service
            # For now, we'll raise an error indicating this needs implementation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Deactivation endpoint not yet implemented in service layer"
            )
        
        return EmailConfigActivateResponse(
            success=True,
            config_id=updated_config.id,
            config_name=updated_config.name,
            is_active=updated_config.is_active,
            message=message,
            previous_active_config=None  # Would need service support to track this
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error activating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate email configuration"
        )


@router.delete("/{config_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete email configuration",
               description="Delete an email configuration (only allowed if not active)")
def delete_email_config(config_id: int):
    """
    Delete email configuration
    
    - **config_id**: Configuration ID (required)
    
    Note: Only inactive configurations can be deleted
    """
    try:
        config_service = get_email_config_service()
        
        # This will raise an exception if config is active or doesn't exist
        success = config_service.delete_config(config_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete email configuration"
            )
        
        # Return 204 No Content on successful deletion
        return None
        
    except Exception as e:
        # Check if it's a business rule violation (active config)
        if "active" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete active email configuration"
            )
        elif "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration with ID {config_id} not found"
            )
        else:
            logger.exception(f"Error deleting email config {config_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete email configuration"
            )


@router.get("/{config_id}/stats",
            response_model=EmailConfigStats,
            summary="Get email configuration statistics",
            description="Get detailed statistics for a specific email configuration")
def get_email_config_stats(config_id: int) -> EmailConfigStats:
    """
    Get email configuration statistics
    
    - **config_id**: Configuration ID (required)
    """
    try:
        config_service = get_email_config_service()
        config = config_service.get_config(config_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration with ID {config_id} not found"
            )
        
        # Calculate success rate (this would need proper implementation in service)
        success_rate = 1.0 if config.emails_processed > 0 else 0.0
        
        return EmailConfigStats(
            config_id=config.id,
            config_name=config.name,
            total_emails_processed=config.emails_processed,
            total_pdfs_found=config.pdfs_found,
            success_rate=success_rate,
            avg_processing_time_ms=0,  # Would need service implementation
            last_24h_emails=0,  # Would need service implementation
            last_24h_pdfs=0,  # Would need service implementation
            last_error=config.last_error_message,
            last_error_at=config.last_error_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting email config stats {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configuration statistics"
        )