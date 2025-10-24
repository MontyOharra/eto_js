# Module Catalog Service Implementation Progress

**Session Date:** 2025-10-23
**Status:** In Progress - Repository Creation

## Overview
Building the module catalog service for the new server architecture. This service manages pipeline transformation modules with auto-discovery, metadata storage, and runtime execution capabilities.

## Completed Work

### 1. Module Type System ✅
**Location:** `server-new/src/shared/types/modules.py`

Created complete module type hierarchy:
- `BaseModule` - Abstract base class for all modules
- `TransformModule` - Pure data transformation modules
- `ActionModule` - Modules with side effects
- `LogicModule` - Conditional/control flow modules
- `ComparatorModule` - Boolean comparison modules

Supporting types:
- `ModuleKind` - Enum for module types
- `AllowedModuleNodeTypes` - Type constraints for module I/O
- `NodeTypeRule`, `NodeGroup`, `IOSideShape`, `IOShape` - I/O shape definitions
- `ModuleMeta` - Metadata wrapper for module I/O constraints

**Exported from:** `server-new/src/shared/types/__init__.py`

### 2. Module Registry System ✅
**Location:** `server-new/src/shared/utils/registry.py`

Implemented singleton registry with:
- **Auto-discovery**: Scans packages and auto-registers modules via `@register` decorator
- **Security validation**: Path validation, blocked patterns, allowed packages whitelist
- **Caching**: LRU-style cache with TTL for loaded module classes
- **Dynamic loading**: Load modules from handler paths (e.g., "module.path:ClassName")
- **Catalog export**: Convert registered modules to database format

Key allowed packages:
```python
"features.modules.transform"
"features.modules.action"
"features.modules.logic"
"features.modules.comparator"
```

Key functions:
- `register(module_class)` - Decorator for module registration
- `get_registry()` - Get singleton instance
- `auto_discover_modules(package_paths)` - Scan and register modules

### 3. Module Catalog Domain Types ✅
**Location:** `server-new/src/shared/types/module_catalog.py`

Created frozen dataclasses:
- `ModuleCatalogCreate` - For creating new catalog entries
  - Includes `to_db_dict()` method with JSON serialization
- `ModuleCatalogUpdate` - For updating catalog entries
  - Includes `to_db_dict()` method for partial updates
- `ModuleCatalog` - Full domain object from database
  - Includes `from_db_model()` static method for conversion

**Exported from:** `server-new/src/shared/types/__init__.py`

### 4. Database Model ✅
**Location:** `server-new/src/shared/database/models.py` (lines 234-258)

`ModuleCatalogModel` already exists with:
- Primary key: `id` (String, composite with version)
- Fields: version, name, description, color, category, module_kind, meta (JSON), config_schema (JSON), handler_name, is_active
- Timestamps: created_at, updated_at
- Relationship: `steps` - Links to PipelineDefinitionStepModel
- Indexes: name, kind, active, category, id+version

## Current Status: Creating Repository

### What's Next
**File to create:** `server-new/src/shared/database/repositories/module_catalog.py`

**Pattern to follow:** Based on old server's `ModuleCatalogRepository` at:
`server/src/shared/database/repositories/module_catalog.py`

**Key methods needed:**
1. `create(module_create: ModuleCatalogCreate) -> ModuleCatalog`
2. `update(module_id, version, module_update) -> ModuleCatalog`
3. `get_by_id(module_id) -> Optional[ModuleCatalog]` - Returns latest version
4. `get_by_module_ref(module_id, version) -> Optional[ModuleCatalog]` - Specific version
5. `get_all(only_active=True) -> List[ModuleCatalog]`
6. `get_by_kind(module_kind, only_active=True) -> List[ModuleCatalog]`
7. `exists_by_module_ref(module_id, version) -> bool`
8. `upsert(module_create) -> ModuleCatalog`
9. `delete(module_id, version) -> bool` - Soft delete via is_active

**Adaptation notes:**
- Use new architecture's connection manager (not session injection)
- Return frozen dataclasses (not Pydantic models)
- Use `to_db_dict()` from domain types for database operations
- Follow pattern from other new repositories (email_config, pipeline_definition, etc.)

## Remaining Tasks

### 1. Complete Repository Creation ⏳
- Create `server-new/src/shared/database/repositories/module_catalog.py`
- Export from `server-new/src/shared/database/repositories/__init__.py`
- Add to Unit of Work in `server-new/src/shared/database/unit_of_work.py`

### 2. Create Modules Service 📋
**File:** `server-new/src/features/modules/service.py`

Based on old service at: `server/src/features/modules/service.py`

**Key responsibilities:**
- Initialize registry and run auto-discovery
- Provide catalog query methods
- Execute modules at runtime
- Sync registry to database
- Handle module loading errors gracefully

**Key methods:**
```python
def __init__(self, connection_manager):
    # Initialize registry
    # Run auto-discovery
    # Set up module catalog repository

def get_module_catalog(self, only_active=True) -> List[ModuleCatalog]:
    # Query database via repository

def get_module_info(self, module_id: str) -> Optional[ModuleCatalog]:
    # Get specific module from database

def execute_module(self, module_id: str, inputs: Dict, config: Dict, context):
    # Load module class from registry
    # Validate config
    # Execute run() method
    # Return outputs

def sync_catalog_to_db(self):
    # Get registered modules from registry
    # Upsert to database
```

### 3. Copy Module Implementations 📋
**Old location:** `server/src/features/modules/`
**New location:** `server-new/src/features/modules/`

**Module directories to copy:**
- `transform/` - Text cleaner, LLM parser, type converter, data duplicator
- `action/` - Create order, print action
- `logic/` - If selector, boolean AND/OR/NOT
- `comparator/` - String, number, date comparators

**Pattern each module follows:**
```python
from shared.utils.registry import register
from shared.types import TransformModule, ModuleMeta, IOShape
from pydantic import BaseModel, Field

class ModuleConfig(BaseModel):
    # Pydantic config with Field descriptions

@register
class MyModule(TransformModule):
    id = "module_id"
    version = "1.0.0"
    title = "Display Title"
    description = "What this module does"
    category = "Category Name"
    color = "#HexColor"

    ConfigModel = ModuleConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[...]),
                outputs=IOSideShape(nodes=[...])
            )
        )

    def run(self, inputs: Dict, cfg: ModuleConfig, context) -> Dict:
        # Module logic here
        return {"output": result}
```

### 4. Create Module Feature Directory Structure 📋
```
server-new/src/features/modules/
├── __init__.py (export ModuleService)
├── service.py
├── transform/
│   ├── __init__.py
│   ├── text_cleaner.py
│   ├── llm_parser.py
│   ├── type_converter.py
│   └── data_duplicator.py
├── action/
│   ├── __init__.py
│   ├── create_order.py
│   └── print_action.py
├── logic/
│   ├── __init__.py
│   ├── if_selector.py
│   ├── boolean_and.py
│   ├── boolean_or.py
│   └── boolean_not.py
└── comparator/
    ├── __init__.py
    ├── string_comparator.py
    ├── number_comparator.py
    └── date_comparator.py
```

## Integration Points

### Pipeline Service
**File:** `server-new/src/features/pipelines/service.py`
**Line:** 515 (get_module_metadata method)

Currently marked as TODO - needs to call module catalog service:
```python
def get_module_metadata(self, module_id: str, version: Optional[str] = None) -> Optional[ModuleMeta]:
    """Get module metadata from catalog"""
    # TODO: Call module catalog service
    # If version specified, get exact version
    # Otherwise get latest version
    # Return meta field
```

### Unit of Work
**File:** `server-new/src/shared/database/unit_of_work.py`

Need to add:
```python
# In TYPE_CHECKING imports (line 12)
from shared.database.repositories.module_catalog import ModuleCatalogRepository

# In __init__ (line 57)
self._module_catalog_repository: Optional['ModuleCatalogRepository'] = None

# Add property (after line 158)
@property
def module_catalog(self) -> 'ModuleCatalogRepository':
    if not self._module_catalog_repository:
        from shared.database.repositories.module_catalog import ModuleCatalogRepository
        self._module_catalog_repository = ModuleCatalogRepository(session=self.session)
        logger.debug("ModuleCatalogRepository loaded in UoW")
    return self._module_catalog_repository
```

### Repository Exports
**File:** `server-new/src/shared/database/repositories/__init__.py`

Need to add:
```python
from .module_catalog import ModuleCatalogRepository

__all__ = [
    # ... existing
    'ModuleCatalogRepository',
]
```

## Architecture Decisions

### New Server Patterns
1. **Domain Layer**: Use frozen dataclasses (not Pydantic) for internal service layer
2. **Repository Pattern**: Repositories use connection manager, return domain objects
3. **Unit of Work**: Lazy-loaded repository properties for transactional access
4. **Module Types**: Pydantic models only for:
   - Module configs (validated at runtime)
   - Module metadata (I/O shapes)
   - Database serialization/deserialization

### Module Loading Strategy
1. **At startup**: Auto-discover all modules in allowed packages
2. **At compile time**: Validate modules exist in catalog
3. **At runtime**: Load module class from registry or handler_name
4. **Catalog sync**: Separate operation to sync registry to database

## Key Files Reference

### Old Server (for reference)
- Service: `server/src/features/modules/service.py`
- Repository: `server/src/shared/database/repositories/module_catalog.py`
- Types: `server/src/shared/types/db/module_catalog.py`
- Registry: `server/src/shared/utils/registry.py`
- Example modules: `server/src/features/modules/transform/text_cleaner.py`

### New Server (created/updated)
- Module types: `server-new/src/shared/types/modules.py`
- Domain types: `server-new/src/shared/types/module_catalog.py`
- Registry: `server-new/src/shared/utils/registry.py`
- Types export: `server-new/src/shared/types/__init__.py`
- Database model: `server-new/src/shared/database/models.py` (lines 234-258)

### New Server (to create)
- Repository: `server-new/src/shared/database/repositories/module_catalog.py`
- Service: `server-new/src/features/modules/service.py`
- Module implementations: `server-new/src/features/modules/{transform,action,logic,comparator}/`

## Testing Strategy (Future)
1. Test registry auto-discovery
2. Test module validation
3. Test module execution
4. Test database sync
5. Test pipeline integration

## API Endpoint (Future)
**Router:** Router 5 - Module Catalog
**Endpoint:** `GET /modules`
- Query params: module_kind, category, search
- Returns: All active modules (no pagination)
- Response excludes: handler_name, created_at, updated_at

## Notes
- Module catalog table already exists in database (migrations complete)
- Old server has ~15 module implementations to migrate
- Auto-discovery runs once at service initialization
- Modules use `@register` decorator pattern for registration
- Type variables (e.g., "T") used for generic module I/O
