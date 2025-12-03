/**
 * Pipelines API Types
 * TypeScript definitions matching backend Pydantic schemas
 * Source: server/src/api/schemas/pipelines.py
 */

import type { PipelineState, VisualState } from '../types';

// ============================================================================
// List Endpoint (GET /pipelines)
// ============================================================================

/**
 * Lightweight pipeline summary for list views
 * Response item from GET /pipelines
 */
export interface PipelineSummary {
  id: number;
}

/**
 * Response for GET /pipelines
 * Paginated list of pipeline summaries
 */
export interface PipelinesListResponse {
  items: PipelineSummary[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Detail Endpoint (GET /pipelines/{id})
// ============================================================================

/**
 * Full pipeline definition details
 * Response for GET /pipelines/{id}
 */
export interface PipelineDetail {
  id: number;
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

// ============================================================================
// Create Endpoint (POST /pipelines)
// ============================================================================

/**
 * Request body for POST /pipelines
 * Create new standalone pipeline for testing
 */
export interface CreatePipelineRequest {
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

/**
 * Response for POST /pipelines
 * Returns created pipeline ID
 */
export interface CreatePipelineResponse {
  id: number;
}

// ============================================================================
// Validation Endpoint (POST /pipelines/validate)
// ============================================================================

/**
 * Single validation error
 * Contains error code, message, and optional context
 */
export interface ValidationError {
  code: string;
  message: string;
  where?: Record<string, any> | null;
}

/**
 * Request body for POST /pipelines/validate
 * Validate pipeline structure without saving
 */
export interface ValidatePipelineRequest {
  pipeline_json: PipelineState;
}

/**
 * Response for POST /pipelines/validate
 * Returns validation result with error details if invalid
 */
export interface ValidatePipelineResponse {
  valid: boolean;
  error: ValidationError | null;
}

// ============================================================================
// Execution Endpoint (POST /pipelines/{id}/execute)
// ============================================================================

/**
 * Request body for POST /pipelines/{id}/execute
 * Execute pipeline with provided entry values (SIMULATION MODE)
 */
export interface ExecutePipelineRequest {
  entry_values: Record<string, any>;
}

/**
 * Result of a single module execution step
 * Contains inputs, outputs, and any error that occurred
 */
export interface ExecutionStepResult {
  module_instance_id: string;
  step_number: number;
  inputs: Record<string, Record<string, any>>;
  outputs: Record<string, Record<string, any>>;
  error: string | null;
}

/**
 * Response for POST /pipelines/{id}/execute
 * Contains execution status, step results, and output module data
 */
export interface ExecutePipelineResponse {
  status: string;
  steps: ExecutionStepResult[];
  output_module_id: string | null;  // ID of the output module (if configured)
  output_module_inputs: Record<string, unknown>;  // Inputs collected for the output module
  error: string | null;
}

// ============================================================================
// Query Parameters
// ============================================================================

/**
 * Query parameters for GET /pipelines
 * Controls sorting, pagination
 */
export interface PipelinesQueryParams {
  sort_by?: 'id' | 'created_at';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}
