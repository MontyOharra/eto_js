/**
 * Mock ETO API Hook
 * Simulates API calls with realistic delays and returns mock data
 */

import { useState } from 'react';
import {
  GetEtoRunsQueryParams,
  GetEtoRunsResponse,
  GetEtoRunDetailResponse,
  PostEtoRunUploadResponse,
  PostEtoRunsReprocessRequest,
  PostEtoRunsSkipRequest,
  DeleteEtoRunsRequest,
} from '../api/types';
import {
  allMockRuns,
  mockRunsByStatus,
  mockRunDetailsById,
  mockSuccessRunDetail,
  mockUploadResponse,
} from '../mocks/data';
import { EtoRunListItem } from '../types';

// Simulated network delay (300-800ms)
const simulateDelay = () =>
  new Promise((resolve) =>
    setTimeout(resolve, Math.random() * 500)
  );

export function useMockEtoApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ==========================================================================
  // GET /eto-runs - List runs with filtering and pagination
  // ==========================================================================
  const getEtoRuns = async (
    params?: GetEtoRunsQueryParams
  ): Promise<GetEtoRunsResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Filter by status if provided
      let filteredRuns: EtoRunListItem[] = params?.status
        ? mockRunsByStatus[params.status]
        : allMockRuns;

      // Sort
      const sortBy = params?.sort_by || 'started_at';
      const sortOrder = params?.sort_order || 'desc';

      filteredRuns = [...filteredRuns].sort((a, b) => {
        let aValue: any;
        let bValue: any;

        switch (sortBy) {
          case 'created_at':
          case 'started_at':
            aValue = a.started_at ? new Date(a.started_at).getTime() : 0;
            bValue = b.started_at ? new Date(b.started_at).getTime() : 0;
            break;
          case 'completed_at':
            aValue = a.completed_at ? new Date(a.completed_at).getTime() : 0;
            bValue = b.completed_at ? new Date(b.completed_at).getTime() : 0;
            break;
          case 'status':
            aValue = a.status;
            bValue = b.status;
            break;
          default:
            aValue = a.id;
            bValue = b.id;
        }

        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1;
        } else {
          return aValue < bValue ? 1 : -1;
        }
      });

      // Pagination
      const limit = params?.limit || 50;
      const offset = params?.offset || 0;
      const paginatedRuns = filteredRuns.slice(offset, offset + limit);

      return {
        items: paginatedRuns,
        total: filteredRuns.length,
        limit,
        offset,
      };
    } catch (err) {
      const errorMessage = 'Failed to fetch ETO runs';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // GET /eto-runs/{id} - Get run details
  // ==========================================================================
  const getEtoRunDetail = async (
    runId: number
  ): Promise<GetEtoRunDetailResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Return mock detail if exists, otherwise return default success detail
      const detail = mockRunDetailsById[runId] || mockSuccessRunDetail;

      // If not found, throw 404
      if (!allMockRuns.find((r) => r.id === runId)) {
        throw new Error('Run not found');
      }

      return detail;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch run details';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /eto-runs/upload - Upload PDF
  // ==========================================================================
  const uploadPdf = async (file: File): Promise<PostEtoRunUploadResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate file type
      if (file.type !== 'application/pdf') {
        throw new Error('Invalid file type. Only PDF files are allowed.');
      }

      // Cycle through actual PDF IDs (2, 3, 4, 103)
      const availablePdfIds = [2, 3, 4, 103];
      const randomPdfId = availablePdfIds[Math.floor(Math.random() * availablePdfIds.length)];

      // Return mock upload response with realistic PDF ID
      return {
        ...mockUploadResponse,
        id: mockUploadResponse.id + Math.floor(Math.random() * 1000),
        pdf_file_id: randomPdfId,
      };
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to upload PDF';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /eto-runs/reprocess - Reprocess runs (bulk)
  // ==========================================================================
  const reprocessRuns = async (
    request: PostEtoRunsReprocessRequest
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate all runs exist
      const invalidRuns = request.run_ids.filter(
        (id) => !allMockRuns.find((r) => r.id === id)
      );
      if (invalidRuns.length > 0) {
        throw new Error(`Runs not found: ${invalidRuns.join(', ')}`);
      }

      // Validate no runs are processing or successful
      const processingRuns = request.run_ids.filter((id) => {
        const run = allMockRuns.find((r) => r.id === id);
        return run?.status === 'processing';
      });
      if (processingRuns.length > 0) {
        throw new Error(
          `Cannot reprocess runs that are currently processing: ${processingRuns.join(', ')}`
        );
      }

      const successfulRuns = request.run_ids.filter((id) => {
        const run = allMockRuns.find((r) => r.id === id);
        return run?.status === 'success';
      });
      if (successfulRuns.length > 0) {
        throw new Error(
          `Cannot reprocess successful runs: ${successfulRuns.join(', ')}`
        );
      }

      // Success - 204 No Content
      console.log(`Reprocessed ${request.run_ids.length} runs`);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to reprocess runs';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // POST /eto-runs/skip - Skip runs (bulk)
  // ==========================================================================
  const skipRuns = async (request: PostEtoRunsSkipRequest): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate all runs exist
      const invalidRuns = request.run_ids.filter(
        (id) => !allMockRuns.find((r) => r.id === id)
      );
      if (invalidRuns.length > 0) {
        throw new Error(`Runs not found: ${invalidRuns.join(', ')}`);
      }

      // Validate no runs are processing or successful
      const processingRuns = request.run_ids.filter((id) => {
        const run = allMockRuns.find((r) => r.id === id);
        return run?.status === 'processing';
      });
      if (processingRuns.length > 0) {
        throw new Error(
          `Cannot skip runs that are currently processing: ${processingRuns.join(', ')}`
        );
      }

      const successfulRuns = request.run_ids.filter((id) => {
        const run = allMockRuns.find((r) => r.id === id);
        return run?.status === 'success';
      });
      if (successfulRuns.length > 0) {
        throw new Error(
          `Cannot skip successful runs: ${successfulRuns.join(', ')}`
        );
      }

      // Success - 204 No Content
      console.log(`Skipped ${request.run_ids.length} runs`);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to skip runs';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // DELETE /eto-runs - Delete runs (bulk)
  // ==========================================================================
  const deleteRuns = async (request: DeleteEtoRunsRequest): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await simulateDelay();

      // Validate all runs exist
      const invalidRuns = request.run_ids.filter(
        (id) => !allMockRuns.find((r) => r.id === id)
      );
      if (invalidRuns.length > 0) {
        throw new Error(`Runs not found: ${invalidRuns.join(', ')}`);
      }

      // Validate all runs are skipped
      const nonSkippedRuns = request.run_ids.filter((id) => {
        const run = allMockRuns.find((r) => r.id === id);
        return run?.status !== 'skipped';
      });
      if (nonSkippedRuns.length > 0) {
        throw new Error(
          `Can only delete skipped runs. Invalid runs: ${nonSkippedRuns.join(', ')}`
        );
      }

      // Success - 204 No Content
      console.log(`Deleted ${request.run_ids.length} runs`);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to delete runs';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================================================
  // GET /pdf-files/{id}/download - Get PDF file URL for streaming
  // ==========================================================================
  const getPdfDownloadUrl = (pdfFileId: number): string => {
    // Mock endpoint - returns URL to PDF stored in public/data/pdfs/
    // In production, this would be: `${API_BASE_URL}/pdf-files/${pdfFileId}/download`
    // Vite dev server automatically serves files from public/ directory
    return `/data/pdfs/${pdfFileId}.pdf`;
  };

  return {
    // API methods
    getEtoRuns,
    getEtoRunDetail,
    uploadPdf,
    reprocessRuns,
    skipRuns,
    deleteRuns,
    getPdfDownloadUrl,

    // State
    isLoading,
    error,
  };
}
