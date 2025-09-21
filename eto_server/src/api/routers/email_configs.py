"""
Email Configuration API Router
No deletion - configs are permanent, only deactivated
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from shared.services.service_container import ServiceContainer, get_service_container
from shared.models.email_config import EmailConfig, EmailConfigCreate, EmailConfigUpdate
from shared.exceptions import ObjectNotFoundError, ServiceError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/email-configs",
    tags=["Email Configurations"]
)


@router.post("/", response_model=EmailConfig, status_code=status.HTTP_201_CREATED)
def create_config(
    config: EmailConfigCreate,
    container: ServiceContainer = Depends(get_service_container)
):
    """Create a new email configuration (permanent - cannot be deleted)"""
    try:
        config_service = container.get_email_config_service()
        created = config_service.create_config(config)
        
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
    is_active: Optional[bool] = None,
    container: ServiceContainer = Depends(get_service_container)
):
    """List all email configurations"""
    try:
        config_service = container.get_email_config_service()
        configs = config_service.list_configs(is_active=is_active)
        
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
    container: ServiceContainer = Depends(get_service_container)
):
    """Get a specific email configuration"""
    try:
        config_service = container.get_email_config_service()
        config = config_service.get_config(config_id)
        
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
    container: ServiceContainer = Depends(get_service_container)
):
    """Update an email configuration"""
    try:
        config_service = container.get_email_config_service()
        ingestion_service = container.get_email_ingestion_service()
        
        # Update configuration
        updated = config_service.update_config(config_id, update)
        
        # Refresh listener if settings changed
        ingestion_service.refresh_config(config_id)
        
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
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Activate or deactivate an email configuration.
    Deactivation deletes the cursor for a fresh start on reactivation.
    """
    try:
        config_service = container.get_email_config_service()
        ingestion_service = container.get_email_ingestion_service()
        
        # Get current config
        config = config_service.get_config(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found"
            )
        
        # Update activation status
        update = EmailConfigUpdate(is_active=activate)
        updated = config_service.update_config(config_id, update)
        
        # Update ingestion service
        if activate:
            ingestion_service.activate_config(updated)
            message = f"Configuration {config_id} activated"
        else:
            ingestion_service.deactivate_config(config_id)
            message = f"Configuration {config_id} deactivated (cursor deleted for fresh start)"
        
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


@router.get("/{config_id}/status")
def get_config_status(
    config_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """Get the monitoring status for a configuration"""
    try:
        ingestion_service = container.get_email_ingestion_service()
        status = ingestion_service.get_status(config_id)
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get status for config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/status/all")
def get_all_status(
    container: ServiceContainer = Depends(get_service_container)
):
    """Get monitoring status for all configurations"""
    try:
        ingestion_service = container.get_email_ingestion_service()
        status = ingestion_service.get_all_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get all status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{config_id}/test")
def test_config(
    config_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """Test an email configuration connection"""
    try:
        config_service = container.get_email_config_service()
        
        # Get configuration
        config = config_service.get_config(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration {config_id} not found"
            )
        
        # Test connection (implement in config service)
        result = config_service.test_connection(config)
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Connection test completed"),
            "details": result.get("details", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test config {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )