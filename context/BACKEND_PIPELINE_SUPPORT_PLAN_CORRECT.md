# Backend Plan: Add Pipeline Data to Template Version GET Response

## Current Architecture Analysis (server-new/)

### ✅ What Already Works

1. **CREATE Template** - `POST /pdf-templates` (lines 77-109 in `api/routers/pdf_templates.py`)
   - ✅ Accepts `pipeline_state: PipelineState` and `visual_state: VisualState` (REQUIRED)
   - ✅ Creates `PipelineDefinition` record via `PipelineService`
   - ✅ Links template version to pipeline via `pipeline_definition_id` FK

2. **UPDATE Template** - `PUT /pdf-templates/{id}` (lines 112-138)
   - ✅ Accepts optional `pipeline_state` and `visual_state`
   - ✅ Creates new version + new pipeline definition when pipeline data changes

3. **Database Structure**:
   ```
   pdf_template_versions
   ├─ pipeline_definition_id (FK) → pipeline_definitions
   │                                 ├─ pipeline_state_json (TEXT)
   │                                 └─ visual_state_json (TEXT)
   ```

### ❌ What's Missing

**GET Template Version** - `GET /pdf-templates/versions/{version_id}` (lines 167-184)

**Current Response** (`GetTemplateVersionResponse` schema):
```python
class GetTemplateVersionResponse(BaseModel):
    version_id: int
    template_id: int
    version_num: int
    source_pdf_id: int
    is_current: bool
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int  # ❌ Only the ID, not the actual data!
```

**Problem**: Frontend gets `pipeline_definition_id: 123` but NOT the actual `pipeline_state` and `visual_state` needed to populate the template builder for editing.

---

## Solution: Add Pipeline Data to GET Version Response

### Required Changes

#### 1. Update API Schema (5 min)

**File**: `server-new/src/api/schemas/pdf_templates.py` (lines 78-88)

```python
# GET /pdf-templates/versions/{version_id} - Version Detail Response
class GetTemplateVersionResponse(BaseModel):
    version_id: int
    template_id: int
    version_num: int
    source_pdf_id: int
    is_current: bool
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int

    # NEW: Add pipeline data
    pipeline_state: PipelineState
    visual_state: VisualState
```

---

#### 2. Update Domain Type (5 min)

**File**: `server-new/src/shared/types/pdf_templates.py` (lines 32-52)

```python
@dataclass(frozen=True)
class PdfTemplateVersion:
    """
    Immutable version snapshot of template wizard data.
    """
    id: int
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: PdfObjects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int
    created_at: datetime

    # NEW: Add pipeline data
    pipeline_state: dict[str, Any]  # Pipeline graph structure
    visual_state: dict[str, Any]    # Node positions
```

---

#### 3. Update Repository to Fetch Pipeline Data (10 min)

**File**: `server-new/src/shared/database/repositories/pdf_template_version.py`

**Current**: `_model_to_version()` method (lines 144-165) doesn't fetch pipeline data

**Add**: Eager-load pipeline definition and deserialize pipeline data

```python
from sqlalchemy.orm import joinedload

def _model_to_version(self, model: PdfTemplateVersionModel) -> PdfTemplateVersion:
    """Convert ORM model to PdfTemplateVersion dataclass"""
    # Deserialize JSON fields
    signature_objects = self._deserialize_pdf_objects(model.signature_objects)
    extraction_fields = self._deserialize_extraction_fields(model.extraction_fields)

    # Get source_pdf_id from the template relationship
    source_pdf_id = model.pdf_template.source_pdf_id if model.pdf_template else 0

    # NEW: Deserialize pipeline data from pipeline_definition relationship
    pipeline_state = {}
    visual_state = {}
    if model.pipeline_definition:
        try:
            pipeline_state = json.loads(model.pipeline_definition.pipeline_state)
            visual_state = json.loads(model.pipeline_definition.visual_state)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to deserialize pipeline data for version {model.id}: {e}")
            # Fall back to empty states

    return PdfTemplateVersion(
        id=model.id,
        template_id=model.pdf_template_id,
        version_number=model.version_num,
        source_pdf_id=source_pdf_id,
        signature_objects=signature_objects,
        extraction_fields=extraction_fields,
        pipeline_definition_id=model.pipeline_definition_id,
        created_at=model.created_at,
        pipeline_state=pipeline_state,  # NEW
        visual_state=visual_state        # NEW
    )
```

**Update `get_by_id()` to eager-load pipeline_definition**:

```python
def get_by_id(self, version_id: int, session=None) -> PdfTemplateVersion | None:
    """Get version by ID with eager-loaded relationships"""
    def _get(sess):
        return (
            sess.query(self.model_class)
            .options(
                joinedload(PdfTemplateVersionModel.pdf_template),
                joinedload(PdfTemplateVersionModel.pipeline_definition)  # NEW
            )
            .filter(self.model_class.id == version_id)
            .first()
        )

    if session:
        model = _get(session)
    else:
        with self._get_session() as session:
            model = _get(session)

    if not model:
        return None

    return self._model_to_version(model)
```

---

#### 4. Update Mapper (5 min)

**File**: `server-new/src/api/mappers/pdf_templates.py` (lines 228-242)

**Current mapper**:
```python
def convert_template_version(
    version: PdfTemplateVersion,
    is_current: bool
) -> GetTemplateVersionResponse:
    """Convert domain template version to API response"""
    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        source_pdf_id=version.source_pdf_id,
        is_current=is_current,
        signature_objects=convert_pdf_objects_to_api(version.signature_objects),
        extraction_fields=convert_extraction_fields_to_api(version.extraction_fields),
        pipeline_definition_id=version.pipeline_definition_id
    )
```

**Updated mapper**:
```python
from api.schemas.pipelines import PipelineState as PipelineStatePydantic, VisualState as VisualStatePydantic

def convert_template_version(
    version: PdfTemplateVersion,
    is_current: bool
) -> GetTemplateVersionResponse:
    """Convert domain template version to API response"""
    # Convert dict pipeline states to Pydantic models
    pipeline_state = PipelineStatePydantic(**version.pipeline_state) if version.pipeline_state else PipelineStatePydantic(entry_points=[], modules=[], connections=[])
    visual_state = VisualStatePydantic(**version.visual_state) if version.visual_state else VisualStatePydantic(modules={}, entry_points={})

    return GetTemplateVersionResponse(
        version_id=version.id,
        template_id=version.template_id,
        version_num=version.version_number,
        source_pdf_id=version.source_pdf_id,
        is_current=is_current,
        signature_objects=convert_pdf_objects_to_api(version.signature_objects),
        extraction_fields=convert_extraction_fields_to_api(version.extraction_fields),
        pipeline_definition_id=version.pipeline_definition_id,
        pipeline_state=pipeline_state,  # NEW
        visual_state=visual_state        # NEW
    )
```

---

## Implementation Checklist

### Phase 1: API Schema ✅
- [ ] Add `pipeline_state: PipelineState` to `GetTemplateVersionResponse`
- [ ] Add `visual_state: VisualState` to `GetTemplateVersionResponse`

### Phase 2: Domain Type ✅
- [ ] Add `pipeline_state: dict[str, Any]` to `PdfTemplateVersion` dataclass
- [ ] Add `visual_state: dict[str, Any]` to `PdfTemplateVersion` dataclass

### Phase 3: Repository ✅
- [ ] Import `joinedload` from `sqlalchemy.orm`
- [ ] Update `get_by_id()` to eager-load `pipeline_definition` relationship
- [ ] Update `_model_to_version()` to deserialize `pipeline_state` and `visual_state` from `pipeline_definition`
- [ ] Add error handling for missing/invalid pipeline data

### Phase 4: Mapper ✅
- [ ] Import `PipelineState` and `VisualState` from `api.schemas.pipelines`
- [ ] Update `convert_template_version()` to convert dict to Pydantic models
- [ ] Handle case where pipeline data is empty/null

---

## Testing Plan

### Test 1: GET version with pipeline data
```bash
# Create a template with pipeline
curl -X POST http://localhost:8090/api/pdf-templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Template",
    "description": "Test",
    "source_pdf_id": 1,
    "signature_objects": {...},
    "extraction_fields": [...],
    "pipeline_state": {
      "entry_points": [{"node_id": "ep1", "name": "test"}],
      "modules": [],
      "connections": []
    },
    "visual_state": {
      "modules": {},
      "entry_points": {"ep1": {"x": 100, "y": 100}}
    }
  }'

# Response includes template_id and current_version_id
# Extract version_id from versions list

# GET version
curl http://localhost:8090/api/pdf-templates/versions/{version_id}

# Expected: Response includes:
# - pipeline_state with entry_points, modules, connections
# - visual_state with modules and entry_points positions
```

### Test 2: Verify data structure
```python
import requests

response = requests.get(f"http://localhost:8090/api/pdf-templates/versions/{version_id}")
data = response.json()

assert "pipeline_state" in data
assert "visual_state" in data
assert "entry_points" in data["pipeline_state"]
assert "modules" in data["pipeline_state"]
assert "connections" in data["pipeline_state"]
assert "modules" in data["visual_state"]
assert "entry_points" in data["visual_state"]
```

### Test 3: Verify eager loading (performance)
```python
# Enable SQL logging
# Verify only ONE query is executed (join, not N+1)
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# GET version should execute:
# SELECT pdf_template_versions.*, pdf_templates.*, pipeline_definitions.*
# FROM pdf_template_versions
# LEFT JOIN pdf_templates ON ...
# LEFT JOIN pipeline_definitions ON ...
# WHERE pdf_template_versions.id = ?
```

---

## Estimated Time: 25-30 minutes

| Phase | Task | Time |
|-------|------|------|
| Phase 1 | Update API schema | 5 min |
| Phase 2 | Update domain type | 5 min |
| Phase 3 | Update repository | 10 min |
| Phase 4 | Update mapper | 5 min |
| Testing | E2E tests | 10 min |
| **Total** | | **35 min** |

---

## Edge Cases to Handle

### Case 1: Missing pipeline_definition relationship
If `model.pipeline_definition` is `None`:
- Return empty pipeline_state and visual_state
- Log warning
- Don't crash

### Case 2: Invalid JSON in pipeline_definition
If `json.loads()` fails:
- Catch `JSONDecodeError`
- Return empty pipeline_state and visual_state
- Log error

### Case 3: Partial pipeline data
If only `pipeline_state` or only `visual_state` exists:
- Handle each independently
- Provide sensible defaults

---

## Alternative: Lazy Loading Approach

If performance is a concern (large pipeline graphs), consider:

**Option B**: Return `pipeline_definition_id` and require frontend to make separate call:
```
GET /pdf-templates/versions/123        → Returns version without pipeline data
GET /pipelines/{pipeline_definition_id} → Returns full pipeline data
```

**Pros**: Smaller initial response, only fetch pipeline when needed
**Cons**: Extra API call, more complex frontend logic

**Recommendation**: Start with Option A (eager loading). Only switch to Option B if response size becomes an issue.

---

## Database Query Impact

### Before (N+1 query problem):
```sql
-- Query 1: Get version
SELECT * FROM pdf_template_versions WHERE id = 123;

-- Query 2: Get template (implicit join)
SELECT * FROM pdf_templates WHERE id = 456;

-- Query 3: Get pipeline (NOT EXECUTED - data missing!)
-- No join for pipeline_definition
```

### After (Optimized single query):
```sql
SELECT
    v.*,
    t.*,
    p.*
FROM pdf_template_versions v
LEFT JOIN pdf_templates t ON v.pdf_template_id = t.id
LEFT JOIN pipeline_definitions p ON v.pipeline_definition_id = p.id
WHERE v.id = 123;
```

**Performance**: Same number of queries, but now includes pipeline data!

---

## Summary

### Current State
- ✅ CREATE works - accepts and stores pipeline data
- ✅ UPDATE works - creates new pipeline definitions
- ❌ GET version - missing pipeline data in response

### After Implementation
- ✅ GET version returns complete data including pipeline_state and visual_state
- ✅ Frontend can populate template builder for editing
- ✅ No extra API calls needed
- ✅ Optimized with eager loading (single query)

### Files Changed
1. `server-new/src/api/schemas/pdf_templates.py` - Add fields to response
2. `server-new/src/shared/types/pdf_templates.py` - Add fields to dataclass
3. `server-new/src/shared/database/repositories/pdf_template_version.py` - Eager load + deserialize
4. `server-new/src/api/mappers/pdf_templates.py` - Map pipeline data

**Total**: 4 files, ~40 lines of code

---

## Ready to Implement?

All changes are straightforward and follow existing patterns in the codebase. No complex business logic, just data plumbing.

**Next step**: Implement Phase 1 (API Schema)
