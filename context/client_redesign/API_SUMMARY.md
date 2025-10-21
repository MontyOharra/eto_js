# Frontend API Summary

This document summarizes all API endpoints and type definitions referenced in the frontend codebase. This serves as a comparison point for backend implementation to ensure unified design.

**Last Updated**: 2025-10-20
**Total Endpoints**: 37 across 6 feature domains

---

## Table of Contents

1. [Templates API](#1-templates-api) (10 endpoints)
2. [ETO Runs API](#2-eto-runs-api) (7 endpoints)
3. [Email Configurations API](#3-email-configurations-api) (10 endpoints)
4. [Modules API](#4-modules-api) (1 endpoint)
5. [Pipelines API](#5-pipelines-api) (5 endpoints)
6. [PDF Files API](#6-pdf-files-api) (4 endpoints)

---

## 1. Templates API

**Base Path**: `/pdf-templates`
**Feature Location**: `client-new/src/renderer/features/templates/`

### 1.1 GET /pdf-templates

List templates with pagination and filtering.

**Query Parameters**:
```typescript
interface GetTemplatesQueryParams {
  status?: 'active' | 'inactive';
  sort_by?: 'name' | 'status' | 'usage_count';
  sort_order?: 'asc' | 'desc';
  limit?: number;    // default: 50, max: 200
  offset?: number;   // default: 0
}
```

**Response**:
```typescript
interface GetTemplatesResponse {
  items: TemplateListItem[];
  total: number;
  limit: number;
  offset: number;
}

interface TemplateListItem {
  id: number;
  name: string;
  description: string | null;
  status: 'active' | 'inactive';
  source_pdf_id: number;
  current_version: {
    version_id: number;
    version_num: number;
    usage_count: number;
  };
  total_versions: number;
}
```

### 1.2 GET /pdf-templates/{id}

Get full template details including current version.

**Response**:
```typescript
interface TemplateDetail {
  id: number;
  name: string;
  description: string | null;
  source_pdf_id: number;
  status: 'active' | 'inactive';
  current_version_id: number;
  current_version: {
    version_id: number;
    version_num: number;
    usage_count: number;
    last_used_at: string | null;  // ISO 8601
    signature_objects: SignatureObject[];
    extraction_fields: ExtractionField[];
    pipeline_definition_id: number;
  };
  total_versions: number;
}
```

**Supporting Types**:
```typescript
interface SignatureObject {
  object_type: 'text_word' | 'text_line' | 'graphic_rect' | 'graphic_line'
              | 'graphic_curve' | 'image' | 'table';
  page: number;
  bbox: [number, number, number, number];  // [x0, y0, x1, y1]
  // Additional properties vary by object_type
  text?: string;
  fontname?: string;
  fontsize?: number;
  linewidth?: number;
  points?: Array<[number, number]>;
  format?: string;
  colorspace?: string;
  bits?: number;
  rows?: number;
  cols?: number;
}

interface ExtractionField {
  field_id: string;
  label: string;
  description: string | null;
  page: number;
  bbox: [number, number, number, number];
  required: boolean;
  validation_regex: string | null;
}
```

### 1.3 POST /pdf-templates

Create new template (always starts as inactive).

**Request**: `multipart/form-data`
```typescript
interface PostTemplateCreateRequest {
  name: string;                    // required, 1-255 chars
  description?: string;             // optional, max 1000 chars
  source_pdf_id?: number | null;   // optional - for existing PDFs
  signature_objects: SignatureObject[];  // required, min: 1
  extraction_fields: ExtractionField[];  // required, min: 1
  pipeline_state: PipelineState;
  visual_state: VisualState;
  // pdf_file: File (if source_pdf_id is null)
}

interface PipelineState {
  entry_points: Array<{
    id: string;
    label: string;
    field_reference: string;  // References extraction field label
  }>;
  modules: Array<{
    instance_id: string;
    module_id: string;
    config: Record<string, any>;
    inputs: Array<{
      node_id: string;
      name: string;
      type: string[];
    }>;
    outputs: Array<{
      node_id: string;
      name: string;
      type: string[];
    }>;
  }>;
  connections: Array<{
    from_node_id: string;
    to_node_id: string;
  }>;
}

interface VisualState {
  positions: Record<string, { x: number; y: number }>;
}
```

**Response**:
```typescript
interface PostTemplateCreateResponse {
  id: number;
  name: string;
  status: 'inactive';  // Always inactive initially
  current_version_id: number;
  current_version_num: 1;
  pipeline_definition_id: number;
}
```

### 1.4 PUT /pdf-templates/{id}

Update template (creates new version).

**Request**:
```typescript
interface PutTemplateUpdateRequest {
  name?: string;        // optional, 1-255 chars
  description?: string;  // optional, max 1000 chars
  signature_objects: SignatureObject[];  // required
  extraction_fields: ExtractionField[];  // required
  pipeline_state: PipelineState;
  visual_state: VisualState;
}
```

**Response**:
```typescript
interface PutTemplateUpdateResponse {
  id: number;
  name: string;
  status: 'active' | 'inactive';  // Status unchanged
  current_version_id: number;     // Updated to new version
  current_version_num: number;    // Incremented
  pipeline_definition_id: number; // New pipeline ID
}
```

### 1.5 DELETE /pdf-templates/{id}

Delete template.

**Response**: `204 No Content`

### 1.6 POST /pdf-templates/{id}/activate

Activate template for use in ETO processing.

**Request**: No body

**Response**:
```typescript
interface PostTemplateActivateResponse {
  id: number;
  status: 'active';
  current_version_id: number;
}
```

### 1.7 POST /pdf-templates/{id}/deactivate

Deactivate template (stops it from being used in ETO processing).

**Request**: No body

**Response**:
```typescript
interface PostTemplateDeactivateResponse {
  id: number;
  status: 'inactive';
  current_version_id: number;
}
```

### 1.8 GET /pdf-templates/{id}/versions

List all versions of a template.

**Response**:
```typescript
type GetTemplateVersionsResponse = TemplateVersionListItem[];

interface TemplateVersionListItem {
  version_id: number;
  version_num: number;
  usage_count: number;
  last_used_at: string | null;  // ISO 8601
  is_current: boolean;
}
```

### 1.9 GET /pdf-templates/{id}/versions/{version_id}

Get detailed information for a specific template version.

**Response**:
```typescript
interface TemplateVersionDetail {
  version_id: number;
  template_id: number;
  version_num: number;
  usage_count: number;
  last_used_at: string | null;
  is_current: boolean;
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_definition_id: number;
}
```

### 1.10 POST /pdf-templates/simulate

Simulate full ETO process without saving results.

**Request**: `multipart/form-data` (discriminated union)

**Variant 1 - Stored PDF**:
```typescript
interface PostTemplateSimulateStoredRequest {
  pdf_source: 'stored';
  pdf_file_id: number;
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
}
```

**Variant 2 - Uploaded PDF**:
```typescript
interface PostTemplateSimulateUploadRequest {
  pdf_source: 'upload';
  // pdf_file: File (multipart)
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
}
```

**Response**:
```typescript
interface PostTemplateSimulateResponse {
  template_matching: {
    status: 'success';
    message: string;  // "Simulation mode - template matching skipped"
  };
  data_extraction: {
    status: 'success' | 'failure';
    extracted_data: Record<string, string> | null;
    error_message: string | null;
    validation_results: Array<{
      field_label: string;
      required: boolean;
      has_value: boolean;
      regex_valid: boolean | null;
      error: string | null;
    }>;
  };
  pipeline_execution: {
    status: 'success' | 'failure';
    error_message: string | null;
    steps: Array<{
      step_number: number;
      module_instance_id: string;
      module_name: string;
      inputs: Record<string, { value: any; type: string }>;
      outputs: Record<string, { value: any; type: string }>;
      error: object | null;
    }>;
    simulated_actions: Array<{
      action_module_name: string;
      inputs: Record<string, any>;
      simulation_note: string;  // "Action not executed - simulation mode"
    }>;
  };
}
```

---

## 2. ETO Runs API

**Base Path**: `/eto-runs`
**Feature Location**: `client-new/src/renderer/features/eto/`

### 2.1 GET /eto-runs

List ETO runs with pagination and filtering.

**Query Parameters**:
```typescript
interface GetEtoRunsQueryParams {
  status?: 'not_started' | 'processing' | 'success' | 'failure'
         | 'needs_template' | 'skipped';
  sort_by?: 'created_at' | 'started_at' | 'completed_at' | 'status';
  sort_order?: 'asc' | 'desc';
  limit?: number;   // default: 50, max: 200
  offset?: number;  // default: 0
}
```

**Response**:
```typescript
interface GetEtoRunsResponse {
  items: EtoRunListItem[];
  total: number;
  limit: number;
  offset: number;
}

interface EtoRunListItem {
  id: number;
  status: EtoRunStatus;
  processing_step: 'template_matching' | 'data_extraction' | 'data_transformation' | null;
  started_at: string | null;
  completed_at: string | null;
  error_type: string | null;
  error_message: string | null;
  pdf: {
    id: number;
    original_filename: string;
    file_size: number | null;
    page_count: number | null;
  };
  source: {
    type: 'manual' | 'email';
    sender_email?: string;
    received_date?: string;
    subject?: string | null;
    folder_name?: string;
  };
  matched_template: {
    template_id: number;
    template_name: string;
    version_id: number;
    version_num: number;
  } | null;
}
```

### 2.2 GET /eto-runs/{id}

Get full run details including all processing stages.

**Response**:
```typescript
interface EtoRunDetail {
  // All fields from EtoRunListItem plus:
  template_matching: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    matched_template: {
      template_id: number;
      template_name: string;
      version_id: number;
      version_num: number;
    } | null;
  };
  data_extraction: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    extracted_data: Record<string, any> | null;
    extracted_fields_with_boxes: Array<{
      field_id: string;
      label: string;
      value: string;
      page: number;
      bbox: [number, number, number, number];
    }>;
  };
  pipeline_execution: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    pipeline_definition_id: number;
    executed_actions: Array<{
      action_module_name: string;
      inputs: Record<string, any>;
    }> | null;
    steps: Array<{
      id: number;
      step_number: number;
      module_instance_id: string;
      inputs: Record<string, { name: string; value: any; type: string }> | null;
      outputs: Record<string, { name: string; value: any; type: string }> | null;
      error: {
        type: string;
        message: string;
        details?: any;
      } | null;
    }>;
  };
}
```

### 2.3 POST /eto-runs/upload

Create ETO run via manual PDF upload.

**Request**: `multipart/form-data` with `pdf_file: File`

**Response**:
```typescript
interface PostEtoRunUploadResponse {
  id: number;
  pdf_file_id: number;
  status: 'not_started';
  processing_step: null;
  started_at: null;
  completed_at: null;
}
```

### 2.4 POST /eto-runs/reprocess

Reprocess multiple runs (bulk operation).

**Request**:
```typescript
interface PostEtoRunsReprocessRequest {
  run_ids: number[];
}
```

**Response**: `204 No Content`

### 2.5 POST /eto-runs/skip

Skip multiple runs (bulk operation).

**Request**:
```typescript
interface PostEtoRunsSkipRequest {
  run_ids: number[];
}
```

**Response**: `204 No Content`

### 2.6 DELETE /eto-runs

Delete multiple runs (bulk operation).

**Request**:
```typescript
interface DeleteEtoRunsRequest {
  run_ids: number[];
}
```

**Response**: `204 No Content`

### 2.7 POST /eto-runs/{id}/reprocess

Reprocess single run (alternative to bulk endpoint).

**Request**: No body

**Response**: `204 No Content`

---

## 3. Email Configurations API

**Base Path**: `/email-configs`
**Feature Location**: `client-new/src/renderer/features/email-configs/`

### 3.1 GET /email-configs

List all email configurations.

**Query Parameters**:
```typescript
interface EmailConfigsListQueryParams {
  order_by?: 'name' | 'is_active' | 'last_check_time';
  desc?: boolean;
}
```

**Response**:
```typescript
type GetEmailConfigsResponse = EmailConfigSummaryDTO[];

interface EmailConfigSummaryDTO {
  id: number;
  name: string;
  is_active: boolean;
  last_check_time: string | null;  // ISO 8601
}
```

### 3.2 GET /email-configs/{id}

Get full configuration details.

**Response**:
```typescript
interface EmailConfigDetailDTO {
  id: number;
  name: string;
  description: string | null;
  email_address: string;
  folder_name: string;
  filter_rules: Array<{
    field: 'sender_email' | 'subject' | 'has_attachments' | 'attachment_types';
    operation: 'contains' | 'equals' | 'starts_with' | 'ends_with';
    value: string;
    case_sensitive: boolean;
  }>;
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
  is_active: boolean;
  activated_at: string | null;  // ISO 8601
  is_running: boolean;
  last_check_time: string | null;
  last_error_message: string | null;
  last_error_at: string | null;
}
```

### 3.3 POST /email-configs

Create new email configuration.

**Request**:
```typescript
interface CreateEmailConfigRequestDTO {
  name: string;                      // required, 1-255 chars
  description?: string;               // optional, max 1000 chars
  email_address: string;              // required, valid email
  folder_name: string;                // required, min 1 char
  filter_rules?: FilterRuleDTO[];     // optional, default: []
  poll_interval_seconds?: number;     // optional, min: 5, default: 5
  max_backlog_hours?: number;         // optional, min: 1, default: 24
  error_retry_attempts?: number;      // optional, min: 1, max: 10, default: 3
}
```

**Response**:
```typescript
interface CreateEmailConfigResponseDTO {
  id: number;
  name: string;
  is_active: boolean;  // false initially
}
```

### 3.4 PUT /email-configs/{id}

Update email configuration.

**Request**:
```typescript
interface UpdateEmailConfigRequestDTO {
  description?: string | null;
  filter_rules?: FilterRuleDTO[];
  poll_interval_seconds?: number;   // min: 5
  max_backlog_hours?: number;       // min: 1
  error_retry_attempts?: number;    // min: 1, max: 10
}
```

**Response**:
```typescript
interface UpdateEmailConfigResponseDTO {
  id: number;
  name: string;
  // Updated fields returned
}
```

### 3.5 DELETE /email-configs/{id}

Delete email configuration.

**Response**: `204 No Content`

### 3.6 POST /email-configs/{id}/activate

Activate email configuration.

**Request**: No body

**Response**:
```typescript
interface ActivateEmailConfigResponseDTO {
  id: number;
  is_active: true;
  activated_at: string;  // ISO 8601
}
```

### 3.7 POST /email-configs/{id}/deactivate

Deactivate email configuration.

**Request**: No body

**Response**:
```typescript
interface DeactivateEmailConfigResponseDTO {
  id: number;
  is_active: false;
}
```

### 3.8 GET /email-configs/discovery/accounts

Discover available email accounts on the system.

**Response**:
```typescript
type GetEmailAccountsResponse = EmailAccountDTO[];

interface EmailAccountDTO {
  email_address: string;
  display_name: string | null;
}
```

### 3.9 GET /email-configs/discovery/folders

Discover folders for a specific email account.

**Query Parameters**:
```typescript
interface EmailFoldersQueryParams {
  email_address: string;  // required
}
```

**Response**:
```typescript
type GetEmailFoldersResponse = EmailFolderDTO[];

interface EmailFolderDTO {
  folder_name: string;
  folder_path: string;  // full path
}
```

### 3.10 POST /email-configs/validate

Validate email configuration before creation.

**Request**:
```typescript
interface ValidateEmailConfigRequestDTO {
  email_address: string;
  folder_name: string;
}
```

**Response**:
```typescript
interface ValidateEmailConfigResponseDTO {
  email_address: string;
  folder_name: string;
  message: string;  // "Configuration is valid"
}
```

---

## 4. Modules API

**Base Path**: `/modules`
**Feature Location**: `client-new/src/renderer/features/modules/`

### 4.1 GET /modules

Get catalog of all available modules.

**Query Parameters**:
```typescript
interface ModulesQueryParams {
  module_kind?: 'transform' | 'action' | 'logic' | 'entry_point';
  category?: string;
  search?: string;
}
```

**Response**:
```typescript
interface ModuleCatalogResponse {
  modules: ModuleTemplate[];
}

interface ModuleTemplate {
  id: string;
  version: string;  // e.g., "1.0.0"
  name: string;
  description: string;
  color: string;    // hex code for UI
  category: string; // e.g., "Text Processing", "Actions"
  module_kind: 'transform' | 'action' | 'logic' | 'entry_point';
  meta: {
    inputs: Array<{
      id: string;
      name: string;
      type: string[];      // Allowed types
      required: boolean;
      description: string;
    }>;
    outputs: Array<{
      id: string;
      name: string;
      type: string[];      // Output types
      description: string;
    }>;
  };
  config_schema: object;  // JSON Schema for configuration UI
}
```

---

## 5. Pipelines API

**Base Path**: `/pipelines`
**Feature Location**: `client-new/src/renderer/features/pipelines/`

**Note**: Pipelines are for dev/testing only. In production, pipelines are embedded in PDF templates.

### 5.1 GET /pipelines

List all pipelines with pagination.

**Query Parameters**:
```typescript
interface PipelinesQueryParams {
  sort_by?: 'id' | 'created_at';
  sort_order?: 'asc' | 'desc';
  limit?: number;   // default: 50, max: 200
  offset?: number;  // default: 0
}
```

**Response**:
```typescript
interface PipelinesListResponseDTO {
  items: Array<{
    id: number;
    compiled_plan_id: number | null;
    created_at: string;  // ISO 8601
    updated_at: string;  // ISO 8601
  }>;
  total: number;
  limit: number;
  offset: number;
}
```

### 5.2 GET /pipelines/{id}

Get full pipeline details.

**Response**:
```typescript
interface PipelineDetailDTO {
  id: number;
  compiled_plan_id: number | null;
  pipeline_state: {
    entry_points: Array<{
      id: string;
      label: string;
      field_reference: string;
    }>;
    modules: Array<{
      instance_id: string;
      module_id: string;
      config: Record<string, any>;
      inputs: Array<{
        node_id: string;
        name: string;
        type: string[];
      }>;
      outputs: Array<{
        node_id: string;
        name: string;
        type: string[];
      }>;
    }>;
    connections: Array<{
      from_node_id: string;
      to_node_id: string;
    }>;
  };
  visual_state: {
    positions: Record<string, { x: number; y: number }>;
  };
}
```

### 5.3 POST /pipelines

Create new pipeline.

**Request**:
```typescript
interface CreatePipelineRequestDTO {
  pipeline_state: PipelineStateDTO;
  visual_state: VisualStateDTO;
}
```

**Response**:
```typescript
interface CreatePipelineResponseDTO {
  id: number;
  compiled_plan_id: number | null;
}
```

### 5.4 PUT /pipelines/{id}

Update existing pipeline.

**Request**:
```typescript
interface UpdatePipelineRequestDTO {
  pipeline_state: PipelineStateDTO;
  visual_state: VisualStateDTO;
}
```

**Response**:
```typescript
interface UpdatePipelineResponseDTO {
  id: number;
  compiled_plan_id: number | null;
}
```

### 5.5 DELETE /pipelines/{id}

Delete pipeline.

**Response**: `204 No Content`

---

## 6. PDF Files API

**Base Path**: `/pdf-files`
**Feature Location**: `client-new/src/renderer/features/pdf-files/`

### 6.1 GET /pdf-files/{id}

Get PDF file metadata.

**Response**:
```typescript
interface PdfFileMetadataDTO {
  id: number;
  email_id: number | null;
  filename: string;
  original_filename: string;
  relative_path: string;
  file_size: number | null;  // bytes
  file_hash: string | null;
  page_count: number | null;
}
```

### 6.2 GET /pdf-files/{id}/download

Download PDF file as binary data.

**Response**: Binary PDF data with headers:
- `Content-Type: application/pdf`
- `Content-Disposition: inline; filename="<original_filename>"`

Frontend handles as `Blob`/`ArrayBuffer` for PDF.js or iframe embedding.

### 6.3 GET /pdf-files/{id}/objects

Get all extracted objects from PDF.

**Response**:
```typescript
interface PdfObjectsResponseDTO {
  pdf_file_id: number;
  page_count: number;
  objects: {
    text_words: Array<{
      page: number;
      bbox: [number, number, number, number];
      text: string;
      fontname: string;
      fontsize: number;
    }>;
    text_lines: Array<{
      page: number;
      bbox: [number, number, number, number];
    }>;
    graphic_rects: Array<{
      page: number;
      bbox: [number, number, number, number];
      linewidth: number;
    }>;
    graphic_lines: Array<{
      page: number;
      bbox: [number, number, number, number];
      linewidth: number;
    }>;
    graphic_curves: Array<{
      page: number;
      bbox: [number, number, number, number];
      points: Array<[number, number]>;
      linewidth: number;
    }>;
    images: Array<{
      page: number;
      bbox: [number, number, number, number];
      format: string;    // e.g., "JPEG", "PNG"
      colorspace: string; // e.g., "RGB", "CMYK"
      bits: number;
    }>;
    tables: Array<{
      page: number;
      bbox: [number, number, number, number];
      rows: number;
      cols: number;
    }>;
  };
}
```

### 6.4 POST /pdf-files/process

Process uploaded PDF file without storing it (for template builder preview).

**Request**: `multipart/form-data` with `pdf_file: File`

**Response**:
```typescript
interface PdfProcessResponseDTO {
  page_count: number;
  objects: {
    // Same structure as GET /pdf-files/{id}/objects
    // but without pdf_file_id field
  };
}
```

---

## Validation Rules Summary

### Templates
- `name`: 1-255 chars
- `description`: max 1000 chars
- `signature_objects`: min 1
- `extraction_fields`: min 1
- New templates always start as `inactive`

### Email Configurations
- `name`: 1-255 chars
- `description`: max 1000 chars
- `email_address`: valid email format
- `folder_name`: min 1 char
- `poll_interval_seconds`: min 5
- `max_backlog_hours`: min 1
- `error_retry_attempts`: min 1, max 10

### Pagination
- Default limit: 50
- Maximum limit: 200
- Default offset: 0

### File Uploads
All file uploads use `multipart/form-data` encoding with appropriate field names.

---

## Common Patterns

### Status Enums
- **Template Status**: `'active' | 'inactive'`
- **ETO Run Status**: `'not_started' | 'processing' | 'success' | 'failure' | 'needs_template' | 'skipped'`
- **Stage Status**: `'not_started' | 'success' | 'failure' | 'skipped'`

### Pagination
All list endpoints follow the pattern:
```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

### BBox Format
All bounding boxes use the format: `[x0, y0, x1, y1]` (4-number array).

### Timestamps
All timestamps are ISO 8601 strings.

### Discriminated Unions
Used in template simulation to distinguish between stored vs. uploaded PDFs via `pdf_source` field.

---

## Implementation Notes

1. **Frontend Mock Implementation**: All features currently use mock data defined in `mocks/` directories
2. **Type Safety**: Full TypeScript types defined in `api/types.ts` files per feature
3. **Multipart Uploads**: File uploads require proper `FormData` construction in frontend
4. **Pipeline Embedding**: Production pipelines are embedded in templates; standalone pipelines are dev/testing only
5. **Version History**: Templates maintain full version history; updates create new versions
6. **Bulk Operations**: ETO runs support bulk reprocess/skip/delete operations
