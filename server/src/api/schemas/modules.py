"""
Modules API Schemas
Pydantic models for module catalog endpoints
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Module Catalog Types
# ============================================================================

class Module(BaseModel):
    """Module catalog entry for API responses"""
    id: str
    version: str
    name: str
    description: Optional[str] = None
    module_kind: str  # "transform", "action", "logic", "comparator"
    meta: Dict[str, Any]  # Module I/O metadata
    config_schema: Dict[str, Any]  # JSON schema for module configuration
    color: str
    category: str


# ============================================================================
# Admin Sync Types
# ============================================================================

class ModuleSyncResult(BaseModel):
    """Result of syncing a single module"""
    id: str
    name: str
    status: str  # "success", "error", "skipped"
    message: Optional[str] = None


class SyncModulesResponse(BaseModel):
    """Response for POST /admin/sync-modules"""
    success: bool
    modules_discovered: int
    modules_synced: int
    modules_failed: int
    results: List[ModuleSyncResult]
    message: str
