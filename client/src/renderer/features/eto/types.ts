// Domain types for ETO runs feature

export type EtoRunStatus =
  | 'not_started'
  | 'processing'
  | 'success'
  | 'failure'
  | 'needs_template'
  | 'skipped';

export type EtoProcessingStep =
  | 'template_matching'
  | 'data_extraction'
  | 'data_transformation';

export type EtoSourceType = 'manual' | 'email';

export interface EtoSource {
  type: EtoSourceType;
  // Email-specific fields (only present when type = "email")
  sender_email?: string;
  received_date?: string;
  subject?: string | null;
  folder_name?: string;
}

export interface EtoPdfInfo {
  id: number;
  original_filename: string;
  file_size: number | null;
  page_count?: number | null;
}

export interface EtoMatchedTemplate {
  template_id: number;
  template_name: string;
  version_id: number;
  version_num: number;
}

// List/summary view of an ETO run
export interface EtoRunListItem {
  id: number;
  status: EtoRunStatus;
  processing_step: EtoProcessingStep | null;
  started_at: string | null;
  completed_at: string | null;
  error_type: string | null;
  error_message: string | null;
  pdf: EtoPdfInfo;
  source: EtoSource;
  matched_template: EtoMatchedTemplate | null;
}

// Full detail view of an ETO run (includes stage details)
export interface EtoRunDetail extends EtoRunListItem {
  error_details: string | null;
  pdf: EtoPdfInfo & { page_count: number | null };
  // Stages are optional - only populated based on run progress
  stage_template_matching: EtoStageTemplateMatching | null;
  stage_data_extraction: EtoStageDataExtraction | null;
  stage_pipeline_execution: EtoStagePipelineExecution | null;
}

// Stage 1: Template Matching
export interface EtoStageTemplateMatching {
  status: 'processing' | 'success' | 'failure';
  started_at: string | null;
  completed_at: string | null;
  // Template info is denormalized at stage level (not nested object)
  matched_template_version_id: number | null;
  matched_template_name: string | null;
  matched_version_number: number | null;
}

// Stage 2: Data Extraction
export interface ExtractedFieldWithBox {
  field_id: string;
  label: string;
  value: string;
  page: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

export interface EtoStageDataExtraction {
  status: 'processing' | 'success' | 'failure';
  started_at: string | null;
  completed_at: string | null;
  extracted_data: Record<string, any> | null;
  // Optional feature - not yet implemented in backend
  extracted_fields_with_boxes?: ExtractedFieldWithBox[];
}

// Stage 3: Pipeline Execution
export interface EtoStagePipelineExecution {
  status: 'processing' | 'success' | 'failure';
  started_at: string | null;
  completed_at: string | null;
  // Server returns Dict, not Array
  executed_actions: Record<string, any> | null;
  // Optional fields - may not be implemented yet in backend
  pipeline_definition_id?: number;
  steps?: EtoPipelineExecutionStep[];
}

export interface EtoPipelineExecutionStep {
  id: number;
  step_number: number;
  module_instance_id: string;
  // Keys are node_ids from pipeline definition (e.g., "i1", "i2", "o1")
  inputs: Record<string, { name: string; value: any; type: string }> | null;
  outputs: Record<string, { name: string; value: any; type: string }> | null;
  // Structured error object
  error: {
    type: string;
    message: string;
    details?: any;
  } | null;
}
