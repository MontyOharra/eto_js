"""
Email Config FastAPI Router
REST endpoints with orchestration between config and ingestion services
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from shared.services import get_email_config_service, get_email_ingestion_service
from shared.exceptions import ObjectNotFoundError, ValidationError, RepositoryError
from shared.models.email_config import (
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfig,
    EmailConfigSummary
)
from api.schemas.email_config import (
    EmailConfigActivateRequest,
    EmailConfigActivateResponse,
    EmailConfigDetailResponse
)

logger = logging.getLogger(__name__)

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
            summary="List all email configurations")
def list_email_configs(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_running: Optional[bool] = Query(None, description="Filter by running status"),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(0, ge=0)
) -> List[EmailConfigSummary]:
    """List email configurations with optional filtering"""
    try:
        # Get configs from config service
        config_service = get_email_config_service()
        configs = config_service.list_configs()
        
        # Get running status from ingestion service
        ingestion_service = get_email_ingestion_service()
        running_ids = ingestion_service.get_active_listener_ids()
        
        # Apply filters and enrich with runtime status
        result = []
        for config in configs:
            # Apply filters
            if is_active is not None and config.is_active != is_active:
                continue
            
            config_is_running = config.id in running_ids
            if is_running is not None and config_is_running != is_running:
                continue
            
            # Create summary with runtime status
            summary = EmailConfigSummary(
                id=config.id,
                name=config.name,
                email_address=config.email_address,
                folder_name=config.folder_name,
                is_active=config.is_active,
                is_running=config_is_running,  # From ingestion service
                emails_processed=config.emails_processed,
                pdfs_found=config.pdfs_found,
                filter_rule_count=len(config.filter_rules),
                last_used_at=config.last_used_at,
                created_at=config.created_at
            )
            result.append(summary)
        
        # Apply pagination
        if offset:
            result = result[offset:]
        if limit:
            result = result[:limit]
        
        return result
        
    except Exception as e:
        logger.exception(f"Error listing email configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configurations"
        )


@router.get("/{config_id}",
            response_model=EmailConfigDetailResponse,
            summary="Get email configuration details")
def get_email_config(config_id: int) -> EmailConfigDetailResponse:
    """Get detailed configuration including cursor statistics"""
    try:
        # Get config from config service
        config_service = get_email_config_service()
        config = config_service.get_config(config_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration {config_id} not found"
            )
        
        # Get runtime info from ingestion service
        ingestion_service = get_email_ingestion_service()
        is_running = ingestion_service.is_listener_running(config_id)
        cursor_stats = ingestion_service.get_cursor_stats(config_id)
        
        # Build detailed response
        return EmailConfigDetailResponse(
            **config.model_dump(),
            is_running=is_running,
            cursor_statistics=cursor_stats
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
             summary="Create a new email configuration")
def create_email_config(config_create: EmailConfigCreate) -> EmailConfig:
    """Create new config with associated cursor"""
    config_service = get_email_config_service()
    ingestion_service = get_email_ingestion_service()
    
    try:
        # Step 1: Create the configuration
        config = config_service.create_config(config_create)
        
        try:
            # Step 2: Create cursor for this config
            ingestion_service.create_cursor_for_config(
                config_id=config.id,
                email_address=config.email_address,
                folder_name=config.folder_name
            )
            
            # Step 3: If marked as active, start the listener
            if config.is_active:
                started = ingestion_service.activate_config(config)
                if not started:
                    logger.warning(f"Config {config.id} created but listener failed to start")
            
            return config
            
        except Exception as e:
            # Rollback: delete the config if cursor/listener setup fails
            logger.error(f"Failed to initialize config {config.id}, rolling back: {e}")
            config_service.delete_config(config.id)
            raise
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error creating email config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email configuration"
        )


@router.patch("/{config_id}",
              response_model=EmailConfig,
              summary="Update email configuration")
def update_email_config(config_id: int, config_update: EmailConfigUpdate) -> EmailConfig:
    """Update config and restart listener if active"""
    try:
        config_service = get_email_config_service()
        ingestion_service = get_email_ingestion_service()
        
        # Update the configuration
        updated_config = config_service.update_config(config_id, config_update)
        
        # If config is active and running, restart the listener with new settings
        if updated_config.is_active and ingestion_service.is_listener_running(config_id):
            # Check if critical fields changed that require restart
            needs_restart = (
                config_update.filter_rules is not None or
                config_update.poll_interval_seconds is not None or
                config_update.max_backlog_hours is not None
            )
            
            if needs_restart:
                logger.info(f"Restarting listener for config {config_id} due to configuration changes")
                ingestion_service.restart_listener(updated_config)
        
        return updated_config
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {config_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error updating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email configuration"
        )


@router.patch("/{config_id}/activate",
              response_model=EmailConfigActivateResponse,
              summary="Activate or deactivate email configuration")
def activate_email_config(config_id: int, 
                         activate_request: EmailConfigActivateRequest) -> EmailConfigActivateResponse:
    """
    Activate or deactivate configuration.
    For multi-config support, multiple configs can be active simultaneously.
    """
    try:
        config_service = get_email_config_service()
        ingestion_service = get_email_ingestion_service()
        
        if activate_request.is_active:
            # Activate this config
            # Note: We don't deactivate others for multi-config support
            updated_config = config_service.activate_config(config_id)
            
            # Start the listener
            started = ingestion_service.activate_config(updated_config)
            
            if not started:
                # Rollback activation if listener fails to start
                config_service.deactivate_config(config_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to start email listener"
                )
            
            message = f"Configuration '{updated_config.name}' activated and listener started"
            
        else:
            # Deactivate this config
            # Stop the listener first
            ingestion_service.deactivate_config(config_id)
            
            # Update config status
            updated_config = config_service.deactivate_config(config_id)
            
            message = f"Configuration '{updated_config.name}' deactivated and listener stopped"
        
        return EmailConfigActivateResponse(
            success=True,
            config_id=updated_config.id,
            config_name=updated_config.name,
            is_active=updated_config.is_active,
            message=message,
            # Could track other active configs if needed for single-active mode
            previous_active_config=None
        )
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration {config_id} not found"
        )
    except Exception as e:
        logger.exception(f"Error activating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration status"
        )


@router.delete("/{config_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete email configuration")
def delete_email_config(config_id: int):
    """Delete config and associated cursor"""
    try:
        config_service = get_email_config_service()
        ingestion_service = get_email_ingestion_service()
        
        # Check if config exists
        config = config_service.get_config(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email configuration {config_id} not found"
            )
        
        # Cannot delete if listener is running
        if ingestion_service.is_listener_running(config_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete configuration with active listener. Deactivate first."
            )
        
        # Delete cursor first
        ingestion_service.delete_cursor_for_config(config_id)
        
        # Delete the configuration
        config_service.delete_config(config_id)
        
        return None
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error deleting email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email configuration"
        )


@router.get("/{config_id}/status",
            summary="Get real-time status of email configuration")
def get_config_status(config_id: int):
    """Get real-time processing status for a configuration"""
    try:
        ingestion_service = get_email_ingestion_service()
        
        # Get all service status
        service_status = ingestion_service.get_service_status()
        
        # Find this config's listener
        for listener_detail in service_status["listener_details"]:
            if listener_detail["config_id"] == config_id:
                return listener_detail
        
        # Config exists but no listener
        return {
            "config_id": config_id,
            "is_running": False,
            "message": "No active listener for this configuration"
        }
        
    except Exception as e:
        logger.exception(f"Error getting config status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration status"
        )