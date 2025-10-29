/**
 * ETO Runs API Hook
 * Hybrid implementation: Real API for getEtoRuns, mock for others
 *
 * This allows incremental migration from mock to real API endpoints.
 * Currently implemented:
 * - getEtoRuns (REAL API)
 *
 * Still using mock:
 * - getEtoRunDetail
 * - uploadPdf
 * - reprocessRuns
 * - skipRuns
 * - deleteRuns
 * - getPdfDownloadUrl
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import {
  GetEtoRunsQueryParams,
  GetEtoRunsResponse,
  GetEtoRunDetailResponse,
  PostEtoRunUploadResponse,
  PostEtoRunsReprocessRequest,
  PostEtoRunsSkipRequest,
  DeleteEtoRunsRequest,
} from '../api/types';
import { useMockEtoApi } from './useMockEtoApi';
import { usePdfFilesApi } from '../../pdf-files/hooks/usePdfFilesApi';

export function useEtoApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get mock API for methods not yet implemented
  const mockApi = useMockEtoApi();

  // Get PDF files API for upload
  const pdfFilesApi = usePdfFilesApi();

  const baseUrl = API_CONFIG.ENDPOINTS.ETO_RUNS;

  /**
   * Helper to handle API calls with loading and error states
   */
  const withLoadingAndError = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiCall();
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // ==========================================================================
  // REAL API: GET /api/eto-runs - List runs with filtering and pagination
  // ==========================================================================
  const getEtoRuns = useCallback(
    async (params?: GetEtoRunsQueryParams): Promise<GetEtoRunsResponse> => {
      return withLoadingAndError(async () => {
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
      });
    },
    [baseUrl, withLoadingAndError]
  );

  // ==========================================================================
  // MOCK API: GET /api/eto-runs/{id} - Get run details
  // ==========================================================================
  const getEtoRunDetail = useCallback(
    async (runId: number): Promise<GetEtoRunDetailResponse> => {
      // TODO: Implement real API call
      return mockApi.getEtoRunDetail(runId);
    },
    [mockApi]
  );

  // ==========================================================================
  // REAL API: POST /api/pdf-files + POST /api/eto-runs - Upload PDF & Create Run
  // ==========================================================================
  const uploadPdf = useCallback(
    async (file: File): Promise<PostEtoRunUploadResponse> => {
      return withLoadingAndError(async () => {
        // Step 1: Upload PDF to pdf-files endpoint
        const pdfMetadata = await pdfFilesApi.uploadPdf(file);

        // Step 2: Create ETO run with the PDF ID
        const response = await apiClient.post<PostEtoRunUploadResponse>(
          baseUrl,
          { pdf_file_id: pdfMetadata.id }
        );

        return response.data;
      });
    },
    [baseUrl, withLoadingAndError, pdfFilesApi]
  );

  // ==========================================================================
  // MOCK API: POST /api/eto-runs/reprocess - Reprocess runs (bulk)
  // ==========================================================================
  const reprocessRuns = useCallback(
    async (request: PostEtoRunsReprocessRequest): Promise<void> => {
      // TODO: Implement real API call
      // await apiClient.post(`${baseUrl}/reprocess`, request);
      return mockApi.reprocessRuns(request);
    },
    [mockApi]
  );

  // ==========================================================================
  // MOCK API: POST /api/eto-runs/skip - Skip runs (bulk)
  // ==========================================================================
  const skipRuns = useCallback(
    async (request: PostEtoRunsSkipRequest): Promise<void> => {
      // TODO: Implement real API call
      // await apiClient.post(`${baseUrl}/skip`, request);
      return mockApi.skipRuns(request);
    },
    [mockApi]
  );

  // ==========================================================================
  // MOCK API: DELETE /api/eto-runs - Delete runs (bulk)
  // ==========================================================================
  const deleteRuns = useCallback(
    async (request: DeleteEtoRunsRequest): Promise<void> => {
      // TODO: Implement real API call
      // await apiClient.delete(baseUrl, { data: request });
      return mockApi.deleteRuns(request);
    },
    [mockApi]
  );

  // ==========================================================================
  // MOCK API: GET /api/pdf-files/{id}/download - Get PDF file URL
  // ==========================================================================
  const getPdfDownloadUrl = useCallback((pdfFileId: number): string => {
    // TODO: Implement real API URL
    // return `${API_CONFIG.BASE_URL}/api/pdf-files/${pdfFileId}/download`;
    return mockApi.getPdfDownloadUrl(pdfFileId);
  }, [mockApi]);

  return {
    // API methods
    getEtoRuns,           // REAL API ✓
    getEtoRunDetail,      // Mock (TODO)
    uploadPdf,            // REAL API ✓ (2-step: pdf-files + eto-runs)
    reprocessRuns,        // Mock (TODO)
    skipRuns,             // Mock (TODO)
    deleteRuns,           // Mock (TODO)
    getPdfDownloadUrl,    // Mock (TODO)

    // State - combine real API loading with mock API loading
    isLoading: isLoading || mockApi.isLoading || pdfFilesApi.isLoading,
    error: error || mockApi.error || pdfFilesApi.error,
  };
}
