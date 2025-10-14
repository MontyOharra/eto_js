"""
Module Catalog Domain Models
Pydantic models for module catalog operations based on modules.md specification
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from shared.database.models import EtoRunExtractionModel
from shared.utils import DateTimeUtils

class EtoRunExtractionBase(BaseModel):
    """Core fields required for any ETO run extraction"""
    eto_run_id: int = Field(..., description="Associated ETO run ID")

    class Config:
        from_attributes = True
        
class EtoRunExtraction(EtoRunExtractionBase):
    """Complete ETO run extraction domain model with database fields"""
    id: int = Field(..., description="Database ID")
    status: str = Field("processing", description="Current status")
    extracted_data: Optional[str] = Field(None, description="JSON-encoded extracted field values")
    started_at: datetime = Field(..., description="When record was created in database")
    created_at: datetime = Field(..., description="When record was created in database")
    
    @field_validator('created_at', mode='before')
    @classmethod
    def ensure_timezone_aware(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, model: EtoRunExtractionModel) -> 'EtoRunExtraction':
        """
        Create from database model.
        Used by repository's _convert_to_domain_object method.
        """
        return cls(
            id=model.id,
            eto_run_id=model.eto_run_id,
            extracted_data=getattr(model, 'extracted_data', None),  # May not exist in older records
            created_at=model.created_at
        )