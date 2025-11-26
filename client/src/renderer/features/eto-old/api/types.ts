/**
 * API Types (Request/Response DTOs)
 * These types represent the exact shape of data sent to/from the API endpoints.
 * They import and use domain types from '../types.ts'
 */

import {
  EtoRunStatus,
  EtoRunListItem,
  EtoRunDetail,
} from '../types';

// =============================================================================
// GET /eto-runs - List runs with pagination
// =============================================================================

export interface GetEtoRunsQueryParams {
  status?: EtoRunStatus;
  sort_by?: 'created_at' | 'started_at' | 'completed_at' | 'status';
  sort_order?: 'asc' | 'desc';
  limit?: number; // default: 50, max: 200
  offset?: number; // default: 0
}

export interface GetEtoRunsResponse {
  items: EtoRunListItem[];
  total: number;
  limit: number;
  offset: number;
}

// =============================================================================
// GET /eto-runs/{id} - Get full run details
// =============================================================================

// Response type is EtoRunDetail from domain types
export type GetEtoRunDetailResponse = EtoRunDetail;

// =============================================================================
// POST /eto-runs - Create run from uploaded PDF
// =============================================================================

// Request: { pdf_file_id: number }

export interface PostEtoRunUploadResponse {
  id: number;
  pdf_file_id: number;
  status: 'not_started';
  started_at: string | null;  // ISO 8601, null for not_started runs
  created_at: string;  // ISO 8601
}

// =============================================================================
// POST /eto-runs/reprocess - Reprocess runs (bulk)
// =============================================================================

export interface PostEtoRunsReprocessRequest {
  run_ids: number[];
}

// Response: 204 No Content

// =============================================================================
// POST /eto-runs/skip - Skip runs (bulk)
// =============================================================================

export interface PostEtoRunsSkipRequest {
  run_ids: number[];
}

// Response: 204 No Content

// =============================================================================
// DELETE /eto-runs - Delete runs (bulk)
// =============================================================================

export interface DeleteEtoRunsRequest {
  run_ids: number[];
}

// =============================================================================
// POST /eto-runs/{run_id}/reprocess - Reprocess single run (aggregates failed sub-runs)
// POST /eto-runs/{run_id}/skip - Skip single run (aggregates failed sub-runs)
// =============================================================================

export interface RunOperationResponse {
  run_id: number;
  new_sub_run_id: number | null;
  message: string;
}