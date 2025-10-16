# Server Redesign - Service Layer Design (Phase 5)

## Overview

This document defines the service layer architecture for the redesigned server, focusing on how services integrate with the API layer using internal dataclasses instead of Pydantic models throughout the entire stack.

**Architecture Pattern:**
```
API Layer (FastAPI Routers)
    ↕ Pydantic Models (HTTP request/response validation only)
Mapper Functions (explicit conversion)
    ↕ Dataclasses (frozen, internal data structures)
Service Layer (business logic)
    ↕ Dataclasses (frozen, internal data structures)
Repository Layer (data access)
    ↕ Dataclasses ↔ SQLAlchemy ORM Models
```

---

## Design Principles

1. **Pydantic at API Boundary Only**: Pydantic models are used exclusively in the API layer for HTTP request validation and response serialization
2. **Dataclasses for Internal Use**: Services and repositories use frozen dataclasses for all internal data transfer - these are NOT DTOs, just internal data structures
3. **Explicit Mapping**: Routers contain explicit mapper functions to convert between Pydantic models (API boundary) and dataclasses (internal)
4. **Service Orchestration**: Services coordinate business logic, handle transactions, and call multiple repositories
5. **Transaction Management**: Services provide methods to execute multi-repository operations in single transactions
6. **Error Bubbling**: Repository errors (ObjectNotFoundError, etc.) bubble up through services to API layer
7. **Universal Dataclass Return**: ALL service methods return dataclasses, including discovery methods - routers always map dataclass → Pydantic for responses

---

## Service 1: Email Ingestion Service

### Current Implementation Status

**Location**: `server/src/features/email_ingestion/service.py`

**What Exists**:
- Complete service implementation with configuration management, listener threads, and email processing
- Discovery endpoints (accounts, folders, connection testing)
- Config lifecycle management (create, update, delete, activate, deactivate)
- Email listener threads that poll integrations on configurable intervals
- Filter rule application within listeners
- Email processing pipeline (email → PDF attachment → ETO run)
- Startup recovery for active configs
- Graceful shutdown handling

**Integration Architecture**:
- `BaseEmailIntegration`: Abstract interface for email providers
- `OutlookComIntegration`: Windows COM implementation (fully built)
- `EmailIntegrationFactory`: Factory for creating integrations
- `EmailListenerThread`: Background polling thread with filter rules

### Service Responsibilities

**1. Account/Folder Discovery**
- `discover_email_accounts(provider_type)`: List available accounts for provider → returns List[EmailAccount] (dataclass)
- `discover_folders(email_address, provider_type)`: List folders for account → returns List[EmailFolder] (dataclass)
- `test_connection_for_new_config(email_address, folder_name, provider_type)`: Validate before config creation → returns ConnectionTestResult (dataclass)

**2. Configuration Management**
- `create_config(config_data)`: Create new email config (validates connection first) → takes dataclass, returns dataclass
- `get_config(config_id)`: Retrieve single config → returns dataclass
- `update_config(config_id, config_data)`: Update config (auto-restarts if active) → takes dataclass, returns dataclass
- `delete_config(config_id)`: Delete config (auto-deactivates first) → returns dataclass
- `list_configs()`: List all configs → returns List[dataclass]
- `list_config_summaries()`: List configs with summary info → returns List[dataclass]

**3. Listener Lifecycle Management**
- `activate_config(config_id)`: Spin up listener thread and integration → returns dataclass
- `deactivate_config(config_id)`: Stop listener and mark inactive in DB → returns bool
- `stop_config_listeners(config_id)`: Stop listeners WITHOUT changing DB status (shutdown only) → returns bool
- `get_active_listeners()`: Get status of all running listeners → returns Dict[int, dataclass]

**4. Email Processing**
- `process_email(config_id, email_msg, attachments)`: Process single email (called by listener threads)
- `_process_pdf_attachment(email_id, attachment)`: Store PDF, trigger ETO processing
- `get_processed_emails(config_id, limit)`: Query processed emails → returns List[dataclass]
- `get_processing_statistics(config_id)`: Get stats for config → returns Dict

**5. Service Lifecycle**
- `startup_recovery()`: Reactivate configs that were active before shutdown
- `stop_all_listeners()`: Stop all listeners without changing DB status
- `shutdown()`: Graceful shutdown of all listeners
- `is_healthy()`: Health check for service → returns bool

### Key Design Decisions

**Listener Thread Management**:
- Threads created on activation, contain integration instance and process callback
- Threads poll at configurable intervals (from config)
- Filter rules applied within thread before processing
- Last check time tracked to avoid duplicate processing
- Fresh activation vs startup recovery distinction (no overlap on fresh activation)

**Deactivation vs Shutdown**:
- **User Deactivation**: Kills listeners AND marks config inactive in DB (no startup recovery)
- **Server Shutdown**: Kills listeners but PRESERVES active status in DB (enables startup recovery)

**Email Processing Pipeline**:
1. Listener finds emails matching filters since last check time
2. Calls `process_email()` for each email
3. Service checks for duplicates (by message_id)
4. Creates email record in DB
5. For each PDF attachment:
   - Calls `pdf_service.store_pdf()` to create PDF file record
   - Calls `eto_service.process_pdf()` to trigger ETO processing
6. Updates config statistics (emails processed, PDFs found, last check time)

**Cross-Service Dependencies**:
- Depends on `PdfProcessingService` (to store PDFs)
- Depends on `EtoProcessingService` (to trigger ETO runs)
- These are injected via constructor

### Dataclasses Required

**Internal Types** (extract from existing `shared/types`):

**Core Types**:
- `EmailConfig`: Config data (name, email_address, folder_name, filter_rules, polling settings)
- `EmailFilterRule`: Single filter rule (field, operation, value, case_sensitive)
- `EmailConfigCreate`: Data for creating config
- `EmailConfigUpdate`: Data for updating config
- `Email`: Email record data
- `EmailCreate`: Data for creating email record

**Discovery Types** (used by integrations and returned by service):
- `EmailMessage`: Message from integration (transient, not persisted)
- `EmailAttachment`: Attachment from integration (transient, not persisted)
- `EmailAccount`: Discovered account info (transient, not persisted)
- `EmailFolder`: Discovered folder info (transient, not persisted)
- `ConnectionTestResult`: Test result (transient, not persisted)

**Response Types**:
- `EmailConfigSummary`: Summary view for list endpoint
- `ListenerStatus`: Status of active listener (already exists as dataclass in service.py:41-52)

**Note**: All of these should be frozen dataclasses. No "DTO" suffix - just domain names.

### Mapping Strategy

**Router → Service** (Pydantic to dataclass):
```python
# In router
@router.post("/email-configs")
def create_email_config(request: EmailConfigCreateRequest) -> EmailConfigResponse:
    # Map Pydantic → dataclass
    config_data = EmailConfigCreate(
        name=request.name,
        description=request.description,
        email_address=request.email_address,
        folder_name=request.folder_name,
        filter_rules=[EmailFilterRule(**rule.dict()) for rule in request.filter_rules],
        poll_interval_seconds=request.poll_interval_seconds,
        max_backlog_hours=request.max_backlog_hours,
        error_retry_attempts=request.error_retry_attempts
    )

    # Call service (gets dataclass back)
    config = email_service.create_config(config_data)

    # Map dataclass → Pydantic response
    return EmailConfigResponse(
        id=config.id,
        name=config.name,
        # ... map all fields
    )
```

**Discovery Endpoints** (also return dataclasses):
```python
@router.post("/email-configs/discover/accounts")
def discover_accounts(request: DiscoverAccountsRequest) -> DiscoverAccountsResponse:
    # Call service (gets List[dataclass])
    accounts = email_service.discover_email_accounts(request.provider_type)

    # Map dataclass → Pydantic for response
    return DiscoverAccountsResponse(
        accounts=[
            EmailAccountResponse(
                email_address=acc.email_address,
                display_name=acc.display_name,
                # ... map all fields
            )
            for acc in accounts
        ]
    )
```

**Service → Repository** (dataclass to dataclass):
- Service already uses repositories correctly
- Need to update repository to accept/return dataclasses instead of Pydantic

**Repository → SQLAlchemy** (dataclass to ORM):
- Repository converts dataclasses to ORM models for persistence
- Repository converts ORM models back to dataclasses for return

### Transaction Management

**Current Implementation**:
- Repositories auto-wrap methods in sessions with auto-commit
- No explicit multi-repository transactions yet

**Required Updates**:
- Add transaction context manager to services
- Services need ability to call multiple repositories in single transaction
- Example: `create_config()` needs to validate connection, create config, potentially create initial stats record

**Pattern**:
```python
# Service method
def create_config_transactional(self, config_data: EmailConfigCreate) -> EmailConfig:
    with self.connection_manager.transaction() as session:
        # Test connection (no DB write)
        test_result = self.test_connection_for_new_config(...)
        if not test_result.success:
            raise ServiceError(...)

        # Create config (pass session to repository)
        config = self.config_repository.create(config_data, session=session)

        # Additional operations if needed
        # ...

        return config
```

### Integration with API Layer

**Endpoints → Service Methods**:

| Endpoint | Service Method | Service Returns | Router Maps To |
|----------|----------------|-----------------|----------------|
| `POST /email-configs/discover/accounts` | `discover_email_accounts()` | `List[EmailAccount]` | `DiscoverAccountsResponse` |
| `POST /email-configs/discover/folders` | `discover_folders()` | `List[EmailFolder]` | `DiscoverFoldersResponse` |
| `POST /email-configs/test-connection` | `test_connection_for_new_config()` | `ConnectionTestResult` | `TestConnectionResponse` |
| `POST /email-configs` | `create_config()` | `EmailConfig` | `EmailConfigResponse` |
| `GET /email-configs` | `list_config_summaries()` | `List[EmailConfigSummary]` | `EmailConfigListResponse` |
| `GET /email-configs/{id}` | `get_config()` | `EmailConfig` | `EmailConfigResponse` |
| `PUT /email-configs/{id}` | `update_config()` | `EmailConfig` | `EmailConfigResponse` |
| `DELETE /email-configs/{id}` | `delete_config()` | `EmailConfig` | `EmailConfigResponse` |
| `POST /email-configs/{id}/activate` | `activate_config()` | `EmailConfig` | `EmailConfigResponse` |
| `POST /email-configs/{id}/deactivate` | `deactivate_config()` | `bool` | `SuccessResponse` |
| `GET /email-configs/active-listeners` | `get_active_listeners()` | `Dict[int, ListenerStatus]` | `ActiveListenersResponse` |

**Key Point**: ALL service methods return dataclasses (or primitives like bool/int). Routers ALWAYS map these to Pydantic for HTTP responses.

### What Needs to Change

**Current State**:
- Service uses Pydantic models from `shared/types` throughout
- Repositories accept/return Pydantic models
- No explicit mapper layer

**Required Changes**:

1. **Create Dataclasses** (frozen dataclasses in `server/src/shared/types/`):
   - Extract persistence-related types from Pydantic models
   - Create frozen dataclasses for configs, emails, filter rules
   - Use simple domain names (no "DTO" suffix)
   - **IMPORTANT**: Types must be in `shared/types/` to avoid circular imports

2. **Update Service**:
   - Update method signatures to accept/return dataclasses instead of Pydantic
   - Keep integration-related types as-is (EmailMessage, EmailAttachment, etc. - these are also dataclasses)
   - Internal processing uses dataclasses

3. **Update Repositories**:
   - Accept dataclasses instead of Pydantic
   - Return dataclasses instead of Pydantic
   - Convert dataclasses ↔ SQLAlchemy ORM models

4. **Create Mappers** (in router file or separate mapper module):
   - Pydantic Request → dataclass (for service calls)
   - dataclass → Pydantic Response (for API responses)
   - Every endpoint needs explicit mapping

5. **Add Transaction Support**:
   - Connection manager provides transaction context
   - Services can execute multi-repo operations in single transaction
   - Repositories accept optional session parameter

### Example Service Method Signature Changes

**Before** (current):
```python
def create_config(self, config_create: EmailConfigCreate) -> EmailConfig:
    # config_create is Pydantic
    # returns Pydantic
```

**After** (with dataclasses):
```python
def create_config(self, config_create: EmailConfigCreate) -> EmailConfig:
    # config_create is frozen dataclass
    # returns frozen dataclass
    # (same signature, different underlying type)
```

### Dependencies

**Service Constructor**:
```python
def __init__(self,
             connection_manager: DatabaseConnectionManager,
             pdf_service: PdfProcessingService,
             eto_service: EtoProcessingService):
```

**Notes**:
- `pdf_service` and `eto_service` are needed for cross-service orchestration
- These dependencies will also be updated to use dataclasses in their own redesigns

---

## Transaction Management Patterns

### Pattern 1: Single Repository Operation

**Use Case**: Most CRUD operations (get, update, delete single record)

**Implementation**: Repository auto-manages session and commit

```python
# Service
def get_config(self, config_id: int) -> Optional[EmailConfig]:
    return self.config_repository.get_by_id(config_id)

# Repository
def get_by_id(self, config_id: int) -> Optional[EmailConfig]:
    with self.connection_manager.session() as session:
        orm_model = session.query(EmailConfigORM).filter_by(id=config_id).first()
        if not orm_model:
            return None
        return self._to_dataclass(orm_model)
```

### Pattern 2: Multi-Repository Transaction

**Use Case**: Operations spanning multiple repositories or tables

**Implementation**: Service manages transaction, repositories accept session

```python
# Service
def complex_operation(self, data: ComplexData) -> Result:
    with self.connection_manager.transaction() as session:
        # Multiple repo calls in same transaction
        record1 = self.repo1.create(data.part1, session=session)
        record2 = self.repo2.create(data.part2, session=session)
        self.repo3.update(data.part3, session=session)
        return Result(record1, record2)

# Repository
def create(self, data: CreateData, session: Optional[Session] = None) -> Result:
    # Use provided session or create new one
    if session:
        return self._create_impl(data, session)
    else:
        with self.connection_manager.session() as new_session:
            return self._create_impl(data, new_session)
```

### Pattern 3: Error Handling and Rollback

**Use Case**: Any transactional operation that might fail

**Implementation**: Context manager auto-rolls back on exception

```python
# Service
def create_with_validation(self, data: CreateData) -> Result:
    try:
        with self.connection_manager.transaction() as session:
            # Validation that might fail
            if not self._validate_business_rules(data):
                raise ServiceError("Validation failed")

            # Create records
            result = self.repository.create(data, session=session)

            # If any exception occurs, transaction auto-rolls back
            return result

    except ObjectNotFoundError:
        # Re-raise repository errors to bubble to API
        raise
    except Exception as e:
        logger.error(f"Error creating record: {e}")
        raise ServiceError(f"Failed to create: {str(e)}")
```

### Pattern 4: Read-Only Queries

**Use Case**: Queries that don't modify data

**Implementation**: Can use auto-commit sessions (no explicit transaction needed)

```python
# Service
def list_configs(self) -> List[EmailConfig]:
    # Repository handles session
    return self.config_repository.get_all()

# Repository
def get_all(self) -> List[EmailConfig]:
    with self.connection_manager.session() as session:
        orm_models = session.query(EmailConfigORM).all()
        return [self._to_dataclass(m) for m in orm_models]
```

---

## Next Steps for Email Service

1. **Create Dataclasses** (`shared/types/`)
   - EmailConfig, EmailConfigCreate, EmailConfigUpdate
   - EmailFilterRule
   - Email, EmailCreate
   - EmailConfigSummary
   - (Discovery types may already exist in integration layer)
   - **IMPORTANT**: Must be in `shared/types/` to avoid circular imports

2. **Update Service** (`features/email_ingestion/service.py`)
   - Change method signatures to use dataclasses (import from `shared/types/`)
   - Keep integration types as-is (they're also dataclasses)

3. **Update Repositories**
   - EmailConfigRepository: Accept/return dataclasses
   - EmailRepository: Accept/return dataclasses
   - Add session parameter support for transactions
   - Create mapper methods (_to_dataclass, _from_dataclass)

4. **Create Mappers** (in router or separate mapper module)
   - Pydantic → dataclass mappers
   - dataclass → Pydantic mappers
   - One mapper function per endpoint

5. **Update Routers** (when we get to router implementation)
   - Use mappers to convert Pydantic ↔ dataclasses
   - Call service with dataclasses
   - Return Pydantic responses

---

## Other Services to Design

After completing the email service redesign, we'll apply the same pattern to:

1. **PDF Processing Service** (`features/pdf_processing/`)
   - PDF storage and object extraction
   - PDF querying and retrieval

2. **ETO Processing Service** (`features/eto_processing/`)
   - Template matching
   - Extraction and transformation
   - Pipeline execution
   - ETO run management

3. **Template Management Service** (`features/template_management/`)
   - Template creation and versioning
   - Signature object definition
   - Extraction field definition
   - Pipeline building

4. **Pipeline Service** (`features/pipeline_management/`)
   - Pipeline creation and editing
   - Pipeline compilation
   - Module catalog

5. **Module Service** (`features/module_catalog/`)
   - Module listing and discovery

Each service will follow the same architecture:
- Frozen dataclasses for internal data transfer
- Service orchestration with transaction support
- Repositories using dataclasses
- Explicit Pydantic ↔ dataclass mapping in routers
- ALL service methods return dataclasses (routers always map to Pydantic)
## Service 2: PDF Processing Service

### Current Implementation Status

**Location**: `server/src/features/pdf_processing/service.py`

**What Exists**:
- PDF storage with filesystem organization (date-based)
- Object extraction using pdfplumber (7 object types)
- SHA-256 hash-based deduplication
- File management utilities
- Object extraction utilities
- Basic PDF querying

**Extraction Architecture**:
- `pdf_extractor.py`: pdfplumber-based extraction (TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table)
- `file_storage.py`: Filesystem operations with date-based organization (`pdfs/YYYY/MM/hash_filename.pdf`)
- Synchronous extraction on every PDF storage

### Service Responsibilities

**1. Storage & Extraction**
- `store_pdf(file_content, original_filename, email_id)`: Main entry point for PDF storage → returns PdfFile (dataclass)
  - Validates PDF content
  - Calculates SHA-256 hash for deduplication
  - Checks for existing duplicate
  - Extracts all objects synchronously (7 types)
  - Stores file on disk with date-based path
  - Creates database record with extracted data
  - Links to email if provided

**2. Retrieval**
- `get_pdf(pdf_id)`: Get PDF metadata from DB → returns PdfFile (dataclass)
- `get_pdf_content(pdf_id)`: Read actual PDF bytes from disk → returns bytes
  - **NOTE**: Needs endpoint added to API design for frontend download
- `get_pdf_objects(pdf_id)`: Get typed PDF objects → returns List[PdfObject] (dataclass union)
  - Objects stored as JSON in DB, converted to typed dataclasses on retrieval

**3. Utilities**
- `check_duplicate(file_content)`: Pre-check for duplicates before storage → returns Optional[PdfFile] (dataclass)
- `is_healthy()`: Service health check → returns bool

### Key Design Decisions

**Object Extraction**:
- Extraction happens synchronously on every PDF storage (not async)
- 7 object types extracted: TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table
- Objects stored as JSON in `pdf_files.objects_json` column
- Repository converts JSON to typed dataclasses (List[PdfObject]) when retrieving
- Service layer works with typed dataclasses, not raw JSON

**File Storage**:
- Filesystem storage with configurable base path
- Date-based organization: `pdfs/YYYY/MM/hash_filename.pdf`
- Filename pattern: `{hash[:8]}_{sanitized_filename}.pdf`
- File path stored in DB as relative path
- PDFs never deleted (persistent historical record)

**Deduplication**:
- SHA-256 hash calculated from PDF bytes
- Duplicate check before storage (returns existing PdfFile if match found)
- Pre-check method available for upfront duplicate detection
- Hash stored in DB for quick lookups

**Error Handling**:
- Invalid PDF content: Validation error returned immediately
- Missing/corrupt file on disk: Repository error bubbles up
- Email ingestion errors: Design needed for visibility (currently just logged)

**Access Pattern**:
- PDFs always accessed by ID (from templates or ETO runs)
- No generic "list all PDFs" or query endpoints needed
- Frontend gets PDF ID from context, then fetches specific PDF

### Dataclasses Required

**Internal Types** (to be created in `shared/types/`):

**Core Types**:
- `PdfFile`: PDF metadata (id, original_filename, file_hash, file_path, email_id, page_count, object_count, created_at)
- `PdfFileCreate`: Data for creating PDF record

**PDF Object Types** (7 types, all frozen dataclasses):
- `TextWord`: text, x0, y0, x1, y1, fontname, fontsize
- `TextLine`: x0, y0, x1, y1 (bounding box only)
- `GraphicRect`: x0, y0, x1, y1, linewidth
- `GraphicLine`: x0, y0, x1, y1, linewidth
- `GraphicCurve`: points (list of tuples), linewidth
- `Image`: x0, y0, x1, y1, width, height, format, colorspace, bits
- `Table`: x0, y0, x1, y1, rows, cols

**Union Type**:
- `PdfObject = Union[TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table]`

**Extraction Result**:
- `PdfExtractionResult`: success, objects (List[PdfObject]), signature_hash, page_count, object_count, error_message

**Note**: All types must be in `shared/types/` to avoid circular imports.

### Mapping Strategy

**Router → Service** (Pydantic to dataclass):
```python
# In router
@router.post("/pdf-files")
def upload_pdf(file: UploadFile, email_id: Optional[int] = None) -> PdfFileResponse:
    # Read file bytes
    file_content = file.file.read()

    # Call service (gets dataclass back)
    pdf_file = pdf_service.store_pdf(
        file_content=file_content,
        original_filename=file.filename,
        email_id=email_id
    )

    # Map dataclass → Pydantic response
    return PdfFileResponse(
        id=pdf_file.id,
        original_filename=pdf_file.original_filename,
        file_hash=pdf_file.file_hash,
        page_count=pdf_file.page_count,
        object_count=pdf_file.object_count,
        created_at=pdf_file.created_at,
        # ... map all fields
    )
```

**Objects Retrieval** (dataclass conversion in repository):
```python
# In router
@router.get("/pdf-files/{pdf_id}/objects")
def get_pdf_objects(pdf_id: int) -> PdfObjectsResponse:
    # Call service (gets List[PdfObject] dataclass)
    objects = pdf_service.get_pdf_objects(pdf_id)

    # Map dataclass → Pydantic for response
    return PdfObjectsResponse(
        objects=[
            _map_pdf_object_to_pydantic(obj)
            for obj in objects
        ]
    )

def _map_pdf_object_to_pydantic(obj: PdfObject) -> PdfObjectResponse:
    # Type-specific mapping based on dataclass type
    if isinstance(obj, TextWord):
        return TextWordResponse(**obj.__dict__)
    elif isinstance(obj, GraphicRect):
        return GraphicRectResponse(**obj.__dict__)
    # ... etc
```

**Service → Repository** (dataclass to dataclass):
- Service calls repository with dataclasses
- Repository accepts dataclasses, returns dataclasses
- Repository handles JSON ↔ dataclass conversion for objects

**Repository → SQLAlchemy** (dataclass to ORM):
- Repository converts dataclasses to ORM models for persistence
- Repository converts ORM models back to dataclasses for return
- JSON serialization/deserialization handled in repository for objects

### Transaction Management

**Current Implementation**:
- Single repository operations (auto-managed sessions)
- No multi-repository transactions needed yet

**Pattern**:
```python
# Service
def store_pdf(self, file_content: bytes, original_filename: str, email_id: Optional[int] = None) -> PdfFile:
    # Validation (no DB)
    if not self._validate_pdf(file_content):
        raise ServiceError("Invalid PDF content")

    # Calculate hash
    file_hash = self._calculate_hash(file_content)

    # Check duplicate (single query)
    existing = self.pdf_repository.get_by_hash(file_hash)
    if existing:
        return existing

    # Extract objects (no DB)
    extraction_result = self.extractor.extract(file_content)

    # Store file (filesystem, no DB)
    file_path = self.file_storage.store(file_content, original_filename, file_hash)

    # Create DB record (single transaction)
    pdf_data = PdfFileCreate(
        original_filename=original_filename,
        file_hash=file_hash,
        file_path=file_path,
        email_id=email_id,
        objects=extraction_result.objects,
        page_count=extraction_result.page_count,
        object_count=extraction_result.object_count
    )
    return self.pdf_repository.create(pdf_data)
```

### Integration with API Layer

**Endpoints → Service Methods**:

| Endpoint | Service Method | Service Returns | Router Maps To | Notes |
|----------|----------------|-----------------|----------------|-------|
| `POST /pdf-files` | `store_pdf()` | `PdfFile` | `PdfFileResponse` | Upload & extract |
| `GET /pdf-files/{id}` | `get_pdf()` | `PdfFile` | `PdfFileResponse` | Metadata only |
| `GET /pdf-files/{id}/objects` | `get_pdf_objects()` | `List[PdfObject]` | `PdfObjectsResponse` | Typed objects |
| **Missing** | `get_pdf_content()` | `bytes` | `FileResponse` | **Needs endpoint for download** |

**Key Point**: ALL service methods return dataclasses (or primitives like bytes/bool). Routers ALWAYS map these to Pydantic for HTTP responses.

### What Needs to Change

**Current State**:
- Service uses Pydantic models from `shared/types` throughout
- Repository accepts/returns Pydantic models
- Objects stored as raw JSON, no typing on retrieval
- No explicit mapper layer

**Required Changes**:

1. **Create Dataclasses** (frozen dataclasses in `server/src/shared/types/`):
   - PdfFile, PdfFileCreate
   - 7 PDF object types (TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table)
   - PdfObject union type
   - PdfExtractionResult
   - **IMPORTANT**: Types must be in `shared/types/` to avoid circular imports

2. **Update Service**:
   - Update method signatures to accept/return dataclasses instead of Pydantic
   - Return typed List[PdfObject] from get_pdf_objects() instead of raw JSON
   - Internal processing uses dataclasses

3. **Update Repository**:
   - Accept dataclasses instead of Pydantic
   - Return dataclasses instead of Pydantic
   - Convert dataclasses ↔ SQLAlchemy ORM models
   - Add JSON ↔ dataclass conversion for objects field
   - Implement `_objects_to_json()` and `_json_to_objects()` helper methods

4. **Create Mappers** (in router file or separate mapper module):
   - Pydantic Request → dataclass (for service calls)
   - dataclass → Pydantic Response (for API responses)
   - Type-specific mapping for PDF object union types
   - Every endpoint needs explicit mapping

5. **Add Missing Endpoint**:
   - `GET /pdf-files/{id}/download` or similar for PDF bytes download
   - Update API_ENDPOINTS.md to include this endpoint
   - Update SCHEMAS.md with FileResponse pattern

### Example Service Method Signature Changes

**Before** (current):
```python
def store_pdf(self, file_content: bytes, original_filename: str, email_id: Optional[int] = None) -> PdfFile:
    # returns Pydantic PdfFile
```

**After** (with dataclasses):
```python
def store_pdf(self, file_content: bytes, original_filename: str, email_id: Optional[int] = None) -> PdfFile:
    # returns frozen dataclass PdfFile
    # (same signature, different underlying type)
```

**New Method Signature** (objects retrieval):
```python
def get_pdf_objects(self, pdf_id: int) -> List[PdfObject]:
    # returns List of typed dataclass objects (union type)
    # Repository converts JSON → typed dataclasses
```

### Dependencies

**Service Constructor**:
```python
def __init__(self,
             connection_manager: DatabaseConnectionManager,
             pdf_repository: PdfFileRepository,
             extractor: PdfExtractor,
             file_storage: FileStorage):
```

**Notes**:
- `extractor` and `file_storage` are utility classes (no DB dependencies)
- Service is called by EmailIngestionService to store PDFs from email attachments
- Service will be called by TemplateManagementService for PDF object retrieval

---
## Service 3: ETO Processing Service

### Current Implementation Status

**Location**: `server/src/features/eto_processing/service.py`

**What Exists**:
- Complete background worker implementation with async processing loop
- Worker lifecycle management (start, stop, pause, resume)
- Batch processing with configurable concurrency
- Sequential pipeline execution (template matching → extraction → transformation)
- Template matching with signature-based algorithm
- Data extraction using bounding boxes from template definitions
- Pipeline execution integration (delegates to Pipeline Service)
- Status management with separate status and processing_step tracking
- User-facing operations (process_pdf, reprocess, skip, delete)
- Startup recovery for pending runs
- Comprehensive error handling with typed errors

**Background Worker Architecture**:
- Async processing loop runs in separate thread
- Processes runs with `status = not_started` in batches
- Configurable batch size and max concurrent runs
- Sequential step execution: template_matching → data_extraction → data_transformation
- Status validation before each step
- Three side tables for intermediate results (matching, extraction, pipeline_execution)

### Service Responsibilities

**1. Run Lifecycle Management**
- `process_pdf(pdf_id, source)`: Create new ETO run for PDF → returns EtoRun (dataclass)
  - Creates run with `status = not_started`
  - Source can be "user_upload" or "email_ingestion"
  - Background worker picks up automatically
- `get_run(run_id)`: Retrieve single run with full details → returns EtoRun (dataclass)
- `list_runs(filters, pagination)`: Query runs with filters → returns List[EtoRun] (dataclass)
- `reprocess_run(run_id)`: Reset run to not_started for reprocessing → returns EtoRun (dataclass)
- `skip_run(run_id)`: Mark run as skipped (user decision) → returns EtoRun (dataclass)
- `delete_run(run_id)`: Delete run and all side table data → returns bool

**2. Background Worker Management**
- `start_worker()`: Start background processing thread → returns bool
- `stop_worker()`: Stop background worker gracefully → returns bool
- `pause_worker()`: Pause worker (stop processing new runs) → returns bool
- `resume_worker()`: Resume paused worker → returns bool
- `get_worker_status()`: Get worker state and statistics → returns WorkerStatus (dataclass)

**3. Processing Pipeline** (internal methods called by worker)
- `_process_single_run_async(run)`: Orchestrates full pipeline for one run
  - Updates status to "processing"
  - Calls template matching
  - Calls extraction
  - Calls pipeline execution
  - Updates final status (success/failure/needs_template)
  - Saves partial results even on failure
- `_step_template_matching(run)`: Match PDF to template → creates EtoRunTemplateMatching record
  - Gets PDF objects from PdfService
  - Gets all active templates from TemplateService
  - Compares signature objects (template signature ⊆ PDF objects)
  - Best match: Most matching objects, tiebreaker prefers text over images
  - If no match: run status = "needs_template"
  - If match found: creates template_matching record with matched_template_version_id
- `_step_extraction(run, template_version_id)`: Extract data using template → creates EtoRunExtraction record
  - Gets extraction field definitions from template version
  - Gets PDF objects for bounding box lookup
  - Pulls text within each field's bounding box (no regex validation)
  - Stores extracted_data as JSON (field_name → value mapping)
- `_step_pipeline_execution(run, template_version_id, extracted_data)`: Execute pipeline → creates EtoRunPipelineExecution record
  - Gets pipeline_definition_id from template version
  - Calls PipelineService.execute_pipeline(pipeline_id, extracted_data)
  - PipelineService executes action modules (create orders, send notifications, etc.)
  - Stores executed_actions summary and individual step results

**4. Error Handling**
- `_handle_centralized_processing_error(run, error, step)`: Centralized error handler
  - Determines error type (template_matching_error, extraction_error, pipeline_error, system_error)
  - Sets run status to "failure"
  - Stores error_type, error_message, error_details in run record
  - Saves partial results to side tables
  - Logs detailed error information
- `_validate_status_for_step(run, expected_status)`: Status validation before each step

**5. Service Lifecycle**
- `startup_recovery()`: Resume processing on server startup
  - Finds runs with `status = processing` (interrupted by shutdown)
  - Resets them to `not_started` for retry
- `shutdown()`: Graceful shutdown
  - Stops worker
  - Allows current runs to complete
  - Does NOT change run statuses (preserved for recovery)
- `is_healthy()`: Health check → returns bool
  - Checks worker status
  - Verifies PDF service availability
  - Verifies Template service availability

### Key Design Decisions

**Template Matching Algorithm**:
- **Signature-based matching**: Template's signature objects must be complete subset of PDF objects
- **Subset comparison**: Every signature object in template must have matching object in PDF
  - Text objects: Match on text content, position (within tolerance), font properties
  - Image objects: Match on position, size (within tolerance)
- **Best match selection**:
  1. Count matching objects for each active template
  2. Template with most matches wins
  3. Tiebreaker: Prefer templates with more text objects over image objects
- **No match handling**: If no template has complete signature match, run status = "needs_template"

**Status Flow**:
```
not_started → processing → success
                        → failure
                        → needs_template

skipped (user action, terminal state)
```

**Processing Step Tracking** (separate from status):
- `processing_step` field: template_matching | data_extraction | data_transformation | null
- Updated during processing to show which step is currently executing
- Independent of status (status = "processing" while step changes)
- Preserved on failure for debugging (shows where it failed)

**Side Table Pattern**:
- Three tables store intermediate results: eto_run_template_matchings, eto_run_extractions, eto_run_pipeline_executions
- Each has own status (processing, success, failure)
- Results saved even if overall run fails (partial data for debugging)
- Side tables cascade delete with main run (foreign key constraint)

**Pipeline Execution Integration**:
- ETO service delegates to Pipeline Service for execution
- Pipeline Service returns execution results (synchronous within ETO process)
- Action modules execute fully during normal runs
- Action modules simulate (no execution) during template wizard testing
- Execution results stored in side table with step-by-step details

**Extraction Process**:
- Uses bounding boxes from template extraction_fields
- For each field: Find all text objects within bounding box, concatenate text
- NO regex validation during extraction (just pull raw text)
- Validation happens later in pipeline if needed (via validation modules)
- Extracted data stored as JSON: `{"field_name": "extracted_value", ...}`

**No Cancellation**:
- Runs cannot be cancelled mid-execution
- User can skip runs before processing starts (status = not_started → skipped)
- Once processing begins, must complete or fail

**Error Handling Strategy**:
- Typed errors with detailed messages
- Error types: template_matching_error, extraction_error, pipeline_error, system_error
- Partial results always saved to side tables
- Error details stored in main run record for visibility
- Errors bubble up to API for user-uploaded PDFs
- Email ingestion errors logged (visibility mechanism TBD)

**Background Worker Behavior**:
- Queries for runs with `status = not_started` on each iteration
- Processes in batches (configurable batch size)
- Concurrent execution within batch (configurable max concurrent)
- Worker pauses between batches (configurable interval)
- Graceful shutdown: Completes current runs, then stops

### Dataclasses Required

**Internal Types** (to be created in `shared/types/`):

**Core Types**:
- `EtoRun`: Run data (id, pdf_file_id, status, processing_step, error_type, error_message, error_details, started_at, completed_at, created_at)
- `EtoRunCreate`: Data for creating run (pdf_file_id, source)
- `EtoRunStatus`: Enum dataclass (not_started, processing, success, failure, needs_template, skipped)
- `EtoRunProcessingStep`: Enum dataclass (template_matching, data_extraction, data_transformation)

**Side Table Types**:
- `EtoRunTemplateMatching`: Template matching result (id, eto_run_id, status, matched_template_version_id, started_at, completed_at)
- `EtoRunExtraction`: Extraction result (id, eto_run_id, status, extracted_data, started_at, completed_at)
- `EtoRunPipelineExecution`: Pipeline execution result (id, eto_run_id, status, executed_actions, started_at, completed_at)
- `EtoRunPipelineExecutionStep`: Individual step result (id, run_id, module_instance_id, step_number, inputs, outputs, error)
- `EtoStepStatus`: Enum dataclass (processing, success, failure)

**Worker Types**:
- `WorkerStatus`: Worker state (is_running, is_paused, runs_processed, runs_pending, current_batch_size, last_error)

**Response Types**:
- `EtoRunSummary`: Summary view for list endpoint (id, pdf_file_id, status, processing_step, created_at, completed_at)
- `EtoRunDetail`: Full detail view including side table data

**Error Types**:
- `ProcessingError`: Error information (type, message, details, step)

**Note**: All types must be in `shared/types/` to avoid circular imports.

### Mapping Strategy

**Router → Service** (Pydantic to dataclass):
```python
# In router
@router.post("/eto-runs")
def create_eto_run(request: CreateEtoRunRequest) -> EtoRunResponse:
    # Call service (gets dataclass back)
    run = eto_service.process_pdf(
        pdf_id=request.pdf_file_id,
        source="user_upload"
    )

    # Map dataclass → Pydantic response
    return EtoRunResponse(
        id=run.id,
        pdf_file_id=run.pdf_file_id,
        status=run.status,
        processing_step=run.processing_step,
        # ... map all fields
    )
```

**List Endpoint with Filters**:
```python
@router.get("/eto-runs")
def list_eto_runs(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> EtoRunListResponse:
    # Build filters dataclass
    filters = EtoRunFilters(
        status=EtoRunStatus(status) if status else None,
        skip=skip,
        limit=limit
    )

    # Call service (gets List[dataclass])
    runs = eto_service.list_runs(filters)

    # Map dataclass → Pydantic for response
    return EtoRunListResponse(
        runs=[
            EtoRunSummaryResponse(
                id=run.id,
                pdf_file_id=run.pdf_file_id,
                status=run.status.value,
                # ... map all fields
            )
            for run in runs
        ]
    )
```

**Detail Endpoint with Side Table Data**:
```python
@router.get("/eto-runs/{run_id}")
def get_eto_run_detail(run_id: int) -> EtoRunDetailResponse:
    # Call service (gets dataclass with full details)
    run_detail = eto_service.get_run(run_id)

    # Map dataclass → Pydantic response
    return EtoRunDetailResponse(
        id=run_detail.id,
        pdf_file_id=run_detail.pdf_file_id,
        status=run_detail.status.value,
        template_matching=_map_template_matching(run_detail.template_matching) if run_detail.template_matching else None,
        extraction=_map_extraction(run_detail.extraction) if run_detail.extraction else None,
        pipeline_execution=_map_pipeline_execution(run_detail.pipeline_execution) if run_detail.pipeline_execution else None,
        # ... map all fields
    )
```

**Service → Repository** (dataclass to dataclass):
- Service calls repository with dataclasses
- Repository accepts dataclasses, returns dataclasses
- Repository handles JSON ↔ dataclass conversion for extracted_data, executed_actions

**Repository → SQLAlchemy** (dataclass to ORM):
- Repository converts dataclasses to ORM models for persistence
- Repository converts ORM models back to dataclasses for return
- JSON serialization/deserialization handled in repository

### Transaction Management

**Current Implementation**:
- Single repository operations for most methods
- Multi-table inserts for pipeline results (parent + steps)

**Required Patterns**:

**Pattern 1: Create Run** (single repo):
```python
# Service
def process_pdf(self, pdf_id: int, source: str) -> EtoRun:
    # Validate PDF exists (read-only query)
    pdf = self.pdf_service.get_pdf(pdf_id)
    if not pdf:
        raise ServiceError(f"PDF {pdf_id} not found")

    # Create run (single transaction)
    run_data = EtoRunCreate(
        pdf_file_id=pdf_id,
        source=source,
        status=EtoRunStatus.NOT_STARTED
    )
    return self.run_repository.create(run_data)
```

**Pattern 2: Update Run with Side Table** (multi-repo transaction):
```python
# Service (internal method)
def _step_template_matching(self, run: EtoRun) -> Optional[int]:
    with self.connection_manager.transaction() as session:
        # Update run status and processing_step
        self.run_repository.update_status(
            run.id,
            status=EtoRunStatus.PROCESSING,
            processing_step=EtoRunProcessingStep.TEMPLATE_MATCHING,
            session=session
        )

        # Perform matching logic (no DB)
        matched_version_id = self._find_best_template_match(run.pdf_file_id)

        # Create matching record
        matching_data = EtoRunTemplateMatchingCreate(
            eto_run_id=run.id,
            status=EtoStepStatus.SUCCESS if matched_version_id else EtoStepStatus.FAILURE,
            matched_template_version_id=matched_version_id,
            started_at=run.started_at,
            completed_at=datetime.utcnow()
        )
        self.matching_repository.create(matching_data, session=session)

        return matched_version_id
```

**Pattern 3: Error Handling with Partial Save**:
```python
# Service (internal method)
def _step_extraction(self, run: EtoRun, template_version_id: int) -> Dict[str, Any]:
    try:
        with self.connection_manager.transaction() as session:
            # Update run processing_step
            self.run_repository.update_processing_step(
                run.id,
                processing_step=EtoRunProcessingStep.DATA_EXTRACTION,
                session=session
            )

            # Perform extraction (no DB)
            extracted_data = self._extract_data(run.pdf_file_id, template_version_id)

            # Save extraction result
            extraction_data = EtoRunExtractionCreate(
                eto_run_id=run.id,
                status=EtoStepStatus.SUCCESS,
                extracted_data=extracted_data,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            self.extraction_repository.create(extraction_data, session=session)

            return extracted_data

    except Exception as e:
        # Save partial result with error status
        with self.connection_manager.transaction() as session:
            extraction_data = EtoRunExtractionCreate(
                eto_run_id=run.id,
                status=EtoStepStatus.FAILURE,
                extracted_data=None,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            self.extraction_repository.create(extraction_data, session=session)
        raise
```

### Integration with API Layer

**Endpoints → Service Methods**:

| Endpoint | Service Method | Service Returns | Router Maps To | Notes |
|----------|----------------|-----------------|----------------|-------|
| `POST /eto-runs` | `process_pdf()` | `EtoRun` | `EtoRunResponse` | Create new run |
| `GET /eto-runs` | `list_runs()` | `List[EtoRun]` | `EtoRunListResponse` | Query with filters |
| `GET /eto-runs/{id}` | `get_run()` | `EtoRunDetail` | `EtoRunDetailResponse` | Full details + side tables |
| `POST /eto-runs/{id}/reprocess` | `reprocess_run()` | `EtoRun` | `EtoRunResponse` | Reset for retry |
| `POST /eto-runs/{id}/skip` | `skip_run()` | `EtoRun` | `EtoRunResponse` | Mark as skipped |
| `DELETE /eto-runs/{id}` | `delete_run()` | `bool` | `SuccessResponse` | Delete run |

**Key Point**: ALL service methods return dataclasses (or primitives like bool). Routers ALWAYS map these to Pydantic for HTTP responses.

### What Needs to Change

**Current State**:
- Service uses Pydantic models from `shared/types` throughout
- Repositories accept/return Pydantic models
- Side table data stored as raw JSON, no typing on retrieval
- No explicit mapper layer

**Required Changes**:

1. **Create Dataclasses** (frozen dataclasses in `server/src/shared/types/`):
   - EtoRun, EtoRunCreate, EtoRunUpdate
   - EtoRunStatus, EtoRunProcessingStep (enums)
   - EtoRunTemplateMatching, EtoRunExtraction, EtoRunPipelineExecution (side table types)
   - EtoRunPipelineExecutionStep
   - EtoStepStatus (enum)
   - WorkerStatus, EtoRunSummary, EtoRunDetail, ProcessingError
   - **IMPORTANT**: Types must be in `shared/types/` to avoid circular imports

2. **Update Service**:
   - Update method signatures to accept/return dataclasses instead of Pydantic
   - Return typed side table dataclasses from get_run() instead of raw JSON
   - Internal processing uses dataclasses

3. **Update Repositories**:
   - Accept dataclasses instead of Pydantic
   - Return dataclasses instead of Pydantic
   - Convert dataclasses ↔ SQLAlchemy ORM models
   - Add JSON ↔ dataclass conversion for extracted_data, executed_actions fields
   - Implement `_to_dataclass()` and `_from_dataclass()` helper methods

4. **Create Mappers** (in router file or separate mapper module):
   - Pydantic Request → dataclass (for service calls)
   - dataclass → Pydantic Response (for API responses)
   - Side table data mapping (nested structures)
   - Every endpoint needs explicit mapping

5. **Update Background Worker**:
   - Worker already uses internal types correctly
   - Just needs to use new dataclasses instead of Pydantic

### Example Service Method Signature Changes

**Before** (current):
```python
def process_pdf(self, pdf_id: int, source: str) -> EtoRun:
    # returns Pydantic EtoRun
```

**After** (with dataclasses):
```python
def process_pdf(self, pdf_id: int, source: str) -> EtoRun:
    # returns frozen dataclass EtoRun
    # (same signature, different underlying type)
```

**New Method Signature** (full detail retrieval):
```python
def get_run(self, run_id: int) -> EtoRunDetail:
    # returns dataclass with nested side table dataclasses
    # Repository converts JSON → typed dataclasses for side tables
```

### Dependencies

**Service Constructor**:
```python
def __init__(self,
             connection_manager: DatabaseConnectionManager,
             pdf_service: PdfProcessingService,
             template_service: TemplateManagementService,
             pipeline_service: PipelineService):
```

**Notes**:
- `pdf_service`: Get PDF objects for template matching and extraction
- `template_service`: Get active templates, get template version details (signature objects, extraction fields, pipeline_id)
- `pipeline_service`: Execute pipelines with extracted data
- All dependencies will be updated to use dataclasses in their own redesigns

### Background Worker Details

**Worker Thread Architecture**:
```python
class BackgroundWorker:
    def __init__(self, eto_service, batch_size=10, max_concurrent=5, poll_interval=5):
        self.eto_service = eto_service
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.is_running = False
        self.is_paused = False
        self.thread = None

    def _worker_loop(self):
        while self.is_running:
            if not self.is_paused:
                # Get pending runs
                pending_runs = self.eto_service.run_repository.get_pending_runs(limit=self.batch_size)

                if pending_runs:
                    # Process batch concurrently
                    with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                        futures = [
                            executor.submit(self.eto_service._process_single_run_async, run)
                            for run in pending_runs
                        ]
                        # Wait for batch to complete
                        for future in futures:
                            future.result()

            # Pause between batches
            time.sleep(self.poll_interval)
```

**Worker Management**:
- Worker starts on service startup (or explicit start_worker() call)
- Worker runs in separate daemon thread
- Worker can be paused (stops processing new runs, current runs complete)
- Worker can be resumed (continues processing)
- Worker stops gracefully on shutdown (completes current runs)

---
## Service 4: Template Management Service

### Current Implementation Status

**Location**: `server/src/features/template_management/service.py` (to be created/refactored)

**What Exists**:
- Template CRUD operations
- Version management
- Basic template querying
- Integration with PDF and Pipeline services

**Key Architecture**:
- Stateless wizard workflow (no draft versions in DB during creation)
- Atomic template creation (creates template + version 1 in single transaction)
- Version history tracking (all versions preserved)
- Pipeline integration (delegates to Pipeline Service)

### Service Responsibilities

**1. Template CRUD Operations**
- `create_template(template_data)`: Create new template with version 1 → returns PdfTemplate (dataclass)
  - Validates source PDF exists
  - Validates wizard data (signature objects, extraction fields, pipeline)
  - Calls Pipeline Service to create/compile pipeline
  - Creates template record with `status = "draft"`
  - Creates version 1 record atomically
  - Sets current_version_id to version 1
- `get_template(template_id)`: Retrieve single template → returns PdfTemplate (dataclass)
- `list_templates(filters)`: Query templates with filters → returns List[PdfTemplate] (dataclass)
  - Filters: status (active/inactive/draft), source_pdf_id, name search
  - Default: Return all statuses
- `update_template_metadata(template_id, metadata)`: Update name/description only → returns PdfTemplate (dataclass)
  - Updates template record (name, description)
  - Does NOT create new version
- `update_template_definition(template_id, definition_data)`: Create new version → returns PdfTemplate (dataclass)
  - Creates new version with incremented version_num
  - Calls Pipeline Service to create/compile new pipeline
  - Updates current_version_id to new version
- `delete_template(template_id)`: Delete draft template only → returns bool
  - Validates template is draft status
  - Cascade deletes all versions and pipelines
  - Throws error if not draft

**2. Template Activation**
- `activate_template(template_id)`: Activate template for matching → returns PdfTemplate (dataclass)
  - Changes status from "draft" or "inactive" to "active"
  - Validates template has at least one version
  - Once activated from draft, never returns to draft
- `deactivate_template(template_id)`: Deactivate template → returns PdfTemplate (dataclass)
  - Changes status from "active" to "inactive"
  - Template matching will ignore inactive templates
  - Can be reactivated later

**3. Version Management**
- `get_template_version(template_id, version_id)`: Get specific version data → returns PdfTemplateVersion (dataclass)
  - Returns version with all details (signature objects, extraction fields, pipeline)
  - Used for viewing version history or loading into template builder for editing
- `list_template_versions(template_id)`: Get all versions for template → returns List[PdfTemplateVersion] (dataclass)
  - Returns ALL versions (including current)
  - Ordered by version_num descending (newest first)
  - Used for version history viewer
- `set_current_version(template_id, version_id)`: Set which version is active → returns PdfTemplate (dataclass)
  - Updates current_version_id
  - Used when user wants to revert to previous version

**4. Wizard Simulation**
- `simulate_template(simulation_data)`: Test template without persistence → returns TemplateSimulationResult (dataclass)
  - Receives: pdf_file_id, signature_objects, extraction_fields, pipeline_definition
  - Gets PDF objects from PDF Service
  - Performs extraction using provided extraction fields
  - Calls Pipeline Service to execute pipeline in simulation mode (actions don't execute)
  - Returns: extracted_data, pipeline_execution_results, any errors
  - Pure computation, no side effects, no DB writes
  - Can be called repeatedly during wizard

**5. Template Discovery** (for ETO matching)
- `get_active_templates()`: Get all active templates → returns List[PdfTemplate] (dataclass)
  - Used by ETO Service for template matching
  - Returns only templates with status = "active"
  - Includes current version data (signature objects)
- `get_template_for_matching(template_id)`: Get template with current version details → returns PdfTemplateWithVersion (dataclass)
  - Returns template + current version (signature objects, extraction fields, pipeline_id)
  - Used by ETO Service during matching/extraction/transformation

**6. Service Lifecycle**
- `is_healthy()`: Health check → returns bool
  - Verifies PDF service availability
  - Verifies Pipeline service availability

### Key Design Decisions

**Stateless Wizard**:
- Frontend maintains all wizard state (signature objects, extraction fields, pipeline)
- No draft versions stored in DB during creation/editing
- Only finalized templates (with version 1+) are persisted
- Simulation endpoint allows testing without DB writes

**Template vs Version Updates**:
- **Metadata updates**: Update template record only (name, description) - no new version
- **Definition updates**: Create new version (signature objects, extraction fields, pipeline) - increment version_num
- Frontend determines which type of update based on what user changed
- Router calls appropriate service method

**Version Lifecycle**:
- All templates start with version 1 (created atomically with template)
- Versions never deleted (historical reference for ETO runs)
- current_version_id points to active version used for matching
- Users can view any version and create new version based on old version
- Users can set current_version_id to previous version (revert)

**Template Status Flow**:
```
draft → active (one-way, never returns to draft)
     → deleted (only if draft)

active ↔ inactive (can toggle)
```

**Deletion Rules**:
- Only draft templates can be deleted
- Active/inactive templates cannot be deleted (referenced by ETO runs)
- Deletion cascades to all versions and associated pipelines
- Source PDF is NOT deleted (kept for reference, even if template deleted)

**Pipeline Integration**:
- Template Service calls Pipeline Service to create/compile pipelines
- Pipeline creation happens during template creation and definition updates
- Pipeline Service handles deduplication (shared pipelines across templates)
- Template Service stores pipeline_definition_id in version record

**Simulation Process**:
- Receives raw wizard data (not yet persisted)
- Converts to typed dataclasses internally
- Performs same steps as real ETO run:
  1. Get PDF objects
  2. Extract data using extraction fields
  3. Execute pipeline in simulation mode (actions simulate, no actual execution)
- Returns results for frontend preview
- No persistence (no template/version/pipeline records created)

**Source PDF Reference**:
- source_pdf_id always required for template creation
- PDF kept indefinitely (never deleted, even if template deleted)
- If PDF somehow deleted, template matching/extraction still works (uses cached objects)
- Template viewing may show error if PDF missing

### Dataclasses Required

**Internal Types** (to be created in `shared/types/`):

**Core Types**:
- `PdfTemplate`: Template data (id, name, description, source_pdf_id, status, current_version_id, created_at)
- `PdfTemplateCreate`: Data for creating template (name, description, source_pdf_id, signature_objects, extraction_fields, pipeline_definition)
- `PdfTemplateStatus`: Enum (draft, active, inactive)
- `PdfTemplateMetadataUpdate`: Data for updating metadata (name, description)
- `PdfTemplateDefinitionUpdate`: Data for creating new version (signature_objects, extraction_fields, pipeline_definition)

**Version Types**:
- `PdfTemplateVersion`: Version data (id, pdf_template_id, version_num, signature_objects, extraction_fields, pipeline_definition_id, usage_count, last_used_at, created_at)
- `PdfTemplateVersionCreate`: Data for creating version
- `PdfTemplateWithVersion`: Template + current version details (for ETO matching)

**Wizard Types**:
- `SignatureObject`: Signature object definition (object_type, coordinates, properties)
- `ExtractionField`: Extraction field definition (field_name, bounding_box, required, validation_regex)
- `PipelineDefinition`: Pipeline structure (nodes, edges, visual_state) - passed to Pipeline Service

**Simulation Types**:
- `TemplateSimulationRequest`: Simulation input (pdf_file_id, signature_objects, extraction_fields, pipeline_definition)
- `TemplateSimulationResult`: Simulation output (extracted_data, pipeline_execution_results, errors)

**Response Types**:
- `PdfTemplateSummary`: Summary view for list endpoint
- `PdfTemplateDetail`: Full detail view with current version

**Filter Types**:
- `TemplateFilters`: Query filters (status, source_pdf_id, name_search, skip, limit)

**Note**: All types must be in `shared/types/` to avoid circular imports.

### Mapping Strategy

**Router → Service** (Pydantic to dataclass):
```python
# In router
@router.post("/pdf-templates")
def create_template(request: CreateTemplateRequest) -> TemplateResponse:
    # Map Pydantic → dataclass
    template_data = PdfTemplateCreate(
        name=request.name,
        description=request.description,
        source_pdf_id=request.source_pdf_id,
        signature_objects=[
            SignatureObject(**obj.dict()) for obj in request.signature_objects
        ],
        extraction_fields=[
            ExtractionField(**field.dict()) for field in request.extraction_fields
        ],
        pipeline_definition=PipelineDefinition(**request.pipeline_definition.dict())
    )

    # Call service (gets dataclass back)
    template = template_service.create_template(template_data)

    # Map dataclass → Pydantic response
    return TemplateResponse(
        id=template.id,
        name=template.name,
        status=template.status.value,
        current_version_id=template.current_version_id,
        # ... map all fields
    )
```

**Metadata vs Definition Updates**:
```python
# Metadata update (no new version)
@router.patch("/pdf-templates/{template_id}/metadata")
def update_template_metadata(template_id: int, request: UpdateMetadataRequest) -> TemplateResponse:
    metadata = PdfTemplateMetadataUpdate(
        name=request.name,
        description=request.description
    )
    template = template_service.update_template_metadata(template_id, metadata)
    return _map_template_to_response(template)

# Definition update (new version)
@router.put("/pdf-templates/{template_id}")
def update_template_definition(template_id: int, request: UpdateDefinitionRequest) -> TemplateResponse:
    definition = PdfTemplateDefinitionUpdate(
        signature_objects=[SignatureObject(**obj.dict()) for obj in request.signature_objects],
        extraction_fields=[ExtractionField(**field.dict()) for field in request.extraction_fields],
        pipeline_definition=PipelineDefinition(**request.pipeline_definition.dict())
    )
    template = template_service.update_template_definition(template_id, definition)
    return _map_template_to_response(template)
```

**Simulation Endpoint**:
```python
@router.post("/pdf-templates/simulate")
def simulate_template(request: SimulateTemplateRequest) -> SimulationResultResponse:
    # Map Pydantic → dataclass
    simulation_data = TemplateSimulationRequest(
        pdf_file_id=request.pdf_file_id,
        signature_objects=[SignatureObject(**obj.dict()) for obj in request.signature_objects],
        extraction_fields=[ExtractionField(**field.dict()) for field in request.extraction_fields],
        pipeline_definition=PipelineDefinition(**request.pipeline_definition.dict())
    )

    # Call service (gets dataclass back)
    result = template_service.simulate_template(simulation_data)

    # Map dataclass → Pydantic response
    return SimulationResultResponse(
        extracted_data=result.extracted_data,
        pipeline_results=result.pipeline_execution_results,
        errors=result.errors
    )
```

**Service → Repository** (dataclass to dataclass):
- Service calls repository with dataclasses
- Repository accepts dataclasses, returns dataclasses
- Repository handles JSON ↔ dataclass conversion for signature_objects, extraction_fields

**Repository → SQLAlchemy** (dataclass to ORM):
- Repository converts dataclasses to ORM models for persistence
- Repository converts ORM models back to dataclasses for return
- JSON serialization/deserialization handled in repository

### Transaction Management

**Required Patterns**:

**Pattern 1: Atomic Template Creation** (multi-repo transaction):
```python
# Service
def create_template(self, template_data: PdfTemplateCreate) -> PdfTemplate:
    # Validate source PDF exists (read-only)
    pdf = self.pdf_service.get_pdf(template_data.source_pdf_id)
    if not pdf:
        raise ServiceError(f"PDF {template_data.source_pdf_id} not found")

    with self.connection_manager.transaction() as session:
        # Create pipeline via Pipeline Service (may create new or return existing if duplicate)
        pipeline_id = self.pipeline_service.create_pipeline(
            template_data.pipeline_definition,
            session=session
        )

        # Create template record
        template = self.template_repository.create(
            PdfTemplateCreate(
                name=template_data.name,
                description=template_data.description,
                source_pdf_id=template_data.source_pdf_id,
                status=PdfTemplateStatus.DRAFT
            ),
            session=session
        )

        # Create version 1 record
        version = self.version_repository.create(
            PdfTemplateVersionCreate(
                pdf_template_id=template.id,
                version_num=1,
                signature_objects=template_data.signature_objects,
                extraction_fields=template_data.extraction_fields,
                pipeline_definition_id=pipeline_id
            ),
            session=session
        )

        # Update template's current_version_id
        template = self.template_repository.update_current_version(
            template.id,
            version.id,
            session=session
        )

        return template
```

**Pattern 2: Definition Update with New Version** (multi-repo transaction):
```python
# Service
def update_template_definition(self, template_id: int, definition_data: PdfTemplateDefinitionUpdate) -> PdfTemplate:
    # Get current template to validate exists
    template = self.template_repository.get_by_id(template_id)
    if not template:
        raise ServiceError(f"Template {template_id} not found")

    with self.connection_manager.transaction() as session:
        # Get current max version number
        max_version = self.version_repository.get_max_version_num(template_id, session=session)

        # Create pipeline via Pipeline Service
        pipeline_id = self.pipeline_service.create_pipeline(
            definition_data.pipeline_definition,
            session=session
        )

        # Create new version
        new_version = self.version_repository.create(
            PdfTemplateVersionCreate(
                pdf_template_id=template_id,
                version_num=max_version + 1,
                signature_objects=definition_data.signature_objects,
                extraction_fields=definition_data.extraction_fields,
                pipeline_definition_id=pipeline_id
            ),
            session=session
        )

        # Update template's current_version_id
        template = self.template_repository.update_current_version(
            template_id,
            new_version.id,
            session=session
        )

        return template
```

**Pattern 3: Simulation (no transaction, read-only + computation)**:
```python
# Service
def simulate_template(self, simulation_data: TemplateSimulationRequest) -> TemplateSimulationResult:
    try:
        # Get PDF objects (read-only)
        pdf_objects = self.pdf_service.get_pdf_objects(simulation_data.pdf_file_id)

        # Perform extraction (computation only, no DB)
        extracted_data = self._extract_data(
            pdf_objects,
            simulation_data.extraction_fields
        )

        # Execute pipeline in simulation mode (no DB writes, actions simulate)
        pipeline_results = self.pipeline_service.execute_pipeline_simulation(
            simulation_data.pipeline_definition,
            extracted_data
        )

        return TemplateSimulationResult(
            extracted_data=extracted_data,
            pipeline_execution_results=pipeline_results,
            errors=None
        )

    except Exception as e:
        return TemplateSimulationResult(
            extracted_data=None,
            pipeline_execution_results=None,
            errors=[str(e)]
        )
```

### Integration with API Layer

**Endpoints → Service Methods**:

| Endpoint | Service Method | Service Returns | Router Maps To | Notes |
|----------|----------------|-----------------|----------------|-------|
| `POST /pdf-templates` | `create_template()` | `PdfTemplate` | `TemplateResponse` | Create with version 1 |
| `GET /pdf-templates` | `list_templates()` | `List[PdfTemplate]` | `TemplateListResponse` | With filters |
| `GET /pdf-templates/{id}` | `get_template()` | `PdfTemplate` | `TemplateDetailResponse` | With current version |
| `PATCH /pdf-templates/{id}/metadata` | `update_template_metadata()` | `PdfTemplate` | `TemplateResponse` | Name/description only |
| `PUT /pdf-templates/{id}` | `update_template_definition()` | `PdfTemplate` | `TemplateResponse` | Creates new version |
| `DELETE /pdf-templates/{id}` | `delete_template()` | `bool` | `SuccessResponse` | Draft only |
| `POST /pdf-templates/{id}/activate` | `activate_template()` | `PdfTemplate` | `TemplateResponse` | draft/inactive → active |
| `POST /pdf-templates/{id}/deactivate` | `deactivate_template()` | `PdfTemplate` | `TemplateResponse` | active → inactive |
| `GET /pdf-templates/{id}/versions` | `list_template_versions()` | `List[PdfTemplateVersion]` | `VersionListResponse` | All versions |
| `GET /pdf-templates/{id}/versions/{version_id}` | `get_template_version()` | `PdfTemplateVersion` | `VersionDetailResponse` | Specific version |
| `POST /pdf-templates/{id}/versions/{version_id}/set-current` | `set_current_version()` | `PdfTemplate` | `TemplateResponse` | Revert to old version |
| `POST /pdf-templates/simulate` | `simulate_template()` | `TemplateSimulationResult` | `SimulationResultResponse` | Test without persist |

**Key Point**: ALL service methods return dataclasses (or primitives like bool). Routers ALWAYS map these to Pydantic for HTTP responses.

### What Needs to Change

**Current State**:
- Service uses Pydantic models from `shared/types` throughout
- Repositories accept/return Pydantic models
- Wizard data (signature objects, extraction fields) stored as raw JSON
- No explicit mapper layer

**Required Changes**:

1. **Create Dataclasses** (frozen dataclasses in `server/src/shared/types/`):
   - PdfTemplate, PdfTemplateCreate, PdfTemplateMetadataUpdate, PdfTemplateDefinitionUpdate
   - PdfTemplateStatus (enum)
   - PdfTemplateVersion, PdfTemplateVersionCreate, PdfTemplateWithVersion
   - SignatureObject, ExtractionField (wizard data structures)
   - TemplateSimulationRequest, TemplateSimulationResult
   - PdfTemplateSummary, PdfTemplateDetail, TemplateFilters
   - **IMPORTANT**: Types must be in `shared/types/` to avoid circular imports

2. **Update Service**:
   - Update method signatures to accept/return dataclasses instead of Pydantic
   - Separate metadata vs definition update logic
   - Implement simulation logic (extraction + pipeline execution without persistence)
   - Return typed wizard dataclasses (SignatureObject, ExtractionField) from version retrieval

3. **Update Repositories**:
   - Accept dataclasses instead of Pydantic
   - Return dataclasses instead of Pydantic
   - Convert dataclasses ↔ SQLAlchemy ORM models
   - Add JSON ↔ dataclass conversion for signature_objects, extraction_fields
   - Implement helper methods for version queries (get_max_version_num, etc.)

4. **Create Mappers** (in router file or separate mapper module):
   - Pydantic Request → dataclass (for service calls)
   - dataclass → Pydantic Response (for API responses)
   - Wizard data mapping (nested structures for signature objects, extraction fields)
   - Every endpoint needs explicit mapping

5. **Add Simulation Logic**:
   - Extraction helper method (takes PDF objects + extraction fields, returns extracted data)
   - Integration with Pipeline Service simulation mode
   - Error handling for simulation failures

### Example Service Method Signature Changes

**Before** (current):
```python
def create_template(self, template_data: PdfTemplateCreate) -> PdfTemplate:
    # template_data is Pydantic
    # returns Pydantic PdfTemplate
```

**After** (with dataclasses):
```python
def create_template(self, template_data: PdfTemplateCreate) -> PdfTemplate:
    # template_data is frozen dataclass with nested SignatureObject, ExtractionField dataclasses
    # returns frozen dataclass PdfTemplate
```

**New Method Signatures**:
```python
def update_template_metadata(self, template_id: int, metadata: PdfTemplateMetadataUpdate) -> PdfTemplate:
    # Updates name/description only, no new version

def update_template_definition(self, template_id: int, definition: PdfTemplateDefinitionUpdate) -> PdfTemplate:
    # Creates new version with new definition

def simulate_template(self, simulation_data: TemplateSimulationRequest) -> TemplateSimulationResult:
    # Pure computation, no DB writes
```

### Dependencies

**Service Constructor**:
```python
def __init__(self,
             connection_manager: DatabaseConnectionManager,
             template_repository: PdfTemplateRepository,
             version_repository: PdfTemplateVersionRepository,
             pdf_service: PdfProcessingService,
             pipeline_service: PipelineService):
```

**Notes**:
- `pdf_service`: Validate source PDF exists, get PDF objects for simulation
- `pipeline_service`: Create/compile pipelines, execute pipeline simulations
- `template_repository`: CRUD operations on pdf_templates table
- `version_repository`: CRUD operations on pdf_template_versions table
- Both repositories needed for atomic template creation with version

### Extraction Helper Method

**Internal Method for Simulation and ETO Processing**:
```python
def _extract_data(self, pdf_objects: List[PdfObject], extraction_fields: List[ExtractionField]) -> Dict[str, str]:
    """
    Extract data from PDF objects using extraction field definitions.

    For each extraction field:
    1. Find all PDF objects (TextWord) within bounding box
    2. Concatenate text from matching objects
    3. Store in result dict with field name as key

    Returns: {field_name: extracted_text, ...}
    """
    extracted_data = {}

    for field in extraction_fields:
        # Find text objects within bounding box
        matching_texts = [
            obj.text for obj in pdf_objects
            if isinstance(obj, TextWord) and self._is_within_bbox(obj, field.bounding_box)
        ]

        # Concatenate and store
        extracted_data[field.field_name] = " ".join(matching_texts)

    return extracted_data

def _is_within_bbox(self, obj: TextWord, bbox: BoundingBox) -> bool:
    """Check if text object is within bounding box."""
    return (
        obj.x0 >= bbox.x0 and
        obj.x1 <= bbox.x1 and
        obj.y0 >= bbox.y0 and
        obj.y1 <= bbox.y1
    )
```

**Note**: This extraction logic is shared between:
- Simulation (called directly by Template Service)
- Real ETO runs (called by ETO Service)

---

## Service 5: Pipeline Service

### Current Implementation Status

**Location**: `server/src/features/pipeline/service.py` and `server/src/features/pipeline_execution/service.py`

**What Exists**:
- Complete validation system (6 stages: schema, indexing, graph, edges, modules, reachability)
- Compilation system (pruning, topological sorting, checksum calculation, step building)
- Checksum-based pipeline deduplication (shared compiled plans)
- Pipeline execution via Dask DAG
- Action/non-action module separation (non-actions run first, actions wait on barrier)
- Module registry integration for handler lookup
- Execution auditing (step-by-step results persisted)
- Error handling and rollback
- Dev/testing CRUD endpoints for standalone pipelines

**Architecture Split**:
- `pipeline/` feature: Validation, compilation, and CRUD operations
- `pipeline_execution/` feature: Execution via Dask, module execution, audit trail
- Both currently have separate services but should be unified

### Service Responsibilities

**1. Pipeline CRUD Operations**
- `create_pipeline(pipeline_data)`: Create and compile new pipeline → returns PipelineDefinition (dataclass)
  - Validates pipeline_state (6-stage validation)
  - Prunes dead branches (reachability analysis)
  - Calculates checksum from pruned pipeline
  - Checks for existing compiled plan (deduplication)
  - If cache miss: Compiles topological layers and saves steps
  - If cache hit: Reuses existing steps
  - Creates pipeline record with plan_checksum and compiled_at
- `get_pipeline(pipeline_id)`: Retrieve single pipeline → returns PipelineDefinition (dataclass)
  - Returns full pipeline with pipeline_state, visual_state, compilation metadata
- `list_pipelines(include_inactive)`: List all pipelines → returns List[PipelineDefinition] (dataclass)
  - Primarily for dev/testing (Router 6)
  - Optionally includes inactive pipelines
- `list_pipeline_summaries(include_inactive)`: List pipeline summaries → returns List[PipelineDefinitionSummary] (dataclass)
  - Lightweight summaries for dropdowns, tables
  - Shows module_count, connection_count, entry_point_count
- `update_pipeline(pipeline_id, pipeline_data)`: Update pipeline (NOT YET IMPLEMENTED)
  - Would follow same flow as create (validate → compile → potentially new checksum)
- `delete_pipeline(pipeline_id)`: Delete standalone pipeline (NOT YET IMPLEMENTED)
  - Only for dev/testing pipelines (Router 6)
  - Cannot delete pipelines associated with template versions

**2. Pipeline Validation** (internal, called during create/update)
- `validate_pipeline(pipeline_state)`: 6-stage validation → returns PipelineValidationResult (dataclass)
  - **Stage 1 - Schema Validation**: Basic structure, uniqueness, types, format
  - **Stage 2 - Index Building**: Create lookups for efficient validation
  - **Stage 3 - Graph Validation**: Check for cycles (must be DAG)
  - **Stage 4 - Edge Validation**: Cardinality and type matching
  - **Stage 5 - Module Validation**: Module templates, type vars, config validation (uses ModuleCatalogRepository)
  - **Stage 6 - Reachability Analysis**: Find action-reachable modules (pruning target)
  - Raises PipelineValidationFailedException on failure with structured errors

**3. Pipeline Compilation** (internal, called during create/update)
- Compilation Flow (from create_pipeline):
  1. Validate pipeline → get reachable_modules
  2. Prune graph → pruned_pipeline (remove dead branches)
  3. Calculate checksum from pruned pipeline (deterministic hash)
  4. Check cache: step_repo.checksum_exists(checksum)
  5a. Cache HIT: Create pipeline record with existing checksum
  5b. Cache MISS: Compile steps, create pipeline, save steps
  6. Return PipelineDefinition with plan_checksum and compiled_at

- Compilation Utilities:
  - `GraphPruner.prune(pipeline_state, reachable_modules)`: Remove dead branches
  - `TopologicalSorter.sort(pruned_pipeline)`: Compute execution layers
  - `ChecksumCalculator.compute(pruned_pipeline)`: Deterministic hash for deduplication
  - `PipelineCompiler.compile(pruned_pipeline, checksum)`: Build PipelineDefinitionStepCreate list

**4. Pipeline Execution**
- `execute_pipeline(pipeline_definition_id, entry_values_by_name, persist_run)`: Execute compiled pipeline → returns PipelineExecutionRun (dataclass)
  - Loads pipeline and compiled steps (ordered by step_number)
  - Validates entry values match pipeline entry_points
  - Builds Dask DAG from compiled steps
  - Separates action modules from non-action modules
  - Creates barrier: All non-actions must complete before actions start
  - Executes DAG via dask.compute()
  - Persists execution run and step results (if persist_run=True)
  - Returns execution results with status (success/failure)

- Execution Flow:
  1. Load pipeline → validate has plan_checksum
  2. Load compiled steps by checksum → ordered list
  3. Map entry names to pin IDs
  4. Seed entry values as Dask delayed constants
  5. Build step tasks (one per module instance):
     - Non-action tasks: Created immediately
     - Action tasks: Deferred until after barrier
  6. Create barrier: delayed(lambda *args: True)(*non_action_tasks)
  7. Add action tasks with barrier dependency
  8. Execute: dask.compute(*all_tasks)
  9. Persist run + steps (if persist_run=True)
  10. Return PipelineExecutionRun with results

- Step Execution (within Dask task):
  - Resolve module handler from ModuleRegistry
  - Gather upstream delayed values (inputs)
  - Execute: handler.run(inputs, cfg, context)
  - Persist step result (inputs, outputs, error)
  - On error: Persist error and raise (stops whole run)
  - Return outputs dict for downstream consumers

**5. Simulation Mode** (for template wizard testing)
- `execute_pipeline_simulation(pipeline_definition, entry_values)`: Execute without persistence → returns PipelineExecutionRun (dataclass)
  - Similar to execute_pipeline but persist_run=False
  - Action modules SIMULATE (no actual execution)
  - Returns synthetic PipelineExecutionRun with id=-1
  - Used by Template Service during wizard simulation

**6. Service Lifecycle**
- `is_healthy()`: Health check → returns bool
  - Verifies module registry availability
  - Verifies repository availability

### Key Design Decisions

**Two Separate Features, One Unified Service**:
- Current codebase has two services: PipelineService (validation/compilation) and PipelineExecutionService (execution)
- Design decision: Unified Pipeline Service in redesign
  - Single service provides both compilation and execution
  - Cleaner dependency injection (other services call one service)
  - Transaction management easier (one connection_manager)
  - Simpler API (routers call one service)

**Checksum-Based Deduplication**:
- Pipelines with identical logic share compiled plans
- Checksum calculated from pruned pipeline_state (canonical form)
- pipeline_definitions table stores plan_checksum
- pipeline_definition_steps table stores steps keyed by plan_checksum
- Multiple pipelines → same checksum → shared steps (storage efficiency)
- Example: Two templates with same transformation logic share compiled plan

**Validation Before Compilation**:
- All pipelines validated through 6 stages before compilation
- Validation errors bubble up to API as PipelineValidationFailedException
- No compilation if validation fails (fail fast)
- Reachability analysis identifies which modules to include in compilation (dead branch removal)

**Execution Architecture**:
- Dask DAG for dataflow execution (not sequential)
- Modules execute when upstream dependencies ready
- Topological layers provide execution order guidance
- Non-action barrier enforces: All transformations complete before actions execute
- Actions never "undo" transformations if they fail (transformations already saved audit trail)

**Action Module Barrier**:
- **Policy**: All action modules run ONLY after all transform/logic modules succeed
- **Implementation**: Barrier = delayed(lambda *args: True)(*non_action_tasks)
- **Rationale**: Actions have side effects (create orders, send emails, etc.)
  - Want all data transformations validated first
  - Prevent partial actions if transformation fails
  - If action fails, at least we have complete transformation audit trail

**Module Execution Context**:
- Modules receive ModuleExecutionContext with:
  - inputs: List[InstanceNodePin] (metadata: node_id, type, name, position)
  - outputs: List[InstanceNodePin]
  - module_instance_id: For logging
  - services: ServiceContainer for cross-service calls (e.g., action modules calling EmailService)
- Modules execute: `run(inputs: Dict[node_id, value], cfg: ConfigModel, context: ModuleExecutionContext) -> Dict[node_id, value]`

**Execution Auditing**:
- PipelineExecutionRun: High-level run record (pipeline_id, status, entry_values, timestamps)
- PipelineExecutionStep: Per-module step record (inputs, outputs, error, module_instance_id, step_number)
- Inputs/outputs stored as JSON: `{node_name: {value, type}, ...}`
- Audit trail useful for:
  - Debugging pipeline failures
  - Understanding data flow through pipeline
  - Reprocessing logic (future feature)

**Standalone vs Template-Associated Pipelines**:
- **Standalone pipelines** (Router 6 `/pipelines`): For dev/testing, can be deleted
- **Template-associated pipelines**: Created by TemplateService, cannot be directly deleted
- Service doesn't enforce this distinction (enforcement in routers/template service)

**No Update Endpoint Yet**:
- Current implementation has create and read, no update
- Update would: Validate → Compile → Potentially new checksum → Update record
- Update blocked for template-associated pipelines (must create new template version instead)

**Error Handling**:
- Validation errors: PipelineValidationFailedException with structured errors list
- Execution errors: Module failure stops entire run, error persisted to step record
- Repository errors: Bubble up to API layer
- Missing module handlers: RuntimeError during execution

### Dataclasses Required

**Internal Types** (to be created in `shared/types/`):

**Core Pipeline Types** (mostly exist as Pydantic, need frozen dataclass versions):
- `PipelineDefinition`: Full pipeline (id, name, description, pipeline_state, visual_state, plan_checksum, compiled_at, is_active, created_at, module_count, connection_count, entry_point_count)
- `PipelineDefinitionCreate`: Data for creating pipeline (name, description, pipeline_state, visual_state)
- `PipelineDefinitionSummary`: Summary view (id, name, description, is_active, module_count, connection_count, entry_point_count, created_at)

**Pipeline State Types** (already exist in pipelines.py as Pydantic, need dataclass versions):
- `PipelineState`: Execution structure (entry_points, modules, connections)
- `VisualState`: Visual layout (module positions, entry point positions)
- `EntryPoint`: Entry point definition (node_id, name)
- `ModuleInstance`: Module instance (module_instance_id, module_ref, config, inputs, outputs, module_kind)
- `NodeInstance`: Pin instance (node_id, type, name, position_index, group_index)
- `NodeConnection`: Connection between nodes (from_node_id, to_node_id)
- `ModulePosition`: Position on canvas (x, y)

**Compiled Pipeline Types**:
- `PipelineDefinitionStep`: Compiled step (id, plan_checksum, module_instance_id, module_ref, module_kind, module_config, input_field_mappings, node_metadata, step_number)
- `PipelineDefinitionStepCreate`: Data for creating step

**Execution Types**:
- `PipelineExecutionRun`: Execution run (id, pipeline_definition_id, status, entry_values, started_at, completed_at, created_at)
- `PipelineExecutionRunCreate`: Data for creating run
- `PipelineExecutionStep`: Step result (id, run_id, module_instance_id, step_number, inputs, outputs, error, started_at, completed_at)
- `PipelineExecutionStepCreate`: Data for creating step result

**Validation Types**:
- `PipelineValidationResult`: Validation result (valid, errors, reachable_modules)
- `PipelineValidationError`: Validation error (code, message, where)
- `PipelineValidationErrorCode`: Error codes enum
- `PipelineIndices`: Lookup structures (pin_by_id, module_by_id, input_to_upstream)
- `PinInfo`: Pin metadata (node_id, type, module_instance_id, direction, name)

**Module Types**:
- `ModuleExecutionContext`: Context for module execution (inputs, outputs, module_instance_id, services)

**Note**: Many of these types already exist as Pydantic models. They need to be converted to frozen dataclasses following the redesign pattern.

### Mapping Strategy

**Router → Service** (Pydantic to dataclass):
```python
# In router (Router 6: /pipelines)
@router.post("/pipelines")
def create_pipeline(request: CreatePipelineRequest) -> PipelineResponse:
    # Map Pydantic → dataclass
    pipeline_data = PipelineDefinitionCreate(
        name=request.name,
        description=request.description,
        pipeline_state=PipelineState(
            entry_points=[EntryPoint(**ep.dict()) for ep in request.pipeline_state.entry_points],
            modules=[ModuleInstance(**m.dict()) for m in request.pipeline_state.modules],
            connections=[NodeConnection(**c.dict()) for c in request.pipeline_state.connections]
        ),
        visual_state=VisualState(**request.visual_state.dict())
    )

    # Call service (gets dataclass back)
    pipeline = pipeline_service.create_pipeline(pipeline_data)

    # Map dataclass → Pydantic response
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        plan_checksum=pipeline.plan_checksum,
        compiled_at=pipeline.compiled_at,
        module_count=pipeline.module_count,
        # ... map all fields
    )
```

**Execution Endpoint** (called by Template Service and ETO Service):
```python
# In Template Service (for simulation)
simulation_run = pipeline_service.execute_pipeline_simulation(
    pipeline_definition=wizard_pipeline_definition,  # dataclass
    entry_values=extracted_data  # Dict[str, Any]
)

# In ETO Service (for real runs)
execution_run = pipeline_service.execute_pipeline(
    pipeline_definition_id=template_version.pipeline_definition_id,
    entry_values_by_name=extracted_data,
    persist_run=True
)
```

**Service → Repository** (dataclass to dataclass):
- Service calls repository with dataclasses
- Repository accepts dataclasses, returns dataclasses
- Repository handles JSON ↔ dataclass conversion for pipeline_state, visual_state, node_metadata

**Repository → SQLAlchemy** (dataclass to ORM):
- Repository converts dataclasses to ORM models for persistence
- Repository converts ORM models back to dataclasses for return
- JSON serialization/deserialization handled in repository

### Transaction Management

**Pattern 1: Create Pipeline with Compilation** (multi-repo transaction):
```python
# Service
def create_pipeline(self, pipeline_data: PipelineDefinitionCreate) -> PipelineDefinition:
    # Validation (no DB, may raise PipelineValidationFailedException)
    validation_result = self.validate_pipeline(pipeline_data.pipeline_state)
    reachable_modules = validation_result.reachable_modules

    # Pruning (no DB)
    pruned_pipeline = GraphPruner.prune(pipeline_data.pipeline_state, reachable_modules)

    # Checksum calculation (no DB)
    checksum = ChecksumCalculator.compute(pruned_pipeline)

    # Cache check (read-only)
    cache_hit = self.step_repo.checksum_exists(checksum)

    compiled_at = datetime.now()

    if cache_hit:
        # Cache hit: Create pipeline only (single repo, single transaction)
        pipeline_dict = pipeline_data.model_dump_for_db()
        pipeline_dict["plan_checksum"] = checksum
        pipeline_dict["compiled_at"] = compiled_at
        return self.pipeline_repo.create_with_checksum(pipeline_dict)
    else:
        # Cache miss: Compile and create everything (multi-repo transaction)
        with self.connection_manager.transaction() as session:
            # Compile steps (no DB)
            steps = PipelineCompiler.compile(pruned_pipeline, checksum)

            # Create pipeline record
            pipeline_dict = pipeline_data.model_dump_for_db()
            pipeline_dict["plan_checksum"] = checksum
            pipeline_dict["compiled_at"] = compiled_at
            pipeline = self.pipeline_repo.create_with_checksum(pipeline_dict, session=session)

            # Save steps
            self.step_repo.save_steps(steps, session=session)

            return pipeline
```

**Pattern 2: Execute Pipeline** (multi-repo transaction for audit persistence):
```python
# Service
def execute_pipeline(
    self,
    pipeline_definition_id: int,
    entry_values_by_name: Dict[str, Any],
    persist_run: bool = True
) -> PipelineExecutionRun:
    # Load pipeline and steps (read-only)
    pipeline = self._require_pipeline(pipeline_definition_id)
    steps = self._require_compiled_steps(pipeline)

    # Create run record (if persisting)
    if persist_run:
        run = self.run_repo.create(
            PipelineExecutionRunCreate(
                pipeline_definition_id=pipeline.id,
                entry_values=entry_values_by_name
            )
        )
        run_id = run.id
    else:
        run_id = None  # Simulation mode

    # Build and execute Dask DAG (no DB during execution)
    # Module tasks will persist their own step results if run_id is provided
    try:
        # ... build DAG and execute ...
        compute(*leaves)

        # Update run status (if persisting)
        if persist_run:
            self.run_repo.update_run_status(run_id, "success")
            return self.run_repo.get_run_by_id(run_id)
        else:
            # Return synthetic run for simulation
            return PipelineExecutionRun(
                id=-1,
                pipeline_definition_id=pipeline_definition_id,
                status="success",
                entry_values=entry_values_by_name
            )

    except Exception as e:
        if persist_run:
            self.run_repo.update_run_status(run_id, "failed")
        raise
```

**Note**: Individual step persistence happens within Dask tasks (one transaction per step). This is acceptable because:
- Steps are independent audit records
- If pipeline fails mid-execution, we want partial step records for debugging
- No need to rollback completed step audits on pipeline failure

### Integration with API Layer

**Endpoints → Service Methods**:

| Endpoint | Service Method | Service Returns | Router Maps To | Notes |
|----------|----------------|-----------------|----------------|-------|
| `GET /pipelines` | `list_pipelines()` | `List[PipelineDefinition]` | `PipelineListResponse` | Dev/testing only |
| `GET /pipelines/{id}` | `get_pipeline()` | `PipelineDefinition` | `PipelineResponse` | Full pipeline |
| `POST /pipelines` | `create_pipeline()` | `PipelineDefinition` | `PipelineResponse` | Create & compile |
| `PUT /pipelines/{id}` | `update_pipeline()` | `PipelineDefinition` | `PipelineResponse` | NOT YET IMPLEMENTED |
| `DELETE /pipelines/{id}` | `delete_pipeline()` | `bool` | `SuccessResponse` | NOT YET IMPLEMENTED |

**Internal Service Methods** (called by other services, not routers):

| Caller | Service Method | Service Returns | Purpose |
|--------|----------------|-----------------|---------|
| Template Service | `create_pipeline()` | `PipelineDefinition` | Create pipeline for template version |
| Template Service | `execute_pipeline_simulation()` | `PipelineExecutionRun` | Test wizard without persistence |
| ETO Service | `execute_pipeline()` | `PipelineExecutionRun` | Execute pipeline for ETO run |

**Key Point**: ALL service methods return dataclasses (or primitives like bool). Routers ALWAYS map these to Pydantic for HTTP responses.

### What Needs to Change

**Current State**:
- Two separate services: PipelineService (validation/compilation) and PipelineExecutionService (execution)
- Uses Pydantic models from `shared/types` throughout
- Repositories accept/return Pydantic models
- Pipeline state/visual state stored as JSON strings
- No explicit mapper layer in routers

**Required Changes**:

1. **Unify Services**:
   - Merge pipeline/ and pipeline_execution/ into single Pipeline Service
   - Single service class with both compilation and execution methods
   - Single connection_manager for both compilation and execution repos

2. **Create Dataclasses** (frozen dataclasses in `server/src/shared/types/`):
   - PipelineDefinition, PipelineDefinitionCreate, PipelineDefinitionSummary
   - PipelineState, VisualState, EntryPoint, ModuleInstance, NodeInstance, NodeConnection, ModulePosition
   - PipelineDefinitionStep, PipelineDefinitionStepCreate
   - PipelineExecutionRun, PipelineExecutionRunCreate
   - PipelineExecutionStep, PipelineExecutionStepCreate
   - PipelineValidationResult, PipelineValidationError, PipelineValidationErrorCode
   - ModuleExecutionContext
   - **IMPORTANT**: Types must be in `shared/types/` to avoid circular imports

3. **Update Service**:
   - Merge both services into one
   - Update method signatures to accept/return dataclasses instead of Pydantic
   - Add execute_pipeline_simulation() method for template wizard
   - Internal processing uses dataclasses

4. **Update Repositories**:
   - PipelineDefinitionRepository: Accept/return dataclasses
   - PipelineDefinitionStepRepository: Accept/return dataclasses
   - PipelineExecutionRunRepository: Accept/return dataclasses
   - PipelineExecutionStepRepository: Accept/return dataclasses
   - Convert dataclasses ↔ SQLAlchemy ORM models
   - Add JSON ↔ dataclass conversion for pipeline_state, visual_state, node_metadata, entry_values, inputs/outputs
   - Implement helper methods for checksum queries

5. **Create Mappers** (in router file or separate mapper module):
   - Pydantic Request → dataclass (for service calls)
   - dataclass → Pydantic Response (for API responses)
   - Pipeline state mapping (nested structures)
   - Every endpoint needs explicit mapping

6. **Update Module Registry**:
   - Ensure ModuleRegistry uses dataclasses for module metadata
   - Module handlers already receive context via ModuleExecutionContext

### Example Service Method Signature Changes

**Before** (current - two separate services):
```python
# In PipelineService
def create_pipeline(self, pipeline_create: PipelineDefinitionCreate) -> PipelineDefinition:
    # pipeline_create is Pydantic
    # returns Pydantic PipelineDefinition

# In PipelineExecutionService
def execute_pipeline(self, pipeline_definition_id: int, entry_values_by_name: Dict[str, Any]) -> PipelineExecutionRun:
    # returns Pydantic PipelineExecutionRun
```

**After** (with dataclasses - unified service):
```python
# In unified PipelineService
def create_pipeline(self, pipeline_data: PipelineDefinitionCreate) -> PipelineDefinition:
    # pipeline_data is frozen dataclass
    # returns frozen dataclass PipelineDefinition

def execute_pipeline(
    self,
    pipeline_definition_id: int,
    entry_values_by_name: Dict[str, Any],
    persist_run: bool = True
) -> PipelineExecutionRun:
    # returns frozen dataclass PipelineExecutionRun

def execute_pipeline_simulation(
    self,
    pipeline_definition: PipelineDefinition,
    entry_values: Dict[str, Any]
) -> PipelineExecutionRun:
    # Simulation mode (persist_run=False)
    # Used by Template Service wizard
```

### Dependencies

**Service Constructor**:
```python
def __init__(self,
             connection_manager: DatabaseConnectionManager,
             pipeline_definition_repo: PipelineDefinitionRepository,
             pipeline_step_repo: PipelineDefinitionStepRepository,
             pipeline_execution_run_repo: PipelineExecutionRunRepository,
             pipeline_execution_step_repo: PipelineExecutionStepRepository,
             module_catalog_repo: ModuleCatalogRepository,
             module_registry: ModuleRegistry):
```

**Notes**:
- `module_catalog_repo`: For validation (stage 5 - module template validation)
- `module_registry`: For execution (handler lookup by module_ref)
- Four repositories: Two for compilation (definition, steps), two for execution (runs, step results)
- Service is called by:
  - Template Service (create pipelines for template versions, execute simulations)
  - ETO Service (execute pipelines for ETO runs)
  - Router 6 (dev/testing CRUD operations)

### Validation Flow Details

**6-Stage Validation Pipeline**:

1. **Schema Validation** (`SchemaValidator.validate()`):
   - Basic structure validation (all required fields present)
   - Uniqueness validation (module_instance_id, node_id, entry point names)
   - Type validation (string enums, numeric ranges)
   - Format validation (node_id patterns, module_ref format)

2. **Index Building** (`IndexBuilder.build_indices()`):
   - Build `PipelineIndices` with lookups:
     - `pin_by_id`: node_id → PinInfo
     - `module_by_id`: module_instance_id → ModuleInstance
     - `input_to_upstream`: input pin → upstream output pin (connection map)
   - Used by subsequent validation stages

3. **Graph Validation** (`GraphBuilder.build_pin_graph()` + cycle check):
   - Build NetworkX directed graph from connections
   - Check if graph is acyclic (DAG required)
   - Find cycles if present (for error reporting)

4. **Edge Validation** (`EdgeValidator.validate()`):
   - **Cardinality validation**: Each input pin has exactly one connection
   - **Type matching**: Connected pins have compatible types
   - Type compatibility rules (exact match or type coercion allowed)

5. **Module Validation** (`ModuleValidator.validate()`):
   - **Template validation**: module_ref exists in module catalog
   - **Type variable resolution**: Generic module types resolved correctly
   - **Config validation**: Module config matches template schema

6. **Reachability Analysis** (`ReachabilityAnalyzer.analyze()`):
   - **Action module requirement**: At least one action module required
   - **Reachability computation**: Which modules are upstream of actions?
   - Returns set of reachable module IDs (used for pruning)

**Output**: `PipelineValidationResult` with:
- `valid: bool`: True if all stages pass
- `errors: List[PipelineValidationError]`: Structured errors with codes and locations
- `reachable_modules: Set[str]`: Module IDs that are upstream of actions

**Error Handling**: Raises `PipelineValidationFailedException` with full validation result if validation fails. API layer catches this and returns structured errors to frontend.

### Compilation Flow Details

**Compilation Steps** (from create_pipeline):

1. **Pruning** (`GraphPruner.prune()`):
   - Input: pipeline_state + reachable_modules (from validation)
   - Output: pruned_pipeline with only reachable modules
   - Dead branches removed (modules not upstream of any action)

2. **Checksum Calculation** (`ChecksumCalculator.compute()`):
   - Input: pruned_pipeline
   - Canonical serialization (deterministic JSON)
   - SHA-256 hash of canonical form
   - Output: checksum string (used for deduplication)

3. **Cache Check**:
   - Query: `step_repo.checksum_exists(checksum)`
   - Returns: bool (True if steps already compiled for this checksum)

4. **Topological Sorting** (`TopologicalSorter.sort()`):
   - Input: pruned_pipeline
   - Build dependency graph from connections
   - Compute topological layers (modules that can run in parallel per layer)
   - Output: `List[List[str]]` (layers of module_instance_ids)
   - Example: `[["m1", "m2"], ["m3"], ["m4", "m5"]]` means m1 and m2 can run in parallel, then m3, then m4 and m5 in parallel

5. **Step Building** (`PipelineCompiler._build_steps()`):
   - Input: pruned_pipeline, layers, checksum
   - For each layer, for each module:
     - Build input_field_mappings (input pin → upstream output pin)
     - Build node_metadata (inputs/outputs with full pin info)
     - Create PipelineDefinitionStepCreate dataclass
     - Assign step_number (increments across layers)
   - Output: `List[PipelineDefinitionStepCreate]`

6. **Persistence**:
   - If cache hit: Create pipeline record with checksum
   - If cache miss: Create pipeline record + save all steps

**Result**: PipelineDefinition with plan_checksum and compiled_at

### Execution Flow Details

**Dask DAG Construction**:

1. **Entry Value Seeding**:
   - Map entry names to pin IDs
   - Create delayed constants for each entry value
   - Seed producer_of_pin dict: `{pin_id: delayed(value)}`

2. **Non-Action Tasks**:
   - For each non-action step (module_kind != "action"):
     - Create `_make_step_task(step, producer_of_pin, run_id)`
     - Task resolves upstream inputs, executes module, persists result
     - Publish outputs: Each output pin becomes delayed(lambda: outputs[pin_id])
     - Add to non_action_tasks list

3. **Barrier Creation**:
   - `barrier = delayed(lambda *args: True)(*non_action_tasks)`
   - Barrier task waits for all non-actions to complete
   - Returns True (dummy value, just for dependency)

4. **Action Tasks**:
   - For each action step:
     - Create `_make_step_task(step, producer_of_pin, run_id, extra_dependencies=[barrier])`
     - Task depends on barrier + its own upstream inputs
     - Ensures actions run ONLY after all non-actions succeed

5. **Execution**:
   - Collect all leaf tasks (tasks with no downstream consumers)
   - Execute: `dask.compute(*leaves)`
   - Dask schedules tasks based on dependencies
   - Each task is a delayed function that:
     - Waits for upstream values to resolve
     - Executes module handler
     - Persists step result (if run_id provided)
     - Returns outputs for downstream

6. **Result Collection**:
   - Update run status (success/failure)
   - Return PipelineExecutionRun with results

**Step Task Implementation** (simplified):
```python
@delayed(pure=False)
def _run_module(*resolved):
    # resolved contains input values in order
    inputs = {inp_id: val for inp_id, val in zip(input_ids, resolved)}

    # Execute module
    try:
        outputs = handler.run(inputs=inputs, cfg=config, context=context)
        error = None
    except Exception as e:
        outputs = {}
        error = str(e)

    # Persist step result
    if run_id:
        step_repo.create(PipelineExecutionStepCreate(
            run_id=run_id,
            module_instance_id=step.module_instance_id,
            step_number=step.step_number,
            inputs=_serialize_io(inputs, context.inputs),
            outputs=_serialize_io(outputs, context.outputs),
            error=error
        ))

    # Raise on error (stops pipeline)
    if error:
        raise RuntimeError(error)

    return outputs
```

**Simulation Mode Differences**:
- persist_run=False → run_id=None
- Step tasks skip persistence
- Action modules check context and simulate (no actual execution)
- Returns synthetic PipelineExecutionRun with id=-1

---

## Service 6: Module Service

### Current Implementation Status

**Location**: `server/src/features/modules/service.py`

**What Exists**:
- Complete service implementation with catalog querying and module execution
- ModuleCatalogRepository integration for database access
- ModuleRegistry integration for runtime module class loading
- Auto-discovery of modules from package paths at service startup
- Module execution with validation and error handling
- Caching through ModuleRegistry

**Integration Architecture**:
- `BaseModule`: Abstract base class for all modules (TransformModule, ActionModule, LogicModule, ComparatorModule)
- `ModuleRegistry`: Singleton registry for module class registration and caching
- `ModuleCatalogRepository`: Database repository for module metadata persistence
- `ModuleCatalogModel`: SQLAlchemy ORM model for module_catalog table
- Auto-discovery: Package scanning that imports modules and triggers @register decorators
- CLI Tools: `sync_modules.py` for syncing registry → database, `watch_modules.py` for development

**Module Metadata Structure**:
- Module class fields: id, version, title, description, kind, ConfigModel
- ModuleMeta: IOShape definition (input/output node groups with typing rules)
- config_schema: JSON Schema with x-ui extensions for frontend form generation
- handler_name: Python import path (e.g., "src.features.modules.transform.text_cleaner:BasicTextCleaner")
- Security validation: Whitelisted package paths, blocked patterns, validation before loading

### Service Responsibilities

**1. Module Catalog Discovery** (Frontend API Support)
- `get_module_catalog(only_active)`: List all modules from database → returns List[ModuleCatalog] (dataclass)
- `get_module_info(module_id)`: Get specific module metadata → returns ModuleCatalog (dataclass)
- `get_modules_by_kind(module_kind, only_active)`: Filter modules by kind → returns List[ModuleCatalog] (dataclass)

**2. Module Registration** (Backend Sync Process)
- `register_module_from_class(module_class)`: Register single module class → returns ModuleCatalog (dataclass)
- `register_modules_from_registry()`: Sync all registered modules to database → returns List[ModuleCatalog] (dataclass)
- `sync_module_packages(package_paths)`: Auto-discover + register from packages → returns SyncResult (dataclass)
- `clear_module_catalog()`: Clear all modules from database (hard delete for refresh)

**3. Module Execution** (Testing & Development)
- `execute_module(module_id, inputs, config, context)`: Execute module with validation → returns Dict[str, Any]
- `_get_module_class(module_info)`: Load module class from registry or handler → returns Type[BaseModule]
- `_execute_module_instance(module_class, inputs, config, context)`: Execute with error handling

**4. Service Lifecycle**
- `_auto_discover_modules()`: Called during __init__ to populate registry from known packages
- `get_registry_stats()`: Get cache hit rate and registry size → returns RegistryStats (dataclass)
- `is_healthy()`: Health check for service → returns bool

### Key Design Decisions

**Dual Responsibility - Discovery vs Registration**:
- **Discovery** (read-only, API support): Query database for module catalog, used by frontend to browse modules
- **Registration** (write, backend sync): Convert module classes → database entries, typically CLI-driven
- Frontend calls GET /modules → service queries database → returns catalog
- Backend calls sync CLI → service auto-discovers → converts to catalog format → upserts to database

**Module Class Lifecycle**:
1. **Development**: Developer creates module class inheriting from BaseModule with @register decorator
2. **Auto-Discovery**: Package import triggers @register, adds to ModuleRegistry singleton
3. **Sync to Database**: CLI tool calls `register_modules_from_registry()` → converts registry → upserts to module_catalog table
4. **Runtime Lookup**: Pipeline execution needs module → service queries database → loads class via handler_name → caches in registry
5. **Execution**: Module class instantiated, config validated, run() method called with inputs + context

**ModuleRegistry Architecture**:
- Singleton pattern (one instance across entire server)
- Two registration paths:
  - **Decorator Registration**: @register decorator on module classes (import-time)
  - **Dynamic Loading**: load_module_from_handler() for handler_name strings (runtime)
- Module cache: LRU cache with TTL for dynamically loaded modules (50 modules, 1 hour TTL)
- Security validation: handler_name validated against whitelist + blocklist before dynamic import
- Registry methods: register(), get(), get_all(), get_by_kind(), resolve_module(), to_catalog_format()

**Database Catalog Structure**:
- Composite primary key: (id, version) for module versioning support
- JSON columns: meta (IOShape structure), config_schema (JSON Schema with UI hints)
- handler_name: Required for dynamic loading (format: "module.path:ClassName")
- is_active: Soft delete flag (inactive modules hidden from catalog queries)
- UI fields: color (hex code), category (for grouping in frontend)

**Registration Process Details**:
1. **Auto-Discovery Phase**:
   - Service startup calls auto_discover_modules(package_paths)
   - Imports all .py files in specified packages
   - @register decorators execute, populate ModuleRegistry
2. **Catalog Conversion Phase**:
   - registry.to_catalog_format() iterates registered modules
   - Calls module_class.meta() and module_class.config_schema()
   - Builds dict with all catalog fields
3. **Database Sync Phase**:
   - For each catalog entry, call repository.upsert(ModuleCatalogCreate)
   - Upsert checks existence by (id, version), creates or updates
   - Validates handler_name security before persisting

**Execution Context**:
- Modules receive ModuleExecutionContext with:
  - instance_ordered_inputs: List of (pin_id, value) tuples in order
  - instance_ordered_outputs: List of (pin_id, value) tuples in order
  - pipeline_run_id: Optional ID for audit trail
  - is_simulation: Boolean flag (action modules check this to skip side effects)
- During pipeline execution, context is fully populated
- During standalone testing (POST /modules/execute), service creates minimal context

**Error Handling**:
- ModuleNotFoundError: Module ID not in database catalog
- ModuleLoadError: Module class cannot be dynamically loaded (import fails, security validation fails)
- ModuleExecutionError: Module run() method raises exception
- All errors bubble up to router for appropriate HTTP status codes

### Dataclasses Required (in `shared/types/`)

**Module Catalog Types**:
- `ModuleCatalog`: Full module catalog entry (from database)
- `ModuleCatalogCreate`: Create new catalog entry
- `ModuleCatalogUpdate`: Update existing entry
- `ModuleCatalogSummary`: Lightweight catalog view (id, version, name, kind, category)

**Module Discovery Types**:
- `EmailAccount`: For email account discovery (wrong service - this is Email service)
- `EmailFolder`: For folder discovery (wrong service - this is Email service)

**Module Registration Types**:
- `SyncResult`: Result of sync operation (success_count, error_count, errors list)
- `RegistryStats`: Registry statistics (cache_size, hit_rate, registered_count)

**Module Execution Types**:
- `ModuleExecutionContext`: Execution context for module run() methods
- (Module types already exist in shared/types/modules.py: BaseModule, ModuleMeta, IOShape, etc.)

### Mapping Strategies

**Router → Service (Pydantic → Dataclass)**:

```python
# GET /modules (catalog query)
# Router receives nothing, calls service, service returns List[ModuleCatalog]
# Router maps each ModuleCatalog → Pydantic response dict

def map_module_catalog_to_response(catalog: ModuleCatalog) -> Dict[str, Any]:
    return {
        "module_ref": f"{catalog.id}:{catalog.version}",
        "id": catalog.id,
        "version": catalog.version,
        "title": catalog.name,
        "description": catalog.description,
        "kind": catalog.module_kind,
        "meta": catalog.meta,  # Already dict from dataclass
        "config_schema": catalog.config_schema,  # Already dict
        "category": catalog.category,
        "color": catalog.color,
        "is_active": catalog.is_active
    }
```

**Service → Repository (Dataclass → Dataclass)**:
- Service already uses dataclasses (ModuleCatalog, ModuleCatalogCreate, etc.)
- Repository accepts/returns same dataclasses
- No mapping needed (type consistency maintained)

**Repository → Database (Dataclass → SQLAlchemy)**:

```python
# Create operation
def create(self, module_create: ModuleCatalogCreate) -> ModuleCatalog:
    # Convert to database format (JSON serialize complex fields)
    data = module_create.model_dump_for_db()  # Serializes meta, config_schema to JSON

    # Create SQLAlchemy model
    model = ModuleCatalogModel(**data)
    session.add(model)
    session.flush()

    # Convert back to dataclass
    return ModuleCatalog.from_db_model(model)  # Deserializes JSON fields
```

### Transaction Management

**Single Repository Operations**:
- Catalog queries (get_all, get_by_id) are read-only, no transaction needed
- Upsert operations use repository's session_scope (one transaction per module)

**Multi-Module Sync Operations**:
```python
def register_modules_from_registry(self) -> List[ModuleCatalog]:
    """
    Sync all registered modules to database
    Each module synced in separate transaction for isolation
    """
    catalog_entries = self.registry.to_catalog_format()
    results = []
    errors = []

    for entry in catalog_entries:
        try:
            # Security validation
            is_valid, error_msg = ModuleSecurityValidator.validate_handler_path(
                entry['handler_name']
            )
            if not is_valid:
                errors.append(f"Security validation failed for {entry['id']}: {error_msg}")
                continue

            # Create dataclass and upsert (one transaction per module)
            module_create = ModuleCatalogCreate(**entry)
            result = self.module_catalog_repo.upsert(module_create)
            results.append(result)

        except Exception as e:
            errors.append(f"Failed to sync {entry['id']}: {e}")

    return SyncResult(
        success_count=len(results),
        error_count=len(errors),
        errors=errors,
        synced_modules=results
    )
```

**No Cross-Service Transactions**:
- Module service is standalone (no orchestration with other services)
- Module execution during pipeline runs is orchestrated by Pipeline Service, not Module Service

### What Needs to Change

**Current Implementation** uses Pydantic models (ModuleCatalog, ModuleCatalogCreate, ModuleCatalogUpdate) throughout the stack.

**Redesign Required**:

1. **Convert Pydantic Models to Frozen Dataclasses** (in `shared/types/`):
   - Change ModuleCatalog, ModuleCatalogCreate, ModuleCatalogUpdate from Pydantic to frozen dataclasses
   - Keep ModuleMeta, IOShape, NodeGroup as Pydantic (they're used for validation)
   - Add new dataclasses: SyncResult, RegistryStats, ModuleCatalogSummary

2. **Update Service Method Signatures**:
   - Change all method signatures to accept/return frozen dataclasses
   - Remove Pydantic dependencies from service layer
   - Example: `get_module_catalog() → List[ModuleCatalog]` (dataclass, not Pydantic)

3. **Update Repository to Accept/Return Dataclasses**:
   - Repository already uses ModuleCatalog, but it's Pydantic currently
   - Change to frozen dataclass version
   - Update from_db_model() to create dataclass instead of Pydantic model
   - Update model_dump_for_db() to serialize dataclass fields

4. **Create Mapper Functions in Router** (Pydantic ↔ Dataclass):
   - Router receives Pydantic models from HTTP requests
   - Router maps Pydantic → dataclass before calling service
   - Service returns dataclass
   - Router maps dataclass → Pydantic for HTTP response
   - Example: map_module_catalog_to_response() function in router

5. **Add New Service Methods for Registration**:
   - Current service only has discovery methods (get_module_catalog, get_module_info, execute_module)
   - Add registration methods: register_module_from_class(), register_modules_from_registry(), sync_module_packages()
   - These methods are called by CLI tools (sync_modules.py), not by API endpoints

6. **Update CLI Tools**:
   - sync_modules.py currently calls repository directly
   - Change to call service methods (register_modules_from_registry)
   - Service handles security validation, error aggregation, result reporting

7. **Keep ModuleRegistry As-Is**:
   - ModuleRegistry is internal implementation detail
   - Uses BaseModule classes (not dataclasses, not Pydantic)
   - No changes needed for registry itself
   - Service acts as adapter between registry and dataclass-based API

### Implementation Notes

**Module Discovery Workflow** (Frontend):
1. Frontend requests GET /modules
2. Router calls service.get_module_catalog(only_active=True)
3. Service calls repository.get_all(only_active=True) → List[ModuleCatalog] (dataclass)
4. Service returns dataclasses to router
5. Router maps each dataclass → Pydantic response dict
6. FastAPI serializes to JSON response

**Module Registration Workflow** (Backend CLI):
1. Developer runs `python -m src.cli.sync_modules sync`
2. CLI tool calls service.register_modules_from_registry()
3. Service calls registry.to_catalog_format() → List[Dict]
4. Service validates each handler_name (security check)
5. Service creates ModuleCatalogCreate dataclass for each entry
6. Service calls repository.upsert() for each module (separate transactions)
7. Service returns SyncResult with success/error counts

**Module Execution Workflow** (Testing):
1. POST /modules/execute with module_id, inputs, config
2. Router maps Pydantic request → calls service.execute_module()
3. Service queries database for module metadata → ModuleCatalog (dataclass)
4. Service loads module class via registry (from cache or dynamic import)
5. Service validates config using module's ConfigModel (Pydantic)
6. Service creates execution context
7. Service calls module_instance.run(inputs, config, context)
8. Service returns outputs dict to router
9. Router wraps in Pydantic response

**Security Considerations**:
- handler_name strings must pass validation before dynamic import
- Whitelist: Only modules in src.features.modules.{transform,action,logic,comparator} allowed
- Blocklist: Path traversal (..), __pycache__, .pyc, exec, eval, os.system, subprocess patterns blocked
- Validation happens BOTH during sync (before DB insert) AND during dynamic loading (before import)

---
