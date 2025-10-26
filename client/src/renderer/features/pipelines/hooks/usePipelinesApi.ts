/**
 * Pipelines API Hook
 * Real API implementation for /api/pipelines endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  PipelinesListResponse,
  PipelineDetailResponse,
  CreatePipelineRequest,
  CreatePipelineResponse,
  UpdatePipelineRequest,
  UpdatePipelineResponse,
  ValidatePipelineRequest,
  ValidatePipelineResponse,
} from '../types';

interface PipelinesQueryParams {
  sort_by?: 'id' | 'created_at';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

interface UsePipelinesApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // API operations
  getPipelines: (params?: PipelinesQueryParams) => Promise<PipelinesListResponse>;
  getPipeline: (id: number) => Promise<PipelineDetailResponse>;
  createPipeline: (data: CreatePipelineRequest) => Promise<CreatePipelineResponse>;
  updatePipeline: (id: number, data: UpdatePipelineRequest) => Promise<UpdatePipelineResponse>;
  deletePipeline: (id: number) => Promise<void>;
  validatePipeline: (data: ValidatePipelineRequest) => Promise<ValidatePipelineResponse>;
}

export function usePipelinesApi(): UsePipelinesApiResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.PIPELINES;

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

  /**
   * GET /api/pipelines
   * List all pipeline definitions with pagination and sorting
   */
  const getPipelines = useCallback(
    async (params?: PipelinesQueryParams): Promise<PipelinesListResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<PipelinesListResponse>(baseUrl, { params });
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/pipelines/{id}
   * Get complete pipeline definition including pipeline_state and visual_state
   */
  const getPipeline = useCallback(
    async (id: number): Promise<PipelineDetailResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<any>(`${baseUrl}/${id}`);
        const data = response.data;

        // Transform backend snake_case to frontend camelCase
        if (data.visual_state?.entry_points) {
          data.visual_state.entryPoints = data.visual_state.entry_points;
          delete data.visual_state.entry_points;
        }

        return data as PipelineDetailResponse;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pipelines
   * Create new standalone pipeline for testing
   */
  const createPipeline = useCallback(
    async (data: CreatePipelineRequest): Promise<CreatePipelineResponse> => {
      return withLoadingAndError(async () => {
        // Transform frontend camelCase to backend snake_case
        const transformedData = { ...data };
        if (transformedData.visual_state?.entryPoints) {
          (transformedData.visual_state as any).entry_points = transformedData.visual_state.entryPoints;
          delete transformedData.visual_state.entryPoints;
        }

        const response = await apiClient.post<CreatePipelineResponse>(baseUrl, transformedData);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * PUT /api/pipelines/{id}
   * Update existing pipeline definition
   */
  const updatePipeline = useCallback(
    async (id: number, data: UpdatePipelineRequest): Promise<UpdatePipelineResponse> => {
      return withLoadingAndError(async () => {
        // Transform frontend camelCase to backend snake_case
        const transformedData = { ...data };
        if (transformedData.visual_state?.entryPoints) {
          (transformedData.visual_state as any).entry_points = transformedData.visual_state.entryPoints;
          delete transformedData.visual_state.entryPoints;
        }

        const response = await apiClient.put<UpdatePipelineResponse>(`${baseUrl}/${id}`, transformedData);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * DELETE /api/pipelines/{id}
   * Delete pipeline definition (only for standalone pipelines)
   */
  const deletePipeline = useCallback(
    async (id: number): Promise<void> => {
      return withLoadingAndError(async () => {
        await apiClient.delete(`${baseUrl}/${id}`);
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pipelines/validate
   * Validate pipeline structure without saving
   */
  const validatePipeline = useCallback(
    async (data: ValidatePipelineRequest): Promise<ValidatePipelineResponse> => {
      return withLoadingAndError(async () => {
        // Transform frontend camelCase to backend snake_case
        const transformedData = { ...data };
        if (transformedData.visual_state?.entryPoints) {
          (transformedData.visual_state as any).entry_points = transformedData.visual_state.entryPoints;
          delete transformedData.visual_state.entryPoints;
        }

        const response = await apiClient.post<ValidatePipelineResponse>(
          `${baseUrl}/validate`,
          transformedData
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  return {
    isLoading,
    error,
    getPipelines,
    getPipeline,
    createPipeline,
    updatePipeline,
    deletePipeline,
    validatePipeline,
  };
}
