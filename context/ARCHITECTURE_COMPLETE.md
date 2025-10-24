# ETO Server Architecture - Complete System Documentation

**Last Updated:** 2025-10-24
**Branch:** server_unification

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Patterns](#architectural-patterns)
3. [Domain: Email Configuration](#domain-email-configuration)
4. [Domain: Email Ingestion](#domain-email-ingestion)
5. [Domain: PDF Templates](#domain-pdf-templates)
6. [Domain: PDF Files](#domain-pdf-files)
7. [Domain: Pipeline System](#domain-pipeline-system)
8. [Domain: Module Catalog](#domain-module-catalog)
9. [Cross-Domain Flows](#cross-domain-flows)
10. [Service Container & Initialization](#service-container--initialization)
11. [API Layer](#api-layer)

---

## System Overview

The ETO server is a transformation pipeline system that processes emails and generates PDF documents. It uses a clean architecture with:

- **Service Layer**: Business logic and orchestration
- **Repository Layer**: Data access with frozen dataclass domain objects
- **API Layer**: FastAPI routers with Pydantic schemas for validation
- **Database**: SQLAlchemy ORM with PostgreSQL

### Key Technologies
- FastAPI for REST API
- SQLAlchemy for ORM
- Pydantic for validation (API schemas only)
- Frozen dataclasses for domain objects
- Unit of Work pattern for transactions

---

## Architectural Patterns

### Repository Pattern
All repositories inherit from `BaseRepository` and support dual-mode operation:
- **Standalone mode**: Uses `connection_manager` to create sessions per operation (auto-commits)
- **Transaction mode**: Uses provided `session` from Unit of Work (caller controls commit)

**Location:** `server-new/src/shared/database/repositories/base.py`

```python
class BaseRepository(ABC, Generic[ModelType]):
    def __init__(self, session: Optional[Session] = None,
                 connection_manager: Optional['DatabaseConnectionManager'] = None):
        # Either session OR connection_manager (not both)
```

### Unit of Work Pattern
Manages database transactions with lazy-loaded repositories.

**Location:** `server-new/src/shared/database/unit_of_work.py`

```python
with connection_manager.unit_of_work() as uow:
    config = uow.email_configs.create(config_data)
    email = uow.emails.create(email_data)
    # Both commit together automatically
```

**Available Repositories in UoW:**
- `email_configs` - EmailConfigRepository
- `emails` - EmailRepository
- `pdf_templates` - PdfTemplateRepository
- `pdf_template_versions` - PdfTemplateVersionRepository
- `pdf_files` - PdfFileRepository
- `pipeline_definitions` - PipelineDefinitionRepository
- `pipeline_compiled_plans` - PipelineCompiledPlanRepository
- `pipeline_definition_steps` - PipelineDefinitionStepRepository
- `module_catalog` - ModuleCatalogRepository

### Domain Objects vs API Schemas
- **Domain objects**: Frozen dataclasses used in service/repository layer (internal)
- **API schemas**: Pydantic models used for HTTP request/response validation (external)
- **Mappers**: Convert between API schemas and domain objects

---

## Domain: Email Configuration

Manages email account configurations that define which email accounts to monitor and what filtering rules to apply.

### Domain Model

**Location:** `server-new/src/shared/types/email_configs.py`

```python
@dataclass(frozen=True)
class FilterRule:
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: bool
```

**Filter Rules:**
- Support 4 field types: sender_email, subject, has_attachments, attachment_types
- Support 4 operations: contains, equals, starts_with, ends_with
- Optional case sensitivity
- Stored as JSON in database, converted to/from FilterRule dataclasses by repository

**Core Types:**
- `EmailConfig` - Full configuration with all fields (database record)
- `EmailConfigSummary` - Lightweight view for list operations (id, name, is_active, last_check_time)
- `EmailConfigCreate` - Data for creating new config (immutable after creation: name, email_address, folder_name)
- `EmailConfigUpdate` - Partial update data (all fields optional)

**Lifecycle Fields:**
- `is_active` - Whether email monitoring is running
- `activated_at` - When monitoring was last activated
- `last_check_time` - Last successful email check
- `last_error_message` / `last_error_at` - Error tracking

### Repository: EmailConfigRepository

**Location:** `server-new/src/shared/database/repositories/email_config.py`

Inherits from `BaseRepository[EmailConfigModel]` for dual-mode operation.

**Key Methods:**

1. **`get_all_summaries(order_by, desc)`** - List all configs with sorting
   - Returns lightweight EmailConfigSummary objects
   - Supports sorting by name, id, or last_check_time

2. **`get_by_id(config_id)`** - Get full config by ID
   - Returns EmailConfig or None
   - Converts JSON filter_rules to FilterRule dataclasses

3. **`create(config_data: EmailConfigCreate)`** - Create new config
   - Always starts with is_active=False (inactive)
   - Converts FilterRule list to JSON for storage
   - Returns created EmailConfig

4. **`update(config_id, config_update: EmailConfigUpdate)`** - Update config
   - Only updates provided fields (partial update)
   - Handles JSON conversion for filter_rules if provided
   - Used for both user updates and lifecycle updates (activation/deactivation)

5. **`delete(config_id)`** - Delete config
   - Hard delete from database
   - Returns deleted EmailConfig before removal

**Helper Methods:**
- `_filter_rules_to_json()` - Convert FilterRule list to JSON string
- `_filter_rules_from_json()` - Parse JSON string to FilterRule list
- `_model_to_dataclass()` - Convert ORM model to EmailConfig
- `_model_to_summary()` - Convert ORM model to EmailConfigSummary

### Service: EmailConfigService

**Location:** `server-new/src/features/email_configs/service.py`

Business logic layer for email configuration management. Delegates activation/deactivation to EmailIngestionService.

**Dependencies:**
- `connection_manager: DatabaseConnectionManager` - Database access
- `ingestion_service: EmailIngestionService` - Email monitoring lifecycle

**CRUD Operations:**

1. **`list_configs_summary(order_by, desc)`** → `list[EmailConfigSummary]`
   - Lists all configs with optional sorting
   - Delegates to repository.get_all_summaries()

2. **`get_config(config_id)`** → `EmailConfig`
   - Gets full config by ID
   - Raises ObjectNotFoundError if not found

3. **`create_config(config_data: EmailConfigCreate)`** → `EmailConfig`
   - Creates new config in inactive state
   - No connection validation on creation
   - User must explicitly activate to start monitoring

4. **`update_config(config_id, config_update: EmailConfigUpdate)`** → `EmailConfig`
   - **Validation:** Config must be inactive
   - Raises ConflictError if config is active
   - Must deactivate before updating

5. **`delete_config(config_id)`** → `EmailConfig`
   - **Validation:** Config must be inactive
   - Raises ConflictError if still active
   - Must deactivate before deleting

**Lifecycle Operations:**

6. **`activate_config(config_id)`** → `EmailConfig`
   - **Process Flow:**
     1. Get config from repository
     2. Validate exists and is inactive
     3. **Delegate to EmailIngestionService.start_monitoring(config)**
     4. Update DB: is_active=True, activated_at=now
     5. Return updated config
   - **Error Handling:**
     - ObjectNotFoundError (404) - Config not found
     - ConflictError (409) - Already active
     - ServiceError (500) - Infrastructure failure (connection failed, etc.)

7. **`deactivate_config(config_id)`** → `EmailConfig`
   - **Process Flow:**
     1. Get config from repository
     2. Validate exists and is active
     3. **Delegate to EmailIngestionService.stop_monitoring(config_id)**
     4. Update DB: is_active=False
     5. Return updated config
   - **Error Handling:**
     - ObjectNotFoundError (404) - Config not found
     - ConflictError (409) - Not active
     - ServiceError (500) - Infrastructure failure

### Integration Points

**EmailIngestionService Integration:**
- Service delegates to EmailIngestionService for:
  - `start_monitoring(config)` - Start email polling for this config
  - `stop_monitoring(config_id)` - Stop email polling for this config
- EmailIngestionService manages listener lifecycle (background tasks, IMAP connections, etc.)
- EmailConfigService only manages database state

**API Router:**
- Router at `server-new/src/api/routers/email_configs.py`
- Converts between Pydantic API schemas and domain dataclasses
- Service receives domain dataclasses, returns domain dataclasses
- Router converts to/from Pydantic for HTTP validation

### Business Rules

1. **Configs start inactive** - New configs cannot start monitoring automatically
2. **No updates while active** - Must deactivate first (prevents race conditions)
3. **No deletion while active** - Must deactivate first (ensures clean shutdown)
4. **Separation of concerns** - Service manages DB state, EmailIngestionService manages infrastructure

---

## Domain: Email Ingestion

*Loading...*

---

## Domain: PDF Templates

Manages PDF templates and their versioning system. Templates define how to match PDFs and extract data, with immutable version snapshots for change tracking.

### Template-Version Relationship

**Core Concept:**
- **Templates** (`pdf_templates` table) - Mutable metadata (name, description, status)
- **Versions** (`pdf_template_versions` table) - Immutable wizard data snapshots (signature objects, extraction fields, pipeline)
- Templates **point to** their current version via `current_version_id` foreign key
- Versions **belong to** a template via `pdf_template_id` foreign key

**Why This Design:**
- Versions are immutable - once created, they never change
- Templates can be updated without losing history
- Users can view/restore previous versions
- Active templates use current version for PDF matching

### Domain Model

**Location:** `server-new/src/shared/types/pdf_templates.py`

**Template Types:**

```python
@dataclass(frozen=True)
class PdfTemplateMetadata:
    """Template metadata - points to current version"""
    id: int
    name: str
    description: str | None
    status: Literal["active", "inactive"]
    source_pdf_id: int
    current_version_id: int | None  # FK to current version
    created_at: datetime
    updated_at: datetime
```

**Version Types:**

```python
@dataclass(frozen=True)
class PdfTemplateVersion:
    """Immutable version snapshot of wizard data"""
    id: int
    template_id: int  # FK to template
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects  # Subset of extracted PDF objects for matching
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int
    created_at: datetime

@dataclass(frozen=True)
class ExtractionField:
    """Field definition for data extraction from PDF"""
    name: str
    description: str
    bound_box: tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int
```

**Summary Types:**
- `PdfTemplateSummary` - List view (includes current_version_number, version_count, usage_count)
- `PdfVersionSummary` - Version history view (version_number, created_at, is_current)
- `PdfTemplateWithVersion` - Detail view (template + current_version combined)

**CRUD Types:**
- `PdfTemplateCreate` - Create template + version 1 atomically
- `PdfTemplateUpdate` - Smart update (metadata-only or create new version)
- `PdfVersionCreate` - Create new version

### Repository: PdfTemplateRepository

**Location:** `server-new/src/shared/database/repositories/pdf_template.py`

**Key Methods:**

1. **`list_templates(status, sort_by, sort_order)`** → `list[PdfTemplateSummary]`
   - **Complex Query:**
     - Joins with current_version to get version_num and usage_count
     - Subquery to count total versions per template
     - Filters by status (active/inactive)
     - Sorts by name, status, or usage_count
   - Returns enriched summaries with version information

2. **`get_by_id(template_id)`** → `PdfTemplateMetadata | None`
   - Simple metadata retrieval
   - Does not load version data (lightweight)

3. **`get_with_details(template_id)`** → `tuple[PdfTemplateMetadata, PdfTemplateVersionModel, int] | None`
   - Returns template, current version model, and total version count
   - Used by get_template_detail service method
   - Loads complete information for detail views

4. **`create(name, description, source_pdf_id, status)`** → `PdfTemplateMetadata`
   - Creates template record with current_version_id=None initially
   - Always starts with status="inactive"
   - Caller must create version separately and update current_version_id

5. **`update(template_id, updates)`** → `PdfTemplateMetadata | None`
   - Generic update method accepting dict of field updates
   - Handles enum conversion for status field
   - Used for both metadata updates and current_version_id updates

### Repository: PdfTemplateVersionRepository

**Location:** `server-new/src/shared/database/repositories/pdf_template_version.py`

Handles JSON serialization/deserialization of complex wizard data.

**Key Methods:**

1. **`create(version_data: PdfVersionCreate)`** → `PdfTemplateVersion`
   - Serializes signature_objects and extraction_fields to JSON
   - Creates version record with usage_count=0
   - Returns domain dataclass with deserialized objects

2. **`get_by_id(version_id)`** → `PdfTemplateVersion | None`
   - Deserializes JSON fields back to domain objects
   - Loads template relationship to get source_pdf_id

3. **`list_by_template(template_id)`** → `list[PdfVersionSummary]`
   - Lists all versions for a template (version history)
   - Ordered by version_number DESC (newest first)
   - Marks which version is current

4. **`get_current_for_template(template_id)`** → `PdfTemplateVersion | None`
   - Joins to template to get current_version_id
   - Returns current active version with deserialized data

**Helper Methods:**
- `_model_to_version()` - Convert ORM model to domain dataclass with JSON deserialization
- `model_to_version_with_source()` - Convert without loading template relationship (when source_pdf_id is known)

### Service: PdfTemplateService

**Location:** `server-new/src/features/pdf_templates/service.py`

Business logic layer managing template lifecycle and smart versioning.

**Dependencies:**
- `connection_manager: DatabaseConnectionManager` - Database access
- `template_repository: PdfTemplateRepository` - Template CRUD
- `version_repository: PdfTemplateVersionRepository` - Version CRUD
- `pipeline_repository: PipelineDefinitionRepository` - Pipeline creation (TODO)

**Query Operations:**

1. **`list_templates(status, sort_by, sort_order)`** → `list[PdfTemplateSummary]`
   - Delegates to repository with validation
   - Returns templates with version statistics

2. **`get_template(template_id)`** → `PdfTemplateMetadata`
   - Gets basic template metadata
   - Raises ObjectNotFoundError if not found

3. **`get_template_detail(template_id)`** → `tuple[PdfTemplateWithVersion, int, list[PdfVersionSummary]]`
   - **Returns:** (template_with_current_version, total_versions, version_history)
   - Combines data from template and version repositories
   - Used by GET /pdf-templates/{id} endpoint

4. **`get_version_detail(template_id, version_id)`** → `tuple[PdfTemplateVersion, bool]`
   - **Returns:** (version_data, is_current)
   - **Validates:** Version belongs to template (raises ConflictError if not)
   - Used by GET /pdf-templates/{id}/versions/{version_id} endpoint

**Atomic Creation:**

5. **`create_template(template_data: PdfTemplateCreate)`** → `tuple[PdfTemplateMetadata, int, int]`
   - **Returns:** (template, version_number, pipeline_definition_id)
   - **Process Flow (Single Transaction):**
     1. Create pipeline definition from wizard Step 3 data (TODO: placeholder=1)
     2. Create template record (status=inactive, current_version_id=None)
     3. Create version 1 with signature_objects, extraction_fields, pipeline_id
     4. Update template.current_version_id to point to version 1
     5. Commit transaction atomically
   - **Uses Unit of Work** for transaction management
   - **Rollback on failure** - all-or-nothing creation

**Smart Update Logic:**

6. **`update_template(template_id, update_data, pipeline_state, visual_state)`** → `tuple[PdfTemplateMetadata, int, int]`
   - **Returns:** (template, current_version_num, pipeline_definition_id)
   - **Smart Logic:**
     - **Metadata-only change** (name/description): Update template only, no new version
     - **Wizard data change** (signature_objects, extraction_fields, pipeline): Create new version
   - **Change Detection:**
     - Compares update_data with current version
     - Checks signature_objects and extraction_fields for differences
   - **Validation:**
     - **Cannot update wizard data while template is active** (raises ConflictError)
     - Must deactivate first to prevent race conditions with matching engine
   - **Version Creation Process:**
     1. Create new pipeline definition (TODO: placeholder)
     2. Calculate next version number (current + 1)
     3. Create new version with updated wizard data
     4. Update template.current_version_id to new version
     5. Update name/description if provided
     6. Commit transaction atomically

**Lifecycle Operations:**

7. **`activate_template(template_id)`** → `PdfTemplateMetadata`
   - **Validation:** Template must have current_version_id (cannot activate without version)
   - Updates status to "active"
   - Active templates are used by ETO matching engine

8. **`deactivate_template(template_id)`** → `PdfTemplateMetadata`
   - Updates status to "inactive"
   - Stops template from being used for ETO matching
   - Required before updating wizard data

### Template-Version Workflows

**Creating a Template:**
```
1. User completes wizard (Steps 1-3: upload PDF, select signature objects, define extraction fields, build pipeline)
2. Service creates pipeline definition from wizard Step 3
3. Service creates template record (inactive, no current_version)
4. Service creates version 1 with wizard data + pipeline_id
5. Service updates template.current_version_id → version 1
6. All operations in single transaction
```

**Updating Metadata Only:**
```
1. User changes template name/description
2. Service compares with current version - wizard data unchanged
3. Service updates template.name and/or template.description
4. Version unchanged, no new version created
```

**Updating Wizard Data:**
```
1. User edits signature objects or extraction fields
2. Service detects wizard data change
3. Service validates template is inactive (fails if active)
4. Service creates new pipeline definition
5. Service creates new version (version_number = current + 1)
6. Service updates template.current_version_id → new version
7. Old version preserved in history
8. All operations in single transaction
```

**Viewing Version History:**
```
1. User views template detail page
2. Service returns current version + list of all versions
3. Each version summary shows: version_number, created_at, is_current
4. User can click to view specific old version
5. Service loads version data with signature_objects and extraction_fields
```

### JSON Serialization

**Complex types stored as JSON in database:**

1. **signature_objects: PdfObjects**
   - Serialized by `serialize_pdf_objects()` from pdf_files module
   - Stores PDF objects selected for template matching

2. **extraction_fields: list[ExtractionField]**
   - Serialized by `serialize_extraction_fields()` in pdf_templates module
   - Format: `{"fields": [{"name": ..., "bound_box": ..., ...}]}`
   - Deserialized by `deserialize_extraction_fields()` with legacy format support

### Integration Points

**Pipeline System:**
- Each version references a pipeline_definition_id
- Pipeline defines transformation steps from extracted data to final output
- TODO: Pipeline creation during template create/update (currently placeholder)

**PDF Files:**
- Templates reference source_pdf_id (the example PDF used in wizard)
- Signature objects are subset of objects extracted from source PDF
- Used for matching incoming PDFs against template

**API Router:**
- Router at `server-new/src/api/routers/pdf_templates.py`
- Converts between Pydantic API schemas and domain dataclasses
- Handles complex nested structures (template + version + history)

### Business Rules

1. **Templates start inactive** - Must explicitly activate for ETO matching
2. **Versions are immutable** - Once created, never changed
3. **No wizard updates while active** - Must deactivate first
4. **Atomic creation** - Template + version 1 created together or not at all
5. **Current version required for activation** - Cannot activate template without at least one version
6. **Version history preserved** - Old versions never deleted, users can view/compare

---

## Domain: PDF Files

*Loading...*

---

## Domain: Pipeline System

Manages data transformation pipelines with sophisticated compilation, validation, and deduplication. Pipelines define how extracted data flows through modules to produce final outputs.

### Three-Table Architecture

**How It's Wired Together:**

1. **`pipeline_definitions`** (User-facing) - Stores pipeline design with execution logic + visual layout
2. **`pipeline_compiled_plans`** (Optimized) - Stores compiled execution plans deduplicated by checksum
3. **`pipeline_definition_steps`** (Execution) - Stores ordered execution steps from topological sort

**Key Relationship:**
- Many pipeline_definitions can → one pipeline_compiled_plan (deduplication via checksum)
- One pipeline_compiled_plan has → many pipeline_definition_steps (ordered execution)

**Why This Design:**
- Users can have different visual layouts for same execution logic
- Compilation is expensive (validation + pruning + topological sort) - avoid redundant work
- Multiple templates can share the same pipeline if semantically identical

### Domain Model

**Location:** `server-new/src/shared/types/pipelines.py` and `pipeline_definition.py`

```python
@dataclass(frozen=True)
class PipelineState:
    """Execution structure (what actually runs)"""
    entry_points: List[EntryPoint]  # Pipeline inputs
    modules: List[ModuleInstance]  # Transformation nodes
    connections: List[NodeConnection]  # Data flow edges

@dataclass(frozen=True)
class VisualState:
    """UI positioning (for visual editor)"""
    modules: Dict[str, tuple[float, float]]  # module_id -> (x, y)
    entry_points: Dict[str, tuple[float, float]]

@dataclass(frozen=True)
class ModuleInstance:
    """Module placed on canvas"""
    module_instance_id: str  # Unique instance ID
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[NodeInstance]  # Input pins
    outputs: List[NodeInstance]  # Output pins

@dataclass(frozen=True)
class NodeInstance:
    """Pin on a module"""
    node_id: str
    type: str  # "str", "int", "float", "bool", etc.
    name: str
    position_index: int
    group_index: int
```

### Service: PipelineService

**Location:** `server-new/src/features/pipelines/service.py`

**The Compilation Pipeline:**

```
User Creates Pipeline
        ↓
   VALIDATE (6 checks)
        ↓
   PRUNE (remove dead branches)
        ↓
   CHECKSUM (SHA-256 of execution semantics)
        ↓
   DEDUP CHECK (existing compiled plan?)
        ↓
  ┌────┴────┐
  YES       NO
   ↓        ↓
  REUSE   COMPILE (Kahn's topological sort)
   ↓        ↓
   └────┬───┘
        ↓
   PERSIST (definition + plan + steps)
```

**1. Validation** (`_validate_pipeline` at service.py:137)

**6 Validation Checks:**
1. Module references exist in module catalog (TODO: placeholder)
2. All connections reference valid pins
3. Connection type compatibility (str → str, int → int, etc.)
4. No duplicate connections
5. No cycles (DAG requirement) via DFS
6. All module inputs are connected

**2. Pruning** (`_prune_dead_branches` at service.py:274)

**Dead Branch Removal:**
- Identifies "output" modules (no downstream connections or action modules)
- BFS backwards from outputs to find reachable modules
- Removes unreachable modules, connections, and entry points
- Ensures minimal execution graph

**Why:** User might build pipeline with experimental branches - only compile what's actually used

**3. Checksum** (`_calculate_checksum` at service.py:376)

**Deterministic Hashing:**
- Converts pruned pipeline to sorted JSON (deterministic ordering)
- Calculates SHA-256 of JSON string
- Same execution logic = same checksum (even with different visual layout)

**4. Deduplication** (in `create_pipeline_definition` at service.py:542)

```python
existing_plan = compiled_plan_repository.get_by_checksum(checksum)
if existing_plan:
    compiled_plan_id = existing_plan.id  # Reuse
else:
    # Compile new plan
```

**5. Compilation** (`_compile_pipeline` at service.py:419)

**Kahn's Topological Sort Algorithm:**

```
1. Build adjacency list (module dependencies)
2. Count in-degrees (how many modules must run first)
3. Start with zero in-degree modules (no dependencies)
4. Process modules in order, decrement downstream in-degrees
5. Result: Ordered list of execution steps
```

**Each Step Contains:**
- `step_number` - Execution order
- `module_ref` - Which module to execute
- `module_config` - Configuration values
- `input_field_mappings` - Map input pins to upstream output pins
- `node_metadata` - Pin information for runtime

**6. Persistence** (in `create_pipeline_definition` at service.py:594)

**Atomic Transaction:**
```python
with connection_manager.unit_of_work() as uow:
    # Create compiled plan
    compiled_plan = uow.pipeline_compiled_plans.create(...)

    # Bulk create steps
    uow.pipeline_definition_steps.create_steps(steps)

    # Commit together
```

Then:
```python
# Create pipeline definition
pipeline_def = definition_repository.create(create_data)

# Link to compiled plan
definition_repository.update_compiled_plan_id(pipeline_def.id, compiled_plan_id)
```

### How Pipeline Execution Would Work (Future)

**Execution Service (Not Yet Implemented):**

1. Load pipeline_definition by ID
2. Get compiled_plan_id from definition
3. Load all steps ordered by step_number
4. For each step:
   - Load module class from catalog using module_ref
   - Get input values using input_field_mappings
   - Instantiate module with module_config
   - Execute module.run(inputs, config, context)
   - Store outputs for downstream modules
5. Return final outputs

### Integration with Module Catalog

**Module References:**
- Pipelines reference modules by `module_ref` (e.g., "text_cleaner:1.0.0")
- Module catalog stores module metadata, I/O shapes, config schemas
- Validation checks module_ref exists (TODO: currently placeholder at service.py:515)
- Execution loads module class from catalog dynamically

### Integration with PDF Templates

**Template Versions → Pipelines:**
- Each `pdf_template_version` has `pipeline_definition_id`
- Template wizard Step 3 creates pipeline definition
- Pipeline transforms extracted PDF data → final output format
- Multiple template versions can share compiled plan if logic is same

**Workflow:**
```
Template Creation:
1. User uploads PDF (Step 1)
2. User selects signature objects and extraction fields (Step 2)
3. User builds transformation pipeline (Step 3)
4. System creates pipeline definition with compilation
5. Template version stores pipeline_definition_id
```

### Indices and Lookup Structures

**PipelineIndices** (built during validation/compilation):

```python
@dataclass(frozen=True)
class PipelineIndices:
    pin_by_id: Dict[str, PinInfo]  # Fast pin lookup
    module_by_id: Dict[str, ModuleInstance]  # Fast module lookup
    input_to_upstream: Dict[str, str]  # Input pin → upstream output pin
```

**Built once, used throughout:**
- Validation uses indices for connection checks
- Pruning uses indices for reachability analysis
- Compilation uses indices for dependency graph construction

### Business Rules

1. **Pipelines must be DAGs** - No cycles allowed (validated via DFS)
2. **All inputs must be connected** - No dangling input pins
3. **Type safety** - Connections must be type-compatible
4. **Deduplication by semantics** - Same logic = same compiled plan
5. **Visual layout separate** - UI positioning doesn't affect compilation
6. **Deterministic compilation** - Same input always produces same output
7. **Minimal execution** - Dead branches are pruned before compilation

---

## Domain: Module Catalog

*Loading...*

---

## Cross-Domain Flows

*Loading...*

---

## Service Container & Initialization

*Loading...*

---

## API Layer

*Loading...*
