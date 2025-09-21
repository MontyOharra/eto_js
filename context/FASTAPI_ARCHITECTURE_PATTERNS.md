# FastAPI Architecture Patterns - PDF Template Implementation

> This document captures the specific implementation strategies, patterns, and architectural decisions used in the PDF Template feature. Use this as a reference when implementing other FastAPI services to maintain consistency.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Type System Design](#type-system-design)
3. [Repository Pattern](#repository-pattern)
4. [Service Layer](#service-layer)
5. [API Layer](#api-layer)
6. [Error Handling](#error-handling)
7. [File Structure](#file-structure)
8. [Key Implementation Details](#key-implementation-details)

---

## Architecture Overview

The PDF Template implementation follows a **clean architecture pattern** with clear separation of concerns:

```
API Layer (FastAPI) 
    ↓ (Domain Models)
Service Layer (Business Logic)
    ↓ (Domain Models)  
Repository Layer (Data Access)
    ↓ (SQLAlchemy Models)
Database Layer
```

### Core Principles:
- **Domain models flow through all layers** - No manual conversions between layers
- **Single source of truth** - Domain models in `shared/models/` define business rules
- **Automatic type conversion** - Pydantic handles SQLAlchemy ↔ Domain model conversion
- **Explicit error handling** - Business exceptions for domain errors, HTTP exceptions for API errors

---

## Type System Design

### Hierarchical Model Structure

Located in `eto_server/src/shared/models/pdf_template.py`

#### **Base Models** - Core business fields only
```python
class PdfTemplateBase(BaseModel):
    """Core fields required for any PDF template"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: int = Field(..., description="ID of the source PDF file")
    status: str = Field("active", pattern="^(active|inactive)$")
    
    class Config:
        from_attributes = True  # Enables SQLAlchemy conversion
```

#### **Create Models** - For creation operations
```python
class PdfTemplateCreate(PdfTemplateBase):
    """Model for creating new PDF templates"""
    # Inherits: name, description, source_pdf_id, status
    
    # Additional creation-specific fields
    initial_signature_objects: List[PdfObject]
    initial_extraction_fields: List[ExtractionField]
    
    def model_dump_for_db(self) -> dict:
        """Exclude fields not stored in main table"""
        return self.model_dump(exclude={'initial_signature_objects', 'initial_extraction_fields'})
```

#### **Update Models** - For partial updates
```python
class PdfTemplateUpdate(BaseModel):
    """Model for updating existing PDF templates"""
    # Only updatable fields - excludes immutable source_pdf_id
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
```

#### **Domain Models** - Complete objects with DB-generated fields
```python
class PdfTemplate(PdfTemplateBase):
    """Complete PDF template with DB-generated fields"""
    # Inherits: name, description, source_pdf_id, status
    
    # DB-generated fields
    id: int = Field(..., description="Template ID (DB-generated)")
    current_version_id: Optional[int] = Field(None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
```

### Version Models with JSON Serialization

```python
class PdfTemplateVersionCreate(PdfTemplateVersionBase):
    """Model for creating new template versions"""
    # Repository auto-calculates version numbers
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format with JSON serialization"""
        data = self.model_dump(exclude={'signature_objects', 'extraction_fields'})
        
        # Serialize complex objects to JSON for database storage
        data['signature_objects'] = json.dumps([obj.model_dump() for obj in self.signature_objects])
        data['extraction_fields'] = json.dumps([field.model_dump() for field in self.extraction_fields])
        
        return data
```

### IDE Type Inference Support

For complex inheritance hierarchies, add explicit type annotations:

```python
class PdfTemplateVersionCreate(PdfTemplateVersionBase):
    # Explicit type annotations for IDE support (inherits Field definitions from base)
    pdf_template_id: int
    signature_objects: List[PdfObject]
    extraction_fields: List[ExtractionField]
    signature_object_count: int
```

---

## Repository Pattern

Located in `eto_server/src/shared/database/repositories/pdf_template.py`

### Base Repository Structure

```python
class PdfTemplateRepository(BaseRepository[PdfTemplateModel]):
    """Repository for PDF template operations"""
    
    @property
    def model_class(self):
        return PdfTemplateModel
    
    def _convert_to_domain_object(self, model: PdfTemplateModel) -> PdfTemplate:
        """Convert SQLAlchemy model to Pydantic domain object"""
        return PdfTemplate.model_validate(model)  # Automatic conversion via from_attributes=True
```

### Session-Scoped Operations

All database operations use session scope pattern:

```python
def create(self, template_create: PdfTemplateCreate) -> PdfTemplate:
    """Create a new PDF template from create model"""
    try:
        with self.connection_manager.session_scope() as session:
            # Convert create model to SQLAlchemy model
            model_data = template_create.model_dump_for_db()
            model = self.model_class(**model_data)
            
            # Standard pattern: add, flush, refresh, convert
            session.add(model)
            session.flush()  # Get ID without committing
            session.refresh(model)  # Load updated fields
            
            return self._convert_to_domain_object(model)
    except SQLAlchemyError as e:
        logger.error(f"Error creating PDF template: {e}")
        raise RepositoryError(f"Failed to create PDF template: {e}") from e
```

### Update Operations with Partial Data

```python
def update(self, template_id: int, update_data: PdfTemplateUpdate) -> Optional[PdfTemplate]:
    """Update a PDF template with the provided data"""
    try:
        with self.connection_manager.session_scope() as session:
            model = session.get(self.model_class, template_id)
            if not model:
                return None
            
            # Update only fields that are provided (exclude_unset=True)
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(model, field):
                    setattr(model, field, value)
            
            # Auto-update timestamp
            model.updated_at = datetime.now(timezone.utc)
            
            session.flush()
            session.refresh(model)
            return self._convert_to_domain_object(model)
    except SQLAlchemyError as e:
        raise RepositoryError(f"Failed to update PDF template: {e}") from e
```

### Auto-Generated Fields Pattern

For fields that should be calculated by the repository (like version numbers):

```python
def create(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    """Create a new PDF template version from create model"""
    try:
        with self.connection_manager.session_scope() as session:
            # Calculate auto-generated fields
            next_version_number = self._get_next_version_number(session, version_create.pdf_template_id)
            
            # Serialize complex objects to JSON
            version_data = version_create.model_dump_for_db()
            
            model = self.model_class(
                version_num=next_version_number,  # Auto-generated
                **version_data
            )
            
            session.add(model)
            session.flush()
            session.refresh(model)
            
            return self._convert_to_domain_object(model)
```

---

## Service Layer

Located in `eto_server/src/features/pdf_templates/service.py`

### Service Class Structure

```python
class PdfTemplateService:
    """Service for PDF template matching and management"""

    def __init__(self, connection_manager):
        # Explicit type annotations for IDE support
        self.pdf_template_repo: PdfTemplateRepository = PdfTemplateRepository(connection_manager)
        self.pdf_template_version_repo: PdfTemplateVersionRepository = PdfTemplateVersionRepository(connection_manager)
```

### Business Logic Coordination

Services coordinate between repositories and implement business rules:

```python
def create_template(self, pdf_template_data: PdfTemplateCreate) -> PdfTemplate:
    """Create a new PDF template with its first version"""
    # Create template
    template = self.pdf_template_repo.create(pdf_template_data)
    
    # Create first version
    version_create = PdfTemplateVersionCreate(
        pdf_template_id=template.id,
        signature_objects=pdf_template_data.initial_signature_objects,
        extraction_fields=pdf_template_data.initial_extraction_fields,
        signature_object_count=len(pdf_template_data.initial_signature_objects)
    )
    version = self.pdf_template_version_repo.create(version_create)
    
    # Set as current version
    template = self.pdf_template_repo.set_current_version_id(template.id, version.id)
    if not template:
        raise ObjectNotFoundError("PdfTemplate", template.id)
    
    return template
```

### Early Validation Pattern

Validate business rules before expensive operations:

```python
def create_template_version(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    """Create a new version of a PDF template"""
    # Early validation - template must exist
    template = self.pdf_template_repo.get_by_id(version_create.pdf_template_id)
    if not template:
        raise ObjectNotFoundError("PdfTemplate", version_create.pdf_template_id)
    
    # Proceed with creation
    version = self.pdf_template_version_repo.create(version_create)
    # ... rest of logic
```

---

## API Layer

Located in `eto_server/src/api/routers/pdf_templates.py`

### Direct Domain Model Usage

FastAPI routes accept and return domain models directly:

```python
@router.post("/", response_model=PdfTemplate, status_code=status.HTTP_201_CREATED)
def create_template(template_create: PdfTemplateCreate) -> PdfTemplate:
    """Create a new PDF template"""
    # No conversion needed - use domain model directly
    template = template_service.create_template(template_create)
    return template
```

### API-Specific Request Types

When URL parameters need to be excluded from request body:

```python
# In api/schemas/pdf_templates.py
class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new template version (excludes pdf_template_id from URL path)"""
    signature_objects: List[PdfObject] = Field(..., min_length=1)
    extraction_fields: List[ExtractionField] = Field(default_factory=list)
    signature_object_count: int = Field(..., ge=1)

# In router
@router.post("/{template_id}/versions")
def create_template_version(
    template_id: int,
    request_data: PdfTemplateVersionCreateRequest
) -> PdfTemplateVersion:
    # Convert API request to domain model
    version_create = PdfTemplateVersionCreate(
        pdf_template_id=template_id,  # From URL
        signature_objects=request_data.signature_objects,
        extraction_fields=request_data.extraction_fields,
        signature_object_count=request_data.signature_object_count
    )
    return template_service.create_template_version(version_create)
```

### Enhanced Response Types

For complex API responses with optional data:

```python
# In api/schemas/pdf_templates.py
class TemplateDetailResponse(BaseModel):
    """Enhanced response for template details with optional includes"""
    template: PdfTemplate = Field(...)
    pdf_data: Optional[bytes] = Field(None, description="PDF file bytes (if requested)")
    current_version: Optional[PdfTemplateVersion] = Field(None)
    version_list: Optional[List[TemplateVersionSummary]] = Field(None)
    total_versions: Optional[int] = Field(None)

# Usage with query parameters
@router.get("/{template_id}")
def get_template(
    template_id: int,
    include_pdf: bool = Query(False),
    include_current_version: bool = Query(False),
    include_version_list: bool = Query(False)
) -> TemplateDetailResponse:
    # Conditionally load heavy data based on query params
```

---

## Error Handling

### Exception Hierarchy

Domain exceptions for business logic errors:

```python
# shared/exceptions.py
class ObjectNotFoundError(Exception):
    """Raised when a requested object doesn't exist"""
    def __init__(self, object_type: str, object_id: Any):
        self.object_type = object_type
        self.object_id = object_id
        super().__init__(f"{object_type} with id {object_id} not found")
```

### API Error Conversion

Convert domain exceptions to appropriate HTTP responses:

```python
@router.post("/{template_id}/versions")
def create_template_version(...):
    try:
        # Business logic
        return template_service.create_template_version(version_create)
    
    except HTTPException:
        raise  # Re-raise FastAPI exceptions as-is
        
    except ObjectNotFoundError as e:
        # Convert domain exception to HTTP 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
    except ValueError as e:
        # Convert validation errors to HTTP 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail="An unexpected error occurred")
```

---

## File Structure

```
eto_server/src/
├── shared/
│   ├── models/
│   │   ├── __init__.py              # Export all domain models
│   │   ├── pdf_template.py          # Complete type hierarchy
│   │   ├── pdf_processing.py        # Supporting types (PdfObject, ExtractionField)
│   │   └── common.py               # Shared types (TemplateMatchResult)
│   │
│   ├── database/
│   │   ├── repositories/
│   │   │   ├── pdf_template.py      # Template CRUD operations
│   │   │   └── pdf_template_version.py  # Version CRUD operations
│   │   └── models.py               # SQLAlchemy models
│   │
│   └── exceptions.py               # Domain exceptions
│
├── features/
│   └── pdf_templates/
│       └── service.py              # Business logic coordination
│
└── api/
    ├── schemas/
    │   ├── __init__.py             # Export all API schemas
    │   └── pdf_templates.py        # API-specific request/response types
    │
    └── routers/
        └── pdf_templates.py        # FastAPI route definitions
```

---

## Key Implementation Details

### 1. Automatic Type Conversion

The `from_attributes = True` configuration enables seamless conversion:

```python
# Repository can return domain objects directly
def _convert_to_domain_object(self, model: PdfTemplateModel) -> PdfTemplate:
    return PdfTemplate.model_validate(model)  # Automatic SQLAlchemy → Pydantic
```

### 2. JSON Serialization for Complex Fields

Store nested objects as JSON in database:

```python
def model_dump_for_db(self) -> dict:
    data = self.model_dump(exclude={'signature_objects', 'extraction_fields'})
    data['signature_objects'] = json.dumps([obj.model_dump() for obj in self.signature_objects])
    data['extraction_fields'] = json.dumps([field.model_dump() for field in self.extraction_fields])
    return data

@classmethod
def from_db_model(cls, db_model) -> 'PdfTemplateVersion':
    # Parse JSON back to typed objects
    signature_objects = [PdfObject(**obj_data) for obj_data in json.loads(db_model.signature_objects)]
    # ... return fully typed domain object
```

### 3. Automatic Field Generation

Repository handles auto-generated fields internally:

```python
def _get_next_version_number(self, session, template_id: int) -> int:
    """Calculate next version number automatically"""
    versions = session.query(self.model_class).filter(
        self.model_class.pdf_template_id == template_id
    ).all()
    
    if not versions:
        return 1
    
    max_version = max(version.version_num for version in versions)
    return max_version + 1
```

### 4. Security Through URL Parameters

Prevent parameter tampering by overriding with URL values:

```python
# Even if client sends wrong pdf_template_id in body, URL parameter takes precedence
version_create = PdfTemplateVersionCreate(
    pdf_template_id=template_id,  # From URL - cannot be spoofed
    signature_objects=request_data.signature_objects,
    # ...
)
```

### 5. Consistent Return Patterns

- **Repositories**: Return `Optional[DomainObject]` for single items, `List[DomainObject]` for collections
- **Services**: Raise `ObjectNotFoundError` for business rule violations, return domain objects otherwise  
- **APIs**: Convert domain exceptions to HTTP exceptions, return domain objects directly

---

## Usage Guidelines

### When implementing new features:

1. **Start with domain models** in `shared/models/` - define the complete type hierarchy
2. **Create repositories** with session-scoped operations and automatic type conversion
3. **Build services** that coordinate repositories and implement business rules
4. **Add API routes** that use domain types directly with proper error handling
5. **Create API schemas** only when needed (URL parameter exclusion, enhanced responses)

### Maintain consistency:

- Use `from_attributes = True` on all domain models
- Follow the Base/Create/Update/Domain model pattern
- Handle errors at the appropriate layer (domain errors in service, HTTP errors in API)
- Use explicit type annotations for IDE support
- Keep business logic in services, data access in repositories

This architecture provides a robust, type-safe, and maintainable foundation for FastAPI services.