"""
Output Channels API Schemas
Pydantic models for admin sync endpoint
"""
from typing import List
from pydantic import BaseModel


class SyncOutputChannelsResponse(BaseModel):
    """Response for POST /admin/sync-output-channels"""
    success: bool
    total: int
    created: int
    updated: int
    channel_names: List[str]
    message: str
