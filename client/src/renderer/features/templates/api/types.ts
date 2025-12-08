/**
 * API Types (Request/Response DTOs)
 * These types represent the exact shape of data sent to/from the API endpoints.
 * They import and use domain types from '../types.ts' and other features
 */

import {
  TemplateStatus,
  ExtractionField,
} from '../types';
import type { PdfObjects } from '../../pdf';
import type { PipelineState, VisualState } from '../../pipelines/types';
import type { PdfObjectsResponse as PdfObjectsResponseDTO } from '../../pdf/api/types';

// =============================================================================
// GET /pdf-templates - List templates
// =============================================================================

export interface GetTemplatesQueryParams {
  status?: TemplateStatus;
  sort_by?: 'name' | 'status' | 'usage_count';
  sort_order?: 'asc' | 'desc';
}

// =============================================================================
// POST /pdf-templates - Create new template
// =============================================================================

export interface CreateTemplateRequest {
  name: string; // required, 1-255 chars
  description?: string; // optional, max 1000 chars
  customer_id?: number; // optional - references external Access DB
  source_pdf_id: number; // required - PDF must be uploaded first via POST /pdf-files

  // Step 1: Signature objects (PdfObjects format)
  signature_objects: PdfObjects;

  // Step 2: Extraction fields
  extraction_fields: ExtractionField[]; // required, min: 1

  // Step 3: Pipeline definition
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

// =============================================================================
// PUT /pdf-templates/{id} - Update template (creates new version)
// =============================================================================

export interface UpdateTemplateRequest {
  // Optional: Update template metadata
  name?: string; // optional, 1-255 chars
  description?: string; // optional, max 1000 chars
  customer_id?: number; // optional - references external Access DB

  // Optional: New version data (wizard steps)
  signature_objects?: PdfObjects;
  extraction_fields?: ExtractionField[];
  pipeline_state?: PipelineState;
  visual_state?: VisualState;
}

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
export interface SimulateTemplateRequest {
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
  inputs: Record<string, { value: unknown; type: string }>;
  outputs: Record<string, { value: unknown; type: string }>;
  error: string | null;
}

/**
 * Response for POST /pdf-templates/simulate
 * Matches backend: server-new/src/api/schemas/pdf_templates.py::SimulateTemplateResponse
 */
export interface SimulateTemplateResponse {
  extraction_results: ExtractedFieldResult[];  // Fields with extracted values and bbox info
  pipeline_status: string;  // "success" | "failed"
  pipeline_steps: ExecutionStepResult[];
  output_module_id: string | null;  // ID of the output module (if configured)
  output_module_inputs: Record<string, unknown>;  // Inputs collected for the output module
  pipeline_error: string | null;
}
