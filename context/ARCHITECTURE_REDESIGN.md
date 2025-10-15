# Data Access & Type System Redesign

## Executive Summary

Refactor the backend to establish clear separation between API contracts (Pydantic) and internal data structures (frozen dataclasses). This achieves:

1. **Performance**: Lightweight dataclasses in hot paths (service/repo layers)
2. **Validation**: Strict Pydantic validation at API boundaries only
3. **Clarity**: Explicit contracts at each layer boundary
4. **Flexibility**: API can evolve independently from internal domain models

---

## Current State Analysis

### What We Have Now
```
API Layer (FastAPI routers)
    ↓ (uses Pydantic directly)
Service Layer
    ↓ (passes Pydantic models)
Repository Layer
    ↓ (converts Pydantic ↔ SQLAlchemy)
Database (SQLAlchemy ORM)
```

**Problems:**
- Pydantic overhead in service/repo layers (unnecessary validation)
- Tight coupling between API contracts and internal types
- JSON serialization logic scattered across repo methods
- Harder to version APIs independently

### What We Want
```
API Layer (FastAPI routers)
    ↓ (Pydantic schemas for validation)
    Mapper functions
    ↓ (DTOs)
Service Layer (business logic)
    ↓ (DTOs)
Repository Layer (data access)
    ↓ (converts DTO ↔ SQLAlchemy + JSON handling)
Database (SQLAlchemy ORM)
```

---

## New Directory Structure

```
server/src/
├── api/
│   ├── routers/
│   │   ├── email_configs.py      # FastAPI endpoints
│   │   ├── pdf_templates.py
│   │   ├── pipelines.py
│   │   └── ...
│   └── schemas/                   # Pydantic API contracts ONLY
│       ├── __init__.py
│       ├── common.py              # APIResponse, Pagination, etc.
│       ├── email_config.py        # Request/Response schemas
│       ├── pdf_template.py
│       ├── pipeline.py
│       └── eto.py
│
├── shared/
│   ├── database/
│   │   ├── models.py              # SQLAlchemy ORM models (schema only)
│   │   ├── connection.py
│   │   └── repositories/          # Data access layer
│   │       ├── base.py
│   │       ├── email_config.py    # Uses DTOs, returns DTOs
│   │       ├── pdf_file.py
│   │       └── ...
│   │
│   ├── types/                     # Internal DTOs (dataclasses)
│   │   ├── __init__.py
│   │   ├── email_config.py        # DTOs for email config domain
│   │   ├── pdf_template.py
│   │   ├── pipeline.py
│   │   ├── eto.py
│   │   ├── modules.py
│   │   └── common.py              # Shared DTOs (enums, value objects)
│   │
│   ├── services/                  # Business logic (orchestration)
│   │   ├── email_ingestion.py    # Uses DTOs
│   │   ├── pdf_processing.py
│   │   └── ...
│   │
│   └── utils/
│       ├── mappers.py             # API schema ↔ DTO conversions
│       └── datetime.py
```

---

## Layer Responsibilities

### 1. API Schemas (`api/schemas/`)

**Purpose:** HTTP contract validation and documentation

**Uses:** Pydantic v2 models with `Field()` constraints

**Responsibilities:**
- Request validation (field constraints, types, regex, etc.)
- Response serialization for JSON
- OpenAPI documentation generation
- camelCase ↔ snake_case aliasing (if needed)

**Example:**
```python
# api/schemas/email_config.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class EmailConfigCreateRequest(BaseModel):
    """API request for creating email config"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    email_address: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    folder_name: str = Field(..., min_length=1)
    filter_rules: List[EmailFilterRuleRequest] = Field(default_factory=list)
    poll_interval_seconds: int = Field(5, ge=5, le=300)
    max_backlog_hours: int = Field(24, ge=1)

class EmailConfigResponse(BaseModel):
    """API response for email config"""
    id: int
    name: str
    email_address: str
    is_active: bool
    is_running: bool
    created_at: datetime
    # ... all fields exposed to clients
```

### 2. DTOs (`shared/types/`)

**Purpose:** Internal data transfer objects

**Uses:** Frozen dataclasses (lightweight, immutable)

**Responsibilities:**
- Carry data between service and repo layers
- Domain-level type safety
- No validation logic (trust repo layer)
- No ORM knowledge

**Example:**
```python
# shared/types/email_config.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass(frozen=True)
class EmailFilterRuleDTO:
    """Individual filter rule"""
    field: str
    operation: str
    value: str
    case_sensitive: bool = False

@dataclass(frozen=True)
class EmailConfigDTO:
    """Complete email configuration domain object"""
    id: int
    name: str
    description: Optional[str]
    email_address: str
    folder_name: str
    filter_rules: List[EmailFilterRuleDTO]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    is_running: bool
    activated_at: Optional[datetime]
    last_check_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class EmailConfigCreateDTO:
    """DTO for creating email config (no DB-generated fields)"""
    name: str
    description: Optional[str]
    email_address: str
    folder_name: str
    filter_rules: List[EmailFilterRuleDTO] = field(default_factory=list)
    poll_interval_seconds: int = 5
    max_backlog_hours: int = 24
    error_retry_attempts: int = 3

@dataclass(frozen=True)
class EmailConfigUpdateDTO:
    """DTO for updating email config (all optional)"""
    description: Optional[str] = None
    filter_rules: Optional[List[EmailFilterRuleDTO]] = None
    poll_interval_seconds: Optional[int] = None
    max_backlog_hours: Optional[int] = None
    error_retry_attempts: Optional[int] = None
```

### 3. Mappers (`shared/utils/mappers.py`)

**Purpose:** Convert between API schemas and DTOs

**Pattern:**
```python
# shared/utils/mappers.py
from api.schemas import email_config as schemas
from shared.types import email_config as dtos

def email_config_create_request_to_dto(
    req: schemas.EmailConfigCreateRequest
) -> dtos.EmailConfigCreateDTO:
    """Map API request to internal DTO"""
    return dtos.EmailConfigCreateDTO(
        name=req.name,
        description=req.description,
        email_address=req.email_address,
        folder_name=req.folder_name,
        filter_rules=[
            dtos.EmailFilterRuleDTO(
                field=rule.field,
                operation=rule.operation,
                value=rule.value,
                case_sensitive=rule.case_sensitive
            ) for rule in req.filter_rules
        ],
        poll_interval_seconds=req.poll_interval_seconds,
        max_backlog_hours=req.max_backlog_hours,
        error_retry_attempts=req.error_retry_attempts
    )

def email_config_dto_to_response(
    dto: dtos.EmailConfigDTO
) -> schemas.EmailConfigResponse:
    """Map internal DTO to API response"""
    return schemas.EmailConfigResponse(
        id=dto.id,
        name=dto.name,
        description=dto.description,
        email_address=dto.email_address,
        folder_name=dto.folder_name,
        is_active=dto.is_active,
        is_running=dto.is_running,
        # ... map all fields
    )
```

### 4. Repositories (`shared/database/repositories/`)

**Purpose:** Data access and persistence

**Responsibilities:**
- Accept DTOs as input
- Convert DTO ↔ SQLAlchemy models
- Handle JSON serialization/deserialization (for JSON columns)
- Return DTOs
- Never expose SQLAlchemy models to callers

**Pattern:**
```python
# shared/database/repositories/email_config.py
from shared.types.email_config import (
    EmailConfigDTO,
    EmailConfigCreateDTO,
    EmailConfigUpdateDTO
)
import json

class EmailConfigRepository(BaseRepository):

    def create(self, create_dto: EmailConfigCreateDTO) -> EmailConfigDTO:
        """Create new email config from DTO"""
        with self.connection_manager.session_scope() as session:
            # Serialize JSON fields
            filter_rules_json = self._serialize_filter_rules(create_dto.filter_rules)

            # Create ORM model
            model = EmailConfigModel(
                name=create_dto.name,
                description=create_dto.description,
                email_address=create_dto.email_address,
                folder_name=create_dto.folder_name,
                filter_rules=filter_rules_json,
                poll_interval_seconds=create_dto.poll_interval_seconds,
                max_backlog_hours=create_dto.max_backlog_hours,
                error_retry_attempts=create_dto.error_retry_attempts
            )
            session.add(model)
            session.flush()

            # Convert to DTO before returning
            return self._model_to_dto(model)

    def get_by_id(self, config_id: int) -> Optional[EmailConfigDTO]:
        """Get config by ID, return DTO"""
        with self.connection_manager.session_scope() as session:
            model = session.get(EmailConfigModel, config_id)
            if model:
                return self._model_to_dto(model)
            return None

    # ===== Private helper methods (repo-scoped) =====

    def _model_to_dto(self, model: EmailConfigModel) -> EmailConfigDTO:
        """Convert ORM model to DTO (with JSON deserialization)"""
        filter_rules = self._deserialize_filter_rules(model.filter_rules)

        return EmailConfigDTO(
            id=model.id,
            name=model.name,
            description=model.description,
            email_address=model.email_address,
            folder_name=model.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=model.poll_interval_seconds,
            max_backlog_hours=model.max_backlog_hours,
            error_retry_attempts=model.error_retry_attempts,
            is_active=model.is_active,
            is_running=model.is_running,
            activated_at=model.activated_at,
            last_check_time=model.last_check_time,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _serialize_filter_rules(
        self,
        rules: List[EmailFilterRuleDTO]
    ) -> Optional[str]:
        """Serialize filter rules to JSON string for DB storage"""
        if not rules:
            return None
        return json.dumps([
            {
                'field': r.field,
                'operation': r.operation,
                'value': r.value,
                'case_sensitive': r.case_sensitive
            }
            for r in rules
        ])

    def _deserialize_filter_rules(
        self,
        json_str: Optional[str]
    ) -> List[EmailFilterRuleDTO]:
        """Deserialize filter rules from JSON string"""
        if not json_str:
            return []
        try:
            data = json.loads(json_str)
            return [EmailFilterRuleDTO(**item) for item in data]
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse filter_rules JSON: {json_str}")
            return []
```

### 5. Services (`shared/services/`)

**Purpose:** Business logic orchestration

**Responsibilities:**
- Accept DTOs from API layer (via mappers)
- Call repositories with DTOs
- Implement domain rules
- Handle transactions
- Return DTOs

**Pattern:**
```python
# shared/services/email_ingestion.py
from shared.types.email_config import EmailConfigDTO, EmailConfigCreateDTO
from shared.database.repositories import EmailConfigRepository

class EmailIngestionService:
    def __init__(self, config_repo: EmailConfigRepository):
        self.config_repo = config_repo

    def create_config(self, create_dto: EmailConfigCreateDTO) -> EmailConfigDTO:
        """Business logic for creating email config"""

        # Domain validation (business rules)
        if self._email_address_already_exists(create_dto.email_address):
            raise ValidationError(f"Email {create_dto.email_address} already configured")

        # Delegate to repository
        config_dto = self.config_repo.create(create_dto)

        logger.info(f"Created email config: {config_dto.name}")
        return config_dto

    def _email_address_already_exists(self, email: str) -> bool:
        # Check business rule
        pass
```

### 6. API Routers (`api/routers/`)

**Purpose:** HTTP endpoints

**Responsibilities:**
- Route incoming requests
- Validate with Pydantic schemas
- Map schemas → DTOs
- Call services
- Map DTOs → response schemas
- Handle HTTP-specific concerns (status codes, headers)

**Pattern:**
```python
# api/routers/email_configs.py
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.email_config import EmailConfigCreateRequest, EmailConfigResponse
from shared.utils.mappers import (
    email_config_create_request_to_dto,
    email_config_dto_to_response
)

router = APIRouter(prefix="/email-configs", tags=["Email Configs"])

@router.post("/", response_model=EmailConfigResponse, status_code=201)
def create_email_config(
    request: EmailConfigCreateRequest,
    service: EmailIngestionService = Depends(get_email_service)
):
    """Create new email configuration"""

    # Map API schema → DTO
    create_dto = email_config_create_request_to_dto(request)

    # Call service
    config_dto = service.create_config(create_dto)

    # Map DTO → API response
    return email_config_dto_to_response(config_dto)

@router.get("/{config_id}", response_model=EmailConfigResponse)
def get_email_config(
    config_id: int,
    service: EmailIngestionService = Depends(get_email_service)
):
    """Get email config by ID"""
    config_dto = service.get_config(config_id)

    if not config_dto:
        raise HTTPException(status_code=404, detail=f"Config {config_id} not found")

    return email_config_dto_to_response(config_dto)
```

---

## Migration Strategy

### Phase 1: Create New Type System
1. Create new DTO files in `shared/types/` (dataclasses)
2. Keep existing Pydantic models temporarily
3. No breaking changes yet

### Phase 2: Migrate Repositories
1. Update repositories to use DTOs internally
2. Keep Pydantic compatibility methods temporarily
3. Test each repository independently

### Phase 3: Create API Schemas
1. Design Pydantic schemas in `api/schemas/`
2. Create mapper functions in `shared/utils/mappers.py`
3. Schemas can differ from DTOs (API versioning)

### Phase 4: Update Services
1. Refactor services to use DTOs
2. Remove Pydantic dependencies from service layer
3. Test business logic independently

### Phase 5: Update API Routers
1. Use new API schemas
2. Wire mappers between schemas and DTOs
3. Verify API contracts unchanged (or version appropriately)

### Phase 6: Cleanup
1. Remove old Pydantic models from `shared/types/db/`
2. Remove compatibility shims
3. Update tests

---

## Benefits Summary

| Concern | Current (Pydantic everywhere) | New (Option B) |
|---------|------------------------------|----------------|
| **API Validation** | ✅ Strong | ✅ Strong (Pydantic) |
| **Performance** | ❌ Overhead in hot paths | ✅ Fast dataclasses |
| **Type Safety** | ✅ Good | ✅ Excellent (explicit DTOs) |
| **Testing** | ❌ Coupled to API | ✅ Independent layers |
| **API Evolution** | ❌ Tightly coupled | ✅ Independent versioning |
| **Clarity** | ❌ Same types everywhere | ✅ Clear boundaries |
| **JSON Handling** | ❌ Scattered | ✅ Centralized in repos |

---

## Open Questions for Discussion

1. **Naming Conventions:**
   - `EmailConfigDTO` vs `EmailConfig`?
   - `CreateDTO` suffix or separate module?

2. **Mapper Location:**
   - Single `mappers.py` or per-domain mapper files?
   - Auto-generation possible?

3. **JSON Field Patterns:**
   - Which fields need complex JSON serialization?
   - Standard patterns for nested objects?

4. **Enum Strategy:**
   - Keep `StrEnum` in shared module?
   - Separate API enums from domain enums?

5. **Migration Priority:**
   - Start with email_config (most mature)?
   - Or new tables first (avoid refactoring twice)?

6. **Dataclass vs NamedTuple:**
   - Frozen dataclasses (proposed) or NamedTuples?
   - Performance considerations?

---

## Next Steps

Once we align on this design:

1. **Implement EmailConfig as pilot** (full stack example)
2. **Create templates** for other domains
3. **Document patterns** for team
4. **Migrate remaining domains** systematically

What do you think? Any concerns or alternative approaches we should consider?
