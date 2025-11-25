/**
 * API Types (Request/Response DTOs)
 * These types represent the exact shape of data sent to/from the API endpoints.
 */

import { EtoRunListItem, EtoRunDetail, EtoRunStatus } from '../types';

// =============================================================================
// GET /eto-runs - List runs with pagination
// =============================================================================

export interface GetEtoRunsQueryParams {
  status?: EtoRunStatus;
  is_read?: boolean;
  sort_by?: 'created_at' | 'updated_at' | 'started_at' | 'completed_at' | 'status';
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
