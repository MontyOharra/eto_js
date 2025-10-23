# Session Continuity Document

**Date**: 2025-10-23
**Session Focus**: PDF Objects Typing Implementation, PDF Template Types & Smart Update Logic

---

## Current Session Summary

### What Was Accomplished

1. **Implemented Full PDF Objects Typing (Complete Stack)**
   - **Types Layer** (`server-new/src/shared/types/pdf_files.py`):
     - Created 7 object type dataclasses (TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table)
     - Created PdfExtractedObjects container with keyed structure
     - Added serialization helpers (serialize/deserialize)
     - Updated PdfMetadata and PdfCreate to use typed PdfExtractedObjects

   - **Repository Layer** (`server-new/src/shared/database/repositories/pdf.py`):
     - Updated imports for typed dataclasses and serialization helpers
     - Updated `_model_to_dataclass()` to deserialize JSON → typed objects with error handling
     - Updated `create()` to serialize typed objects → JSON

   - **Service Layer** (`server-new/src/features/pdf_files/service.py`):
     - Updated `_extract_objects_from_file()` to return PdfExtractedObjects (creates typed dataclasses directly)
     - Updated `extract_objects_from_bytes()` return type to PdfExtractedObjects
     - Updated `get_pdf_objects()` return type to PdfExtractedObjects
     - Updated `store_pdf()` to work with typed objects throughout

   - **API Layer** (`server-new/src/api/routers/pdf_files.py`):
     - Added `_convert_to_pydantic_objects()` helper to convert dataclasses → Pydantic
     - Updated GET `/{id}/objects` endpoint to use GetPdfObjectsResponse
     - Updated POST `/process-objects` endpoint to use ProcessPdfObjectsResponse

2. **Created PDF Template Types** (`server-new/src/shared/types/pdf_templates.py`)
   - **12 Core Dataclasses**:
     - TemplateMetadata, TemplateSummary, TemplateWithVersion
     - TemplateCreate, TemplateUpdate, TemplateMetadataUpdate, TemplateStatusUpdate
     - TemplateVersion, VersionCreate, VersionSummary
     - SignatureObject, SignatureObjects (KEYED STRUCTURE - breaking change)
     - ExtractionField
   - **4 Serialization Helpers**:
     - serialize/deserialize_signature_objects()
     - serialize/deserialize_extraction_fields()
   - **All types frozen** for immutability
   - **Keyed object structure** matching PdfExtractedObjects pattern

3. **Updated Design Documentation with Smart Update Logic**
   - Updated `context/server_redesign/SERVICE_LAYER_DESIGN_V2.md`
   - Documented smart update strategy for `update_template()` method:
     - **Metadata-only changes** (name, description): Update template only, no new version
     - **Wizard data changes** (signature_objects, extraction_fields, pipeline_definition_id): Create new version
     - **Status changes**: Handled by separate activate/deactivate endpoints
   - Added detailed implementation with branching logic
   - Documented repository calls for each branch

---

## Current State of Codebase

### ✅ Completed Features

**Email Domain (100% Complete)**:
- ✅ Email integration types (`shared/types/email_integrations.py`)
- ✅ Email config types (`shared/types/email_configs.py`)
- ✅ Email ingestion types (`shared/types/email_ingestion.py`)
- ✅ EmailConfigRepository (`shared/database/repositories/email_config.py`)
- ✅ EmailRepository (`shared/database/repositories/email.py`)
- ✅ EmailIngestionService (`features/email_ingestion/service.py`)
- ✅ EmailListenerThread (`features/email_ingestion/utils/email_listener_thread.py`)
- ✅ EmailConfigService (`features/email_configs/service.py`)
- ✅ Filter rule checking logic with proper type handling
- ✅ Complete type hints throughout

**PDF Files Domain (100% Complete - Types, Repository, Service)**:
- ✅ PDF file types with strongly-typed extracted objects (`shared/types/pdf_files.py`)
- ✅ PdfRepository with typed serialization/deserialization (`shared/database/repositories/pdf.py`)
- ✅ PdfFilesService with typed object extraction (`features/pdf_files/service.py`)
- ✅ API router with Pydantic conversion layer (`api/routers/pdf_files.py`)
- ✅ Full type safety from extraction through API response

**PDF Templates Domain (30% Complete - Types Only)**:
- ✅ Template types with smart update support (`shared/types/pdf_templates.py`)
- ✅ Version types for immutable snapshots
- ✅ Wizard data types with keyed structure (BREAKING CHANGE)
- ✅ Serialization helpers for JSON conversion
- ✅ Design documentation with smart update logic
- ❌ TemplateRepository (not yet implemented)
- ❌ TemplateVersionRepository (not yet implemented)
- ❌ TemplateManagementService (not yet implemented)
- ❌ API router (not yet implemented)

**Shared Infrastructure**:
- ✅ Database connection manager (synchronous)
- ✅ Unit of Work pattern
- ✅ Base repository with `model_class` pattern
- ✅ Exception hierarchy (repository + service layers)
- ✅ Type system using `T | None` instead of `Optional[T]`

### 🔨 In Progress

**PDF Templates Domain (30% Complete)**:
- ✅ Types defined
- 📍 Ready to implement repositories
- 📍 Ready to implement service with smart update logic
- 📍 Ready to implement API router

### 📋 Next Steps (Priority Order)

1. **Complete PDF Templates Domain**
   - Create TemplateRepository in `shared/database/repositories/template.py`
   - Create TemplateVersionRepository in `shared/database/repositories/template_version.py`
   - Implement TemplateManagementService in `features/template_management/service.py`
   - Create API router in `api/routers/pdf_templates.py`
   - **Database migration** to convert signature_objects from array to keyed structure
   - **Frontend updates** to work with keyed signature objects

2. **Implement Remaining Service Domains**
   - EtoProcessingService
   - PipelineService (if not already implemented)

---

## PDF Templates Domain - Implementation Checklist

### Types ✅ COMPLETE
- ✅ All 12 dataclasses created
- ✅ Serialization helpers implemented
- ✅ Smart update types (TemplateUpdate, TemplateMetadataUpdate)
- ✅ Keyed SignatureObjects structure

### Repositories to Create

**TemplateRepository** (`shared/database/repositories/template.py`):
- [ ] Implement with `model_class = TemplateModel` (or whatever the model is called)
- [ ] `get_by_id(template_id)` → TemplateMetadata | None
- [ ] `get_by_id_with_current_version(template_id)` → TemplateWithVersion | None
- [ ] `list_with_pagination(status_filter, sort_by, sort_order, limit, offset)` → tuple[list[TemplateSummary], int]
- [ ] `create(template_data: TemplateCreate)` → TemplateMetadata
- [ ] `update(template_id: int, template_update: TemplateMetadataUpdate)` → TemplateMetadata
- [ ] `delete(template_id: int)` → None
- [ ] `update_status(template_id: int, status_update: TemplateStatusUpdate)` → TemplateMetadata
- [ ] Helper: `_model_to_dataclass()` for ORM→dataclass conversion

**TemplateVersionRepository** (`shared/database/repositories/template_version.py`):
- [ ] Implement with `model_class = TemplateVersionModel` (or whatever the model is called)
- [ ] `get_by_id(version_id)` → TemplateVersion | None
- [ ] `get_by_template_id(template_id)` → list[TemplateVersion]
- [ ] `get_versions_summary(template_id)` → list[VersionSummary]
- [ ] `create(version_data: VersionCreate)` → TemplateVersion
- [ ] `delete(version_id: int)` → None
- [ ] Helper: `_model_to_dataclass()` for ORM→dataclass conversion
- [ ] Helper: Need to serialize/deserialize SignatureObjects using helper functions

### TemplateManagementService (`features/template_management/service.py`)

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    pdf_service: PdfFilesService,
    pipeline_service: PipelineService  # May not exist yet
) -> None:
    self.connection_manager = connection_manager
    self.pdf_service = pdf_service
    self.pipeline_service = pipeline_service  # Optional for now

    self.template_repository = TemplateRepository(connection_manager=connection_manager)
    self.version_repository = TemplateVersionRepository(connection_manager=connection_manager)
    self.pdf_repository = PdfRepository(connection_manager=connection_manager)
```

**Public Methods** (in priority order):

1. [ ] `list_templates(status, sort_by, sort_order, limit, offset)` → TemplateListResult
   - Simple delegation to repository with pagination
   - Used by: `GET /pdf-templates`

2. [ ] `get_template(template_id)` → TemplateWithVersion
   - Get template with current version
   - Used by: `GET /pdf-templates/{id}`

3. [ ] `create_template(template_data: TemplateCreate)` → TemplateMetadata
   - Validate signature objects and extraction fields
   - Create template + version 1 atomically (UoW)
   - Set status to "draft" or "inactive"
   - Used by: `POST /pdf-templates`

4. [ ] `update_template(template_id, template_data: TemplateUpdate)` → TemplateMetadata
   - **SMART UPDATE LOGIC**:
     - Check if wizard data changed (signature_objects, extraction_fields, pipeline_definition_id)
     - If changed: validate, create new version, update current_version_id
     - If not changed: update metadata only (name, description)
   - Used by: `PUT /pdf-templates/{id}`

5. [ ] `delete_template(template_id)` → None
   - Check if template has been used (check version usage_count)
   - If used: raise ConflictError (suggest deactivate instead)
   - Delete all versions first, then template (UoW)
   - Used by: `DELETE /pdf-templates/{id}`

6. [ ] `activate_template(template_id)` → TemplateMetadata
   - Set status to "active"
   - Record activated_at timestamp
   - Used by: `POST /pdf-templates/{id}/activate`

7. [ ] `deactivate_template(template_id)` → TemplateMetadata
   - Set status to "inactive"
   - Used by: `POST /pdf-templates/{id}/deactivate`

8. [ ] `list_versions(template_id)` → list[VersionSummary]
   - Get version history for template
   - Used by: `GET /pdf-templates/{id}/versions`

9. [ ] `get_version(template_id, version_id)` → TemplateVersion
   - Get specific version details
   - Used by: `GET /pdf-templates/{id}/versions/{version_id}`

10. [ ] `simulate_template(template_data, pdf_bytes)` → SimulationResult (if time allows)
    - Test template without persistence
    - Used by: `POST /pdf-templates/simulate`

**Internal Methods**:

11. [ ] `_validate_template_fields(signature_objects, extraction_fields)` → None
    - Validate field references point to valid signature objects
    - Validate no duplicate field names
    - Validate object_ids exist in signature_objects

---

## Breaking Change: SignatureObjects Structure

### Migration Required

**Old Format (array)**:
```json
{
  "signature_objects": [
    {"id": "1", "type": "text_word", "page": 0, "bbox": [10, 20, 30, 40], ...},
    {"id": "2", "type": "graphic_rect", "page": 0, "bbox": [50, 60, 70, 80], ...}
  ]
}
```

**New Format (keyed by type)**:
```json
{
  "signature_objects": {
    "text_words": [
      {"id": "1", "page": 0, "bbox": [10, 20, 30, 40], "object_type": "text_word", ...}
    ],
    "text_lines": [],
    "graphic_rects": [
      {"id": "2", "page": 0, "bbox": [50, 60, 70, 80], "object_type": "graphic_rect", ...}
    ],
    "graphic_lines": [],
    "graphic_curves": [],
    "images": [],
    "tables": []
  }
}
```

### Migration Steps

1. **Database Migration Script** (Python):
   - Read all existing template_versions records
   - For each version:
     - Parse old signature_objects JSON
     - Convert array to keyed structure by grouping by type
     - Add object_type field to each object
     - Write back to database
   - Test on dev database first

2. **Frontend Template Builder Updates**:
   - Update signature object selection to work with keyed structure
   - Update rendering to iterate over keyed groups
   - Update field configuration to reference objects in keyed structure

### Why This Change?

- **Consistency**: Matches PdfExtractedObjects keyed structure
- **Efficiency**: Type-based filtering without iteration
- **Type Safety**: Clear structure for each object type
- **Matching Logic**: ETO matching can efficiently compare by type

---

## Key Design Patterns to Follow

### Repository Pattern
- Use `model_class` abstract property
- Use `session.get(self.model_class, id)` for primary key lookups
- Use `session.query(self.model_class)` for queries
- Helper method `_model_to_dataclass()` for conversions
- Serialization helpers in types layer, called by repository
- Only CRUD methods (no business logic)

### Service Pattern
- Constructor takes dependencies (connection_manager, other services)
- Lazy-load repositories in constructor
- Proper exception handling:
  - Preserve `ObjectNotFoundError` (404)
  - Preserve `ValidationError` (400)
  - Preserve `ConflictError` (409)
  - Wrap infrastructure failures as `ServiceError` (500)
- Delegate complex operations to other services
- Use UnitOfWork for multi-table transactions

### Type System
- Use `T | None` instead of `Optional[T]`
- Use frozen dataclasses for domain types
- All parameters and return types fully typed
- Class variables annotated
- Serialization helpers in types layer (not repository)

### Smart Update Logic (Templates Only)
- Check what fields changed in TemplateUpdate
- Branch on wizard data vs metadata changes
- Create version only when needed
- Clear logging for each branch

---

## Important Technical Details

### Serialization Pattern (PDF Objects & Template Objects)

**In Types Layer** (`shared/types/`):
```python
def serialize_extracted_objects(objects: PdfExtractedObjects) -> dict:
    """Convert dataclass to dict for JSON storage"""
    return asdict(objects)

def deserialize_extracted_objects(objects_dict: dict) -> PdfExtractedObjects:
    """Convert dict to dataclass from JSON"""
    return PdfExtractedObjects(
        text_words=[TextWord(**obj) for obj in objects_dict.get("text_words", [])],
        # ... etc
    )
```

**In Repository Layer**:
```python
def _model_to_dataclass(self, model: PdfFileModel) -> PdfMetadata:
    # Deserialize JSON → dict → typed dataclass
    objects_dict = json.loads(model.objects_json)
    extracted_objects = deserialize_extracted_objects(objects_dict)
    return PdfMetadata(..., extracted_objects=extracted_objects)

def create(self, pdf_data: PdfCreate) -> PdfMetadata:
    # Serialize typed dataclass → dict → JSON
    objects_dict = serialize_extracted_objects(pdf_data.extracted_objects)
    objects_json = json.dumps(objects_dict)
    # ... create model with objects_json
```

**Same pattern applies to SignatureObjects in template repositories**

### Database Field Mappings

**PDF Files** (already implemented):
- `objects_json` (TEXT) ↔ `extracted_objects` (PdfExtractedObjects dataclass)

**Templates** (to be implemented):
- `signature_objects_json` (TEXT) ↔ `signature_objects` (SignatureObjects dataclass)
- `extraction_fields_json` (TEXT) ↔ `extraction_fields` (list[ExtractionField])

---

## Architecture Decisions

### Core Principles
- **Synchronous Only**: No async/await in backend (SQL Server limitation)
- **Dataclasses for Domain**: Frozen dataclasses for immutability
- **Dual-Mode Repositories**: Work standalone or within UoW transactions
- **Service Layer Separation**: Clear boundaries between services
- **Type Safety**: Full type hints, Literal types for enums
- **Keyed Object Structures**: Group objects by type for efficiency

### File Locations
- Types: `server-new/src/shared/types/`
- Repositories: `server-new/src/shared/database/repositories/`
- Services: `server-new/src/features/{domain}/service.py`
- Models: `server-new/src/shared/database/models.py`
- Exceptions: `server-new/src/shared/exceptions/`
- API Routers: `server-new/src/api/routers/`

### Common Pitfalls to Avoid
- ❌ Don't use async/await
- ❌ Don't use `Optional[T]` (use `T | None`)
- ❌ Don't put business logic in repositories
- ❌ Don't use `select()` statements (use `session.query()`)
- ❌ Don't hardcode model classes (use `model_class` property)
- ❌ Don't put serialization logic in repositories (belongs in types layer)

---

## Files Modified This Session

1. **server-new/src/shared/types/pdf_files.py** (modified, +250 lines)
   - Added 7 object type dataclasses
   - Added PdfExtractedObjects container
   - Added serialization helpers
   - Updated PdfMetadata and PdfCreate

2. **server-new/src/shared/database/repositories/pdf.py** (modified, +30 lines)
   - Updated imports for typed dataclasses
   - Updated `_model_to_dataclass()` with deserialization
   - Updated `create()` with serialization

3. **server-new/src/features/pdf_files/service.py** (modified, ~150 lines)
   - Updated `_extract_objects_from_file()` to create typed objects
   - Updated all public method return types
   - Updated `store_pdf()` to work with typed objects

4. **server-new/src/api/routers/pdf_files.py** (modified, +80 lines)
   - Added `_convert_to_pydantic_objects()` helper
   - Updated endpoints to use typed responses

5. **server-new/src/shared/types/pdf_templates.py** (NEW, 300+ lines)
   - Created 12 dataclasses for templates/versions/wizard data
   - Created 4 serialization helpers
   - SignatureObjects keyed structure

6. **context/server_redesign/SERVICE_LAYER_DESIGN_V2.md** (modified)
   - Updated `update_template()` with smart update logic
   - Documented branching behavior
   - Added version_created flag to return type

---

## Reference Examples for Next Implementation

When implementing TemplateRepository and TemplateVersionRepository, use these as reference:

1. **For typed object serialization**: See `PdfRepository` (lines 46-89, 129-161)
2. **For filter rules serialization**: See `EmailConfigRepository` (lines 40-70)
3. **For list/pagination**: See `EmailConfigRepository.get_all_summaries()` (lines 104-136)
4. **For composite queries**: See `PdfRepository.get_by_hash()` (lines 111-127)

When implementing TemplateManagementService, use these as reference:

1. **For smart update logic**: See updated design in SERVICE_LAYER_DESIGN_V2.md (lines 3307-3477)
2. **For UoW transactions**: See EmailConfigService methods (activate/deactivate patterns)
3. **For validation logic**: See PdfFilesService._validate_pdf() pattern
4. **For file operations**: See PdfFilesService.store_pdf() pattern

---

## Questions to Resolve Before Starting Templates Implementation

1. **Model Names**: What are the actual model class names?
   - TemplateModel or PdfTemplateModel?
   - TemplateVersionModel or PdfTemplateVersionModel?

2. **Database Fields**: Confirm JSON field names in database:
   - `signature_objects_json` or `signature_objects`?
   - `extraction_fields_json` or `extraction_fields`?

3. **Pipeline Service**: Does PipelineService exist yet?
   - If not, template creation/updates can skip pipeline validation for now
   - Can use `pipeline_definition_id: int | None` without compilation

4. **Migration Timing**: When should signature_objects migration run?
   - Before or after repository implementation?
   - Need existing templates in database to test migration?

---

## Session Handoff Notes

The PDF Files domain typing is now 100% complete with strong type safety from extraction through API response. All layers (types, repository, service, API) have been updated and work together seamlessly.

The PDF Templates domain types are complete and ready for implementation. The smart update logic is fully designed and documented. The keyed SignatureObjects structure is a breaking change that will require database migration and frontend updates, but provides better consistency and efficiency.

Next session should focus on implementing TemplateRepository and TemplateVersionRepository first, followed by TemplateManagementService with the smart update logic. Once complete, create the API router and Pydantic schemas.

The pattern established for PDF objects typing can be directly applied to template signature objects - same serialization approach, same keyed structure, same frozen dataclass pattern.
