# Template Creation Type Flow Analysis

This document traces how data types transform across the entire stack during template creation, from frontend React state to backend database persistence.

---

## Overview: The Journey of Template Data

```
Frontend State (React)
    ↓ (transformation in API hook)
Frontend API Call (FormData)
    ↓ (HTTP multipart/form-data)
Backend Router (FastAPI Form parameters)
    ↓ (parse JSON strings, validate with Pydantic)
Backend API Schemas (Pydantic models)
    ↓ (mapper functions)
Backend Domain Types (dataclasses)
    ↓ (service layer processing)
Backend Repository (SQL operations)
    ↓
Database (PostgreSQL)
```

---

## Type-by-Type Analysis

### 1. Extraction Fields

#### Frontend State (TemplateBuilderModal.tsx)
```typescript
interface ExtractionField {
  field_id: string;        // unique identifier (frontend only)
  label: string;           // e.g., "hawb", "customer_name"
  description: string | null;
  page: number;            // 0-indexed
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  required: boolean;       // frontend validation only
  validation_regex: string | null; // frontend validation only
}
```

**Location**: `client/src/renderer/features/templates/types.ts:43-51`

**State Storage**: `const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([])`

---

#### Frontend API Layer (useTemplatesApi.ts)
```typescript
// Transformation happens here!
const backendExtractionFields = request.extraction_fields.map(field => ({
  name: field.label,      // ⚠️ RENAME: label → name
  description: field.description,
  bbox: field.bbox,
  page: field.page,       // Still 0-indexed here
  // ❌ DROPPED: field_id, required, validation_regex
}));
```

**Location**: `client/src/renderer/features/templates/hooks/useTemplatesApi.ts:119-124`

**Sent as**: JSON string in FormData field `extraction_fields`

---

#### Backend Router (pdf_templates.py)
```python
# Received as Form parameter
extraction_fields: str = Form(...)  # JSON string

# Parsed to list of dicts
extraction_fields_data = json.loads(extraction_fields)
# [{name: "hawb", description: null, bbox: [10,20,30,40], page: 0}, ...]

# Validated with Pydantic
from api.schemas.pdf_templates import ExtractionField as ExtractionFieldSchema
parsed_extraction_fields = [
    ExtractionFieldSchema(**field) for field in extraction_fields_data
]
```

**Location**: `server-new/src/api/routers/pdf_templates.py:141-145`

---

#### Backend API Schema (pdf_templates.py)
```python
class ExtractionField(BaseModel):
    name: str                    # Required
    description: Optional[str] = None
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int                    # Still 0-indexed (or is it? Check usage!)
```

**Location**: `server-new/src/api/schemas/pdf_templates.py:10-14`

---

#### Backend Mapper (pdf_templates.py)
```python
def convert_extraction_fields_to_domain(fields: list[ExtractionFieldAPI]) -> list[ExtractionFieldDomain]:
    return [
        ExtractionFieldDomain(
            name=field.name,
            description=field.description,
            bound_box=field.bbox,    # ⚠️ RENAME: bbox → bound_box
            page=field.page
        )
        for field in fields
    ]
```

**Location**: `server-new/src/api/mappers/pdf_templates.py:60-70`

---

#### Backend Domain Type (pdf_templates.py in shared/types)
```python
@dataclass(frozen=True)
class ExtractionField:
    name: str
    bound_box: tuple[float, float, float, float]  # Note: bound_box not bbox
    page: int
    description: str | None = None
```

**Location**: `server-new/src/shared/types/pdf_templates.py` (inferred)

**Used in**: Template version creation, PDF text extraction

---

#### Issues and Required Changes for Extraction Fields

##### Issue 1.1: Frontend Stores Unnecessary Properties
**Problem**: Frontend ExtractionField includes properties that should not exist anywhere:
- ❌ `field_id` - Not needed; use `name` as React key instead
- ❌ `required` - Should be removed completely from all layers
- ❌ `validation_regex` - Should be removed completely from all layers

**Rationale**:
- `field_id` is redundant since `name` must be unique anyway
- `required` and `validation_regex` were UI-only validation concepts that don't belong in the data model
- These fields create unnecessary complexity and confusion

**Required Changes**:
```typescript
// BEFORE (Current - WRONG)
interface ExtractionField {
  field_id: string;           // ❌ Remove completely
  label: string;              // ❌ Rename to 'name'
  description: string | null;
  page: number;               // ❌ Currently 0-indexed, should be 1-indexed
  bbox: [number, number, number, number];
  required: boolean;          // ❌ Remove completely
  validation_regex: string | null;  // ❌ Remove completely
}

// AFTER (Proposed - CORRECT)
interface ExtractionField {
  name: string;               // ✅ Use as React key (unique identifier)
  description: string | null;
  page: number;               // ✅ 1-indexed (matches backend)
  bbox: [number, number, number, number];
}
```

**Files to Update**:
1. `client/src/renderer/features/templates/types.ts:43-51` - Update interface
2. All React components using ExtractionField:
   - Change `key={field.field_id}` to `key={field.name}`
   - Remove all references to `required` and `validation_regex`
3. `client/src/renderer/features/templates/hooks/useTemplatesApi.ts` - Remove transformation of `label` → `name`

---

##### Issue 1.2: Backend Domain Type Has Non-Optional Description
**Problem**: Backend has inconsistent typing for `description`:
- **API Schema** (pdf_templates.py:12): `description: Optional[str] = None` ✅
- **Domain Type** (pdf_templates.py:22): `description: str` ❌ (not optional!)

**Impact**: Mismatch causes issues when description is None

**Required Fix**:
```python
# In server-new/src/shared/types/pdf_templates.py:14-24
@dataclass(frozen=True)
class ExtractionField:
    name: str
    description: str | None  # ✅ Change from 'str' to 'str | None'
    bound_box: tuple[float, float, float, float]  # ⚠️ See Issue 1.3
    page: int
```

**Files to Update**:
- `server-new/src/shared/types/pdf_templates.py:22` - Change type annotation
- `server-new/src/shared/types/pdf_templates.py:188` - Update deserialize function
- Any service/repository code assuming description is always present

---

##### Issue 1.3: Property Name Inconsistency (bbox vs bound_box)
**Problem**: Different names used at different layers:
- **Frontend**: `bbox`
- **API Schema**: `bbox`
- **Domain Type**: `bound_box` ⚠️ Different!
- **Mapper**: Explicitly converts `bbox` → `bound_box`

**Impact**: Unnecessary mapping logic and confusion

**Required Fix**: Standardize on `bbox` everywhere
```python
# In server-new/src/shared/types/pdf_templates.py:14-24
@dataclass(frozen=True)
class ExtractionField:
    name: str
    description: str | None
    bbox: tuple[float, float, float, float]  # ✅ Changed from 'bound_box'
    page: int
```

**Files to Update**:
1. `server-new/src/shared/types/pdf_templates.py:23` - Rename `bound_box` to `bbox`
2. `server-new/src/api/mappers/pdf_templates.py:60-70` - Remove conversion logic
3. `server-new/src/shared/types/pdf_templates.py:189` - Update deserialize function key
4. `server-new/src/features/pdf_templates/service.py` - Update any references
5. `server-new/src/shared/database/repositories/pdf_template_version_repository.py` - Update column mapping if needed

---

##### Issue 1.4: Page Number Indexing Must Be 1-Indexed Everywhere
**Problem**: Page numbers must be 1-indexed throughout the entire stack (frontend and backend).

**Rationale**:
- PDF libraries use 1-indexed pages
- Previous bugs were caused by 0-indexed confusion
- Consistency prevents errors

**Required Changes**:

**Frontend State** (1-indexed):
```typescript
// In all components that create/manage extraction fields
const newField: ExtractionField = {
  name: "field_name",
  description: null,
  page: 1,  // ✅ First page is 1, not 0
  bbox: [x0, y0, x1, y1]
};
```

**Frontend API Layer** (no conversion needed):
```typescript
// In useTemplatesApi.ts:119-124
const backendExtractionFields = request.extraction_fields.map(field => ({
  name: field.name,  // ✅ Already correct after frontend fix
  description: field.description,
  bbox: field.bbox,
  page: field.page,  // ✅ Already 1-indexed, no conversion
}));
```

**Backend** (1-indexed throughout):
- API Schema: Expects 1-indexed
- Domain Type: Stores 1-indexed
- PDF extraction: Uses 1-indexed

**Files to Update**:
1. All frontend components creating extraction fields - ensure page is 1-indexed
2. PDF canvas components - display "Page 1" for first page
3. Any page selection dropdowns - start from 1
4. Remove any +1 or -1 conversions that were workarounds
5. Add validation: `page >= 1` everywhere

---

##### Implementation Priority for Extraction Fields

1. **CRITICAL** - Fix page indexing to 1-indexed everywhere (Issue 1.4)
2. **HIGH** - Remove `required` and `validation_regex` completely (Issue 1.1)
3. **HIGH** - Replace `field_id` with `name` as React key (Issue 1.1)
4. **HIGH** - Rename `label` to `name` in frontend (Issue 1.1)
5. **MEDIUM** - Make backend description optional (Issue 1.2)
6. **MEDIUM** - Rename `bound_box` to `bbox` in backend (Issue 1.3)

---

##### Updated Transformation Flow (After Fixes)

```
FRONTEND STATE (1-indexed)
{
  name: "hawb",
  description: "House Air Waybill Number",
  page: 1,                    // ✅ 1-indexed
  bbox: [100, 200, 300, 400]
}
    ↓ (NO transformation needed in useTemplatesApi.ts)
FRONTEND API CALL (FormData)
{
  name: "hawb",               // ✅ No conversion
  description: "House Air Waybill Number",
  page: 1,                    // ✅ Still 1-indexed
  bbox: [100, 200, 300, 400]
}
    ↓ (JSON parsing + Pydantic validation in router)
BACKEND API SCHEMA
ExtractionField(
  name="hawb",
  description="House Air Waybill Number",
  bbox=(100, 200, 300, 400),  // ✅ Pydantic converts list to tuple
  page=1
)
    ↓ (mapper conversion - simplified after fixes)
BACKEND DOMAIN TYPE
ExtractionField(
  name="hawb",
  description="House Air Waybill Number",
  bbox=(100, 200, 300, 400),  // ✅ Same property name now
  page=1
)
    ↓ (repository saves to DB)
DATABASE
{
  "name": "hawb",
  "description": "House Air Waybill Number",
  "bbox": [100, 200, 300, 400],
  "page": 1
}
```

**Key Improvements After Fixes**:
- ✅ No label→name conversion needed
- ✅ No page indexing conversion needed
- ✅ No bbox→bound_box conversion needed
- ✅ No field_id management needed
- ✅ No unused required/validation_regex fields

---

### 2. Signature Objects

#### Frontend State
```typescript
interface SignatureObject {
  object_type: PdfObjectType;  // 'text_word' | 'graphic_rect' | etc.
  page: number;                // 0-indexed
  bbox: [number, number, number, number];
  // Optional properties based on object_type
  text?: string;
  fontname?: string;
  fontsize?: number;
  linewidth?: number;
  points?: Array<[number, number]>;
  format?: string;
  // ... etc
}
```

**Location**: `client/src/renderer/features/templates/types.ts:26-41`

**State Storage**: `const [signatureObjects, setSignatureObjects] = useState<SignatureObject[]>([])`

---

#### Frontend API Layer
```typescript
// NO transformation! Sent as-is
formData.append('signature_objects', JSON.stringify(request.signature_objects));
```

**Sent as**: JSON string in FormData

---

#### Backend Router
```python
# Received as JSON string
signature_objects: str = Form(...)

# Parsed to dict
signature_objects_data = json.loads(signature_objects)
# Expected format: {"text_words": [...], "graphic_rects": [...]}
```

**⚠️ CRITICAL ISSUE**: Frontend sends array, backend expects grouped dict!

---

#### Backend API Schema
```python
signature_objects: Dict[str, List[Dict[str, Any]]]
# Grouped format: {"text_words": [...], "graphic_rects": [...]}
```

**Location**: `server-new/src/api/schemas/pdf_templates.py:95`

---

#### Backend Mapper
```python
def convert_pdf_objects_to_domain(objects_dict: dict[str, list[dict[str, Any]]]) -> PdfObjects:
    return deserialize_pdf_objects(objects_dict)
```

**Location**: `server-new/src/api/mappers/pdf_templates.py:38-44`

---

#### Backend Domain Type
```python
@dataclass(frozen=True)
class PdfObjects:
    """Grouped PDF objects by type"""
    text_words: list[dict]
    text_lines: list[dict]
    graphic_rects: list[dict]
    graphic_lines: list[dict]
    graphic_curves: list[dict]
    images: list[dict]
    tables: list[dict]
```

**Location**: `server-new/src/shared/types/pdf_files.py` (inferred)

---

### 3. Pipeline State

#### Frontend State
```typescript
interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: NodeConnection[];
}

interface EntryPoint {
  node_id: string;
  name: string;
  type: string;  // e.g., "str", "int", "float"
}

interface ModuleInstance {
  instance_id: string;
  module_id: string;       // e.g., "text_cleaner:1.0.0"
  config: Record<string, any>;
  inputs: NodePin[];
  outputs: NodePin[];
}

interface NodePin {
  node_id: string;
  name: string;
  type: string[];          // Array of allowed types
  position_index: number;
  group_index: number;
}

interface NodeConnection {
  from_node_id: string;
  to_node_id: string;
}
```

**Location**: `client/src/renderer/types/pipelineTypes.ts:32-56`

**State Storage**: `const [pipelineState, setPipelineState] = useState<PipelineState>(...)`

---

#### Frontend API Layer
```typescript
// NO transformation! Sent as-is
formData.append('pipeline_state', JSON.stringify(request.pipeline_state));
```

---

#### Backend Router
```python
# Received as JSON string
pipeline_state: str = Form(...)

# Parsed to dict
pipeline_state_data = json.loads(pipeline_state)

# Validated with Pydantic DTO
from api.schemas.pipelines import PipelineStateDTO
pipeline_state_dto = PipelineStateDTO(**pipeline_state_data)
```

**Location**: `server-new/src/api/routers/pdf_templates.py:182`

**⚠️ CRITICAL**: Uses `api.schemas.pipelines.PipelineStateDTO`, NOT `api.schemas.pdf_templates.PipelineState`!

---

#### Backend API Schema - Version 1 (in pdf_templates.py)
```python
class PipelineEntryPoint(BaseModel):
    id: str              # ⚠️ Frontend calls this "node_id"
    label: str           # ⚠️ Frontend calls this "name"
    field_reference: str # ⚠️ Frontend doesn't have this!

class PipelineState(BaseModel):
    entry_points: List[PipelineEntryPoint]
    modules: List[PipelineModuleInstance]
    connections: List[PipelineConnection]
```

**Location**: `server-new/src/api/schemas/pdf_templates.py:18-46`

**⚠️ MISMATCH**: This schema is WRONG for the actual data format!

---

#### Backend API Schema - Version 2 (in pipelines.py)
```python
class EntryPointDTO(BaseModel):
    node_id: str  # ✅ Matches frontend
    name: str     # ✅ Matches frontend

class NodeDTO(BaseModel):
    node_id: str
    type: str     # ⚠️ Frontend has type: string[], backend has type: str
    name: str
    position_index: int
    group_index: int

class ModuleInstanceDTO(BaseModel):
    module_instance_id: str  # ⚠️ Frontend calls this "instance_id"
    module_ref: str          # ⚠️ Frontend calls this "module_id"
    config: Dict[str, Any]
    inputs: List[NodeDTO]
    outputs: List[NodeDTO]

class PipelineStateDTO(BaseModel):
    entry_points: List[EntryPointDTO]
    modules: List[ModuleInstanceDTO]
    connections: List[NodeConnectionDTO]
```

**Location**: `server-new/src/api/schemas/pipelines.py:21-46`

**⚠️ MISMATCH**: Frontend uses different property names!

---

#### Backend Mapper
```python
def convert_dto_to_pipeline_state(pipeline_state_dto: PipelineStateDTO) -> PipelineStateDomain:
    return PipelineStateDomain(
        entry_points=[convert_dto_to_entry_point(ep) for ep in pipeline_state_dto.entry_points],
        modules=[convert_dto_to_module_instance(mod) for mod in pipeline_state_dto.modules],
        connections=[convert_dto_to_connection(conn) for conn in pipeline_state_dto.connections]
    )

def convert_dto_to_module_instance(module_dto: ModuleInstanceDTO) -> ModuleInstanceDomain:
    return ModuleInstanceDomain(
        module_instance_id=module_dto.module_instance_id,
        module_ref=module_dto.module_ref,  # Not module_id!
        config=module_dto.config,
        inputs=[convert_dto_to_node(node) for node in module_dto.inputs],
        outputs=[convert_dto_to_node(node) for node in module_dto.outputs]
    )
```

**Location**: `server-new/src/api/mappers/pipelines.py:161-167`

---

#### Backend Domain Type
```python
@dataclass(frozen=True)
class ModuleInstance:
    module_instance_id: str
    module_ref: str       # e.g., "text_cleaner:1.0.0"
    config: dict
    inputs: list[NodeInstance]
    outputs: list[NodeInstance]

@dataclass(frozen=True)
class NodeInstance:
    node_id: str
    type: str            # Single type, not array!
    name: str
    position_index: int
    group_index: int

@dataclass(frozen=True)
class EntryPoint:
    node_id: str
    name: str

@dataclass(frozen=True)
class PipelineState:
    entry_points: list[EntryPoint]
    modules: list[ModuleInstance]
    connections: list[NodeConnection]
```

**Location**: `server-new/src/shared/types/pipelines.py`

---

### 4. Visual State

#### Frontend State
```typescript
interface VisualState {
  modules: Record<string, { x: number; y: number }>;
  entryPoints?: Record<string, { x: number; y: number }>;
}
```

**Location**: `client/src/renderer/types/pipelineTypes.ts:60-63`

**Example**:
```typescript
{
  modules: {
    "module_1": { x: 100, y: 200 },
    "module_2": { x: 300, y: 400 }
  },
  entryPoints: {
    "entry_1": { x: 50, y: 100 }
  }
}
```

---

#### Frontend API Layer
```typescript
// NO transformation! Sent as-is
formData.append('visual_state', JSON.stringify(request.visual_state));
```

---

#### Backend API Schema (in pipelines.py)
```python
class PositionDTO(BaseModel):
    x: float
    y: float

class VisualStateDTO(BaseModel):
    modules: Dict[str, PositionDTO] = {}
    entry_points: Dict[str, PositionDTO] = {}
```

**Location**: `server-new/src/api/schemas/pipelines.py:53-62`

**✅ MATCHES** frontend format perfectly!

---

#### Backend API Schema (in pdf_templates.py)
```python
class VisualState(BaseModel):
    positions: Dict[str, Dict[str, float]]  # ⚠️ DIFFERENT SCHEMA!
```

**Location**: `server-new/src/api/schemas/pdf_templates.py:49-50`

**⚠️ CRITICAL**: This schema is WRONG! It expects a single `positions` dict, not separate `modules` and `entry_points`.

---

#### Backend Mapper
```python
def convert_dto_to_visual_state(visual_state_dto: VisualStateDTO) -> VisualStateDomain:
    return VisualStateDomain(
        modules={
            key: (pos.x, pos.y)  # ⚠️ Converts dict to tuple
            for key, pos in visual_state_dto.modules.items()
        },
        entry_points={
            key: (pos.x, pos.y)  # ⚠️ Converts dict to tuple
            for key, pos in visual_state_dto.entry_points.items()
        }
    )
```

**Location**: `server-new/src/api/mappers/pipelines.py:170-181`

---

#### Backend Domain Type
```python
@dataclass(frozen=True)
class VisualState:
    modules: dict[str, tuple[float, float]]        # {id: (x, y)}
    entry_points: dict[str, tuple[float, float]]   # {id: (x, y)}
```

**Location**: `server-new/src/shared/types/pipelines.py`

---

## Critical Issues Identified

### Issue 1: Duplicate Pipeline Schemas
**Problem**: Two different `PipelineState` schemas exist:
- `api.schemas.pdf_templates.PipelineState` (WRONG schema)
- `api.schemas.pipelines.PipelineStateDTO` (CORRECT schema)

**Current Behavior**: Router uses the correct `PipelineStateDTO` from pipelines.py

**Fix Needed**: Remove the incorrect schemas from pdf_templates.py

---

### Issue 2: Duplicate Visual State Schemas
**Problem**: Two different `VisualState` schemas:
- `api.schemas.pdf_templates.VisualState` (WRONG - expects `positions`)
- `api.schemas.pipelines.VisualStateDTO` (CORRECT - expects `modules` + `entry_points`)

**Current Behavior**: Router uses the correct `VisualStateDTO` from pipelines.py

**Fix Needed**: Remove the incorrect schema from pdf_templates.py

---

### Issue 3: Frontend/Backend Property Name Mismatches

#### PipelineState Mismatches:
| Frontend Property | Backend DTO Property | Status |
|-------------------|---------------------|---------|
| `instance_id` | `module_instance_id` | ⚠️ MISMATCH |
| `module_id` | `module_ref` | ⚠️ MISMATCH |
| `type: string[]` (NodePin) | `type: str` (NodeDTO) | ⚠️ MISMATCH |

**Fix Needed**: Frontend needs transformation layer OR backend needs to accept frontend format

---

### Issue 4: Signature Objects Format Mismatch
**Problem**:
- Frontend: Array of objects `[{object_type: "text_word", ...}, ...]`
- Backend: Grouped dict `{"text_words": [...], "graphic_rects": [...]}`

**Current State**: Frontend sends array, backend expects grouped dict → **VALIDATION ERROR**

**Fix Needed**: Frontend must group objects by type before sending

---

### Issue 5: Page Number Indexing
**Issue**: Frontend uses 0-indexed pages, backend may expect 1-indexed

**Current Fix**: Already handled in extraction step transformation (adds +1)

**Status**: ✅ Fixed in useTemplatesApi.ts but needs verification in all paths

---

## Recommended Fixes

### Priority 1: Fix Signature Objects (Blocking)
```typescript
// In useTemplatesApi.ts
const groupedSignatureObjects = groupSignatureObjects(request.signature_objects);

function groupSignatureObjects(objects: SignatureObject[]): Record<string, any[]> {
  const grouped: Record<string, any[]> = {
    text_words: [],
    text_lines: [],
    graphic_rects: [],
    graphic_lines: [],
    graphic_curves: [],
    images: [],
    tables: []
  };

  for (const obj of objects) {
    const key = obj.object_type + 's'; // 'text_word' → 'text_words'
    if (grouped[key]) {
      grouped[key].push(obj);
    }
  }

  return grouped;
}
```

---

### Priority 2: Fix Pipeline State Property Names (Blocking)
```typescript
// In useTemplatesApi.ts
const backendPipelineState = transformPipelineState(request.pipeline_state);

function transformPipelineState(state: PipelineState) {
  return {
    entry_points: state.entry_points, // Already matches
    modules: state.modules.map(mod => ({
      module_instance_id: mod.instance_id,     // Rename
      module_ref: mod.module_id,                // Rename
      config: mod.config,
      inputs: mod.inputs.map(pin => ({
        ...pin,
        type: pin.type[0]  // Convert array to single string (or join?)
      })),
      outputs: mod.outputs.map(pin => ({
        ...pin,
        type: pin.type[0]
      }))
    })),
    connections: state.connections  // Already matches
  };
}
```

---

### Priority 3: Clean Up Duplicate Schemas
Remove these from `api/schemas/pdf_templates.py`:
- `class PipelineEntryPoint`
- `class PipelineNodePin`
- `class PipelineModuleInstance`
- `class PipelineConnection`
- `class PipelineState`
- `class VisualState`

Import from `api.schemas.pipelines` instead.

---

## Data Flow Summary

### Complete Type Transformation Chain

```
FRONTEND STATE → FRONTEND API → BACKEND ROUTER → BACKEND MAPPER → BACKEND DOMAIN

ExtractionField:
  {field_id, label, ...} → {name, ...} → ExtractionField(Pydantic) → ExtractionField(Domain) → {name, bound_box, ...}

SignatureObject:
  [{object_type: "text_word", ...}] → ⚠️ NEEDS GROUPING → {text_words: [...], ...} → PdfObjects(Domain)

PipelineState:
  {entry_points, modules: [{instance_id, module_id, inputs: [{type: []}]}]}
    → ⚠️ NEEDS TRANSFORMATION → PipelineStateDTO
    → PipelineState(Domain)

VisualState:
  {modules: {id: {x, y}}, entryPoints: {id: {x, y}}}
    → VisualStateDTO (no change)
    → VisualState(Domain) {modules: {id: (x,y)}, ...}
```

---

## Testing Checklist

- [ ] Verify signature objects are properly grouped before sending
- [ ] Verify pipeline module property names are transformed
- [ ] Verify NodePin type array is converted to string
- [ ] Verify extraction field page numbers are 0 or 1 indexed correctly throughout
- [ ] Verify visual state preserves modules and entryPoints structure
- [ ] Test template creation with uploaded PDF
- [ ] Test template creation with stored PDF
- [ ] Verify created template can be retrieved and displayed
- [ ] Verify pipeline can be executed after creation

---

## Schema Reference Locations

### Frontend
- Template Types: `client/src/renderer/features/templates/types.ts`
- Pipeline Types: `client/src/renderer/types/pipelineTypes.ts`
- Module Types: `client/src/renderer/types/moduleTypes.ts`

### Backend API Schemas
- PDF Templates: `server-new/src/api/schemas/pdf_templates.py`
- Pipelines: `server-new/src/api/schemas/pipelines.py`

### Backend Mappers
- PDF Templates: `server-new/src/api/mappers/pdf_templates.py`
- Pipelines: `server-new/src/api/mappers/pipelines.py`

### Backend Domain Types
- PDF Templates: `server-new/src/shared/types/pdf_templates.py`
- Pipelines: `server-new/src/shared/types/pipelines.py`
- PDF Files: `server-new/src/shared/types/pdf_files.py`

### Backend Routers
- PDF Templates Router: `server-new/src/api/routers/pdf_templates.py`
