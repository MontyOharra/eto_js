/**
 * Email Ingestion Configs API Hooks
 * API implementation for email-ingestion-configs endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type { IngestionConfigListItem, IngestionConfigDetail } from '../types';
import type {
  CreateEmailConfigRequest,
  UpdateEmailConfigRequest,
  EmailConfigsListQueryParams,
} from './types';

interface IngestionConfigListResponse {
  configs: IngestionConfigListItem[];
  total: number;
}

interface UseEmailConfigsApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // List operations
  getEmailConfigs: (params?: EmailConfigsListQueryParams) => Promise<IngestionConfigListItem[]>;
  getEmailConfigDetail: (id: number) => Promise<IngestionConfigDetail>;

  // CRUD operations
  createEmailConfig: (data: CreateEmailConfigRequest) => Promise<IngestionConfigDetail>;
  updateEmailConfig: (id: number, data: UpdateEmailConfigRequest) => Promise<IngestionConfigDetail>;
  deleteEmailConfig: (id: number) => Promise<IngestionConfigDetail>;

  // Activation operations
  activateEmailConfig: (id: number) => Promise<IngestionConfigDetail>;
  deactivateEmailConfig: (id: number) => Promise<IngestionConfigDetail>;
}

export function useEmailConfigsApi(): UseEmailConfigsApiResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.EMAIL_INGESTION_CONFIGS;

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
   * GET /api/email-ingestion-configs
   * List all ingestion configs with account information
   */
  const getEmailConfigs = useCallback(
    async (params?: EmailConfigsListQueryParams): Promise<IngestionConfigListItem[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<IngestionConfigListResponse>(baseUrl, { params });
        return response.data.configs;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-ingestion-configs/{id}
   * Get detailed information about a specific ingestion config
   */
  const getEmailConfigDetail = useCallback(
    async (id: number): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<IngestionConfigDetail>(`${baseUrl}/${id}`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-ingestion-configs
   * Create a new ingestion config
   */
  const createEmailConfig = useCallback(
    async (data: CreateEmailConfigRequest): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<IngestionConfigDetail>(baseUrl, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * PATCH /api/email-ingestion-configs/{id}
   * Update an existing ingestion config
   */
  const updateEmailConfig = useCallback(
    async (id: number, data: UpdateEmailConfigRequest): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.patch<IngestionConfigDetail>(`${baseUrl}/${id}`, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * DELETE /api/email-ingestion-configs/{id}
   * Delete an ingestion config
   */
  const deleteEmailConfig = useCallback(
    async (id: number): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.delete<IngestionConfigDetail>(`${baseUrl}/${id}`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-ingestion-configs/{id}/activate
   * Activate an ingestion config and start polling
   */
  const activateEmailConfig = useCallback(
    async (id: number): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<IngestionConfigDetail>(`${baseUrl}/${id}/activate`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-ingestion-configs/{id}/deactivate
   * Deactivate an ingestion config and stop polling
   */
  const deactivateEmailConfig = useCallback(
    async (id: number): Promise<IngestionConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<IngestionConfigDetail>(`${baseUrl}/${id}/deactivate`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  return {
    isLoading,
    error,
    getEmailConfigs,
    getEmailConfigDetail,
    createEmailConfig,
    updateEmailConfig,
    deleteEmailConfig,
    activateEmailConfig,
    deactivateEmailConfig,
  };
}
