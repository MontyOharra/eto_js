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

// Base template data shared by both request types
interface TemplateSimulationData {
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
}

// Request variant for stored PDFs (from database)
export interface PostTemplateSimulateStoredRequest extends TemplateSimulationData {
  pdf_source: 'stored';
  pdf_file_id: number;
}

// Request variant for uploaded PDFs (template builder with local file)
export interface PostTemplateSimulateUploadRequest extends TemplateSimulationData {
  pdf_source: 'upload';
  // pdf_file: File will be sent as multipart/form-data
}

// Discriminated union of both request types
export type PostTemplateSimulateRequest =
  | PostTemplateSimulateStoredRequest
  | PostTemplateSimulateUploadRequest;

export interface ValidationResult {
  field_label: string;
  required: boolean;
  has_value: boolean;
  regex_valid: boolean | null; // null if no regex
  error: string | null;
}

export interface SimulationStep {
  step_number: number;
  module_instance_id: string;
  module_name: string; // Human-readable
  inputs: Record<string, { value: any; type: string }>;
  outputs: Record<string, { value: any; type: string }>;
  error: object | null;
}

export interface SimulatedAction {
  action_module_name: string;
  inputs: Record<string, any>;
  simulation_note: string; // "Action not executed - simulation mode"
}

export interface PostTemplateSimulateResponse {
  // Stage 1: Template Matching (always succeeds)
  template_matching: {
    status: 'success';
    message: string;
  };

  // Stage 2: Data Extraction
  data_extraction: {
    status: 'success' | 'failure';
    extracted_data: Record<string, string> | null;
    error_message: string | null;
    validation_results: ValidationResult[];
  };

  // Stage 3: Pipeline Execution
  pipeline_execution: {
    status: 'success' | 'failure';
    error_message: string | null;
    steps: SimulationStep[];
    simulated_actions: SimulatedAction[];
  };
}
