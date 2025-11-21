# ETO Database Redesign: Multi-Template Matching Per PDF

## Document Purpose

This document outlines the proposed database schema changes to enable **multiple template matches per PDF** in the ETO (Extract-Transform-Output) system. Currently, the system matches one template to an entire PDF. The new design will allow different page ranges within a single PDF to match different templates.

---

## Current System Overview

### Current Flow
```
Email → PDF File → ETO Run (1:1 with PDF)
                      ↓
              Template Matching (finds ONE template for entire PDF)
                      ↓
              Data Extraction (extracts from entire PDF)
                      ↓
              Pipeline Execution (processes all extracted data)
```

### Current Database Structure

```
eto_runs (1 per PDF)
    ├── eto_run_template_matchings (1 record - matches entire PDF to one template)
    ├── eto_run_extractions (1 record - extracts from entire PDF)
    └── eto_run_pipeline_executions (1 record - processes all extracted data)
            └── eto_run_pipeline_execution_steps (multiple steps)
```

### Current Limitations

1. **One Template Per PDF**: If a PDF contains multiple document types (e.g., pages 1-3 are an Invoice, pages 4-6 are a Receipt), only ONE template can match the entire PDF
2. **Missed Documents**: Other document types in the same PDF are ignored
3. **Manual Splitting Required**: Users must manually split PDFs containing multiple document types
4. **Inefficient Processing**: Cannot process different sections of a PDF with different extraction/pipeline logic

---

## New System Design

### New Flow
```
Email → PDF File → ETO Run (still 1:1 with PDF)
                      ↓
              ┌──────┴──────┬──────────────┬──────────────┐
              ↓             ↓              ↓              ↓
     Match 1 (pg 1-3)  Match 2 (pg 4-6)  Match 3 (pg 7)  Match 4 (pg 8-10)
     Invoice Template  Receipt Template  Form Template   NO MATCH
              ↓             ↓              ↓              ↓
     Extract (pg 1-3)  Extract (pg 4-6)  Extract (pg 7)  (tracked only)
              ↓             ↓              ↓
     Pipeline 1        Pipeline 2        Pipeline 3
              ↓             ↓              ↓
     Steps 1-N         Steps 1-N         Steps 1-N
```

### New Database Structure (Hierarchical)

```
eto_runs (1 per PDF)
    ├── eto_run_template_matches (MULTIPLE - one per page range)
    │       ├── eto_run_extractions (1 per match, if template found)
    │       └── eto_run_pipeline_executions (1 per match, if template found)
    │               └── eto_run_pipeline_execution_steps (multiple)
    │
    ├── eto_run_template_matches (another page range)
    │       ├── eto_run_extractions
    │       └── eto_run_pipeline_executions
    │               └── eto_run_pipeline_execution_steps
    │
    └── eto_run_template_matches (unmatched pages - no template)
            └── (no extraction or pipeline - just tracked)
```

---

## Key Design Principles

### 1. **Hierarchical Relationships**
- `eto_run` → `eto_run_template_matches` (parent → children)
- `eto_run_template_matches` → `eto_run_extractions` (1:1, optional)
- `eto_run_template_matches` → `eto_run_pipeline_executions` (1:1, optional)
- `eto_run_pipeline_executions` → `eto_run_pipeline_execution_steps` (1:many)

### 2. **Template Matching is Binary (Not Confidence-Based)**
- Each page range either matches a template (YES) or doesn't (NO)
- If multiple templates could match, an algorithm picks the BEST one
- No confidence scores or probabilistic matching

### 3. **All Pages Must Be Accounted For**
- Every page in the PDF must be assigned to a template match record
- Unmatched pages get a record with `match_status='no_match'` and `matched_template_version_id=NULL`
- No pages should be orphaned or untracked

### 4. **No Extraction/Pipeline for Unmatched Pages**
- If `match_status='no_match'`, no extraction or pipeline execution is created
- The match record exists purely for tracking purposes

---

## Schema Changes

### NEW TABLE: `eto_run_template_matches`

**Purpose:** Primary intermediary table that represents a template match for a specific page range.

```sql
CREATE TABLE eto_run_template_matches (
    id                          INT PRIMARY KEY AUTO_INCREMENT,
    eto_run_id                  INT NOT NULL,  -- FK to eto_runs.id

    -- Pages this match covers (1-indexed)
    matched_pages               VARCHAR(500) NOT NULL,  -- JSON array: "[1,2,3]"

    -- Template that matched (NULL if no template matched these pages)
    matched_template_version_id INT,  -- FK to pdf_template_versions.id (nullable)

    -- Status of the matching process
    match_status                ENUM('matched', 'no_match', 'skipped', 'error') NOT NULL,

    -- Processing order (for UI display and sequential processing)
    match_sequence              INT NOT NULL,

    -- Error tracking
    error_message               TEXT,

    created_at                  DATETIME NOT NULL,
    updated_at                  DATETIME NOT NULL,

    FOREIGN KEY (eto_run_id) REFERENCES eto_runs(id),
    FOREIGN KEY (matched_template_version_id) REFERENCES pdf_template_versions(id),
    INDEX idx_template_match_run (eto_run_id),
    INDEX idx_template_match_status (match_status),
    INDEX idx_template_match_sequence (eto_run_id, match_sequence)
);
```

**Field Explanations:**

- **`matched_pages`**: JSON array of 1-indexed page numbers, e.g., `"[1,2,3]"` for pages 1-3
- **`matched_template_version_id`**:
  - If `match_status='matched'`: references the template that matched
  - If `match_status='no_match'`: NULL (no template found)
- **`match_status`**:
  - `'matched'`: Template successfully matched these pages
  - `'no_match'`: No template matched these pages
  - `'skipped'`: User manually skipped these pages
  - `'error'`: Matching process failed
- **`match_sequence`**: Defines processing order (pages 1-3 = sequence 1, pages 4-6 = sequence 2, etc.)

---

### MODIFIED TABLE: `eto_run_extractions`

**Changes:**
- **Remove:** `eto_run_id` foreign key
- **Add:** `template_match_id` foreign key (references `eto_run_template_matches.id`)

**New Structure:**
```sql
CREATE TABLE eto_run_extractions (
    id                 INT PRIMARY KEY AUTO_INCREMENT,
    template_match_id  INT NOT NULL,  -- FK to eto_run_template_matches.id (CHANGED)
    status             ENUM('processing', 'success', 'failure') NOT NULL DEFAULT 'processing',
    extracted_data     TEXT,
    error_message      TEXT,
    started_at         DATETIME,
    completed_at       DATETIME,
    created_at         DATETIME NOT NULL,
    updated_at         DATETIME NOT NULL,

    FOREIGN KEY (template_match_id) REFERENCES eto_run_template_matches(id),
    INDEX idx_extraction_template_match (template_match_id),
    INDEX idx_extraction_status (status)
);
```

**Rationale:** Each extraction now belongs to a specific template match (not directly to the ETO run).

---

### MODIFIED TABLE: `eto_run_pipeline_executions`

**Changes:**
- **Remove:** `eto_run_id` foreign key
- **Add:** `template_match_id` foreign key (references `eto_run_template_matches.id`)

**New Structure:**
```sql
CREATE TABLE eto_run_pipeline_executions (
    id                   INT PRIMARY KEY AUTO_INCREMENT,
    template_match_id    INT NOT NULL,  -- FK to eto_run_template_matches.id (CHANGED)
    status               ENUM('processing', 'success', 'failure') NOT NULL DEFAULT 'processing',
    executed_actions     TEXT,
    error_message        TEXT,
    started_at           DATETIME,
    completed_at         DATETIME,
    created_at           DATETIME NOT NULL,
    updated_at           DATETIME NOT NULL,

    FOREIGN KEY (template_match_id) REFERENCES eto_run_template_matches(id),
    INDEX idx_pipeline_exec_template_match (template_match_id),
    INDEX idx_pipeline_exec_status (status)
);
```

**Rationale:** Each pipeline execution now belongs to a specific template match (not directly to the ETO run).

---

### MODIFIED TABLE: `eto_runs`

**Changes:**
- **Remove:** Direct relationships to `eto_run_extractions` and `eto_run_pipeline_executions`
- **Add:** Relationship to `eto_run_template_matches`

**Updated Relationships:**
```python
class EtoRunModel(BaseModel):
    # ... existing fields unchanged ...

    # Relationships
    pdf_file: Mapped["PdfFileModel"] = relationship(back_populates="eto_runs")

    # NEW: Primary relationship to template matches
    template_matches: Mapped[List["EtoRunTemplateMatchModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    # REMOVED: Direct relationships to extractions and pipeline_executions
    # (Now accessed through template_matches)
```

---

## Example Data Scenario

### Scenario: 10-page PDF with Mixed Document Types

**PDF Contents:**
- Pages 1-3: Invoice
- Pages 4-6: Receipt
- Pages 7: W-9 Form
- Pages 8-10: Unrecognized document (no template match)

### Database Records Created

#### `eto_runs`
```json
{
  "id": 100,
  "pdf_file_id": 50,
  "status": "success",
  "processing_step": null,
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### `eto_run_template_matches` (4 records)
```json
[
  {
    "id": 1001,
    "eto_run_id": 100,
    "matched_pages": "[1,2,3]",
    "matched_template_version_id": 10,  // Invoice template
    "match_status": "matched",
    "match_sequence": 1,
    "error_message": null
  },
  {
    "id": 1002,
    "eto_run_id": 100,
    "matched_pages": "[4,5,6]",
    "matched_template_version_id": 15,  // Receipt template
    "match_status": "matched",
    "match_sequence": 2,
    "error_message": null
  },
  {
    "id": 1003,
    "eto_run_id": 100,
    "matched_pages": "[7]",
    "matched_template_version_id": 20,  // W-9 template
    "match_status": "matched",
    "match_sequence": 3,
    "error_message": null
  },
  {
    "id": 1004,
    "eto_run_id": 100,
    "matched_pages": "[8,9,10]",
    "matched_template_version_id": null,  // No template
    "match_status": "no_match",
    "match_sequence": 4,
    "error_message": null
  }
]
```

#### `eto_run_extractions` (3 records - only for matched templates)
```json
[
  {
    "id": 2001,
    "template_match_id": 1001,
    "status": "success",
    "extracted_data": "{\"invoice_number\": \"INV-123\", ...}"
  },
  {
    "id": 2002,
    "template_match_id": 1002,
    "status": "success",
    "extracted_data": "{\"receipt_total\": 45.67, ...}"
  },
  {
    "id": 2003,
    "template_match_id": 1003,
    "status": "success",
    "extracted_data": "{\"taxpayer_id\": \"12-3456789\", ...}"
  }
]
```
*Note: No extraction for match 1004 (unmatched pages)*

#### `eto_run_pipeline_executions` (3 records - only for matched templates)
```json
[
  {
    "id": 3001,
    "template_match_id": 1001,
    "status": "success",
    "executed_actions": "{\"email_sent\": true, ...}"
  },
  {
    "id": 3002,
    "template_match_id": 1002,
    "status": "success",
    "executed_actions": "{\"database_updated\": true, ...}"
  },
  {
    "id": 3003,
    "template_match_id": 1003,
    "status": "success",
    "executed_actions": "{\"file_archived\": true, ...}"
  }
]
```
*Note: No pipeline execution for match 1004 (unmatched pages)*

#### `eto_run_pipeline_execution_steps` (variable count per pipeline)
```json
[
  // Steps for pipeline 3001 (Invoice)
  {"id": 4001, "pipeline_execution_id": 3001, "step_number": 1, "module_instance_id": "M1"},
  {"id": 4002, "pipeline_execution_id": 3001, "step_number": 2, "module_instance_id": "M2"},

  // Steps for pipeline 3002 (Receipt)
  {"id": 4003, "pipeline_execution_id": 3002, "step_number": 1, "module_instance_id": "M3"},

  // Steps for pipeline 3003 (W-9)
  {"id": 4004, "pipeline_execution_id": 3003, "step_number": 1, "module_instance_id": "M4"},
  {"id": 4005, "pipeline_execution_id": 3003, "step_number": 2, "module_instance_id": "M5"}
]
```

---

## Page Coverage Validation

### Requirement
Every page in the PDF must be accounted for in `eto_run_template_matches` records.

### Validation Logic
```python
def validate_page_coverage(eto_run_id: int, total_pages: int) -> dict:
    """Ensure all pages are covered by template matches"""

    matches = db.query(EtoRunTemplateMatchModel).filter_by(eto_run_id=eto_run_id).all()

    covered_pages = set()
    for match in matches:
        pages = json.loads(match.matched_pages)
        covered_pages.update(pages)

    all_pages = set(range(1, total_pages + 1))
    missing_pages = all_pages - covered_pages

    # Check for overlapping pages (same page in multiple matches - should not happen)
    all_listed_pages = []
    for match in matches:
        pages = json.loads(match.matched_pages)
        all_listed_pages.extend(pages)

    has_overlaps = len(all_listed_pages) > len(set(all_listed_pages))

    return {
        "complete": len(missing_pages) == 0,
        "missing_pages": sorted(list(missing_pages)),
        "has_overlaps": has_overlaps,
        "coverage_percent": len(covered_pages) / total_pages * 100
    }
```

### Rules
1. **No Missing Pages**: All pages from 1 to `page_count` must be in at least one match
2. **No Overlapping Pages**: Each page should appear in exactly one match (no duplicates)
3. **Sequential Matching**: `match_sequence` should be ordered by page ranges for UI display

---

## Query Examples

### Get All Matches for a Run (Including Unmatched)
```python
matches = db.query(EtoRunTemplateMatchModel)\
    .filter_by(eto_run_id=100)\
    .order_by(EtoRunTemplateMatchModel.match_sequence)\
    .all()
```

### Get Only Successful Extractions for a Run
```python
extractions = db.query(EtoRunExtractionModel)\
    .join(EtoRunTemplateMatchModel)\
    .filter(EtoRunTemplateMatchModel.eto_run_id == 100)\
    .filter(EtoRunExtractionModel.status == 'success')\
    .all()
```

### Find Unmatched Pages in a Run
```python
unmatched = db.query(EtoRunTemplateMatchModel)\
    .filter_by(eto_run_id=100, match_status='no_match')\
    .all()

for match in unmatched:
    pages = json.loads(match.matched_pages)
    print(f"Unmatched pages: {pages}")
```

### Get Complete Hierarchy for a Run
```python
from sqlalchemy.orm import joinedload

run = db.query(EtoRunModel)\
    .options(
        joinedload(EtoRunModel.template_matches)
            .joinedload(EtoRunTemplateMatchModel.extraction),
        joinedload(EtoRunModel.template_matches)
            .joinedload(EtoRunTemplateMatchModel.pipeline_execution)
            .joinedload(EtoRunPipelineExecutionModel.steps)
    )\
    .filter_by(id=100)\
    .one()

# Access data
for match in run.template_matches:
    print(f"Match {match.id}: Pages {match.matched_pages}")
    if match.extraction:
        print(f"  Extraction: {match.extraction.status}")
    if match.pipeline_execution:
        print(f"  Pipeline: {match.pipeline_execution.status}")
        for step in match.pipeline_execution.steps:
            print(f"    Step {step.step_number}: {step.module_instance_id}")
```

### Count Templates Matched Per Run
```python
matched_count = db.query(EtoRunTemplateMatchModel)\
    .filter_by(eto_run_id=100, match_status='matched')\
    .count()

unmatched_count = db.query(EtoRunTemplateMatchModel)\
    .filter_by(eto_run_id=100, match_status='no_match')\
    .count()
```

---

## Migration Strategy

### Phase 1: Schema Migration (Backward Compatible)

1. **Add New Table**: `eto_run_template_matches`
2. **Add New Columns**: `template_match_id` to `eto_run_extractions` and `eto_run_pipeline_executions` (nullable initially)
3. **Keep Old Columns**: `eto_run_id` in child tables (for backward compatibility)

### Phase 2: Data Backfill

For each existing ETO run:
1. Create ONE `eto_run_template_matches` record representing the entire PDF
2. Set `matched_pages` = all pages `"[1,2,3,...,N]"`
3. Set `matched_template_version_id` = the current template match
4. Set `match_status` = `'matched'` (or `'no_match'` if no template)
5. Set `match_sequence` = 1
6. Update `eto_run_extractions.template_match_id` to reference this match
7. Update `eto_run_pipeline_executions.template_match_id` to reference this match

### Phase 3: Code Updates

1. **Template Matching Service**: Update to create multiple match records per run
2. **Extraction Service**: Update to work with `template_match_id` instead of `eto_run_id`
3. **Pipeline Service**: Update to work with `template_match_id` instead of `eto_run_id`
4. **API Endpoints**: Update to return template matches in hierarchical structure

### Phase 4: Remove Old Schema

1. **Drop Foreign Keys**: Remove `eto_run_id` from `eto_run_extractions` and `eto_run_pipeline_executions`
2. **Remove Old Columns**: Drop the now-unused `eto_run_id` columns

---

## Benefits

### 1. **Multiple Documents Per PDF**
- Process invoices, receipts, and forms from the same PDF automatically
- No manual splitting required

### 2. **Page-Level Tracking**
- Know exactly which pages matched which template
- Identify unmatched pages for manual review

### 3. **Independent Processing Paths**
- Different templates can have different extraction fields
- Different pipelines can execute different actions
- Process each document type optimally

### 4. **Better Error Handling**
- If one template match fails, others can still succeed
- Granular error tracking per page range

### 5. **Scalability**
- Handle complex multi-document PDFs (10+ different document types)
- Support non-contiguous page ranges (e.g., pages 1,3,5 match one template)

### 6. **Backward Compatible**
- Single-template PDFs work exactly as before (just one match record)
- Migration path preserves existing data

### 7. **Audit Trail**
- Complete history of which pages were processed by which template
- Track unmatched pages for template creation opportunities

---

## Open Questions

### 1. Template Matching Algorithm
**Question:** When multiple templates could match a page range, how is the "best" template selected?

**Options:**
- Signature object overlap percentage (most objects matched)
- Template priority/ranking system
- Manual user selection in case of ambiguity

### 2. Page Range Specification
**Question:** Should page ranges be contiguous only, or allow non-contiguous pages?

**Example:**
- Contiguous: `"[1,2,3]"` (pages 1-3)
- Non-contiguous: `"[1,3,5]"` (pages 1, 3, and 5 only)

**Current Design:** Supports both (JSON array format)

### 3. Overlapping Matches
**Question:** Can the same page appear in multiple template matches?

**Recommendation:** NO - each page should belong to exactly one match to avoid processing the same page twice.

### 4. Minimum Match Size
**Question:** What's the minimum number of pages for a match?

**Options:**
- Minimum 1 page (single-page documents allowed)
- Minimum 2+ pages (enforce multi-page documents only)

**Recommendation:** Minimum 1 page (templates can match single pages)

### 5. UI Display of Matches
**Question:** How should unmatched pages be displayed to users?

**Options:**
- Show as "Unmatched" status with page range
- Allow user to manually assign template
- Suggest creating new template from unmatched pages

---

## Related Documentation

- **Current Database Schema**: `server/src/shared/database/models.py`
- **Template Matching Service**: `server/src/features/eto/services/template_matching.py` (to be updated)
- **ETO Processing Service**: `server/src/features/eto/services/processing.py` (to be updated)
- **Frontend ETO Run Display**: `client/src/features/eto/components/EtoRunDetailViewer.tsx` (to be updated)

---

## Next Steps

1. **Finalize Design**: Review and approve schema changes
2. **Create Migration Scripts**: Write Alembic migrations for schema changes
3. **Update Models**: Modify SQLAlchemy models in `models.py`
4. **Update Services**: Refactor template matching, extraction, and pipeline services
5. **Update API**: Modify endpoints to support new hierarchical structure
6. **Update Frontend**: Build UI to display multiple matches per run
7. **Testing**: Comprehensive testing with multi-document PDFs
8. **Documentation**: Update API docs and user guides

---

## Schema Diagram (ASCII)

```
┌─────────────────┐
│   eto_runs      │
│  (1 per PDF)    │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌──────────────────────────┐
│ eto_run_template_matches │
│  (1 per page range)      │
│  - matched_pages         │
│  - template_version_id   │
│  - match_status          │
└────────┬────────┬────────┘
         │        │
    1:1  │        │ 1:1
    opt  │        │ opt
         ▼        ▼
┌─────────────┐ ┌──────────────────────┐
│ extractions │ │ pipeline_executions  │
│  (if match) │ │  (if match)          │
└─────────────┘ └──────────┬───────────┘
                           │
                      1:N  │
                           ▼
                ┌────────────────────┐
                │ pipeline_steps     │
                │  (execution steps) │
                └────────────────────┘
```

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Author:** Database Redesign Team
