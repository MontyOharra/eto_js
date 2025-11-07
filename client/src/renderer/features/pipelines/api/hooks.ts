/**
 * Pipelines API Hook
 * Real API implementation for /api/pipelines endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  PipelinesListResponse,
  PipelineDetail,
  CreatePipelineRequest,
  CreatePipelineResponse,
  ValidatePipelineRequest,
  ValidatePipelineResponse,
  ExecutePipelineRequest,
  ExecutePipelineResponse,
  PipelinesQueryParams,
} from './types';

interface UsePipelinesApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // API operations
  getPipelines: (params?: PipelinesQueryParams) => Promise<PipelinesListResponse>;
  getPipeline: (id: number) => Promise<PipelineDetail>;
  createPipeline: (data: CreatePipelineRequest) => Promise<CreatePipelineResponse>;
  validatePipeline: (data: ValidatePipelineRequest) => Promise<ValidatePipelineResponse>;
  executePipeline: (id: number, request: ExecutePipelineRequest) => Promise<ExecutePipelineResponse>;
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
    async (id: number): Promise<PipelineDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<PipelineDetail>(`${baseUrl}/${id}`);
        return response.data;
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
        const response = await apiClient.post<CreatePipelineResponse>(baseUrl, data);
        return response.data;
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
        const response = await apiClient.post<ValidatePipelineResponse>(
          `${baseUrl}/validate`,
          data
        );
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/pipelines/{id}/execute
   * Execute pipeline with entry values (simulation mode)
   */
  const executePipeline = useCallback(
    async (id: number, request: ExecutePipelineRequest): Promise<ExecutePipelineResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<ExecutePipelineResponse>(
          `${baseUrl}/${id}/execute`,
          request
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
    validatePipeline,
    executePipeline,
  };
}
