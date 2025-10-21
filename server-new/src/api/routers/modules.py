"""
Modules Router - API endpoints for module management
Provides endpoints for module discovery and catalog access
"""
import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from api.schemas.modules import (
    ListModulesResponse,
    ModuleCatalogItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules",
    tags=["Modules"]
)


@router.get("", response_model=List[ModuleCatalogItem])
async def list_modules() -> List[ModuleCatalogItem]:
    """List all active modules (complete catalog for pipeline builder)"""
    pass
