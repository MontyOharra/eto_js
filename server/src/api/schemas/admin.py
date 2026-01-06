"""
Admin API Schemas
Request/response models for admin endpoints
"""
from pydantic import BaseModel


# ============================================================================
# Module Sync Types
# ============================================================================

class ModuleSyncResult(BaseModel):
    """Result of syncing a single module."""
    id: str  # identifier
    name: str
    status: str  # "success", "error"
    message: str | None = None


class SyncModulesResponse(BaseModel):
    """Response for POST /admin/sync-modules."""
    success: bool
    modules_discovered: int
    modules_synced: int
    modules_failed: int
    results: list[ModuleSyncResult]
    message: str


# ============================================================================
# Output Channel Sync Types
# ============================================================================

class SyncOutputChannelsResponse(BaseModel):
    """Response for POST /admin/sync-output-channels."""
    success: bool
    total: int
    created: int
    updated: int
    channel_names: list[str]
    message: str
