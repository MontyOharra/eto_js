# ETO Processing Flow

## Overview

The ETO (Email-to-Order) system processes PDFs from emails automatically through a multi-stage pipeline. PDFs are received via the email ingestion service, matched to templates, have data extracted, and then transformed through pipelines.

---

## Architecture Components

- **Email Ingestion Service**: Monitors email accounts and creates PDF file records
- **ETO Service**: Orchestrates the processing workflow with a background worker
- **PDF Templates Service**: Provides template matching algorithms
- **Pipeline Execution Service**: Executes data transformation pipelines

---

## Processing Stages

### Stage 1: Template Matching
Match the PDF to the best available template using signature objects.

### Stage 2: Data Extraction
Extract field values from the PDF using the matched template's extraction fields.

### Stage 3: Data Transformation
Execute the pipeline associated with the template to transform/validate/action the extracted data.

---

## Complete Process Flow

### Step 1: Email Receipt & PDF Creation
**Trigger**: Email received by email ingestion process

- Email ingestion service detects new email with PDF attachment
- PDF file record created in database (`pdf_files` table)
- Email ingestion service calls ETO service to initiate processing

---

### Step 2: ETO Run Creation
**Trigger**: Email ingestion service calls ETO service

**Input**: PDF file ID

**Action**:
- New record created in `eto_runs` table
- Initial state:
  - `status = "not_started"`
  - `processing_step = null`
  - `pdf_file_id = {provided_id}`

**Database State**:
```
eto_runs:
  id: 123
  pdf_file_id: 456
  status: "not_started"
  processing_step: null
```

---

### Step 3: Worker Detection
**Trigger**: Background worker polling loop

**Action**:
- ETO worker constantly checks `eto_runs` table for records with `status = "not_started"`
- When found, worker picks up the run and begins processing
- Worker updates:
  - `status = "processing"`
  - `processing_step = "template_matching"`
  - `started_at = {current_timestamp}`

**Database State**:
```
eto_runs:
  id: 123
  status: "processing"
  processing_step: "template_matching"
  started_at: 2025-10-29T12:00:00Z
```

---

### Step 4: Template Matching Stage
**Trigger**: Worker begins processing

**Action**:
- Create record in `eto_run_template_matchings` table:
  - `eto_run_id = 123`
  - `status = "processing"`
  - `started_at = {current_timestamp}`

- Call PDF Templates Service with PDF file data
- Template matching algorithm runs (signature object comparison)
- Algorithm returns best matching template version ID

**Success Path**:
- Update `eto_run_template_matchings`:
  - `status = "success"`
  - `matched_template_version_id = {version_id}`
  - `completed_at = {current_timestamp}`

- Fetch template definition from matched version:
  - `extraction_fields` - Array of bounding boxes and field names
  - `pipeline_definition_id` - ID of pipeline to execute

**Database State**:
```
eto_run_template_matchings:
  id: 789
  eto_run_id: 123
  status: "success"
  matched_template_version_id: 42
  started_at: 2025-10-29T12:00:01Z
  completed_at: 2025-10-29T12:00:05Z
```

**Failure Path**:
- If no template matches or error occurs:
  - Update `eto_run_template_matchings`: `status = "failure"`
  - Update `eto_runs`:
    - `status = "needs_template"` (if no match) or `"failure"` (if error)
    - `error_type`, `error_message`, `error_details` populated
  - **Process stops**

---

### Step 5: Data Extraction Stage
**Trigger**: Template matching success

**Action**:
- Update `eto_runs`:
  - `processing_step = "data_extraction"`

- Create record in `eto_run_extractions` table:
  - `eto_run_id = 123`
  - `status = "processing"`
  - `started_at = {current_timestamp}`

- Extract data from PDF using `extraction_fields` from template:
  - For each field: read text from bounding box coordinates
  - Build dictionary: `{field_name: extracted_text}`

**Success Path**:
- Update `eto_run_extractions`:
  - `status = "success"`
  - `extracted_data = {json_string}` (serialized dictionary)
  - `completed_at = {current_timestamp}`

**Database State**:
```
eto_runs:
  processing_step: "data_extraction"

eto_run_extractions:
  id: 101
  eto_run_id: 123
  status: "success"
  extracted_data: '{"invoice_number": "INV-001", "total": "1234.56"}'
  started_at: 2025-10-29T12:00:06Z
  completed_at: 2025-10-29T12:00:08Z
```

**Failure Path**:
- If extraction fails:
  - Update `eto_run_extractions`: `status = "failure"`
  - Update `eto_runs`: `status = "failure"`, error fields populated
  - **Process stops**

---

### Step 6: Data Transformation Stage
**Trigger**: Data extraction success

**Action**:
- Update `eto_runs`:
  - `processing_step = "data_transformation"`

- Create record in `eto_run_pipeline_executions` table:
  - `eto_run_id = 123`
  - `status = "processing"`
  - `started_at = {current_timestamp}`

- Execute pipeline using:
  - **Pipeline Definition ID**: From matched template version
  - **Entry Point Values**: Extracted data from previous stage
  - **Execution Mode**: Production (actions execute for real)

- Pipeline execution creates audit trail:
  - Records created in `eto_run_pipeline_execution_steps` for each step
  - Each step records:
    - `module_instance_id`
    - `step_number`
    - `inputs` (JSON) - What data went into this module
    - `outputs` (JSON) - What data came out of this module
    - `error` (JSON) - If step failed, error details

**Success Path**:
- Update `eto_run_pipeline_executions`:
  - `status = "success"`
  - `executed_actions = {json_array}` - Summary of action modules executed
  - `completed_at = {current_timestamp}`

- Update `eto_runs`:
  - `status = "success"`
  - `completed_at = {current_timestamp}`

**Database State**:
```
eto_runs:
  status: "success"
  processing_step: "data_transformation"
  completed_at: 2025-10-29T12:00:15Z

eto_run_pipeline_executions:
  id: 202
  eto_run_id: 123
  status: "success"
  executed_actions: '[{"action": "send_email", "inputs": {...}}]'
  started_at: 2025-10-29T12:00:09Z
  completed_at: 2025-10-29T12:00:15Z

eto_run_pipeline_execution_steps:
  [Multiple records for each pipeline step]
```

**Failure Path**:
- If pipeline execution fails:
  - Update `eto_run_pipeline_executions`: `status = "failure"`
  - Update `eto_runs`: `status = "failure"`, error fields populated
  - **Process stops**

---

## Error Handling

### Error Recording
When any stage fails, the error is recorded in the `eto_runs` table:

- `status = "failure"`
- `error_type` - Error category (e.g., "TemplateMatchingError", "ExtractionError")
- `error_message` - Human-readable error message
- `error_details` - JSON string with full error context/stack trace

### Recovery
- Failed runs remain in `failure` status
- Can be manually reprocessed via API (resets to `not_started`)
- Worker will not automatically retry failed runs

---

## Status Transitions

### ETO Run Statuses
```
not_started → processing → success
                ↓
              failure / needs_template / skipped
```

### Processing Steps (while status = "processing")
```
null → template_matching → data_extraction → data_transformation
```

### Stage Statuses (for stage tables)
```
processing → success
    ↓
  failure
```

---

## Database Tables Involved

### Primary Table
- `eto_runs` - Main orchestration record

### Stage Tables
- `eto_run_template_matchings` - Stage 1 results
- `eto_run_extractions` - Stage 2 results
- `eto_run_pipeline_executions` - Stage 3 results
- `eto_run_pipeline_execution_steps` - Detailed audit trail for pipeline

### Referenced Tables
- `pdf_files` - Input PDF
- `pdf_template_versions` - Matched template
- `pipeline_definitions` - Pipeline to execute

---

## Worker Implementation Notes

### Worker Responsibilities
1. Poll `eto_runs` for `status = "not_started"`
2. Pick up runs and update status to `"processing"`
3. Execute stages sequentially
4. Handle errors and update status accordingly
5. Continue polling for new runs

### Worker Characteristics
- **Constant Background Process**: Always running
- **Polling Interval**: TBD (e.g., every 5 seconds)
- **Concurrency**: TBD (single-threaded or multiple workers)
- **Error Handling**: Graceful failure, no crashes
- **Logging**: Comprehensive logging at each stage

---

## API Integration Points

### Email Ingestion → ETO Service
**Endpoint**: `POST /eto-runs` (or internal service method)
**Payload**: `{ pdf_file_id: number }`
**Response**: `{ id: number, status: "not_started" }`

### ETO Service → PDF Templates Service
**Method**: Template matching algorithm call
**Input**: PDF file data, signature objects
**Output**: Best matching template version ID, extraction fields, pipeline definition ID

### ETO Service → Pipeline Execution Service
**Method**: Pipeline execution call
**Input**: Pipeline definition ID, entry point values (extracted data)
**Output**: Execution results, action summaries, step audit trail

---

## Future Considerations

- **Manual Triggers**: API endpoint to manually create ETO runs for non-email PDFs
- **Retry Logic**: Automatic retry for transient failures
- **Parallel Processing**: Multiple workers for high throughput
- **Priority Queues**: Prioritize certain runs over others
- **Monitoring**: Dashboards for run status, success rates, processing times
