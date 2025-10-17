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
  pdf: EtoPdfInfo & { page_count: number | null };
  template_matching: EtoStageTemplateMatching;
  data_extraction: EtoStageDataExtraction;
  pipeline_execution: EtoStagePipelineExecution;
}

// Stage 1: Template Matching
export interface EtoStageTemplateMatching {
  status: 'not_started' | 'success' | 'failure' | 'skipped';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  matched_template: EtoMatchedTemplate | null;
}

// Stage 2: Data Extraction
export interface EtoStageDataExtraction {
  status: 'not_started' | 'success' | 'failure' | 'skipped';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  extracted_data: Record<string, any> | null;
}

// Stage 3: Pipeline Execution
export interface EtoStagePipelineExecution {
  status: 'not_started' | 'success' | 'failure' | 'skipped';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  executed_actions: Array<{
    action_module_name: string;
    inputs: Record<string, any>;
  }> | null;
  steps: EtoPipelineExecutionStep[];
}

export interface EtoPipelineExecutionStep {
  id: number;
  step_number: number;
  module_instance_id: string;
  inputs: Record<string, { value: any; type: string }> | null;
  outputs: Record<string, { value: any; type: string }> | null;
  error: Record<string, any> | null;
}
