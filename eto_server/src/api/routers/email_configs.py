"""
Email Config FastAPI Router
REST endpoints for email ingestion configuration management
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from shared.services import get_email_config_service
from shared.exceptions import ObjectNotFoundError, ValidationError, RepositoryError
from shared.models.email_config import (
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfig,
    EmailConfigSummary
)
from api.schemas.email_config import (
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
                email_address=config.email_address,
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
        
    except RepositoryError as e:
        logger.exception(f"Repository error listing email configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configurations"
        )
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
        
        return config
        
    except HTTPException:
        raise
    except RepositoryError as e:
        logger.exception(f"Repository error getting email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email configuration"
        )
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
             description="Create a new email configuration with filter rules")
def create_email_config(config_create: EmailConfigCreate) -> EmailConfig:
    """
    Create a new email configuration
    
    - **name**: Configuration name (required)
    - **description**: Configuration description (optional)
    - **email_address**: Email address to monitor (required)
    - **folder_name**: Email folder name (required)
    - **filter_rules**: Email filter rules (optional)
    - **poll_interval_seconds**: Polling interval in seconds (default: 5)
    - **max_backlog_hours**: Maximum backlog hours (default: 24)
    - **error_retry_attempts**: Error retry attempts (default: 3)
    """
    try:
        config_service = get_email_config_service()
        
        # Service now accepts Pydantic model directly
        created_config = config_service.create_config(config_create)
        return created_config
        
    except RepositoryError as e:
        logger.exception(f"Repository error creating email config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email configuration"
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
              description="Update email configuration settings")
def update_email_config(config_id: int, config_update: EmailConfigUpdate) -> EmailConfig:
    """
    Update email configuration
    
    - **config_id**: Configuration ID (required)
    - **description**: Configuration description (optional)
    - **filter_rules**: Email filter rules (optional)
    - **poll_interval_seconds**: Polling interval in seconds (optional)
    - **max_backlog_hours**: Maximum backlog hours (optional)
    - **error_retry_attempts**: Error retry attempts (optional)
    
    Note: email_address and folder_name cannot be updated after creation
    """
    try:
        config_service = get_email_config_service()
        
        # Service now accepts Pydantic model directly and handles ObjectNotFoundError
        updated_config = config_service.update_config(config_id, config_update)
        return updated_config
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration with ID {config_id} not found"
        )
    except RepositoryError as e:
        logger.exception(f"Repository error updating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email configuration"
        )
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
            # Deactivate this specific config
            updated_config = config_service.deactivate_config(config_id)
            message = f"Configuration '{updated_config.name}' has been deactivated"
        
        return EmailConfigActivateResponse(
            success=True,
            config_id=updated_config.id,
            config_name=updated_config.name,
            is_active=updated_config.is_active,
            message=message,
            previous_active_config=None  # Could track this in service if needed
        )
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration with ID {config_id} not found"
        )
    except RepositoryError as e:
        logger.exception(f"Repository error activating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email configuration status"
        )
    except Exception as e:
        logger.exception(f"Error activating email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email configuration status"
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
        
        # Service returns deleted config and raises exceptions for errors
        deleted_config = config_service.delete_config(config_id)
        
        # Return 204 No Content on successful deletion
        return None
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email configuration with ID {config_id} not found"
        )
    except ValidationError as e:
        # Handle active config validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RepositoryError as e:
        logger.exception(f"Repository error deleting email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email configuration"
        )
    except Exception as e:
        logger.exception(f"Error deleting email config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email configuration"
        )