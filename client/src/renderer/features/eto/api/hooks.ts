/**
 * ETO Runs API Hooks
 * TanStack Query hooks for ETO run operations
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { useUploadPdf } from '../../pdf';
import {
  GetEtoRunsQueryParams,
  GetEtoRunsResponse,
  GetEtoRunDetailResponse,
  CreateEtoRunResponse,
  ReprocessRunsRequest,
  SkipRunsRequest,
  DeleteRunsRequest,
  UpdateEtoRunRequest,
  SubRunOperationResponse,
  RunOperationResponse,
  ReprocessWarningsResponse,
} from './types';
import { EtoSubRunFullDetail } from '../types';

const baseUrl = API_CONFIG.ENDPOINTS.ETO_RUNS;

// ============================================================================
// Query Keys
// ============================================================================

export const etoRunsQueryKeys = {
  all: ['eto-runs'] as const,
  lists: () => [...etoRunsQueryKeys.all, 'list'] as const,
  list: (params?: GetEtoRunsQueryParams) => [...etoRunsQueryKeys.lists(), params] as const,
  details: () => [...etoRunsQueryKeys.all, 'detail'] as const,
  detail: (id: number) => [...etoRunsQueryKeys.details(), id] as const,
  // Sub-run detail keys
  subRunDetails: () => [...etoRunsQueryKeys.all, 'sub-run-detail'] as const,
  subRunDetail: (subRunId: number) => [...etoRunsQueryKeys.subRunDetails(), subRunId] as const,
};

// ============================================================================
// Query Hooks (GET operations)
// ============================================================================

/**
 * Fetch list of ETO runs with filtering, search, and pagination
 */
export function useEtoRuns(params?: GetEtoRunsQueryParams) {
  return useQuery({
    queryKey: etoRunsQueryKeys.list(params),
    queryFn: async (): Promise<GetEtoRunsResponse> => {
      const response = await apiClient.get<GetEtoRunsResponse>(baseUrl, {
        params: {
          is_read: params?.is_read,
          has_sub_run_status: params?.has_sub_run_status,
          search: params?.search,
          date_from: params?.date_from,
          date_to: params?.date_to,
          sort_by: params?.sort_by || 'last_processed_at',
          sort_order: params?.sort_order || 'desc',
          limit: params?.limit || 50,
          offset: params?.offset || 0,
        },
      });
      return response.data;
    },
    // Keep previous data visible while fetching new data (prevents flash)
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000, // Consider data stale after 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

/**
 * Fetch detailed information for a single ETO run
 */
export function useEtoRunDetail(runId: number | null) {
  return useQuery({
    queryKey: etoRunsQueryKeys.detail(runId!),
    queryFn: async (): Promise<GetEtoRunDetailResponse> => {
      const response = await apiClient.get<GetEtoRunDetailResponse>(
        `${baseUrl}/${runId}`
      );
      return response.data;
    },
    enabled: runId !== null,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch full details for a single sub-run including extraction and pipeline data
 * Used by the sub-run detail modal
 */
export function useEtoSubRunDetail(subRunId: number | null) {
  return useQuery({
    queryKey: etoRunsQueryKeys.subRunDetail(subRunId!),
    queryFn: async (): Promise<EtoSubRunFullDetail> => {
      const response = await apiClient.get<EtoSubRunFullDetail>(
        `${baseUrl}/sub-runs/${subRunId}`
      );
      return response.data;
    },
    enabled: subRunId !== null,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

// ============================================================================
// Mutation Hooks (POST/PATCH/DELETE operations)
// ============================================================================

/**
 * Create new ETO run from uploaded PDF
 */
export function useCreateEtoRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pdfFileId: number): Promise<CreateEtoRunResponse> => {
      const response = await apiClient.post<CreateEtoRunResponse>(baseUrl, {
        pdf_file_id: pdfFileId,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
    },
  });
}

/**
 * Upload PDF and create ETO run in one operation
 * Two-step process: Upload PDF → Create ETO run
 */
export function useUploadAndCreateEtoRun() {
  const queryClient = useQueryClient();
  const { mutateAsync: uploadPdfMutation } = useUploadPdf();

  return useMutation({
    mutationFn: async (pdfFile: File): Promise<CreateEtoRunResponse> => {
      // Step 1: Upload PDF to pdf-files endpoint
      const pdfMetadata = await uploadPdfMutation(pdfFile);

      // Step 2: Create ETO run with the PDF ID
      const response = await apiClient.post<CreateEtoRunResponse>(baseUrl, {
        pdf_file_id: pdfMetadata.id,
      });

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
    },
  });
}

/**
 * Reprocess ETO runs (bulk operation)
 */
export function useReprocessRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ReprocessRunsRequest): Promise<void> => {
      await apiClient.post(`${baseUrl}/reprocess`, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.all });
    },
  });
}

/**
 * Skip ETO runs (bulk operation)
 */
export function useSkipRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: SkipRunsRequest): Promise<void> => {
      await apiClient.post(`${baseUrl}/skip`, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.all });
    },
  });
}

/**
 * Delete ETO runs (bulk operation)
 */
export function useDeleteRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeleteRunsRequest): Promise<void> => {
      await apiClient.delete(baseUrl, { data: request });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
    },
  });
}

/**
 * Update ETO run (e.g., mark as read/unread)
 */
export function useUpdateEtoRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      runId,
      updates,
    }: {
      runId: number;
      updates: UpdateEtoRunRequest;
    }): Promise<void> => {
      await apiClient.patch(`${baseUrl}/${runId}`, updates);
    },
    onSuccess: (_, { runId }) => {
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(runId) });
    },
  });
}

// ============================================================================
// Sub-Run Level Operations
// ============================================================================

/**
 * Check for warnings before reprocessing a sub-run.
 * Returns info about any terminal actions (completed/rejected/failed) that would be affected.
 */
export function useReprocessWarnings(subRunId: number | null) {
  return useQuery({
    queryKey: ['eto-runs', 'sub-runs', subRunId, 'reprocess-warnings'],
    queryFn: async (): Promise<ReprocessWarningsResponse> => {
      const response = await apiClient.get<ReprocessWarningsResponse>(
        `${baseUrl}/sub-runs/${subRunId}/reprocess-warnings`
      );
      return response.data;
    },
    enabled: subRunId !== null,
    staleTime: 30 * 1000,
  });
}

/**
 * Reprocess a single sub-run
 * Deletes the sub-run and creates a new one with the same pages for re-processing
 */
export function useReprocessSubRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (subRunId: number): Promise<SubRunOperationResponse> => {
      const response = await apiClient.post<SubRunOperationResponse>(
        `${baseUrl}/sub-runs/${subRunId}/reprocess`
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both lists and the specific run detail
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(data.eto_run_id) });
    },
  });
}

/**
 * Skip a single sub-run
 * Deletes the sub-run and creates a new one with status='skipped'
 */
export function useSkipSubRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (subRunId: number): Promise<SubRunOperationResponse> => {
      const response = await apiClient.post<SubRunOperationResponse>(
        `${baseUrl}/sub-runs/${subRunId}/skip`
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both lists and the specific run detail
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(data.eto_run_id) });
    },
  });
}

// ============================================================================
// Run-Level Aggregated Operations
// ============================================================================

/**
 * Reprocess a single ETO run by aggregating all failed/needs_template sub-runs
 * into a single new sub-run for reprocessing.
 */
export function useReprocessRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number): Promise<RunOperationResponse> => {
      const response = await apiClient.post<RunOperationResponse>(
        `${baseUrl}/${runId}/reprocess`
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate lists and the specific run detail
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(data.run_id) });
    },
  });
}

/**
 * Skip a single ETO run by aggregating all failed/needs_template sub-runs
 * into a single skipped sub-run.
 */
export function useSkipRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number): Promise<RunOperationResponse> => {
      const response = await apiClient.post<RunOperationResponse>(
        `${baseUrl}/${runId}/skip`
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate lists and the specific run detail
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(data.run_id) });
    },
  });
}
