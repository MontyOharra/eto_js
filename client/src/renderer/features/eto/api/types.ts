/**
 * API Types (Request/Response DTOs)
 * These types represent the exact shape of data sent to/from the API endpoints.
 */

import { EtoRunListItem, EtoRunDetail, EtoSubRunStatus } from '../types';

// =============================================================================
// GET /eto-runs - List runs with pagination
// =============================================================================

export type EtoRunSortField = 'last_processed_at' | 'created_at' | 'started_at' | 'completed_at';

export interface GetEtoRunsQueryParams {
  /** Filter by read status (true=read, false=unread) */
  is_read?: boolean;
  /** Filter runs that have at least one sub-run with this status */
  has_sub_run_status?: EtoSubRunStatus;
  /** Search in PDF filename, email sender, and subject */
  search?: string;
  /** Filter runs created on or after this date (ISO 8601) */
  date_from?: string;
  /** Filter runs created on or before this date (ISO 8601) */
  date_to?: string;
  /** Field to sort by (default: last_processed_at) */
  sort_by?: EtoRunSortField;
  /** Sort order (default: desc) */
  sort_order?: 'asc' | 'desc';
  /** Number of runs to return (default: 50, max: 200) */
  limit?: number;
  /** Number of runs to skip (default: 0) */
  offset?: number;
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

export type GetEtoRunDetailResponse = EtoRunDetail;

// =============================================================================
// POST /eto-runs - Create run from uploaded PDF
// =============================================================================

export interface CreateEtoRunRequest {
  pdf_file_id: number;
}

export interface CreateEtoRunResponse {
  id: number;
  status: string;
  pdf_file_id: number;
  started_at: string | null;
  created_at: string;
}

// =============================================================================
// POST /eto-runs/reprocess - Reprocess runs (bulk)
// =============================================================================

export interface ReprocessRunsRequest {
  run_ids: number[];
}

// Response: 204 No Content

// =============================================================================
// POST /eto-runs/skip - Skip runs (bulk)
// =============================================================================

export interface SkipRunsRequest {
  run_ids: number[];
}

// Response: 204 No Content

// =============================================================================
// DELETE /eto-runs - Delete runs (bulk)
// =============================================================================

export interface DeleteRunsRequest {
  run_ids: number[];
}

// Response: 204 No Content

// =============================================================================
// PATCH /eto-runs/{id} - Update run (e.g., mark as read)
// =============================================================================

export interface UpdateEtoRunRequest {
  is_read?: boolean;
}

// Response: 204 No Content or updated EtoRunListItem

// =============================================================================
// Sub-Run Level Operations
// =============================================================================

// POST /eto-runs/sub-runs/{sub_run_id}/reprocess
// POST /eto-runs/sub-runs/{sub_run_id}/skip

export interface SubRunOperationResponse {
  new_sub_run_id: number;
  eto_run_id: number;
}

// =============================================================================
// Run-Level Aggregated Operations
// =============================================================================

// POST /eto-runs/{run_id}/reprocess - Reprocess all failed/needs_template sub-runs
// POST /eto-runs/{run_id}/skip - Skip all failed/needs_template sub-runs

export interface RunOperationResponse {
  run_id: number;
  new_sub_run_id: number | null;
  message: string;
}
