/**
 * ETO Runs API Hooks
 * TanStack Query hooks for ETO run operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
} from './types';

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
};

// ============================================================================
// Query Hooks (GET operations)
// ============================================================================

/**
 * Fetch list of ETO runs with filtering and pagination
 */
export function useEtoRuns(params?: GetEtoRunsQueryParams) {
  return useQuery({
    queryKey: etoRunsQueryKeys.list(params),
    queryFn: async (): Promise<GetEtoRunsResponse> => {
      const response = await apiClient.get<GetEtoRunsResponse>(baseUrl, {
        params: {
          status: params?.status,
          is_read: params?.is_read,
          sort_by: params?.sort_by || 'updated_at',
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
