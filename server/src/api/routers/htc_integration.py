"""
HTC Integration API Router
Test endpoint for HTC order creation
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from shared.services.service_container import ServiceContainer
from features.htc_integration.service import HtcIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/htc",
    tags=["HTC Integration"]
)


# ==================== Request/Response Schemas ====================

class TestCreateOrderRequest(BaseModel):
    """Request to test order creation without a pending order."""
    customer_id: int
    hawb: str
    pickup_company_name: str
    pickup_address: str
    pickup_time_start: str
    pickup_time_end: str
    delivery_company_name: str
    delivery_address: str
    delivery_time_start: str
    delivery_time_end: str
    # Optional fields
    mawb: Optional[str] = None
    pickup_notes: Optional[str] = None
    delivery_notes: Optional[str] = None
    order_notes: Optional[str] = None
    pieces: Optional[int] = None
    weight: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 1,
                "hawb": "TEST123456",
                "pickup_company_name": "Test Company",
                "pickup_address": "123 Main St, Dallas, TX 75201",
                "pickup_time_start": "2025-12-15 09:00",
                "pickup_time_end": "2025-12-15 12:00",
                "delivery_company_name": "Another Company",
                "delivery_address": "456 Oak Ave, Fort Worth, TX 76102",
                "delivery_time_start": "2025-12-15 14:00",
                "delivery_time_end": "2025-12-15 17:00",
                "mawb": "MAWB789",
                "pickup_notes": "Call on arrival",
                "delivery_notes": "Dock 5",
                "order_notes": "Handle with care",
                "pieces": 3,
                "weight": 150.5
            }
        }


class TestCreateOrderResponse(BaseModel):
    """Response from test order creation."""
    success: bool
    order_number: Optional[float] = None
    message: str


class HtcOrderFieldsResponse(BaseModel):
    """Response containing all editable fields of an HTC order."""
    order_number: float
    customer_id: int
    hawb: str
    fields: dict  # Field name -> value mapping


# ==================== Endpoints ====================

@router.post("/test-create-order", response_model=TestCreateOrderResponse)
async def test_create_order(
    request: TestCreateOrderRequest,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> TestCreateOrderResponse:
    """
    Test order creation with raw data.

    Calls the HTC order creation flow directly with the provided data.
    Use this to test the HTC order creation logic without needing a
    pending order in the database.

    WARNING: This will create real records in the HTC database!
    """
    try:
        # Call create_order directly with the request data
        order_number = htc_service.create_order(
            customer_id=request.customer_id,
            hawb=request.hawb,
            pickup_company_name=request.pickup_company_name,
            pickup_address=request.pickup_address,
            pickup_time_start=request.pickup_time_start,
            pickup_time_end=request.pickup_time_end,
            delivery_company_name=request.delivery_company_name,
            delivery_address=request.delivery_address,
            delivery_time_start=request.delivery_time_start,
            delivery_time_end=request.delivery_time_end,
            mawb=request.mawb,
            pickup_notes=request.pickup_notes,
            delivery_notes=request.delivery_notes,
            order_notes=request.order_notes,
            pieces=request.pieces,
            weight=request.weight,
        )

        return TestCreateOrderResponse(
            success=True,
            order_number=order_number,
            message=f"Successfully created HTC order {int(order_number)}"
        )

    except ValueError as e:
        logger.error(f"Validation error in test order creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in test order creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )


@router.get("/orders/{order_number}", response_model=HtcOrderFieldsResponse)
async def get_order_fields(
    order_number: float,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> HtcOrderFieldsResponse:
    """
    Get all editable fields of an HTC order.

    Returns all field values that can be compared against pending updates,
    allowing the frontend to show current HTC values vs proposed changes.

    The response includes a `fields` dict containing all editable field values
    with keys matching the pending order field names:
    - pickup_company_name
    - pickup_address
    - pickup_time_start
    - pickup_time_end
    - delivery_company_name
    - delivery_address
    - delivery_time_start
    - delivery_time_end
    - mawb
    - pickup_notes
    - delivery_notes
    - order_notes
    - pieces
    - weight
    """
    order_fields = htc_service.get_order_fields(order_number)

    if order_fields is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_number} not found"
        )

    # Convert dataclass to dict for the fields
    return HtcOrderFieldsResponse(
        order_number=order_fields.order_number,
        customer_id=order_fields.customer_id,
        hawb=order_fields.hawb,
        fields={
            "pickup_company_name": order_fields.pickup_company_name,
            "pickup_address": order_fields.pickup_address,
            "pickup_time_start": order_fields.pickup_time_start,
            "pickup_time_end": order_fields.pickup_time_end,
            "delivery_company_name": order_fields.delivery_company_name,
            "delivery_address": order_fields.delivery_address,
            "delivery_time_start": order_fields.delivery_time_start,
            "delivery_time_end": order_fields.delivery_time_end,
            "mawb": order_fields.mawb,
            "pickup_notes": order_fields.pickup_notes,
            "delivery_notes": order_fields.delivery_notes,
            "order_notes": order_fields.order_notes,
            "pieces": order_fields.pieces,
            "weight": order_fields.weight,
        }
    )
