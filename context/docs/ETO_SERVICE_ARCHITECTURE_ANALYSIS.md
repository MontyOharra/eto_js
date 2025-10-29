# ETO Service Architecture Analysis

## Date: 2025-10-29

## Purpose
This document analyzes existing service patterns in the codebase to inform the design and implementation of the ETO Processing Service.

---

## Service Container Pattern

### Location
`server-new/src/shared/services/service_container.py`

### Architecture
- **Pure Class-Based Singleton**: No instances created, all methods are class methods
- **Lazy Instantiation**: Services only created when first accessed
- **Dependency Injection**: Services declare dependencies via constructor
- **Circular Dependency Support**: Uses `ServiceProxy` for lazy resolution
- **Single Registration Point**: All services defined in `_register_service_definitions()`

### Service Definition Structure

```python
'service_name': {
    'class': 'path.to.ServiceClass',  # or 'factory': 'path.to.factory_function'
    'args': [
        connection_manager,           # Direct argument
        '_service:other_service'      # Service dependency (lazy resolved)
    ],
    'singleton': True,                # Cache instance (default: True)
    'description': 'Human readable description'
}
```

### Initialization Flow

1. **App Startup** (`app.py`):
   ```python
   # Initialize database connection
   _connection_manager = init_database_connection(database_url)

   # Initialize service container
   ServiceContainer.initialize(_connection_manager, pdf_storage_path)

   # Eagerly initialize critical services
   modules_service = ServiceContainer.get_modules_service()
   # ... other services
   ```

2. **Service Resolution**:
   - First access triggers lazy creation
   - Dependencies resolved via `ServiceProxy`
   - Singleton instances cached for reuse

### Existing Service Registrations

```python
'modules': ModulesService(connection_manager)
'pdf_files': PdfFilesService(connection_manager, storage_config)
'email_ingestion': EmailIngestionService(connection_manager, pdf_files)
'email_configs': EmailConfigService(connection_manager, email_ingestion)
'pipeline_execution': PipelineExecutionService(connection_manager)
'pipelines': PipelineService(connection_manager, pipeline_execution)
'pdf_templates': PdfTemplateService(connection_manager, pipelines, pdf_files, pipeline_execution)
```

---

## Service Design Patterns

### Pattern Analysis from EmailConfigService

**File**: `server-new/src/features/email_configs/service.py`

#### 1. Structure
```python
class EmailConfigService:
    """Docstring explaining purpose and responsibilities"""

    # Type annotations for attributes
    connection_manager: DatabaseConnectionManager
    config_repository: EmailConfigRepository

    def __init__(self, connection_manager, other_service):
        """Initialize with dependencies"""
        self.connection_manager = connection_manager
        self.other_service = other_service
        self.config_repository = EmailConfigRepository(connection_manager=connection_manager)
```

#### 2. Key Patterns

**Repository Initialization**:
- Repositories created in `__init__` from connection_manager
- Pattern: `self.repo = RepoClass(connection_manager=connection_manager)`

**Error Handling**:
- Import from `shared.exceptions.service`:
  - `ObjectNotFoundError` - 404 errors
  - `ConflictError` - 409 state conflicts
  - `ValidationError` - 422 validation failures
  - `ServiceError` - 500 infrastructure failures

**Validation Pattern**:
```python
def update_config(self, config_id, update_data):
    # 1. Get resource to validate existence
    config = self.config_repository.get_by_id(config_id)
    if not config:
        raise ObjectNotFoundError(f"Config {config_id} not found")

    # 2. Business validation
    if config.is_active:
        raise ConflictError("Cannot update active config")

    # 3. Perform operation
    return self.config_repository.update(config_id, update_data)
```

**Logging**:
- Import: `logger = logging.getLogger(__name__)`
- Log important operations: `logger.info(f"Created config {config_id}")`
- Log errors: `logger.error(f"Failed: {e}", exc_info=True)`

#### 3. Method Types

**CRUD Operations**:
- `list_*()` - Query operations, return lists
- `get_*(id)` - Fetch single resource, raise ObjectNotFoundError if missing
- `create_*(data)` - Create new resource
- `update_*(id, data)` - Update resource with validation
- `delete_*(id)` - Delete resource with validation

**Business Logic Operations**:
- `activate_*()` - State transitions with side effects
- `deactivate_*()` - Reverse state transitions

---

## Pattern Analysis from PipelineService

**File**: `server-new/src/features/pipelines/service.py`

#### Key Differences

**Multiple Repositories**:
```python
def __init__(self, connection_manager, other_service):
    self.connection_manager = connection_manager
    self.other_service = other_service

    # Initialize multiple repositories
    self.definition_repository = PipelineDefinitionRepository(connection_manager=connection_manager)
    self.compiled_plan_repository = PipelineCompiledPlanRepository(connection_manager=connection_manager)
    self.step_repository = PipelineDefinitionStepRepository(connection_manager=connection_manager)
    self.module_catalog_repository = ModuleRepository(connection_manager=connection_manager)
```

**Internal Helper Methods**:
- Private methods prefixed with `_`
- Used for complex logic breakdown
- Not exposed to API layer

**Complex Orchestration**:
- Validates across multiple entities
- Coordinates multiple repository calls
- Implements business algorithms (compilation, validation)

---

## ETO Service Requirements (from ETO_PROCESSING_FLOW.md)

### Primary Responsibilities

1. **Create ETO Run**: Accept PDF file ID, create `eto_runs` record with status="not_started"

2. **Process Run** (orchestration):
   - Stage 1: Template Matching
   - Stage 2: Data Extraction
   - Stage 3: Data Transformation
   - Error handling and status updates

3. **Query Operations**:
   - List runs with filtering/pagination
   - Get run details with all stage data

4. **Bulk Operations**:
   - Reprocess runs (reset to not_started)
   - Skip runs
   - Delete runs

### Service Dependencies

**Required Services**:
- `pdf_templates` - Template matching algorithm
- `pdf_files` - PDF data access
- `pipeline_execution` - Pipeline execution

**Required Repositories**:
- `EtoRunRepository`
- `EtoRunTemplateMatchingRepository`
- `EtoRunExtractionRepository`
- `EtoRunPipelineExecutionRepository`
- `EtoRunPipelineExecutionStepRepository`

---

## Proposed ETO Service Structure

### Service Definition (for ServiceContainer)

```python
'eto_processing': {
    'class': 'features.eto_processing.service.EtoProcessingService',
    'args': [
        cls._connection_manager,
        '_service:pdf_templates',
        '_service:pdf_files',
        '_service:pipeline_execution'
    ],
    'singleton': True,
    'description': 'ETO workflow orchestration service'
}
```

### Service Class Structure

```python
class EtoProcessingService:
    """
    ETO Processing Service

    Orchestrates the 3-stage ETO workflow:
    1. Template Matching
    2. Data Extraction
    3. Data Transformation (Pipeline Execution)

    Manages ETO run lifecycle and provides query/control operations.
    """

    # Dependencies
    connection_manager: DatabaseConnectionManager
    pdf_template_service: PdfTemplateService
    pdf_files_service: PdfFilesService
    pipeline_execution_service: PipelineExecutionService

    # Repositories
    eto_run_repo: EtoRunRepository
    template_matching_repo: EtoRunTemplateMatchingRepository
    extraction_repo: EtoRunExtractionRepository
    pipeline_execution_repo: EtoRunPipelineExecutionRepository
    pipeline_execution_step_repo: EtoRunPipelineExecutionStepRepository

    def __init__(self, connection_manager, pdf_template_service, pdf_files_service, pipeline_execution_service):
        """Initialize with dependencies and create repositories"""
        pass

    # === Public API Methods ===

    def create_run(self, pdf_file_id: int) -> EtoRun:
        """Create new ETO run with status=not_started"""
        pass

    def list_runs(self, status=None, limit=None, offset=None) -> list[EtoRun]:
        """List runs with filtering"""
        pass

    def get_run_detail(self, run_id: int) -> EtoRunDetail:
        """Get run with all stage data"""
        pass

    # === Processing Methods (called by worker) ===

    def process_run(self, run_id: int) -> bool:
        """Execute full 3-stage workflow"""
        pass

    def _execute_template_matching(self, run_id: int) -> bool:
        """Stage 1: Template matching"""
        pass

    def _execute_data_extraction(self, run_id: int) -> bool:
        """Stage 2: Data extraction"""
        pass

    def _execute_data_transformation(self, run_id: int) -> bool:
        """Stage 3: Pipeline execution"""
        pass

    # === Helper Methods ===

    def _mark_run_success(self, run_id: int) -> None:
        """Update run to success status"""
        pass

    def _mark_run_failure(self, run_id: int, error: Exception) -> None:
        """Update run to failure with error details"""
        pass
```

---

## Key Design Decisions

### 1. Service Naming
- **Decision**: Name the service `EtoProcessingService` (not `EtoRunsService`)
- **Rationale**:
  - Emphasizes orchestration role
  - Distinguishes from simple CRUD service
  - Matches pattern: `EmailIngestionService`, `PipelineExecutionService`

### 2. Repository Management
- **Decision**: Initialize all 5 ETO repositories in constructor
- **Rationale**:
  - All repositories needed for orchestration
  - Follows pattern from `PipelineService`
  - Clean separation: service = orchestration, repositories = data

### 3. Error Handling
- **Decision**: Use custom exceptions from `shared.exceptions.service`
- **Rationale**:
  - Consistent with existing services
  - Maps directly to HTTP status codes
  - Clear separation: business errors vs infrastructure errors

### 4. Logging Strategy
- **Decision**: Comprehensive logging at each stage
- **Rationale**:
  - Worker runs in background (no user visibility)
  - Debug failures requires detailed logs
  - Follows existing service patterns

### 5. Worker Separation
- **Decision**: Worker is separate from service (not a service method)
- **Rationale**:
  - Service = business logic
  - Worker = infrastructure (polling loop)
  - Service can be used without worker (manual triggers)
  - Worker file: `features/eto_processing/worker.py`

---

## File Structure

```
server-new/src/features/eto_processing/
├── __init__.py
├── service.py              # EtoProcessingService
└── worker.py               # EtoWorker (background polling)
```

---

## Next Steps

1. ✅ Analyze existing services and patterns
2. ✅ Document findings
3. ⏳ Create boilerplate service class
4. ⏳ Register service in ServiceContainer
5. ⏳ Add convenience method to ServiceContainer
6. ⏳ Create worker boilerplate
7. ⏳ Test service instantiation

---

## References

- **ServiceContainer**: `server-new/src/shared/services/service_container.py`
- **EmailConfigService**: `server-new/src/features/email_configs/service.py`
- **PipelineService**: `server-new/src/features/pipelines/service.py`
- **ETO Processing Flow**: `context/docs/ETO_PROCESSING_FLOW.md`
- **ETO Implementation Guide**: `context/docs/ETO_IMPLEMENTATION_GUIDE.md`
- **App Initialization**: `server-new/src/app.py`
