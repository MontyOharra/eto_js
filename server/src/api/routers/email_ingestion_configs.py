"""
Email Ingestion Config API Routes

REST endpoints for email ingestion config management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.email_ingestion_configs import (
    ValidateIngestionConfigRequest,
    ValidateIngestionConfigResponse,
    CreateIngestionConfigRequest,
    UpdateIngestionConfigRequest,
    IngestionConfigResponse,
    IngestionConfigListResponse,
)
from shared.services.service_container import ServiceContainer
from features.email.service import EmailService
from shared.exceptions.service import ObjectNotFoundError, ValidationError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-ingestion-configs", tags=["Email Ingestion Configs"])


@router.post(
    "/validate",
    response_model=ValidateIngestionConfigResponse,
    summary="Validate ingestion config",
    description="Validate that an ingestion config can be created for the given account and folder.",
)
def validate_config(
    request: ValidateIngestionConfigRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> ValidateIngestionConfigResponse:
    """Validate ingestion config before creation."""
    try:
        service.validate_ingestion_config(
            account_id=request.account_id,
            folder_name=request.folder_name,
        )
        return ValidateIngestionConfigResponse(valid=True, message="Configuration is valid")
    except ObjectNotFoundError as e:
        return ValidateIngestionConfigResponse(valid=False, message=str(e))
    except ValidationError as e:
        return ValidateIngestionConfigResponse(valid=False, message=str(e))


@router.get(
    "",
    response_model=IngestionConfigListResponse,
    summary="List ingestion configs",
    description="Get all ingestion configs with account information.",
)
def list_configs(
    order_by: str = Query("name", description="Field to sort by"),
    desc: bool = Query(False, description="Sort descending"),
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigListResponse:
    """List all ingestion configs."""
    configs = service.list_ingestion_configs(order_by=order_by, desc=desc)
    return IngestionConfigListResponse(configs=configs, total=len(configs))


@router.get(
    "/{config_id}",
    response_model=IngestionConfigResponse,
    summary="Get ingestion config",
    description="Get a single ingestion config by ID.",
)
def get_config(
    config_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Get ingestion config by ID."""
    try:
        config = service.ingestion_config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "",
    response_model=IngestionConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create ingestion config",
    description="Create a new ingestion config. The config is created in inactive state.",
)
def create_config(
    request: CreateIngestionConfigRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Create a new ingestion config."""
    try:
        config = service.create_ingestion_config(request)
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{config_id}",
    response_model=IngestionConfigResponse,
    summary="Update ingestion config",
    description="Update an ingestion config. Cannot update an active config.",
)
def update_config(
    config_id: int,
    request: UpdateIngestionConfigRequest,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Update an ingestion config."""
    try:
        config = service.update_ingestion_config(config_id, request)
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{config_id}",
    response_model=IngestionConfigResponse,
    summary="Delete ingestion config",
    description="Delete an ingestion config. Cannot delete an active config.",
)
def delete_config(
    config_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Delete an ingestion config."""
    try:
        config = service.delete_ingestion_config(config_id)
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/{config_id}/activate",
    response_model=IngestionConfigResponse,
    summary="Activate ingestion config",
    description="Activate an ingestion config and start polling for new emails.",
)
def activate_config(
    config_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Activate an ingestion config and start polling."""
    try:
        config = service.activate_config(config_id)
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{config_id}/deactivate",
    response_model=IngestionConfigResponse,
    summary="Deactivate ingestion config",
    description="Deactivate an ingestion config and stop polling.",
)
def deactivate_config(
    config_id: int,
    service: EmailService = Depends(lambda: ServiceContainer.get_email_service()),
) -> IngestionConfigResponse:
    """Deactivate an ingestion config and stop polling."""
    try:
        config = service.deactivate_config(config_id)
        return config
    except ObjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
