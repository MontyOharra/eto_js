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
  | 'processing'
  | 'success'
  | 'failure'
  | 'needs_template'
  | 'skipped';

// =============================================================================
// Nested Types for List View
// =============================================================================

export interface EtoPdfInfo {
  id: number;
  original_filename: string;
  file_size: number | null;
  page_count: number | null;
}

export interface EtoSourceManual {
  type: 'manual';
}

export interface EtoSourceEmail {
  type: 'email';
  sender_email: string;
  received_date: string; // ISO 8601
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

// =============================================================================
// ETO Run List Item (for GET /eto-runs)
// =============================================================================

export interface EtoSubRunListItem {
  id: number;
  sequence: number | null;
  status: string;
  matched_pages: number[];
  is_unmatched_group: boolean;
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

export interface EtoSubRunExtraction {
  id: number;
  status: 'processing' | 'success' | 'failure';
  extraction_results: ExtractedFieldResult[] | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ExtractedFieldResult {
  name: string;
  description: string | null;
  bbox: [number, number, number, number];
  page: number;
  extracted_value: string;
}

export interface EtoSubRunPipelineExecutionStep {
  id: number;
  step_number: number;
  module_instance_id: string;
  inputs: Record<string, any> | null;
  outputs: Record<string, any> | null;
  error: string | null;
}

export interface EtoSubRunPipelineExecution {
  id: number;
  status: 'processing' | 'success' | 'failure';
  executed_actions: Record<string, any>[] | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  steps: EtoSubRunPipelineExecutionStep[] | null;
}

export interface EtoSubRunDetail {
  id: number;
  sequence: number | null;
  status: string;
  matched_pages: number[];
  is_unmatched_group: boolean;

  // Error tracking
  error_type: string | null;
  error_message: string | null;

  // Timestamps
  started_at: string | null;
  completed_at: string | null;

  // Template info (null for unmatched groups)
  template: EtoMatchedTemplate | null;

  // Stage data
  extraction: EtoSubRunExtraction | null;
  pipeline_execution: EtoSubRunPipelineExecution | null;
}

export interface EtoRunDetail {
  id: number;
  status: EtoRunStatus;
  processing_step: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_type: string | null;
  error_message: string | null;
  error_details: string | null;

  // PDF file info
  pdf: EtoPdfInfo;

  // Source (manual or email)
  source: EtoSource;

  // Sub-runs with full detail
  sub_runs: EtoSubRunDetail[];
}
