# Templates Feature Refactoring - Session Continuity Document

## Session Overview
**Date**: 2025-11-09
**Status**: Templates API layer refactored, PdfObjects type consolidated
**Primary Goal**: Refactor templates feature to match architecture patterns established in modules/pipelines features

---

## What We Accomplished

### 1. Templates API Type Refactoring

**Goal**: Align templates API types with naming conventions used in modules and pipelines features.

**Analysis Phase**:
- Compared `templates/api/types.ts` with `modules/api/types.ts` and `pipelines/api/types.ts`
- Identified verbose HTTP method prefixes (PostTemplateCreateRequest, PutTemplateUpdateRequest)
- Found unnecessary type aliases pointing to domain types
- Discovered unused `GetTemplatesResponse` interface

**Changes Implemented**:

#### A. Renamed Request Types (Remove HTTP Prefixes)
**File**: `client/src/renderer/features/templates/api/types.ts`

```typescript
// BEFORE:
export interface PostTemplateCreateRequest { ... }
export interface PutTemplateUpdateRequest { ... }
export interface PostTemplateSimulateRequest { ... }
export interface PostTemplateSimulateResponse { ... }

// AFTER:
export interface CreateTemplateRequest { ... }
export interface UpdateTemplateRequest { ... }
export interface SimulateTemplateRequest { ... }
export interface SimulateTemplateResponse { ... }
```

**Rationale**: Matches pattern in modules/pipelines features (CreatePipelineRequest, not PostPipelineCreateRequest)

#### B. Removed Type Aliases
**File**: `client/src/renderer/features/templates/api/types.ts`

```typescript
// REMOVED (unnecessary):
export type PostTemplateCreateResponse = TemplateDetail;
export type GetTemplateDetailResponse = TemplateDetail;
export type GetTemplateVersionResponse = TemplateVersionDetail;
export type PutTemplateUpdateResponse = TemplateDetail;

// NOW: Use domain types directly in hooks
mutationFn: async (request: CreateTemplateRequest): Promise<TemplateDetail> => {
  const response = await apiClient.post<TemplateDetail>(baseUrl, request);
  return response.data;
}
```

**Rationale**: TanStack Query hooks can use domain types directly, no need for API-specific response wrappers

#### C. Removed Unused Type
**File**: `client/src/renderer/features/templates/api/types.ts`

```typescript
// REMOVED (unused):
export interface GetTemplatesResponse {
  templates: TemplateListItem[];
  total: number;
  page: number;
  page_size: number;
}
```

**Rationale**: Backend returns `TemplateListItem[]` directly without pagination wrapper

#### D. Simplified Exports
**File**: `client/src/renderer/features/templates/api/index.ts`

```typescript
// BEFORE (36 lines of explicit exports):
export {
  useTemplates,
  useTemplateDetail,
  // ... 7 more hooks
} from './hooks';

export type {
  GetTemplatesQueryParams,
  CreateTemplateRequest,
  // ... 10 more types
} from './types';

// AFTER (7 lines):
/**
 * Templates API
 * Unified exports for template operations
 */

export * from './types';
export * from './hooks';
```

**Rationale**: Simpler, less maintenance, matches pattern in other features

#### E. Updated Hook Implementations
**File**: `client/src/renderer/features/templates/api/hooks.ts`

```typescript
// Updated all imports and type signatures
import {
  CreateTemplateRequest,
  UpdateTemplateRequest,
  SimulateTemplateRequest,
  SimulateTemplateResponse,
} from './types';
import { TemplateListItem, TemplateDetail, TemplateVersionDetail } from '../types';

// Updated all mutation/query functions to use new type names
```

**Status**: ✅ Complete and verified (TypeScript: 0 errors)

---

### 2. PdfObjects Type Consolidation (CRITICAL FIX)

**Problem Discovered**: Two different `PdfObjects` type definitions existed with conflicting structures:
1. `pdf/api/types.ts`: Correct structure matching backend
2. `templates/types.ts`: Incorrect structure with extra fields and wrong optionality

**Root Cause Analysis**:

**Backend Schema** (server/src/api/schemas/pdf_files.py) - Source of Truth:
```python
class TextWord(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]
    text: str
    fontname: str      # REQUIRED (not Optional)
    fontsize: float    # REQUIRED (not Optional)

class GraphicRect(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]
    linewidth: float   # REQUIRED (not Optional)

class PdfObjects(BaseModel):
    text_words: List[TextWord]
    text_lines: List[TextLine]
    graphic_rects: List[GraphicRect]
    # ... more object types
```

**Frontend Incorrect Version** (templates/types.ts - REMOVED):
```typescript
export interface PdfObjects {
  text_words: Array<{
    type: 'text_word';     // ❌ Backend doesn't have this field
    page: number;
    bbox: BBox;
    text: string;
    fontname?: string;     // ❌ Should be required, not optional
    fontsize?: number;     // ❌ Should be required, not optional
  }>;
  graphic_rects: Array<{
    type: 'graphic_rect';  // ❌ Backend doesn't have this field
    page: number;
    bbox: BBox;
    linewidth?: number;    // ❌ Should be required, not optional
  }>;
  // ... 70+ more lines of incorrect definitions
}
```

**Frontend Correct Version** (pdf/api/types.ts):
```typescript
export interface TextWordObject {
  page: number;
  bbox: BBox;
  text: string;
  fontname: string;   // ✅ Required (matches backend)
  fontsize: number;   // ✅ Required (matches backend)
}

export interface GraphicRectObject {
  page: number;
  bbox: BBox;
  linewidth: number;  // ✅ Required (matches backend)
}

export interface PdfObjects {
  text_words: TextWordObject[];
  text_lines: TextLineObject[];
  graphic_rects: GraphicRectObject[];
  // ... all object types
}
```

**Architectural Improvement**: User requested to move PdfObjects from `pdf/api/types.ts` to `pdf/types.ts`:

> "I feel like the PdfObjects type should exist in pdf/types.ts instead of pdf/api/types.ts since it is not specific to the api, but is instead used in multiple places"

**Solution Implemented**:

#### A. Created pdf/types.ts (NEW FILE)
**File**: `client/src/renderer/features/pdf/types.ts`

```typescript
/**
 * PDF Domain Types
 * Represents the structure of PDF objects extracted from PDF files
 * These types match the backend domain types and are used across features
 */

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

export interface TextWordObject {
  page: number;
  bbox: BBox;
  text: string;
  fontname: string;  // REQUIRED (not optional)
  fontsize: number;  // REQUIRED (not optional)
}

export interface TextLineObject {
  page: number;
  bbox: BBox;
  text: string;
  fontname: string;  // REQUIRED
  fontsize: number;  // REQUIRED
}

export interface GraphicRectObject {
  page: number;
  bbox: BBox;
  linewidth: number;  // REQUIRED (not optional)
}

export interface GraphicLineObject {
  page: number;
  bbox: BBox;
  linewidth: number;  // REQUIRED
}

export interface GraphicCurveObject {
  page: number;
  bbox: BBox;
  linewidth: number;  // REQUIRED
  points: [number, number][];  // REQUIRED
}

export interface ImageObject {
  page: number;
  bbox: BBox;
  format: string;      // REQUIRED
  colorspace: string;  // REQUIRED
  bits: number;        // REQUIRED
}

export interface TableObject {
  page: number;
  bbox: BBox;
  rows: number;  // REQUIRED
  cols: number;  // REQUIRED
}

export interface PdfObjects {
  text_words: TextWordObject[];
  text_lines: TextLineObject[];
  graphic_rects: GraphicRectObject[];
  graphic_lines: GraphicLineObject[];
  graphic_curves: GraphicCurveObject[];
  images: ImageObject[];
  tables: TableObject[];
}
```

**Key Points**:
- NO `type` discriminator field (backend doesn't have it)
- All required fields are truly required (not optional)
- Matches backend Pydantic schemas exactly

#### B. Updated pdf/api/types.ts
**File**: `client/src/renderer/features/pdf/api/types.ts`

```typescript
// BEFORE: Defined all PDF object types inline

// AFTER: Import from domain types
import type {
  BBox,
  PdfObjects,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
} from '../types';

// Re-export domain types for convenience
export type {
  BBox,
  PdfObjects,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
};

// API-specific types remain here
export interface PdfFileMetadata { ... }
export interface PdfObjectsResponse { ... }
export interface PdfProcessResponse { ... }
```

**Rationale**: Separates domain types (types.ts) from API types (api/types.ts)

#### C. Updated pdf/index.ts
**File**: `client/src/renderer/features/pdf/index.ts`

```typescript
/**
 * PDF Feature
 * Unified exports for PDF viewing and API operations
 */

// Domain types (core PDF object types) - EXPORTED FIRST
export type {
  BBox,
  PdfObjects,
  TextWordObject,
  TextLineObject,
  GraphicRectObject,
  GraphicLineObject,
  GraphicCurveObject,
  ImageObject,
  TableObject,
} from './types';

// API hooks and utilities
export {
  usePdfData,
  usePdfMetadata,
  usePdfObjects,
  useUploadPdf,
  useProcessPdfObjects,
  getPdfDownloadUrl,
} from './api';

// API types
export type { PdfData } from './api';
export type {
  PdfFileMetadata,
  PdfObjectsResponse,
  PdfProcessResponse,
} from './api/types';

// Components
export { PdfViewer } from './components';
export { usePdfViewer } from './components/PdfViewer/PdfViewerContext';

// Hooks
export { usePdfCoordinates } from './hooks';
```

**Rationale**: Domain types prioritized in exports, clearly separated from API types

#### D. Removed Incorrect PdfObjects from templates/types.ts
**File**: `client/src/renderer/features/templates/types.ts`

```typescript
// REMOVED 81 lines of incorrect PdfObjects definition

// ADDED: Import from pdf feature
import type { BBox, PdfObjects } from '../pdf';

// Re-export for convenience
export type { BBox, PdfObjects };
```

**Impact**: Deleted 81 lines of incorrect type definitions, now imports canonical version

#### E. Updated templates/api/types.ts
**File**: `client/src/renderer/features/templates/api/types.ts`

```typescript
// BEFORE:
import { PdfObjects } from '../types';

// AFTER:
import type { PdfObjects } from '../../pdf';
```

**Rationale**: Import PdfObjects from source feature, not local duplicate

#### F. Updated templates/index.ts
**File**: `client/src/renderer/features/templates/index.ts`

```typescript
// Simplified to use export * pattern
export * from './api';

export type {
  TemplateStatus,
  PdfObjectType,
  BBox,
  PdfObjects,  // Re-exported from pdf feature
  TemplateVersionSummary,
  VersionListItem,
  SignatureObject,
  ExtractionField,
  TemplateVersion,
  TemplateVersionDetail,
  TemplateListItem,
  TemplateDetail,
} from './types';
```

**Status**: ✅ Complete and verified (TypeScript: 0 errors)

---

## Architecture Decisions

### Domain Types vs API Types

**Established Pattern**:
- **types.ts**: Domain types representing business entities, used across features
- **api/types.ts**: API-specific request/response DTOs, wire format types

**Example**: PdfObjects is a domain type (represents PDF structure) → belongs in `pdf/types.ts`

### Type Import Strategy

**Pattern**: Features can import domain types from other features
```typescript
// templates/types.ts imports from pdf feature
import type { BBox, PdfObjects } from '../pdf';
```

**Rationale**: Avoids duplication, ensures single source of truth

### Naming Conventions

**Request Types**: `{Verb}{Entity}Request`
- ✅ `CreateTemplateRequest`
- ✅ `UpdateTemplateRequest`
- ❌ `PostTemplateCreateRequest`
- ❌ `PutTemplateUpdateRequest`

**Response Types**: Use domain types directly
- ✅ `Promise<TemplateDetail>`
- ❌ `Promise<GetTemplateDetailResponse>` (unnecessary alias)

### Export Patterns

**Prefer `export *` for simplicity**:
```typescript
// api/index.ts
export * from './types';
export * from './hooks';
```

**Exception**: Feature index.ts uses explicit exports for clarity of public API

---

## Files Modified

### Created
- `client/src/renderer/features/pdf/types.ts` (NEW)

### Modified
- `client/src/renderer/features/pdf/api/types.ts`
- `client/src/renderer/features/pdf/index.ts`
- `client/src/renderer/features/templates/types.ts`
- `client/src/renderer/features/templates/api/types.ts`
- `client/src/renderer/features/templates/api/hooks.ts`
- `client/src/renderer/features/templates/api/index.ts`
- `client/src/renderer/features/templates/index.ts`

### Verification
- TypeScript compilation: **0 errors** ✅
- All type imports verified working across feature boundaries

---

## Pending Tasks

### 1. Commit and Push Changes ⏳
**Status**: Ready to commit

**Changes to Commit**:
1. Templates API type refactoring (naming conventions)
2. PdfObjects type consolidation (domain vs API separation)

**Commit Message Format**:
```
refactor: Consolidate PdfObjects types and align templates API naming

- Create pdf/types.ts for PDF domain types (BBox, PdfObjects, all object interfaces)
- Move PdfObjects from pdf/api/types.ts to pdf/types.ts (domain vs API separation)
- Remove duplicate PdfObjects definition from templates/types.ts (81 lines deleted)
- Update templates to import PdfObjects from pdf feature (single source of truth)
- Rename templates API types to remove HTTP prefixes (CreateTemplateRequest vs PostTemplateCreateRequest)
- Remove unnecessary type aliases (use domain types directly in hooks)
- Remove unused GetTemplatesResponse interface
- Simplify api/index.ts exports to use export * pattern

TypeScript compilation: 0 errors

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 2. Continue Templates Component Refactoring
**Next Steps** (from user directive):
> "We have so far found the most success with starting via the api, and the types, and then working our way through the component tree."

**To Do**:
- Analyze templates component structure
- Compare with modules/pipelines component patterns
- Refactor components to match established architecture
- Ensure consistent patterns across features

---

## Important Code Locations

### PDF Feature
```
client/src/renderer/features/pdf/
├── types.ts                        [NEW: Domain types - BBox, PdfObjects, all object interfaces]
├── api/
│   ├── types.ts                    [API types - PdfFileMetadata, PdfObjectsResponse, etc.]
│   ├── hooks.ts                    [TanStack Query hooks]
│   └── index.ts                    [API exports]
└── index.ts                        [Feature exports - domain types first]
```

### Templates Feature
```
client/src/renderer/features/templates/
├── types.ts                        [Domain types - imports PdfObjects from pdf]
├── api/
│   ├── types.ts                    [API types - CreateTemplateRequest, etc.]
│   ├── hooks.ts                    [TanStack Query hooks]
│   └── index.ts                    [API exports - simplified to export *]
└── index.ts                        [Feature exports]
```

### Backend (Read-Only Reference)
```
server/src/api/schemas/
├── pdf_files.py                    [PdfObjects schema - source of truth]
└── pdf_templates.py                [Template schemas]
```

---

## Data Type Reference

### BBox (Bounding Box)
```typescript
export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]
```

### PdfObjects Structure
```typescript
export interface PdfObjects {
  text_words: TextWordObject[];      // Text at word granularity
  text_lines: TextLineObject[];      // Text at line granularity
  graphic_rects: GraphicRectObject[]; // Rectangle graphics
  graphic_lines: GraphicLineObject[]; // Line graphics
  graphic_curves: GraphicCurveObject[]; // Curve graphics (bezier, etc.)
  images: ImageObject[];              // Embedded images
  tables: TableObject[];              // Table structures
}
```

### Required Fields (NOT Optional)
All object types have required fields that match backend:
- TextWordObject: `fontname`, `fontsize` (REQUIRED)
- GraphicRectObject: `linewidth` (REQUIRED)
- GraphicLineObject: `linewidth` (REQUIRED)
- GraphicCurveObject: `linewidth`, `points` (REQUIRED)
- ImageObject: `format`, `colorspace`, `bits` (REQUIRED)
- TableObject: `rows`, `cols` (REQUIRED)

**Critical**: Templates feature previously had these as optional (`fontname?`) - INCORRECT

---

## Debugging Reference

### TypeScript Compilation Check
```bash
cd client && npx tsc --noEmit
```

### Finding Type Definitions
```bash
# Find all PdfObjects definitions
grep -r "interface PdfObjects" client/src/renderer/features/

# Find all imports of PdfObjects
grep -r "import.*PdfObjects" client/src/renderer/features/
```

---

## User Feedback History

1. **"Awesome, all of the pipeline stuff is totally working now"** - Pipeline work complete, move to templates
2. **Request to refactor templates** - "build out the directory structure of templates to match the others"
3. **Directive to start with API layer** - "start via the api, and the types, and then working our way through the component tree"
4. **Request for analysis** - "Make no changes, just provide an analysis"
5. **Approval to implement** - "Ok, please implement those improvements in that case"
6. **PdfObjects issue identified** - "we need to first fix the reference to the pdf objects"
7. **Architectural improvement** - "PdfObjects type should exist in pdf/types.ts instead of pdf/api/types.ts"
8. **Session continuity** - "create / update continuity.md...commit all uncommited changes and push to remote"

---

## Quick Start for Next Session

1. Read this document completely
2. Review git status to verify all changes are committed
3. Continue with templates component tree refactoring
4. Follow established patterns from modules/pipelines features
5. Focus on component structure, not API layer (already complete)

---

## Additional Context

### Session Rituals (from CLAUDE.md)
- Read CHANGELOG.md before starting work
- Append new entry to CHANGELOG.md after session
- Rotate to last 10 entries only
- Commit substantial changes with conventional commit format
- Never run `npm run dev` or development servers (user manages testing)

### Commit Discipline
**Substantial change = any of**:
- Functional behavior changed or new feature added
- Database schema / migrations modified
- Public API, CLI flags, or file formats changed
- Refactor exceeding ~30 lines in a file, or multi-file edits
- Dependency or build config updated

**Current session**: Qualifies as substantial (multi-file refactor, type system changes)

---

## Success Criteria

- [x] Templates API types follow naming conventions
- [x] No unnecessary type aliases
- [x] PdfObjects type consolidated to single source
- [x] Domain types separated from API types
- [x] TypeScript compilation: 0 errors
- [x] All imports work across feature boundaries
- [ ] Changes committed and pushed to remote
- [ ] Templates component tree refactored (future work)

---

## End of Continuity Document

**Current Status**: Templates API layer refactored, PdfObjects consolidated, ready to commit

**Next Immediate Action**: Commit changes and push to remote

**Next Development Action**: Begin templates component tree refactoring

**Estimated Time for Component Refactoring**: 2-4 hours depending on component complexity

---

## Architecture Pattern Summary

**Feature Structure** (Established Pattern):
```
features/{feature-name}/
├── types.ts              # Domain types (business entities)
├── api/
│   ├── types.ts          # API request/response DTOs
│   ├── hooks.ts          # TanStack Query hooks
│   └── index.ts          # API exports (export *)
├── components/           # React components
├── hooks/                # React hooks (non-API)
└── index.ts              # Feature public API (explicit exports)
```

**Cross-Feature Type Imports**: Allowed and encouraged to avoid duplication
```typescript
// templates/types.ts
import type { BBox, PdfObjects } from '../pdf';
```

**Type Naming**:
- Request: `{Verb}{Entity}Request` (CreateTemplateRequest)
- Response: Use domain types directly (TemplateDetail)
- No HTTP method prefixes (Post, Get, Put)
- No unnecessary aliases

**Export Patterns**:
- api/index.ts: `export *` for simplicity
- feature/index.ts: Explicit exports for clear public API
