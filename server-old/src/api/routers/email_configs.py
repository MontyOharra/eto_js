"""
Email Configuration API Router
No deletion - configs are permanent, only deactivated
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from shared.services.service_container import ServiceContainer
from shared.types import EmailConfig, EmailConfigCreate, EmailConfigUpdate, ServiceStatusResponse, ServiceHealth
from shared.exceptions import ObjectNotFoundError, ServiceError

from features.email_ingestion.service import EmailIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/email-configs",
    tags=["Email Configurations"]
)


@router.post("/", response_model=EmailConfig, status_code=status.HTTP_201_CREATED)
def create_config(
    config: EmailConfigCreate,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """Create a new email configuration (permanent - cannot be deleted)"""
    try:
        
        # Create config (service will test connection internally)
        created = ingestion_service.create_config(config)
        
        logger.info(f"Created email config {created.id}")
        return created
        
    except ServiceError as e:
        logger.error(f"Failed to create config: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/", response_model=List[EmailConfig])
def list_configs(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """List all email configurations"""
    try:
        configs = ingestion_service.list_configs()
        
        return configs
        
    except Exception as e:
        logger.error(f"Failed to list configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{config_id}", response_model=EmailConfig)
def get_config(
    config_id: int,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """Get a specific email configuration"""
    try:
        config = ingestion_service.get_config(config_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found"
            )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{config_id}", response_model=EmailConfig)
def update_config(
    config_id: int,
    update: EmailConfigUpdate,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ), 
):
    """Update an email configuration"""
    try:
        
        logger.info(f"Update body: {update}")
        logger.info(f"Update filter_rules: {update.filter_rules}")

        # Update configuration and refresh listener if needed
        updated = ingestion_service.update_config(config_id, update)
        
        logger.info(f"Updated email config {config_id}")
        return updated
        
    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )
    except ServiceError as e:
        logger.error(f"Failed to update config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{config_id}/activate")
def toggle_activation(
    config_id: int,
    activate: bool,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """
    Activate or deactivate an email configuration.
    Deactivation deletes the cursor for a fresh start on reactivation.
    """
    try:
        
        # Toggle activation
        if activate:
            updated = ingestion_service.activate_config(config_id)
            message = f"Configuration {config_id} activated"
        else:
            updated = ingestion_service.deactivate_config(config_id)
            message = f"Configuration {config_id} deactivated (progress reset for fresh start)"
        
        logger.info(message)
        return {
            "message": message,
            "config": updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle activation for config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )




@router.get("/discovery/accounts")
def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """Discover all email accounts available in Outlook"""
    try:
        accounts = ingestion_service.discover_email_accounts()
        
        return accounts
        
    except Exception as e:
        logger.error(f"Failed to discover email accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/discovery/folders")
def discover_folders(
    email_address: str,
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
):
    """Discover all folders for a specific email account"""
    try:
        folders = ingestion_service.discover_folders(email_address)
        
        return folders
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to discover folders for {email_address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/status", response_model=ServiceStatusResponse)
def get_email_configs_status(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    ),
) -> ServiceStatusResponse:
    """
    Get email configurations service status

    Returns health status of the email ingestion service including database connectivity
    """
    try:
        if not ingestion_service:
            return ServiceStatusResponse(
                service="email_configs",
                status=ServiceHealth.DOWN,
                message="Email ingestion service is not available"
            )

        is_healthy = ingestion_service.is_healthy()

        return ServiceStatusResponse(
            service="email_configs",
            status=ServiceHealth.UP if is_healthy else ServiceHealth.DOWN,
            message="Service is operational" if is_healthy else "Service is not operational"
        )

    except Exception as e:
        logger.error(f"Error checking email configs service status: {e}")
        return ServiceStatusResponse(
            service="email_configs",
            status=ServiceHealth.DOWN,
            message=f"Service health check failed: {str(e)}"
        )