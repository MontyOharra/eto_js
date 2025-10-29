# API Design Specification

## Status: In Progress

**Current Phase:** Phase 1 - Domain & Router Segmentation ✓ (Complete)

---

## Design Process Tracker

- [x] Phase 1: Domain & Router Segmentation
- [ ] Phase 2: Per-Domain Analysis (Defining needs for each router)
- [ ] Phase 3: Endpoint Definitions
- [ ] Phase 4: Schema Definitions (Request/Response/Errors)
- [ ] Phase 5: Cross-router Integration Points

---

## Foundation

### Source of Truth
**Database Schema:** `server/src/shared/database/models.py`
- This is the definitive data storage design
- All API design must align with this schema
- Schema is considered finalized (for current iteration)

### Design Focus
- **Conceptual understanding** of system functionality
- **Frontend requirements** drive all decisions
- **No implementation details** at this stage
- Focus on **what the system does**, not **how it works**

---

## Domains & Routers

### 1. `/email-configs` - Email Ingestion Control
**Purpose:** Manage email ingestion configurations that instruct the server how to monitor and process emails.

**Core Responsibility:**
- User defines email monitoring rules and settings
- Server executes email ingestion based on these configurations
- User manages active/inactive states of configs

**Database Tables:**
- `email_configs` (primary)
- `emails` (related - stores processed emails)

---

### 2. `/eto-runs` - ETO Processing Control
**Purpose:** Monitor and manage ETO (Email-to-Order) processing runs that extract data from PDFs.

**Core Responsibility:**
- **Create runs manually** by uploading PDF files (manual mode)
- View status and details of ETO processing runs
- Manage run lifecycle (skip failed runs, trigger reprocessing)
- Monitor processing stages (template matching, data extraction, transformation)
- Triggered both manually (PDF upload via this route) and automatically (email ingestion)

**Database Tables:**
- `eto_runs` (primary - orchestration record)
- `eto_run_template_matchings` (stage 1 details)
- `eto_run_extractions` (stage 2 details)
- `eto_run_pipeline_executions` (stage 3 run details)
- `eto_run_pipeline_execution_steps` (stage 3 step details)
- `pdf_files` (related - source PDFs created during manual upload)

---

### 3. `/pdf-templates` - PDF Template Management
**Purpose:** Define and manage templates that specify how the system processes PDFs during ETO runs.

**Core Responsibility:**
- Create new templates from source PDFs
- Define signature objects (for template matching)
- Define extraction fields (spatial bounding boxes)
- Associate transformation pipelines with templates
- Manage template versions and activation status

**Database Tables:**
- `pdf_templates` (primary - template metadata)
- `pdf_template_versions` (versions with signature objects, extraction fields, pipeline references)
- `pdf_files` (related - source PDFs for templates)
- `pipeline_definitions` (related - associated transformation logic)

---

### 4. `/modules` - Module Catalog Viewing
**Purpose:** Provide read-only access to available transformation modules for pipeline building.

**Core Responsibility:**
- List available modules (transform, action, logic, etc.)
- Provide module metadata (inputs, outputs, configuration schema)
- Filter modules by category, type, or active status
- Support frontend pipeline builder UI with module information

**Database Tables:**
- `module_catalog` (primary - read-only for frontend)

**Note:** Users cannot create/modify modules via frontend - modules are server-managed code.

---

### 5. `/pipelines` - Pipeline Viewing & Building
**Purpose:** View and manage transformation pipelines that define data processing logic within templates.

**Core Responsibility:**
- View compiled pipelines and their execution steps
- Provide pipeline definitions for frontend graph builder
- Save pipeline state (visual representation + logical structure)
- Support pipeline compilation (validation, topological sort, step generation)

**Database Tables:**
- `pipeline_definitions` (primary - stores pipeline state)
- `pipeline_compiled_plans` (compiled execution plans)
- `pipeline_definition_steps` (individual transformation steps)
- `module_catalog` (related - modules used in steps)

**Note:** Pipelines are tightly coupled to templates but separated for data complexity reasons.

---

### 6. `/health` - System Health Monitoring
**Purpose:** Provide system health status for frontend monitoring and operational visibility.

**Core Responsibility:**
- Report overall system health status
- Indicate service availability (email ingestion, ETO processing, etc.)
- Support frontend "system running" indicators
- Enable operational monitoring for troubleshooting

**Database Tables:**
- None (reports runtime status, not persistent data)

**Note:** Authentication not required for current iteration (on-premise local network deployment).

---

## Router Relationships

### Data Flow Overview
```
Manual Upload OR Email Ingestion → PDF Files → ETO Runs → Template Matching
                                                      ↓
                                              PDF Templates (with Pipelines)
                                                      ↓
                                              Data Extraction + Transformation
```

### Cross-Domain Interactions
1. **Email Configs → ETO Runs**: Email ingestion triggers automatic ETO processing
2. **ETO Runs → PDF Files**: Manual uploads create PDFs and initiate runs
3. **PDF Templates → ETO Runs**: Templates determine how ETO runs process PDFs
4. **Pipelines → PDF Templates**: Each template version references a pipeline
5. **Modules → Pipelines**: Pipelines are built from module instances
6. **PDF Files → Templates & ETO**: PDFs serve as both template sources and processing inputs

### Design Decisions
- **No dedicated `/pdf-files` router**: PDF uploads handled via `/eto-runs` (manual mode)
- **No `/emails` router**: Email data is internal; users only interact via email configs
- **No authentication**: Current iteration is on-premise local network deployment
- **Future `/admin` consideration**: Module version management deferred to future iteration

---

## Global Design Rules

### Field Exclusions
**Never include in API responses (dev audit only):**
- `created_at`
- `updated_at`

These timestamp fields exist solely for development auditing and should not be exposed to frontend clients.

---

## Phase 2: Per-Domain Analysis

### Domain 1: `/email-configs` - Email Ingestion Configuration

#### User Workflows

**1. Configuration Lifecycle**
- **Create**: Multi-step wizard with discovery and validation
- **Read**: List view (summary) and detail view (full config)
- **Update**: Edit existing configuration settings
- **Delete**: Remove configuration
- **Activate**: Enable email monitoring (starts background thread)
- **Deactivate**: Stop email monitoring (stops background thread)

**2. Configuration Discovery (Pre-Creation)**
- **Step 1 - Account Discovery**: List available email accounts/addresses
- **Step 2 - Folder Discovery**: List available folders for selected account
- **Step 3 - Configuration**: Define monitoring rules and filters
- **Step 4 - Validation**: Test configuration before saving

**3. Configuration Management**
- **Concurrent Active Configs**: Multiple configs can be active simultaneously (each runs on separate thread)
- **Runtime Monitoring**: View real-time status of active configs
- **Error Handling**: View error messages from failed operations

---

#### Data Requirements

**List View (Summary)**
- `id`
- `name`
- `is_active` (boolean)
- `last_check_time` (datetime - only if activated)

**Detail View (Full Configuration)**
All fields from `email_configs` table except:
- ❌ `created_at` (excluded - audit only)
- ❌ `updated_at` (excluded - audit only)

**Included fields:**
- `id`
- `name`
- `description`
- `email_address`
- `folder_name`
- `filter_rules` (JSON - see structure below)
- `poll_interval_seconds`
- `max_backlog_hours`
- `error_retry_attempts`
- `is_active`
- `activated_at`
- `is_running`
- `last_check_time`
- `last_error_message`
- `last_error_at`
- `total_emails_processed` (statistics)
- `total_pdfs_found` (statistics)

**Filter Rules Structure:**
```
FilterRule {
  field: "sender_email" | "subject" | "has_attachments" | "attachment_types"
  operation: "contains" | "equals" | "starts_with" | "ends_with"
  value: string
  case_sensitive: boolean
}
```

---

#### Business Rules & Constraints

**Configuration Validation**
- Email address must be accessible by server
- Folder must exist within specified email account
- Filter rules must have valid field/operation combinations
- Poll interval must be >= 5 seconds
- Max backlog must be >= 1 hour
- Error retry attempts must be 1-10

**Activation Rules**
- Can activate multiple configs simultaneously
- Each active config runs on independent thread
- Activation sets `activated_at` and `last_check_time` to current time
- Cannot delete active config (must deactivate first)

**Threading Model**
- Each config runs independently
- Threads can be stopped/started individually
- Thread crashes do not affect other configs
- Server restart resumes all previously active configs

**Monitoring Rules**
- Only show `is_running` if config is active
- `last_check_time` only meaningful when active
- Statistics (`total_emails_processed`) only increment while active

---

#### Frontend Workflows

**Creation Wizard (4 Steps)**

**Step 1: Account Discovery**
- API call: Get available email accounts
- User selects email address
- Validates server can access account

**Step 2: Folder Discovery**
- API call: Get available folders for selected account
- User selects folder to monitor
- Displays folder metadata (message count, etc.)

**Step 3: Configuration**
- User enters: name, description
- User configures: poll interval, backlog, retry attempts
- User defines filter rules (add/remove/edit)

**Step 4: Validation & Save**
- API call: Validate configuration (test connection)
- Display validation results (success/errors)
- User saves configuration (POST to create)

**Management Actions**
- **View List**: See all configs with summary info
- **View Details**: Open specific config to see full settings
- **Edit**: Modify config settings (must be inactive)
- **Activate**: Start email monitoring
- **Deactivate**: Stop email monitoring
- **Delete**: Remove config (must be inactive)

---

#### Design Decisions for `/email-configs`

1. **Edit restrictions**: Must deactivate before editing, then reactivate
2. **Statistics persistence**: Statistics persist through deactivation/reactivation cycles
3. **Discovery strategy**: Always fetch fresh (no caching) - infrequent operation
4. **Validation scope**: Test connection only (not actual email retrieval)
5. **Filter rule limits**: Unlimited (no artificial cap)

---

### Domain 1: `/email-configs` - ✓ COMPLETE

---

---

### Domain 2: `/eto-runs` - ETO Processing Control

#### User Workflows

**1. Manual Run Creation**
- **Upload PDF**: User uploads single PDF file (no metadata required)
- **Immediate Creation**: System creates ETO run with `not_started` status
- **Background Processing**: Worker automatically picks up `not_started` runs

**2. Run Monitoring (Status-Based Views)**
Six separate tables, one per status:
- `not_started` - Queued for processing
- `processing` - Currently being processed
- `success` - Completed successfully
- `failure` - Failed during processing
- `needs_template` - No matching template found
- `skipped` - Manually skipped by user

**3. Run Lifecycle Actions**
- **Reprocess**: Reset to `not_started` status, clear stage records (start from beginning)
- **Skip**: Set status to `skipped` (exclude from bulk reprocessing)
- **Delete**: Permanently remove from database (only from `skipped` table)
- **View Details**: Open detailed view of run stages and results
- **Create Template**: Build new template from PDF (only from `needs_template` table)

---

#### Data Requirements

**Table View (Status-Segmented)**

Each status table shows:
- `id` (run ID)
- `pdf_file_id` (reference to source PDF)
- `status` (current status)
- `processing_step` (last completed step)
- `started_at` (when processing began)
- `completed_at` (when processing finished)
- `error_type` (if failure)
- `error_message` (brief error description)

**Sorting Options (All Tables):**
- `started_at` (ASC/DESC)
- `completed_at` (ASC/DESC)

**Detail View (Full Run Information)**

**Core Run Data:**
- All fields from `eto_runs` table (except `created_at`, `updated_at`)

**Stage 1: Template Matching** (`eto_run_template_matchings`)
- `status` (processing/success/failure)
- `matched_template_version_id` (which template matched)
- `started_at`, `completed_at`

**Stage 2: Data Extraction** (`eto_run_extractions`)
- `status` (processing/success/failure)
- `extracted_data` (JSON - field values extracted from PDF)
- `started_at`, `completed_at`

**Stage 3: Pipeline Execution** (`eto_run_pipeline_executions`)
- `status` (processing/success/failure)
- `executed_actions` (JSON - list of actions performed, e.g., "Order Created", "Email Sent")
- `started_at`, `completed_at`

**Stage 3 Steps** (`eto_run_pipeline_execution_steps`)
- `module_instance_id` (which module executed)
- `step_number` (execution order)
- `inputs` (JSON - data fed to module)
- `outputs` (JSON - data produced by module)
- `error` (JSON - error details if step failed)

**PDF Access:**
- View PDF via existing `/api/pdf-files/{pdf_file_id}` endpoint
- PDF file ID available in run data
- Only shown in `success` and `failure` detail views

---

#### Business Rules & Constraints

**Run Creation Rules**
- Single PDF upload only
- No user metadata required
- Immediately creates run with `not_started` status
- Worker processes runs automatically

**Processing Model**
- Worker polls for `not_started` runs
- Processes stages sequentially: Template Matching → Extraction → Transformation
- Cannot skip or isolate individual stages
- Automatic process (no manual stage triggering)

**Status Transitions**
```
not_started → processing → success
                         → failure
                         → needs_template

skipped (manual) → not_started (reprocess)
failure → not_started (reprocess)
        → skipped (skip)
needs_template → skipped (skip)

skipped → DELETED (permanent removal)
```

**Reprocessing Rules**
- Clears all stage records (`eto_run_template_matchings`, `eto_run_extractions`, `eto_run_pipeline_executions` + steps)
- Resets status to `not_started`
- Worker picks up and reprocesses from beginning

**Skip Rules**
- Status set to `skipped`
- Excluded from bulk reprocessing operations
- Can be deleted or reprocessed from `skipped` table

**Needs Template Handling**
- Template matching completes successfully (returns `success`)
- ETO run status set to `needs_template`
- Processing stops (extraction/transformation not attempted)
- User must create template via template builder
- No manual template assignment

**Error Visibility**
- `error_type` (category of error)
- `error_message` (brief description)
- `error_details` (full stack trace/context)
- `processing_step` (which stage failed: template_matching, data_extraction, data_transformation)

---

#### Frontend Workflows

**ETO Runs Page Overview**

Six status-based tables with distinct interactions:

**1. Not Started Table**
- **Purpose**: View queued runs awaiting processing
- **Actions**: None (automatic processing)
- **Sorting**: `started_at`, `completed_at`

**2. Processing Table**
- **Purpose**: View currently executing runs
- **Actions**: None (read-only monitoring)
- **Sorting**: `started_at`
- **Display**: Real-time status updates

**3. Success Table**
- **Purpose**: View successfully completed runs
- **Display**: `executed_actions` summary (e.g., "Order #12345 Created", "Confirmation Email Sent")
- **Actions**:
  - **View Details**: See extracted data, transformation steps, execution logs, and PDF
- **Sorting**: `started_at`, `completed_at`

**4. Failure Table**
- **Purpose**: View and recover from failed runs
- **Display**: Error information (`error_type`, `error_message`, `processing_step`)
- **Actions**:
  - **View Details**: See what ran successfully, error specifics, module/function that failed, PDF
  - **Reprocess**: Retry processing from beginning
  - **Skip**: Mark as skipped to exclude from bulk operations
- **Sorting**: `started_at`, `completed_at`

**5. Needs Template Table**
- **Purpose**: Handle PDFs with no matching template
- **Display**: PDF information
- **Actions**:
  - **Create Template**: Open template builder with this PDF
  - **Skip**: Mark as skipped if PDF should not be processed
- **Sorting**: `started_at`, `completed_at`

**6. Skipped Table**
- **Purpose**: Manage intentionally skipped runs
- **Display**: Skipped run information
- **Actions**:
  - **Reprocess**: Reset to `not_started` and retry
  - **Delete**: Permanently remove from database
- **Sorting**: `started_at`, `completed_at`

---

#### Detail View Structure

**Success Detail View:**
- ETO run core info
- Matched template details
- Extracted data (field-by-field)
- Transformation steps (module execution log)
- Executed actions (final results)
- PDF viewer

**Failure Detail View:**
- ETO run core info
- Stage completion status (which stages succeeded)
- Error details:
  - Processing step that failed
  - Error type and message
  - Error details (stack trace, context)
  - Module instance ID (if transformation failure)
- Partial results (if extraction succeeded before transformation failed)
- PDF viewer

**Needs Template Detail View:**
- ETO run core info
- PDF information
- Template matching results (no matches found)
- Link to template builder

---

#### Design Decisions for `/eto-runs`

1. **Upload model**: Single file only, no metadata
2. **Processing trigger**: Automatic via worker polling `not_started` runs
3. **Status segmentation**: Six separate tables (one per status)
4. **Reprocessing**: Always from beginning, clears all stage data
5. **Skip behavior**: Marks as skipped, excludes from bulk reprocessing
6. **Stage isolation**: Not supported (sequential processing only)
7. **Template assignment**: Not supported (must create new template)
8. **PDF viewing**: Via existing `/api/pdf-files/{pdf_file_id}` endpoint (no separate ETO endpoint)
9. **Deletion**: Only from `skipped` status (permanent)
10. **Stage data**: All stages returned in single `GET /{id}` response (no separate stage endpoints)
11. **Statistics**: Not implemented (future enhancement if needed)

---

### Domain 2: `/eto-runs` - ✓ COMPLETE

---

---

### Domain 3: `/pdf-templates` - PDF Template Management

#### Template Conceptual Model

**What is a Template?**
Templates define how to process a specific PDF format:
1. **Signature Objects**: Static elements that identify the template (unchanging images, lines, tables, labels)
2. **Extraction Fields**: Variable areas where form-fillers enter data (spatial bounding boxes)
3. **Transformation Pipeline**: Logic to transform extracted data into orders

**Template Versioning Model:**
- **Template**: High-level container (name, description, source PDF, status)
- **Version**: Specific implementation (signature objects, extraction fields, pipeline)
- Editing creates new version, updates template's `current_version_id`
- Old versions preserved for historical ETO run reference
- Versions never deleted (audit trail)

**Status Model:**
- **Draft**: Being created/tested, not used for matching
- **Active**: Current template used for PDF matching
- **Inactive**: Archived, not used for matching

**Special Version: Draft Version**
- `version_num = 0` reserved for draft versions
- `is_draft = true` flag
- Used for testing before finalizing
- Deleted if user cancels creation

---

#### User Workflows

**1. Template Creation**

**Entry Points:**
- **Via Template Page**: Upload new PDF to create template
- **Via ETO Run**: Create template from `needs_template` run PDF

**3-Step Wizard:**

**Step 1: Signature Objects Selection**
- PDF displayed with extracted objects (text, images, lines, tables)
- User clicks objects to mark as "signature" (static identifiers)
- Selected objects form template's unique fingerprint

**Step 2: Extraction Fields Definition**
- User draws bounding boxes over variable data areas
- Each box labeled (e.g., "customer_name", "hawb", "address")
- Optional validation regex per field
- Mark required fields

**Step 3: Transformation Pipeline Building**
- Visual pipeline graph builder
- Connect modules to transform extracted data
- Define data flow from extraction to actions
- Must build new pipeline (no pipeline reuse)

**Step 4: Testing (Optional)**
- Test template against source PDF
- Backend runs full ETO process **without creating ETO record**
- Action modules **do not execute** (simulation only)
- Returns simulated results (what would be extracted/transformed)
- User validates results

**Finalization:**
- If testing successful: Set status to `active`, save template
- If cancelled: Delete draft version (if editing) or entire template (if new)

---

**2. Template Editing (Version Creation)**

**Process:**
- Select existing template version to edit
- Creates new draft version (`version_num = 0`, `is_draft = true`)
- User modifies: signature objects, extraction fields, and/or pipeline
- Test new version (optional - same testing process)
- Save: Creates new numbered version, updates `current_version_id`, deletes draft
- Cancel: Deletes draft version

**Important:**
- Can edit active templates (creates new version)
- Old versions remain accessible for historical runs
- New version becomes current for all future matching

---

**3. Template Management**

**List View:**
- `id`
- `name`
- `status` (draft/active/inactive)
- `version_count` (total versions)
- `usage_count` (from current version)

**Actions:**
- **View**: See template details and version history
- **Edit**: Create new version (any status)
- **Activate/Deactivate**: Toggle between active/inactive
- **Delete**: Only under specific conditions (see below)
- **View Versions**: List all versions with details

---

#### Data Requirements

**List View (Summary):**
- `id`
- `name`
- `status` (draft/active/inactive)
- Current version number
- Total version count (calculated)
- Current version usage count

**Detail View (Full Template):**
- `id`
- `name`
- `description`
- `source_pdf_id`
- `status`
- `current_version_id`
- Current version details (see below)

**Version Detail View:**
- `id`
- `pdf_template_id`
- `version_num`
- `is_draft`
- `signature_objects` (JSON - list of PDF object IDs/coordinates)
- `extraction_fields` (JSON - bounding boxes with labels)
- `pipeline_definition_id`
- `usage_count` (how many ETO runs used this version)
- `last_used_at`

**Version History View:**
- List of all versions (sorted by version_num DESC)
- Each showing: version_num, created_at, usage_count, is_draft

---

#### Business Rules & Constraints

**Template Creation Rules:**
- Must start from PDF (uploaded or from ETO run)
- PDF automatically processed for object extraction
- Template starts as `draft` status
- Must complete all 3 steps (signature, extraction, pipeline)
- Pipeline must be built from scratch (no pipeline sharing)

**Version Management:**
- Editing always creates new version
- Draft version uses `version_num = 0`, `is_draft = true`
- Saving draft creates new numbered version, updates current_version_id
- Cancelling draft deletes draft version record
- Old versions never deleted (historical reference)

**Status Transitions:**
```
draft → active (after successful test or user confirmation)
active → inactive (deactivate)
inactive → active (reactivate)
```

**Testing Rules:**
- Optional during creation/editing
- Runs full ETO process without creating ETO record
- Action modules simulate (no actual execution)
- Returns extracted data and transformation results
- Does not affect template status until user confirms

**Template Matching:**
- Only `active` templates used for matching
- Matching always uses `current_version_id`
- Old versions not considered for new runs

**Deletion Rules:**
- Can delete templates under specific conditions (TBD - see open questions)
- Cannot delete versions (historical integrity)

**Pipeline Integration:**
- Each template has one unique pipeline
- Pipeline only editable via template wizard
- Multiple pipelines may compile to same execution plan (deduplication)
- Compiler checks if new pipeline matches existing compiled plan
- If match found, reuses existing `pipeline_compiled_plan_id`

---

#### Frontend Workflows

**Template Creation Wizard:**

**Starting Point:**
- Template page: "Create New Template" → Upload PDF
- ETO Run page: `needs_template` run → "Create Template" button

**Step 1: Define Signature Objects**
- Display PDF with overlaid clickable objects
- Object types: text_words, text_lines, images, graphic_rects, tables
- Click to select/deselect signature objects
- Visual indication of selected objects
- "Next" proceeds to Step 2

**Step 2: Define Extraction Fields**
- Drawing mode: Click-and-drag to create bounding boxes
- Box properties:
  - Label (required)
  - Description (optional)
  - Required field (checkbox)
  - Validation regex (optional)
- Edit existing boxes (resize, move, delete)
- "Next" proceeds to Step 3

**Step 3: Build Transformation Pipeline**
- Visual graph builder
- Drag modules from catalog
- Connect modules to define data flow
- Configure module parameters
- Entry points: Extracted fields
- "Next" proceeds to Testing/Save

**Step 4: Test & Finalize**
- "Test Template" button
- Shows simulated results:
  - Extracted data preview
  - Transformation step outputs
  - Simulated actions (without execution)
- "Save Template" → Create/update template
- "Cancel" → Delete draft or entire template

---

**Template Editing (Version Creation):**

**Starting Point:**
- Template list: Select template → "Edit" button
- Opens wizard with existing version data pre-populated

**Workflow:**
- Creates draft version (`version_num = 0`)
- User modifies any/all steps
- Pipeline must be rebuilt (shows previous pipeline as reference)
- Test (optional)
- Save: Creates new numbered version, sets as current
- Cancel: Deletes draft version

---

**Template Management Page:**

**List View:**
- Table showing all templates
- Columns: name, status, version_count, usage_count
- Actions: View, Edit, Activate/Deactivate, Delete

**Detail View:**
- Template metadata
- Current version details
- "View Version History" → List all versions
- "Edit Template" → Create new version

**Version History View:**
- List all versions with metadata
- "View Version" → See specific version details (read-only)
- "Edit from this Version" → Create new draft based on selected version

---

#### Design Decisions for `/pdf-templates`

1. **Creation entry**: Upload PDF or from `needs_template` run
2. **Wizard steps**: 3 steps (signature, extraction, pipeline) + optional testing
3. **Signature selection**: Click PDF objects (pre-extracted)
4. **Extraction definition**: Draw bounding boxes with labels
5. **Pipeline**: Must build new pipeline each time (no reuse)
6. **Versioning**: Edit = new version, old versions preserved
7. **Version history**: Fully visible, can edit from any version
8. **Version activation**: Editing updates current_version_id
9. **Old version handling**: Remain for historical ETO run reference
10. **Editing active templates**: Allowed (creates new version)
11. **Template deletion**: Conditional (TBD)
12. **Testing**: Optional, simulates ETO without execution/record creation
13. **Draft versions**: `version_num = 0`, deleted on cancel
14. **Pipeline sharing**: Not allowed (each template has unique pipeline)
15. **Pipeline editing**: Only via template wizard, triggers version creation
16. **Compilation deduplication**: Backend deduplicates compiled plans

---

#### Additional Design Decisions for `/pdf-templates`

1. **Template deletion**: Only `draft` status templates can be deleted (set during creation). `active`/`inactive` templates are permanent.
2. **Inactive status purpose**: Indicates template should not be considered during ETO template matching (archive without deletion).
3. **PDF object extraction**: Automatic via PDF processing service upon PDF record creation (agnostic to source - email or manual upload).
4. **Pipeline editing**: Only via template wizard (no standalone pipeline editor). Users view full version details (signature, extraction, pipeline) then edit to create new version.
5. **Version viewing**: Users cycle through versions to view how each is defined (no diff comparison).

---

### Domain 3: `/pdf-templates` - ✓ COMPLETE

---

---

### Domain 4: `/modules` - Module Catalog Viewing

#### User Workflows

**Read-Only Module Discovery:**
- Modules displayed during pipeline building (Step 3 of template wizard)
- Users browse catalog to find modules for transformation graph
- Users drag modules onto pipeline canvas
- Users configure module parameters based on `config_schema`

**Purpose:**
- Frontend needs complete module catalog for offline pipeline building
- Users maintain access to catalog even if connectivity lost
- Developers control module creation (backend-managed)

---

#### Data Requirements

**Module List (All Modules):**

All fields from `module_catalog` table **except**:
- ❌ `handler_name` (backend execution only)
- ❌ `created_at` (audit only)
- ❌ `updated_at` (audit only)

**Included fields:**
- `id` (module identifier)
- `version` (module version)
- `name` (display name)
- `description` (user-facing description)
- `color` (UI display color)
- `category` (e.g., "Text Processing", "Data Validation", "Actions")
- `module_kind` (e.g., "transform", "action", "logic", "entry_point")
- `meta` (JSON - I/O node definitions, future extensibility)
- `config_schema` (JSON Schema for configuration UI)
- `is_active` (filter flag)

**Meta Field Structure (JSON):**
```typescript
{
  "inputs": [
    {
      "id": string,
      "name": string,
      "type": string[], // allowed types
      "required": boolean,
      "description": string
    }
  ],
  "outputs": [
    {
      "id": string,
      "name": string,
      "type": string[], // output types
      "description": string
    }
  ]
  // Future: additional metadata
}
```

**Config Schema (JSON Schema):**
Standard JSON Schema for dynamic form generation in UI.

---

#### Business Rules & Constraints

**Access Control:**
- Read-only access for frontend users
- Developers manage module creation/updates via backend

**Module Visibility:**
- Only `is_active = true` modules shown
- Inactive modules completely hidden from users

**Module Organization:**
- **Primary grouping**: `module_kind` (transform, action, logic, entry_point)
- **Secondary grouping**: `category` within each kind
- **Sorting**: Alphabetical by name within category

**Filtering Options:**
- By `module_kind` (transform/action/logic/entry_point)
- By `category` (Text Processing, Data Validation, etc.)
- By `is_active` (always true - hidden if false)
- Search by `name` or `description` (text search)

**Data Loading:**
- Fetch all modules in single request (no pagination)
- Frontend caches for offline pipeline building
- Reduces dependency on constant connectivity

---

#### Frontend Workflows

**Pipeline Building Context:**

**Module Selection Pane:**
- Collapsible sidebar in pipeline builder (template wizard Step 3)
- **Organization hierarchy:**
  ```
  Transform Modules
    ├─ Text Processing
    │   ├─ Basic Text Cleaner
    │   └─ Advanced Text Cleaner
    └─ Data Validation
        └─ Type Converter

  Action Modules
    ├─ Database
    │   └─ Create Order
    └─ Communication
        └─ Send Email

  Logic Modules
    └─ Conditionals
        └─ If/Else Branch

  Entry Point Modules
    └─ Data Sources
        └─ Field Mapper
  ```

- **Search bar**: Filter by name/description
- **Active filters**: Show selected kind/category
- **Module cards**: Display name, description, color

**Module Usage:**
- Drag module from pane to canvas
- Drop creates module instance in pipeline graph
- Opens configuration panel (based on `config_schema`)
- User connects inputs/outputs to other modules
- Node visuals driven by `meta.inputs/outputs`

---

#### Design Decisions for `/modules`

1. **Organization**: Primary by `module_kind`, secondary by `category`
2. **Filtering**: kind, category, text search, is_active (hidden if false)
3. **Sorting**: Alphabetical within category
4. **Data exposure**: All fields except `handler_name`, `created_at`, `updated_at`
5. **Meta field**: I/O node definitions (extensible for future metadata)
6. **Config schema**: JSON Schema for dynamic configuration UI
7. **Handler name**: Backend execution reference (not exposed to frontend)
8. **Loading strategy**: Single request for all modules (offline capability)
9. **Inactive modules**: Hidden from users
10. **Dependencies**: None currently (future: custom modules composed of other modules)

---

### Domain 4: `/modules` - ✓ COMPLETE

---

---

### Domain 5: `/pipelines` - Pipeline Viewing & Building

#### User Workflows

**Primary Access: Via Templates**
- Users view/edit pipelines during template creation/editing (Step 3 of wizard)
- Visual graph builder shows pipeline structure
- Entry points correspond to extraction fields

**Temporary Standalone Access (Development/Testing)**
- Standalone pipeline page for isolated testing (most complex feature)
- Create and test pipelines without template context
- **Note:** Will be removed in production (end product only accesses via templates)

**Pipeline Viewing Contexts:**
- **Template Wizard**: Build/edit transformation pipeline
- **Template Details**: View historical pipeline for specific template version
- **ETO Run Details**: View execution steps showing data transformation

---

#### Data Requirements

**Pipeline Definition (For Graph Visualization):**

From `pipeline_definitions` table:
- `id`
- `pipeline_state` (JSON - see structure below)
- `visual_state` (JSON - see structure below)
- `compiled_plan_id` (reference only, not exposed to users)

**Pipeline State Structure (JSON):**
```typescript
{
  "entry_points": [
    {
      "id": string,
      "label": string,
      "field_reference": string // matches extraction field label
    }
  ],
  "modules": [
    {
      "instance_id": string,
      "module_id": string, // reference to module_catalog
      "config": object, // module-specific configuration
      "inputs": [
        {
          "node_id": string,
          "name": string,
          "type": string[]
        }
      ],
      "outputs": [
        {
          "node_id": string,
          "name": string,
          "type": string[]
        }
      ]
    }
  ],
  "connections": [
    {
      "from_node_id": string, // entry_point or module output node
      "to_node_id": string     // module input node
    }
  ]
}
```

**Visual State Structure (JSON):**
```typescript
{
  "positions": {
    "entry_point_id" | "module_instance_id": {
      "x": number,
      "y": number
    }
  }
  // Note: zoom/pan handled by frontend auto-centering
}
```

**Pipeline Execution Steps (For ETO Run Details):**

From `eto_run_pipeline_execution_steps` table (via ETO run detail view):
- `module_instance_id` (which module executed)
- `step_number` (execution order)
- `inputs` (JSON - data fed to module)
- `outputs` (JSON - data produced by module)
- `error` (JSON - error details if step failed)

**Not Exposed to Users:**
- ❌ `pipeline_compiled_plans` table (backend execution only)
- ❌ `pipeline_definition_steps` table (backend execution optimization)
- ❌ Compiled plan checksum
- ❌ Which pipelines share compiled plans

---

#### Business Rules & Constraints

**Pipeline Lifecycle:**
- Created during template wizard (Step 3)
- Stored with template version
- Never edited standalone (only via template editing)
- Immutable once template version finalized

**Pipeline State Storage:**
- `pipeline_state`: Logical structure (entry points, modules, connections)
- `visual_state`: UI layout (node positions)
- Both required to reconstruct graph builder

**Graph Reconstruction:**
- Frontend uses `pipeline_state` + `visual_state` to render visual graph
- Auto-centering applies zoom/pan on load
- Entry points mapped to extraction fields from template version

**Execution Steps vs Definition Steps:**
- **Execution steps** (`eto_run_pipeline_execution_steps`): User-facing data transformation log
- **Definition steps** (`pipeline_definition_steps`): Backend execution optimization (not exposed)

**Compiled Plans:**
- Backend deduplication mechanism
- Transparent to users
- Multiple pipelines may share same compiled plan
- Checksum and plan details hidden from frontend

---

#### Frontend Workflows

**Pipeline Building (Template Wizard Step 3):**

**Initial State:**
- Blank canvas with entry points pre-populated
- Entry points correspond to extraction fields defined in Step 2
- Module catalog sidebar open

**Build Process:**
- Drag modules from catalog to canvas
- Configure module parameters
- Connect entry points → modules → other modules
- Visual feedback for valid/invalid connections
- Save stores `pipeline_state` and `visual_state`

**Pipeline Editing (Template Version Creation):**
- Load existing `pipeline_state` and `visual_state`
- Reconstruct graph with entry points and modules
- Apply `visual_state` positions
- Auto-center and zoom to fit
- Allow modifications (add/remove/reconnect modules)
- Save creates new template version with updated pipeline

---

**Pipeline Viewing (Template Details):**

**Context:** Viewing historical template version

**Display:**
- Read-only visual graph
- Entry points labeled with extraction field names
- Modules showing configuration
- Connections showing data flow
- No editing allowed (historical view)

---

**Pipeline Execution Viewing (ETO Run Details):**

**Context:** Viewing successful or failed ETO run

**Display:**
- Step-by-step execution log
- Each step shows:
  - Module name (from `module_instance_id`)
  - Step number (execution order)
  - Input data (JSON formatted)
  - Output data (JSON formatted)
  - Error details (if step failed)
- Shows exact data transformation flow
- Helps debug extraction/transformation issues

**Purpose:**
- Understand how extracted data was transformed
- Trace data flow through pipeline
- Debug transformation errors

---

**Standalone Pipeline Page (Temporary - Development Only):**

**Purpose:**
- Isolated pipeline testing during development
- Most complex feature needs independent testing
- **Will be removed in production**

**Functionality:**
- Create pipeline without template context
- Test pipeline logic
- Validate module connections
- Not connected to templates or ETO runs

---

#### Design Decisions for `/pipelines`

1. **Primary access**: Via template wizard only (production)
2. **Standalone page**: Temporary for testing, will be removed
3. **Compiled plans**: Hidden from users (backend optimization)
4. **User views**: Visual graph (building/viewing) + execution steps (ETO run logs)
5. **Pipeline state**: Logical structure (entry points, modules, connections)
6. **Visual state**: Node positions only (zoom/pan auto-calculated)
7. **Graph reconstruction**: Both states required for visual builder
8. **Execution vs definition steps**: Only execution steps exposed to users
9. **Step details**: Simple input/output data transformation log
10. **Checksum exposure**: Not visible to users
11. **Shared plans**: Not visible to users (backend deduplication)

---

### Domain 5: `/pipelines` - ✓ COMPLETE

---

---

### Domain 6: `/health` - System Health Monitoring

#### User Workflows

**Pre-Application Health Check:**
- Frontend checks health before loading application
- Blocks application load if server is down
- Shows service-specific errors if individual services are down

**Service-Specific Handling:**
- Overall server down: Show browser-native error message
- Individual service down: Show service-specific error message
- Allow application to function with degraded services (e.g., email ingestion works while ETO service is down)

**Service Recovery:**
- Services can be restarted independently
- ETO runs queued while service is down will process after restart
- Email ingestion continues if ETO service is down

---

#### Data Requirements

**Health Response:**

```typescript
{
  "status": "healthy" | "degraded" | "unhealthy",
  "server": {
    "status": "up" | "down"
  },
  "services": {
    "email_ingestion": {
      "status": "healthy" | "unhealthy",
      "message": string? // optional error message
    },
    "eto_processing": {
      "status": "healthy" | "unhealthy",
      "message": string?
    },
    "pdf_processing": {
      "status": "healthy" | "unhealthy",
      "message": string?
    },
    "database": {
      "status": "healthy" | "unhealthy",
      "message": string?
    }
    // ... other services from service container
  }
}
```

**Overall Status Logic:**
- `healthy`: All services healthy
- `degraded`: Some services unhealthy, but server functional
- `unhealthy`: Server down or critical services down

**Services Monitored:**
- All services registered in service container
- Email ingestion service
- ETO processing service
- PDF processing service
- Database connection
- Any other services in service container

---

#### Business Rules & Constraints

**Health Check Logic:**
- Check all services in service container
- Service is "unhealthy" if any failure detected
- Overall status:
  - `unhealthy` if server cannot respond
  - `degraded` if any service unhealthy
  - `healthy` if all services healthy

**Service Independence:**
- Individual services can fail without bringing down entire server
- Application can function with degraded services
- Example: Email ingestion continues if ETO processing is down

**Error Reporting:**
- Overall server down: Browser-native error (connection refused, etc.)
- Individual service down: Service-specific error message in response
- Detailed diagnostics: Available in server logs (not exposed via API)

**No Detailed Diagnostics:**
- Health endpoint returns simple status only
- No error counts, uptime, or version information
- Detailed diagnostics via server logs

---

#### Frontend Workflows

**Application Startup:**

**Initial Health Check:**
- Frontend calls `/health` before loading application
- Occurs before authentication
- Occurs before any other API calls

**Server Down (Overall Unhealthy):**
- Browser shows native connection error
- Application does not load
- No custom error UI needed (browser handles)

**Service Degraded:**
- Application loads normally
- Show banner/alert for degraded service
- Example: "ETO Processing service is currently unavailable. Queued runs will process when service is restored."
- User can still access other features

**All Services Healthy:**
- Application loads normally
- No error messages
- Proceed to authentication

---

**Polling Strategy:**

**Open Question:** Polling frequency
- Health checks are generally low-cost operations
- Backend: Simple status check on service container
- Frontend: Lightweight HTTP GET request
- **Needs decision:** How often to poll? Options:
  - On startup only (no polling)
  - Every 30 seconds (detect service failures quickly)
  - Every 1-2 minutes (balance freshness vs overhead)
  - On user action (lazy loading)

**Recommendation:** Start with polling every 30-60 seconds. Adjust based on:
- Service stability
- Network conditions
- User experience (how quickly should user know service is down?)

---

**Error Handling:**

**Overall Server Down:**
- Browser-native error message
- Retry connection periodically
- No custom UI needed

**Individual Service Down:**
- Display service-specific error banner
- Continue allowing access to working features
- Example error messages:
  - "Email ingestion service unavailable. New emails will not be processed until service is restored."
  - "ETO processing service unavailable. Queued runs will process when service is restored."
  - "PDF processing service unavailable. New PDF uploads temporarily disabled."

**Service Recovery:**
- Poll health endpoint periodically
- Remove error banner when service recovers
- Optionally show success toast: "ETO processing service restored"

---

#### Design Decisions for `/health`

1. **Services monitored**: All services in service container
2. **Status levels**: Overall (healthy/degraded/unhealthy) + per-service status
3. **Health definition**: Any service failure = unhealthy service, server responds = server up
4. **Response data**: Overall status + per-service status with optional error message
5. **No detailed diagnostics**: Simple status only (logs for detailed info)
6. **Frontend usage**: Pre-load check + periodic polling (frequency TBD)
7. **Overall server down**: Browser-native error (no custom UI)
8. **Service degraded**: Service-specific error messages, application continues
9. **Service independence**: Individual services can fail without server failure
10. **Polling frequency**: TBD based on cost analysis (recommend 30-60 seconds)
11. **No monitoring integration**: No Prometheus/Grafana for current iteration
12. **Ops usage**: Same endpoint as frontend (no separate detailed endpoint)

---

#### Open Question for `/health`

**Polling Frequency:** How often should frontend poll health endpoint?
- **Option 1**: On startup only (no polling) - simple, but won't detect failures
- **Option 2**: Every 30 seconds - quick failure detection, minimal overhead
- **Option 3**: Every 1-2 minutes - balance freshness vs cost
- **Option 4**: On user action - lazy, no overhead, delayed detection

**Recommendation:** Start with 30-60 second polling. Health checks are typically very low-cost:
- Backend: Simple boolean checks on service container
- Frontend: ~1KB HTTP GET request
- Modern systems handle this easily

Monitor actual overhead and adjust if needed.

---

### Domain 6: `/health` - ✓ COMPLETE

---

---

## Phase 2: COMPLETE! ✓

All 6 domains fully analyzed:
- ✅ `/email-configs` - Email ingestion configuration management
- ✅ `/eto-runs` - ETO processing control with status-based views
- ✅ `/pdf-templates` - Template creation with versioning and testing
- ✅ `/modules` - Read-only module catalog for pipeline building
- ✅ `/pipelines` - Pipeline viewing and building (via templates)
- ✅ `/health` - System health monitoring

---

## Next: Phase 3 - Endpoint Definitions

Now that we understand all domain requirements, we can define:
- Specific HTTP endpoints (paths, methods)
- Path parameters
- Query parameters
- Request body structures
- Response structures
- Error responses
- Status codes

Ready to proceed to Phase 3?

---
