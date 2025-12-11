"""
HTC Integration API Router
Test endpoints for HTC address resolution, creation, and order creation
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

class FindAddressRequest(BaseModel):
    """Request to find an existing address."""
    address_string: str

    class Config:
        json_schema_extra = {
            "example": {
                "address_string": "1075 S. Beltline Road, Coppell, TX 75019"
            }
        }


class FindAddressResponse(BaseModel):
    """Response from address lookup."""
    found: bool
    fav_id: Optional[float] = None
    message: str


class CreateAddressRequest(BaseModel):
    """Request to create a new address."""
    company_name: str
    addr_ln1: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    addr_ln2: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "ACME Corp",
                "addr_ln1": "123 Main St",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75201",
                "country": "USA",
                "addr_ln2": ""
            }
        }


class CreateAddressResponse(BaseModel):
    """Response from address creation."""
    success: bool
    fav_id: Optional[float] = None
    message: str


class FindOrCreateAddressRequest(BaseModel):
    """Request to find or create an address."""
    address_string: str
    company_name: str
    country: str = "USA"

    class Config:
        json_schema_extra = {
            "example": {
                "address_string": "123 Main St, Dallas, TX 75201",
                "company_name": "ACME Corp",
                "country": "USA"
            }
        }


class FindOrCreateAddressResponse(BaseModel):
    """Response from find or create operation."""
    success: bool
    fav_id: Optional[float] = None
    was_created: bool
    message: str


class LookupAciRequest(BaseModel):
    """Request to lookup ACI by zip code."""
    zip_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "zip_code": "75019"
            }
        }


class LookupAciResponse(BaseModel):
    """Response from ACI lookup."""
    found: bool
    aci_id: int
    message: str


class TestCreateOrderRequest(BaseModel):
    """Request to test order creation without a pending order."""
    customer_id: int
    hawb: str
    pickup_address: str
    pickup_time_start: str
    pickup_time_end: str
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
                "pickup_address": "Test Company, 123 Main St, Dallas, TX 75201",
                "pickup_time_start": "2025-12-15 09:00",
                "pickup_time_end": "2025-12-15 12:00",
                "delivery_address": "Another Company, 456 Oak Ave, Fort Worth, TX 76102",
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


# ==================== Endpoints ====================

@router.post("/find-address", response_model=FindAddressResponse)
async def find_address(
    request: FindAddressRequest,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> FindAddressResponse:
    """
    Find an existing address by address string.

    Uses normalized matching to find addresses with variations in
    abbreviations, punctuation, and case.
    """
    try:
        fav_id = htc_service.find_address_id(request.address_string)

        if fav_id is not None:
            return FindAddressResponse(
                found=True,
                fav_id=fav_id,
                message=f"Found address with FavID: {fav_id}"
            )
        else:
            return FindAddressResponse(
                found=False,
                fav_id=None,
                message="Address not found"
            )

    except Exception as e:
        logger.error(f"Error finding address: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding address: {str(e)}"
        )


@router.post("/create-address", response_model=CreateAddressResponse)
async def create_address(
    request: CreateAddressRequest,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> CreateAddressResponse:
    """
    Create a new address in the HTC database.

    Creates a new address record with all required fields populated.
    Returns the new FavID.
    """
    try:
        fav_id = htc_service.create_address(
            company_name=request.company_name,
            addr_ln1=request.addr_ln1,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code,
            country=request.country,
            addr_ln2=request.addr_ln2,
        )

        return CreateAddressResponse(
            success=True,
            fav_id=fav_id,
            message=f"Created address with FavID: {fav_id}"
        )

    except Exception as e:
        logger.error(f"Error creating address: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating address: {str(e)}"
        )


@router.post("/find-or-create-address", response_model=FindOrCreateAddressResponse)
async def find_or_create_address(
    request: FindOrCreateAddressRequest,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> FindOrCreateAddressResponse:
    """
    Find an existing address or create a new one.

    This is the main entry point for address resolution:
    1. Parses the address string
    2. Searches for existing match
    3. Creates new address if not found
    """
    try:
        # First check if it exists
        existing_id = htc_service.find_address_id(request.address_string)

        if existing_id is not None:
            return FindOrCreateAddressResponse(
                success=True,
                fav_id=existing_id,
                was_created=False,
                message=f"Found existing address with FavID: {existing_id}"
            )

        # Not found, create it
        new_id = htc_service.find_or_create_address(
            address_string=request.address_string,
            company_name=request.company_name,
            country=request.country,
        )

        return FindOrCreateAddressResponse(
            success=True,
            fav_id=new_id,
            was_created=True,
            message=f"Created new address with FavID: {new_id}"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid address: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in find_or_create_address: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing address: {str(e)}"
        )


@router.post("/lookup-aci", response_model=LookupAciResponse)
async def lookup_aci(
    request: LookupAciRequest,
    htc_service: HtcIntegrationService = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> LookupAciResponse:
    """
    Look up ACI data by ZIP code.

    Returns the ACI ID for a given ZIP code if found in the DFW_ACI_Data table.
    """
    try:
        found, aci_id = htc_service.lookup_aci_by_zip(request.zip_code)

        if found:
            return LookupAciResponse(
                found=True,
                aci_id=aci_id,
                message=f"Found ACI ID: {aci_id} for ZIP: {request.zip_code}"
            )
        else:
            return LookupAciResponse(
                found=False,
                aci_id=0,
                message=f"No ACI data found for ZIP: {request.zip_code}"
            )

    except Exception as e:
        logger.error(f"Error looking up ACI: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error looking up ACI: {str(e)}"
        )


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
            pickup_address=request.pickup_address,
            pickup_time_start=request.pickup_time_start,
            pickup_time_end=request.pickup_time_end,
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
