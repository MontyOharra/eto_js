/**
 * Domain types for test feature
 * These types match the backend API schema structure exactly
 */

// =============================================================================
// Shared Types
// =============================================================================

export type EtoRunStatus =
  | 'processing'
  | 'success'
  | 'failure'
  | 'skipped';

export type EtoSubRunStatus =
  | 'not_started'
  | 'matched'
  | 'processing'
  | 'success'
  | 'failure'
  | 'needs_template'
  | 'skipped';

// =============================================================================
// Nested Types (Shared)
// =============================================================================

export interface EtoPdfInfo {
  id: number;
  original_filename: string;
  file_size: number | null;
  page_count: number; // Required for detail view
}

export interface EtoSourceManual {
  type: 'manual';
  created_at: string; // ISO 8601
}

export interface EtoSourceEmail {
  type: 'email';
  sender_email: string;
  received_at: string; // ISO 8601
  subject: string | null;
  folder_name: string;
}

export type EtoSource = EtoSourceManual | EtoSourceEmail;

export interface EtoSubRunsSummary {
  total_count: number;
  matched_count: number;
  needs_template_count: number;
  success_count: number;
  failure_count: number;
  processing_count: number;
  not_started_count: number;
  pages_matched_count: number;
  pages_unmatched_count: number;
}

export interface EtoMatchedTemplate {
  template_id: number;
  template_name: string;
  version_id: number;
  version_num: number;
}

export interface EtoSubRunTemplate {
  id: number;
  name: string;
}

// =============================================================================
// ETO Run List Item (for GET /eto-runs)
// =============================================================================

export interface EtoSubRunListItem {
  id: number;
  sequence: number | null;
  status: string;
  matched_pages: number[];
  template: EtoMatchedTemplate | null;
}

export interface EtoRunListItem {
  id: number;
  status: EtoRunStatus;
  processing_step: string | null;
  is_read: boolean;
  started_at: string | null; // ISO 8601
  completed_at: string | null; // ISO 8601
  updated_at: string | null; // ISO 8601
  last_processed_at: string | null; // ISO 8601 - Max sub-run timestamp
  error_type: string | null;
  error_message: string | null;

  // Embedded related data
  pdf: EtoPdfInfo;
  source: EtoSource;

  // Sub-runs summary
  sub_runs_summary: EtoSubRunsSummary;

  // Optional: basic sub-run list for expandable rows
  sub_runs: EtoSubRunListItem[] | null;
}

// =============================================================================
// ETO Run Detail Types (for GET /eto-runs/{id})
// =============================================================================

export interface TransformResult {
  field_name: string;
  value: string;
}

export interface EtoSubRunSummary {
  id: number;
  status: EtoSubRunStatus;
  matched_pages: number[];
  template: EtoSubRunTemplate | null; // null for needs_template sub-runs
  transform_results: TransformResult[]; // empty for now
  error_message: string | null;
}

export interface EtoRunOverview {
  templates_matched_count: number;
  processing_time_ms: number | null;
}

export interface PageStatus {
  page_number: number;
  status: EtoSubRunStatus;
  sub_run_id: number;
}

export interface EtoRunDetail {
  id: number;
  status: EtoRunStatus;
  processing_step: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_type: string | null;
  error_message: string | null;

  // PDF file info
  pdf: EtoPdfInfo;

  // Source (manual or email)
  source: EtoSource;

  // Computed overview stats
  overview: EtoRunOverview;

  // Sub-runs (UI filters by status)
  sub_runs: EtoSubRunSummary[];

  // Page breakdown
  page_statuses: PageStatus[];
}

// =============================================================================
// ETO Sub-Run Full Detail Types (for GET /eto-runs/sub-runs/{id})
// =============================================================================

export interface ExtractionResult {
  name: string;
  description: string | null;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  page: number;
  extracted_value: string;
}

// Used by ExtractedFieldsOverlay for rendering bounding boxes
export interface ExtractedFieldWithBox {
  field_id: string;
  label: string;
  value: string;
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
}

export interface EtoSubRunExtractionDetail {
  status: 'processing' | 'success' | 'failure';
  started_at: string | null;
  completed_at: string | null;
  extraction_results: ExtractionResult[];
}

export interface PipelineExecutionStepError {
  type: string;
  message: string;
  details: unknown | null;
}

export interface PipelineExecutionStep {
  id: number;
  step_number: number;
  module_instance_id: string;
  inputs: Record<string, unknown> | null;
  outputs: Record<string, unknown> | null;
  error: PipelineExecutionStepError | null;
}

export interface EtoSubRunPipelineExecutionDetail {
  status: 'processing' | 'success' | 'failure';
  started_at: string | null;
  completed_at: string | null;
  pipeline_definition_id: number | null;
  steps: PipelineExecutionStep[];
}

export interface EtoSubRunFullDetail {
  id: number;
  eto_run_id: number;
  status: EtoSubRunStatus;
  matched_pages: number[];
  template: EtoSubRunTemplate | null;
  template_version_id: number | null;
  error_type: string | null;
  error_message: string | null;
  error_details: string | null;
  started_at: string | null;
  completed_at: string | null;

  // PDF info (from parent run)
  pdf: EtoPdfInfo;

  // Stage details (optional, only present if processing reached that stage)
  stage_data_extraction: EtoSubRunExtractionDetail | null;
  stage_pipeline_execution: EtoSubRunPipelineExecutionDetail | null;
}
