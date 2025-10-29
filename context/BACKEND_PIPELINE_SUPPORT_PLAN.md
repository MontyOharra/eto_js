# Backend Plan: Add Pipeline Support to Template Version Creation

## Current Architecture Analysis

### Database Layer (Models)
**File**: `server/src/shared/database/models.py` (lines 208-231)

```python
class PdfTemplateVersionModel(BaseModel):
    id: Mapped[int]
    pdf_template_id: Mapped[int]
    version_num: Mapped[int]
    signature_objects: Mapped[str]  # JSON
    extraction_fields: Mapped[str]  # JSON
    pipeline_definition_id: Mapped[int]  # FK to pipeline_definitions (REQUIRED)
    # ... other fields
```

**Current Approach**: Uses foreign key to `pipeline_definitions` table (REQUIRED, not nullable).

---

### Domain Types
**File**: `server/src/shared/types/db/pdf_template_version.py`

**PdfTemplateVersionCreate** (lines 70-86):
```python
class PdfTemplateVersionCreate(PdfTemplateVersionBase):
    pdf_template_id: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    # ❌ NO pipeline_state
    # ❌ NO visual_state
```

**PdfTemplateVersion** (lines 25-67):
```python
class PdfTemplateVersion(PdfTemplateVersionBase):
    id: int
    version_num: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    # ❌ NO pipeline_state
    # ❌ NO visual_state
    # ❌ NO pipeline_definition_id
```

---

### Service Layer
**File**: `server/src/features/pdf_templates/service.py` (lines 473-500)

**create_template_version()** method:
```python
def create_template_version(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    # 1. Verify template exists
    # 2. Create version (repository will auto-calculate version number)
    # 3. Set as current version
    # ❌ DOES NOT handle pipeline creation
```

---

### Repository Layer
**File**: `server/src/shared/database/repositories/pdf_template_version.py` (lines 36-63)

**create()** method:
```python
def create(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    # 1. Calculate next version number
    # 2. Serialize objects to JSON via version_create.model_dump_for_db()
    # 3. Create database record
    # ❌ DOES NOT handle pipeline_definition_id (will FAIL because it's required)
```

---

### API Layer
**File**: `server/src/api/routers/pdf_templates.py` (lines 99-159)

**create_template_version()** endpoint:
```python
@router.post("/{template_id}/versions")
def create_template_version(
    template_id: int,
    request_data: PdfTemplateVersionCreateRequest,  # ❌ No pipeline fields
    template_service: PdfTemplateService = Depends(...)
) -> PdfTemplateVersion:
```

**File**: `server/src/api/schemas/pdf_templates.py` (lines 10-14)

**PdfTemplateVersionCreateRequest**:
```python
class PdfTemplateVersionCreateRequest(BaseModel):
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    signature_object_count: int
    # ❌ NO pipeline_state
    # ❌ NO visual_state
```

---

## Problem Summary

### ❌ Current State
1. API schema doesn't accept `pipeline_state` or `visual_state`
2. Domain `PdfTemplateVersionCreate` doesn't have pipeline fields
3. Domain `PdfTemplateVersion` doesn't expose pipeline data
4. Service doesn't create pipeline definitions
5. Repository fails because `pipeline_definition_id` is required but not provided

### ✅ Goal State
1. Accept `pipeline_state` and `visual_state` in API request (optional)
2. Store pipeline data by creating a `PipelineDefinition` record
3. Link template version to pipeline definition via FK
4. Return pipeline data when fetching template version

---

## Implementation Plan

## OPTION A: Inline Storage (Add New Columns) ⚠️ REQUIRES MIGRATION

Add `pipeline_state_json` and `visual_state_json` columns directly to `pdf_template_versions` table.

**Pros**: Simpler, no joins needed
**Cons**: Requires database migration, breaks existing architecture

## OPTION B: Use Existing FK Architecture ✅ RECOMMENDED

Keep using `pipeline_definitions` table via FK. Auto-create pipeline definition when creating template version.

**Pros**: No migration needed, maintains architecture, reuses existing pipeline infrastructure
**Cons**: Requires join to fetch pipeline data

---

## Detailed Implementation: Option B (Recommended)

### Phase 1: Update API Schema (5 minutes)

**File**: `server/src/api/schemas/pdf_templates.py`

```python
from typing import Optional
from shared.types import PipelineState, VisualState

class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new template version"""
    signature_objects: PdfObjects = Field(..., min_length=1, description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(default_factory=list, description="Fields to extract")
    signature_object_count: int = Field(..., ge=1, description="Count of signature objects")

    # NEW: Pipeline fields (optional)
    pipeline_state: Optional[PipelineState] = Field(None, description="Pipeline configuration")
    visual_state: Optional[VisualState] = Field(None, description="Visual layout for pipeline")
```

---

### Phase 2: Update Domain Types (10 minutes)

**File**: `server/src/shared/types/db/pdf_template_version.py`

#### Step 2.1: Update PdfTemplateVersionCreate

```python
from typing import Optional
from ..pipelines import PipelineState, VisualState

class PdfTemplateVersionCreate(PdfTemplateVersionBase):
    """Model for creating new template versions"""
    # Existing fields
    pdf_template_id: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]

    # NEW: Optional pipeline fields
    pipeline_state: Optional[PipelineState] = None
    visual_state: Optional[VisualState] = None

    def model_dump_for_db(self) -> dict:
        """Convert to database format with JSON serialization"""
        # Exclude pipeline fields - they'll be handled separately
        data = self.model_dump(exclude={
            'signature_objects',
            'extraction_fields',
            'pipeline_state',  # NEW
            'visual_state'     # NEW
        })

        # Serialize objects and fields to JSON for database storage
        data['signature_objects'] = self.signature_objects.to_json()
        data['extraction_fields'] = json.dumps([field.model_dump() for field in self.extraction_fields])

        # NOTE: pipeline_definition_id will be added by service layer
        return data
```

#### Step 2.2: Update PdfTemplateVersion to include pipeline data

```python
class PdfTemplateVersion(PdfTemplateVersionBase):
    """Complete template version with DB-generated fields"""
    id: int
    version_num: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime

    # NEW: Pipeline fields
    pipeline_definition_id: int
    pipeline_state: Optional[PipelineState] = None
    visual_state: Optional[VisualState] = None

    @classmethod
    def from_db_model(cls, db_model: PdfTemplateVersionModel) -> 'PdfTemplateVersion':
        """Create from database model with JSON deserialization"""
        # Parse signature objects
        if db_model.signature_objects:
            signature_objects = PdfObjects.from_json(db_model.signature_objects)

        # Parse extraction fields
        extraction_fields = []
        if db_model.extraction_fields:
            try:
                fields_data = json.loads(db_model.extraction_fields)
                extraction_fields = [ExtractionField(**field_data) for field_data in fields_data]
            except (json.JSONDecodeError, TypeError):
                pass

        # NEW: Parse pipeline data from related pipeline_definition
        pipeline_state = None
        visual_state = None
        if db_model.pipeline_definition:
            try:
                pipeline_state = PipelineState(**json.loads(db_model.pipeline_definition.pipeline_state))
                visual_state = VisualState(**json.loads(db_model.pipeline_definition.visual_state))
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

        return cls(
            id=db_model.id,
            pdf_template_id=db_model.pdf_template_id,
            version_num=db_model.version_num,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields,
            usage_count=db_model.usage_count,
            last_used_at=db_model.last_used_at,
            created_at=db_model.created_at,
            pipeline_definition_id=db_model.pipeline_definition_id,
            pipeline_state=pipeline_state,
            visual_state=visual_state
        )
```

---

### Phase 3: Update Service Layer (15 minutes)

**File**: `server/src/features/pdf_templates/service.py`

#### Step 3.1: Import pipeline dependencies

```python
from shared.types import PipelineState, VisualState, PipelineDefinitionCreate
from shared.database.repositories.pipeline_definition import PipelineDefinitionRepository
```

#### Step 3.2: Add pipeline repository to service

```python
class PdfTemplateService:
    def __init__(self, connection_manager):
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager

        # Existing repositories
        self.pdf_template_repo: PdfTemplateRepository = PdfTemplateRepository(self.connection_manager)
        self.pdf_template_version_repo: PdfTemplateVersionRepository = PdfTemplateVersionRepository(self.connection_manager)

        # NEW: Pipeline repository
        self.pipeline_definition_repo: PipelineDefinitionRepository = PipelineDefinitionRepository(self.connection_manager)

        logger.info("PDF Template Service initialized")
```

#### Step 3.3: Update create_template_version() method

```python
def create_template_version(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    """
    Create a new version of a PDF template

    Args:
        version_create: Template version create model with all required data

    Returns:
        Created template version (full domain object)

    Raises:
        ObjectNotFoundError: If the template doesn't exist
    """
    # 1. Verify the template exists
    template = self.pdf_template_repo.get_by_id(version_create.pdf_template_id)
    if not template:
        raise ObjectNotFoundError("PdfTemplate", version_create.pdf_template_id)

    # NEW: 2. Create pipeline definition if pipeline data provided
    pipeline_definition_id = None
    if version_create.pipeline_state and version_create.visual_state:
        logger.info(f"Creating pipeline definition for template version")

        # Create a PipelineDefinition with auto-generated name
        pipeline_create = PipelineDefinitionCreate(
            name=f"Template {version_create.pdf_template_id} Pipeline",
            description=f"Pipeline for template {template.name}",
            pipeline_state=version_create.pipeline_state,
            visual_state=version_create.visual_state
        )

        pipeline_definition = self.pipeline_definition_repo.create(pipeline_create)
        pipeline_definition_id = pipeline_definition.id
        logger.info(f"Created pipeline definition {pipeline_definition_id}")
    else:
        # No pipeline data provided - need to create empty pipeline or use default
        logger.warning("No pipeline data provided - creating empty pipeline definition")

        # Create empty pipeline
        empty_pipeline_create = PipelineDefinitionCreate(
            name=f"Template {version_create.pdf_template_id} Empty Pipeline",
            description="Empty pipeline (no transformation)",
            pipeline_state=PipelineState(entry_points=[], modules=[], connections=[]),
            visual_state=VisualState(modules={}, entry_points={})
        )

        pipeline_definition = self.pipeline_definition_repo.create(empty_pipeline_create)
        pipeline_definition_id = pipeline_definition.id

    # 3. Create the version (repository will auto-calculate version number)
    # Note: We need to pass pipeline_definition_id to repository
    version = self.pdf_template_version_repo.create(version_create, pipeline_definition_id)

    # 4. Set as current version
    updated_template = self.pdf_template_repo.set_current_version_id(version_create.pdf_template_id, version.id)
    if not updated_template:
        raise ObjectNotFoundError("PdfTemplate", version_create.pdf_template_id)

    return version
```

**ISSUE**: The repository `create()` method doesn't accept `pipeline_definition_id` as a parameter. We need to update it.

---

### Phase 4: Update Repository Layer (10 minutes)

**File**: `server/src/shared/database/repositories/pdf_template_version.py`

#### Update create() method signature

```python
def create(self, version_create: PdfTemplateVersionCreate, pipeline_definition_id: int) -> PdfTemplateVersion:
    """Create a new PDF template version from create model"""
    try:
        with self.connection_manager.session_scope() as session:
            # Calculate next version number for this template
            next_version_number = self._get_next_version_number(session, version_create.pdf_template_id)

            # Serialize objects to JSON for database storage
            version_data = version_create.model_dump_for_db()

            # NEW: Add pipeline_definition_id
            version_data['pipeline_definition_id'] = pipeline_definition_id

            model = self.model_class(
                version_num=next_version_number,
                **version_data
            )

            # Add to session and flush to get ID
            session.add(model)
            session.flush()

            # Refresh to get updated fields
            session.refresh(model)

            logger.debug(f"Created PDF template version with ID: {model.id}")
            return self._convert_to_domain_object(model)

    except SQLAlchemyError as e:
        logger.error(f"Error creating PDF template version: {e}")
        raise RepositoryError(f"Failed to create PDF template version: {e}") from e
```

---

### Phase 5: Update Router to Pass Pipeline Data (5 minutes)

**File**: `server/src/api/routers/pdf_templates.py` (lines 99-159)

```python
@router.post("/{template_id}/versions",
             response_model=PdfTemplateVersion,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new version of a PDF template",
             description="Create a new version of an existing PDF template with updated signature objects and extraction fields")
def create_template_version(
    template_id: int,
    request_data: PdfTemplateVersionCreateRequest,
    template_service: PdfTemplateService = Depends(
        lambda: ServiceContainer.get_pdf_template_service()
    ),
) -> PdfTemplateVersion:
    """
    Create a new version of a PDF template

    - **template_id**: ID of the existing template (from path)
    - **signature_objects**: PDF objects for template matching (required, min 1)
    - **extraction_fields**: Fields to extract from matching PDFs (optional)
    - **pipeline_state**: Pipeline configuration (optional)
    - **visual_state**: Visual layout for pipeline (optional)
    """
    try:
        if not template_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF template service is not available"
            )

        # Create domain model, adding pdf_template_id from URL parameter
        version_create = PdfTemplateVersionCreate(
            pdf_template_id=template_id,
            signature_objects=request_data.signature_objects,
            extraction_fields=request_data.extraction_fields,
            pipeline_state=request_data.pipeline_state,      # NEW
            visual_state=request_data.visual_state            # NEW
        )

        # Create the template version using the create model
        version = template_service.create_template_version(version_create)

        logger.info(f"Created version {version.version_num} for template {template_id}")

        return version

    except HTTPException:
        raise
    except ObjectNotFoundError as e:
        logger.warning(f"Template not found in create_template_version: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Value error in create_template_version: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating template version: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the template version"
        )
```

---

### Phase 6: Update create_template() to Handle Pipeline (10 minutes)

The `create_template()` method in the service also needs to be updated to handle initial pipeline data.

**File**: `server/src/features/pdf_templates/service.py` (lines 437-471)

Currently it creates the first version like this:

```python
# Create first version using create model
version_create = PdfTemplateVersionCreate(
    pdf_template_id=new_template_id,
    signature_objects=pdf_template_data.initial_signature_objects,
    extraction_fields=pdf_template_data.initial_extraction_fields,
)
version = self.pdf_template_version_repo.create(version_create)
```

This will break because `create()` now requires `pipeline_definition_id`. We need to update `PdfTemplateCreate` to include initial pipeline data as well.

**File**: `server/src/shared/types/db/pdf_template.py` (lines 60-68)

```python
class PdfTemplateCreate(PdfTemplateBase):
    """Model for creating new PDF templates"""

    initial_signature_objects: PdfObjects
    initial_extraction_fields: List[ExtractionField]

    # NEW: Optional initial pipeline
    initial_pipeline_state: Optional[PipelineState] = None
    initial_visual_state: Optional[VisualState] = None

    def model_dump_for_db(self) -> dict:
        return self.model_dump(exclude={
            'initial_signature_objects',
            'initial_extraction_fields',
            'initial_pipeline_state',   # NEW
            'initial_visual_state'      # NEW
        })
```

**Update create_template() in service**:

```python
def create_template(self, pdf_template_data: PdfTemplateCreate) -> PdfTemplate:
    """Create a new PDF template with its first version"""

    template = self.pdf_template_repo.create(pdf_template_data)
    new_template_id = template.id

    # NEW: Create pipeline definition for first version
    if pdf_template_data.initial_pipeline_state and pdf_template_data.initial_visual_state:
        pipeline_create = PipelineDefinitionCreate(
            name=f"Template {new_template_id} Pipeline v1",
            description=f"Pipeline for template {template.name} version 1",
            pipeline_state=pdf_template_data.initial_pipeline_state,
            visual_state=pdf_template_data.initial_visual_state
        )
        pipeline_definition = self.pipeline_definition_repo.create(pipeline_create)
        pipeline_definition_id = pipeline_definition.id
    else:
        # Create empty pipeline
        empty_pipeline_create = PipelineDefinitionCreate(
            name=f"Template {new_template_id} Empty Pipeline v1",
            description="Empty pipeline (no transformation)",
            pipeline_state=PipelineState(entry_points=[], modules=[], connections=[]),
            visual_state=VisualState(modules={}, entry_points={})
        )
        pipeline_definition = self.pipeline_definition_repo.create(empty_pipeline_create)
        pipeline_definition_id = pipeline_definition.id

    # Create first version using create model
    version_create = PdfTemplateVersionCreate(
        pdf_template_id=new_template_id,
        signature_objects=pdf_template_data.initial_signature_objects,
        extraction_fields=pdf_template_data.initial_extraction_fields,
        pipeline_state=pdf_template_data.initial_pipeline_state,    # NEW
        visual_state=pdf_template_data.initial_visual_state          # NEW
    )
    version = self.pdf_template_version_repo.create(version_create, pipeline_definition_id)  # Pass pipeline_definition_id

    # Set as current version
    template = self.pdf_template_repo.set_current_version_id(template.id, version.id)

    if not template:
        raise ObjectNotFoundError("PdfTemplate", new_template_id)

    return template
```

---

## Database Query Optimization

To fetch pipeline data when retrieving a template version, the repository needs to eagerly load the `pipeline_definition` relationship.

**File**: `server/src/shared/database/repositories/pdf_template_version.py`

Update `get_by_id()`:

```python
from sqlalchemy.orm import joinedload

def get_by_id(self, version_id: int) -> Optional[PdfTemplateVersion]:
    """Get PDF template version by ID with pipeline definition"""
    try:
        with self.connection_manager.session_scope() as session:
            model = session.query(self.model_class).options(
                joinedload(PdfTemplateVersionModel.pipeline_definition)  # Eager load
            ).filter(
                self.model_class.id == version_id
            ).first()

            if not model:
                return None
            return self._convert_to_domain_object(model)
    except SQLAlchemyError as e:
        logger.error(f"Error getting PDF template version {version_id}: {e}")
        raise RepositoryError(f"Failed to get PDF template version: {e}") from e
```

---

## Summary Checklist

### Phase 1: API Schema ✅
- [ ] Add `pipeline_state: Optional[PipelineState]` to `PdfTemplateVersionCreateRequest`
- [ ] Add `visual_state: Optional[VisualState]` to `PdfTemplateVersionCreateRequest`

### Phase 2: Domain Types ✅
- [ ] Add optional `pipeline_state` and `visual_state` to `PdfTemplateVersionCreate`
- [ ] Update `model_dump_for_db()` to exclude pipeline fields
- [ ] Add `pipeline_state`, `visual_state`, `pipeline_definition_id` to `PdfTemplateVersion`
- [ ] Update `from_db_model()` to parse pipeline data from related `pipeline_definition`
- [ ] Add initial pipeline fields to `PdfTemplateCreate`

### Phase 3: Service Layer ✅
- [ ] Import `PipelineState`, `VisualState`, `PipelineDefinitionCreate`
- [ ] Add `PipelineDefinitionRepository` to service `__init__`
- [ ] Update `create_template_version()` to:
  - Create pipeline definition if data provided
  - Create empty pipeline if no data provided
  - Pass `pipeline_definition_id` to repository
- [ ] Update `create_template()` to handle initial pipeline data

### Phase 4: Repository Layer ✅
- [ ] Update `create()` to accept `pipeline_definition_id` parameter
- [ ] Add `pipeline_definition_id` to version data before creating model
- [ ] Update `get_by_id()` to eagerly load `pipeline_definition` relationship

### Phase 5: Router ✅
- [ ] Update `create_template_version()` to pass pipeline fields to domain model

---

## Testing Plan

### Unit Tests (Repository)
```python
def test_create_version_with_pipeline():
    # Create pipeline definition first
    pipeline_create = PipelineDefinitionCreate(...)
    pipeline_def = pipeline_repo.create(pipeline_create)

    # Create version with pipeline
    version_create = PdfTemplateVersionCreate(
        pipeline_state=pipeline_state,
        visual_state=visual_state
    )
    version = version_repo.create(version_create, pipeline_def.id)

    assert version.pipeline_definition_id == pipeline_def.id
```

### Integration Tests (Service)
```python
def test_create_template_version_with_pipeline():
    version_create = PdfTemplateVersionCreate(
        pdf_template_id=1,
        signature_objects=...,
        extraction_fields=...,
        pipeline_state=PipelineState(...),
        visual_state=VisualState(...)
    )

    version = service.create_template_version(version_create)

    assert version.pipeline_state is not None
    assert version.visual_state is not None
    assert version.pipeline_definition_id > 0
```

### API Tests (E2E)
```bash
# Test creating version with pipeline
curl -X POST http://localhost:8090/pdf_templates/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "signature_objects": {...},
    "extraction_fields": [...],
    "signature_object_count": 5,
    "pipeline_state": {
      "entry_points": [...],
      "modules": [...],
      "connections": [...]
    },
    "visual_state": {
      "modules": {...},
      "entry_points": {...}
    }
  }'

# Expected: 201 Created with full version object including pipeline data

# Test creating version without pipeline
curl -X POST http://localhost:8090/pdf_templates/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "signature_objects": {...},
    "extraction_fields": [...],
    "signature_object_count": 5
  }'

# Expected: 201 Created with empty pipeline

# Test fetching version
curl http://localhost:8090/pdf_templates/1/versions/2

# Expected: Response includes pipeline_state and visual_state fields
```

---

## Estimated Time: 50-60 minutes

| Phase | Time |
|-------|------|
| Phase 1: API Schema | 5 min |
| Phase 2: Domain Types | 10 min |
| Phase 3: Service Layer | 15 min |
| Phase 4: Repository | 10 min |
| Phase 5: Router | 5 min |
| Phase 6: Update create_template | 10 min |
| Testing | 10-15 min |
| **Total** | **55-70 min** |

---

## Notes

- ✅ **No database migration required** - uses existing `pipeline_definition_id` FK
- ✅ **Maintains existing architecture** - reuses pipeline infrastructure
- ✅ **Backward compatible** - can create versions without pipeline (creates empty pipeline)
- ⚠️ **Creates extra pipeline records** - each version creates a pipeline definition
- ⚠️ **Repository signature change** - `create()` now requires `pipeline_definition_id` parameter

---

## Alternative: Make pipeline_definition_id Optional

If you want to avoid creating empty pipelines, you could make `pipeline_definition_id` nullable in the database:

```python
pipeline_definition_id: Mapped[Optional[int]] = mapped_column(
    ForeignKey("pipeline_definitions.id"),
    nullable=True,  # Change to nullable
    index=True
)
```

Then update service to only create pipeline if data is provided:

```python
pipeline_definition_id = None
if version_create.pipeline_state and version_create.visual_state:
    pipeline_definition = self.pipeline_definition_repo.create(pipeline_create)
    pipeline_definition_id = pipeline_definition.id

version = self.pdf_template_version_repo.create(version_create, pipeline_definition_id)
```

**This requires a database migration** to make the column nullable.
