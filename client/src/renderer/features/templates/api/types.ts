/**
 * API Types (Request/Response DTOs)
 * These types represent the exact shape of data sent to/from the API endpoints.
 * They import and use domain types from '../types.ts'
 */

import {
  TemplateStatus,
  TemplateListItem,
  TemplateDetail,
  TemplateVersionListItem,
  TemplateVersionDetail,
  SignatureObject,
  ExtractionField,
} from '../types';
import type { PipelineState, VisualState } from '../../../types/pipelineTypes';
import type { PdfObjectsResponseDTO } from '../../pdf-files/api/types';

// =============================================================================
// GET /pdf-templates - List templates with pagination
// =============================================================================

export interface GetTemplatesQueryParams {
  status?: TemplateStatus;
  sort_by?: 'name' | 'status' | 'usage_count';
  sort_order?: 'asc' | 'desc';
  limit?: number; // default: 50, max: 200
  offset?: number; // default: 0
}

export interface GetTemplatesResponse {
  items: TemplateListItem[];
  total: number;
  limit: number;
  offset: number;
}

// =============================================================================
// GET /pdf-templates/{id} - Get full template details
// =============================================================================

// Response type is TemplateDetail from domain types
export type GetTemplateDetailResponse = TemplateDetail;

// =============================================================================
// POST /pdf-templates - Create new template
// =============================================================================

export interface PostTemplateCreateRequest {
  name: string; // required, 1-255 chars
  description?: string; // optional, max 1000 chars

  // PDF source - either existing file or new upload
  // If source_pdf_id is null, pdf_file must be provided as multipart/form-data
  source_pdf_id?: number | null; // optional - for templates from existing PDFs

  // Step 1: Signature objects
  signature_objects: SignatureObject[]; // required, min: 1

  // Step 2: Extraction fields
  extraction_fields: ExtractionField[]; // required, min: 1

  // Step 3: Pipeline definition
  pipeline_state: PipelineState;
  visual_state: VisualState;

  // Note: pdf_file (File) will be sent as multipart/form-data when source_pdf_id is null
}

export interface PostTemplateCreateResponse {
  id: number; // Created template ID
  name: string;
  status: 'inactive'; // Always starts as inactive
  current_version_id: number; // Version 1 ID
  current_version_num: 1;
  pipeline_definition_id: number;
}

// =============================================================================
// PUT /pdf-templates/{id} - Update template (creates new version)
// =============================================================================

export interface PutTemplateUpdateRequest {
  // Optional: Update template metadata
  name?: string; // optional, 1-255 chars
  description?: string; // optional, max 1000 chars

  // Required: New version data (all 3 wizard steps)
  signature_objects: SignatureObject[]; // required, min: 1
  extraction_fields: ExtractionField[]; // required, min: 1
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

export interface PutTemplateUpdateResponse {
  id: number;
  name: string;
  status: TemplateStatus; // Status unchanged
  current_version_id: number; // Updated to new version ID
  current_version_num: number; // Incremented
  pipeline_definition_id: number; // New pipeline ID
}

// =============================================================================
// DELETE /pdf-templates/{id} - Delete template
// =============================================================================

// No request body
// Response: 204 No Content

// =============================================================================
// POST /pdf-templates/{id}/activate - Activate template
// =============================================================================

// No request body

export interface PostTemplateActivateResponse {
  id: number;
  status: 'active';
  current_version_id: number;
}

// =============================================================================
// POST /pdf-templates/{id}/deactivate - Deactivate template
// =============================================================================

// No request body

export interface PostTemplateDeactivateResponse {
  id: number;
  status: 'inactive';
  current_version_id: number;
}

// =============================================================================
// GET /pdf-templates/{id}/versions - List all versions
// =============================================================================

// Response is array of TemplateVersionListItem from domain types
export type GetTemplateVersionsResponse = TemplateVersionListItem[];

// =============================================================================
// GET /pdf-templates/{id}/versions/{version_id} - Get version details
// =============================================================================

// Response type is TemplateVersionDetail from domain types
export type GetTemplateVersionDetailResponse = TemplateVersionDetail;

// =============================================================================
// POST /pdf-templates/simulate - Simulate full ETO process
// =============================================================================

/**
 * Request for template simulation (testing/preview only)
 *
 * The frontend must provide the extracted PDF objects (from either:
 * - Stored PDF: fetched via GET /api/pdf-files/{id}/objects
 * - Uploaded PDF: extracted via POST /api/pdf-files/process-objects
 *
 * Backend accepts JSON body with:
 * - pdf_objects: Already-extracted PDF objects (no file upload!)
 * - extraction_fields: Field definitions with bbox coordinates
 * - pipeline_state: Pipeline graph structure
 */
export interface PostTemplateSimulateRequest {
  pdf_objects: PdfObjectsResponseDTO['objects'];  // Pre-extracted PDF objects
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
}

/**
 * Single extraction field result with bbox for visual display
 * Matches backend: server-new/src/api/schemas/pdf_templates.py::ExtractedFieldResult
 */
export interface ExtractedFieldResult {
  name: string;
  description: string | null;
  bbox: [number, number, number, number];  // [x0, y0, x1, y1]
  page: number;
  extracted_value: string;  // The actual extracted text
}

/**
 * Result of a single module execution
 * Matches backend: server-new/src/api/schemas/pipelines.py::ExecutionStepResult
 */
export interface ExecutionStepResult {
  module_instance_id: string;
  step_number: number;
  inputs: Record<string, { value: any; type: string }>;
  outputs: Record<string, { value: any; type: string }>;
  error: string | null;
}

/**
 * Response for POST /pdf-templates/simulate
 * Matches backend: server-new/src/api/schemas/pdf_templates.py::SimulateTemplateResponse
 */
export interface PostTemplateSimulateResponse {
  extraction_results: ExtractedFieldResult[];  // Fields with extracted values and bbox info
  pipeline_status: string;  // "success" | "failed"
  pipeline_steps: ExecutionStepResult[];
  pipeline_actions: Record<string, Record<string, any>>;  // {module_instance_id: inputs}
  pipeline_error: string | null;
}
