/**
 * ETO Runs API Hooks
 * TanStack Query hooks for ETO run operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import { useUploadPdf, getPdfDownloadUrl } from '../../pdf';
import {
  GetEtoRunsQueryParams,
  GetEtoRunsResponse,
  GetEtoRunDetailResponse,
  PostEtoRunUploadResponse,
  PostEtoRunsReprocessRequest,
  PostEtoRunsSkipRequest,
  DeleteEtoRunsRequest,
} from '../api/types';

const baseUrl = API_CONFIG.ENDPOINTS.ETO_RUNS;

// ============================================================================
// Query Hooks (GET operations)
// ============================================================================

/**
 * Fetch list of ETO runs with filtering and pagination
 * Supports status filtering, sorting, and pagination
 */
export function useEtoRuns(params?: GetEtoRunsQueryParams) {
  return useQuery({
    queryKey: ['eto-runs', params],
    queryFn: async (): Promise<GetEtoRunsResponse> => {
      const response = await apiClient.get<GetEtoRunsResponse>(baseUrl, {
        params: {
          status_filter: params?.status,
          sort_by: params?.sort_by || 'created_at',
          sort_order: params?.sort_order || 'desc',
          limit: params?.limit || 50,
          offset: params?.offset || 0,
        },
      });
      return response.data;
    },
    staleTime: 30 * 1000, // Consider data stale after 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

/**
 * Fetch detailed information for a single ETO run
 * Includes all processing stages (matching, extraction, pipeline execution)
 */
export function useEtoRunDetail(runId: number | null) {
  return useQuery({
    queryKey: ['eto-run', runId],
    queryFn: async (): Promise<GetEtoRunDetailResponse> => {
      if (!runId) {
        throw new Error('No run ID provided');
      }

      const response = await apiClient.get<GetEtoRunDetailResponse>(
        `${baseUrl}/${runId}`
      );
      return response.data;
    },
    enabled: !!runId, // Only run query if runId exists
    staleTime: 30 * 1000, // Consider data stale after 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

// ============================================================================
// Mutation Hooks (POST/DELETE operations)
// ============================================================================

/**
 * Create new ETO run from uploaded PDF
 * Two-step process: Upload PDF → Create ETO run
 */
export function useCreateEtoRun() {
  const queryClient = useQueryClient();
  const { mutateAsync: uploadPdfMutation } = useUploadPdf();

  return useMutation({
    mutationFn: async (pdfFile: File): Promise<PostEtoRunUploadResponse> => {
      // Step 1: Upload PDF to pdf-files endpoint
      const pdfMetadata = await uploadPdfMutation(pdfFile);

      // Step 2: Create ETO run with the PDF ID
      const response = await apiClient.post<PostEtoRunUploadResponse>(
        baseUrl,
        { pdf_file_id: pdfMetadata.id }
      );

      return response.data;
    },
    onSuccess: () => {
      // Invalidate runs list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
    },
  });
}

/**
 * Reprocess failed or skipped ETO runs (bulk operation)
 * Resets runs to "not_started" status for background worker to pick up
 */
export function useReprocessRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: PostEtoRunsReprocessRequest): Promise<void> => {
      await apiClient.post(`${baseUrl}/reprocess`, request);
    },
    onSuccess: () => {
      // Invalidate runs list and any cached run details
      queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
      queryClient.invalidateQueries({ queryKey: ['eto-run'] });
    },
  });
}

/**
 * Mark ETO runs as skipped (bulk operation)
 * Preserves stage data but excludes from bulk reprocessing
 */
export function useSkipRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: PostEtoRunsSkipRequest): Promise<void> => {
      await apiClient.post(`${baseUrl}/skip`, request);
    },
    onSuccess: () => {
      // Invalidate runs list and any cached run details
      queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
      queryClient.invalidateQueries({ queryKey: ['eto-run'] });
    },
  });
}

/**
 * Permanently delete ETO runs (bulk operation)
 * Can only delete runs with status="skipped"
 */
export function useDeleteRuns() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeleteEtoRunsRequest): Promise<void> => {
      await apiClient.delete(baseUrl, { data: request });
    },
    onSuccess: () => {
      // Invalidate runs list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['eto-runs'] });
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get PDF download URL for a given PDF file ID
 * Re-exported from PDF feature for convenience
 */
export { getPdfDownloadUrl };
