/**
 * Email Configs API Hook
 * Real API implementation for email-configs endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  EmailConfigListItem,
  EmailConfigDetail,
  CreateEmailConfigRequest,
  UpdateEmailConfigRequest,
  EmailAccount,
  EmailFolder,
  ValidateEmailConfigRequest,
  ValidateEmailConfigResponse,
  EmailConfigsListQueryParams,
  EmailFoldersQueryParams,
} from '../api/types';

interface UseEmailConfigsApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // List operations
  getEmailConfigs: (params?: EmailConfigsListQueryParams) => Promise<EmailConfigListItem[]>;
  getEmailConfigDetail: (id: number) => Promise<EmailConfigDetail>;

  // CRUD operations
  createEmailConfig: (data: CreateEmailConfigRequest) => Promise<EmailConfigDetail>;
  updateEmailConfig: (id: number, data: UpdateEmailConfigRequest) => Promise<EmailConfigDetail>;
  deleteEmailConfig: (id: number) => Promise<void>;

  // Activation operations
  activateEmailConfig: (id: number) => Promise<EmailConfigDetail>;
  deactivateEmailConfig: (id: number) => Promise<EmailConfigDetail>;

  // Discovery operations
  getEmailAccounts: () => Promise<EmailAccount[]>;
  getEmailFolders: (params: EmailFoldersQueryParams) => Promise<EmailFolder[]>;

  // Validation operations
  validateEmailConfig: (data: ValidateEmailConfigRequest) => Promise<ValidateEmailConfigResponse>;
}

export function useEmailConfigsApi(): UseEmailConfigsApiResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = `${API_CONFIG.ENDPOINTS.EMAIL_CONFIGS}`;

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
   * GET /api/email-configs
   * List all email configurations with optional filtering and sorting
   */
  const getEmailConfigs = useCallback(
    async (params?: EmailConfigsListQueryParams): Promise<EmailConfigListItem[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailConfigListItem[]>(baseUrl, { params });
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-configs/{id}
   * Get detailed information about a specific email configuration
   */
  const getEmailConfigDetail = useCallback(
    async (id: number): Promise<EmailConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailConfigDetail>(`${baseUrl}/${id}`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-configs
   * Create a new email configuration
   */
  const createEmailConfig = useCallback(
    async (data: CreateEmailConfigRequest): Promise<EmailConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetail>(baseUrl, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * PUT /api/email-configs/{id}
   * Update an existing email configuration
   */
  const updateEmailConfig = useCallback(
    async (id: number, data: UpdateEmailConfigRequest): Promise<EmailConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.put<EmailConfigDetail>(`${baseUrl}/${id}`, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * DELETE /api/email-configs/{id}
   * Delete an email configuration
   */
  const deleteEmailConfig = useCallback(
    async (id: number): Promise<void> => {
      return withLoadingAndError(async () => {
        await apiClient.delete(`${baseUrl}/${id}`);
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-configs/{id}/activate
   * Activate an email configuration to start monitoring
   */
  const activateEmailConfig = useCallback(
    async (id: number): Promise<EmailConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetail>(`${baseUrl}/${id}/activate`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-configs/{id}/deactivate
   * Deactivate an email configuration to stop monitoring
   */
  const deactivateEmailConfig = useCallback(
    async (id: number): Promise<EmailConfigDetail> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetail>(`${baseUrl}/${id}/deactivate`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-configs/discovery/accounts
   * Get list of available email accounts from Outlook
   */
  const getEmailAccounts = useCallback(
    async (): Promise<EmailAccount[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailAccount[]>(`${baseUrl}/discovery/accounts`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-configs/discovery/folders
   * Get list of available folders for a specific email account
   */
  const getEmailFolders = useCallback(
    async (params: EmailFoldersQueryParams): Promise<EmailFolder[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailFolder[]>(`${baseUrl}/discovery/folders`, {
          params,
        });
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-configs/validate
   * Validate email configuration settings (checks connectivity and folder access)
   */
  const validateEmailConfig = useCallback(
    async (data: ValidateEmailConfigRequest): Promise<ValidateEmailConfigResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<ValidateEmailConfigResponse>(
          `${baseUrl}/validate`,
          data
        );
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
    getEmailAccounts,
    getEmailFolders,
    validateEmailConfig,
  };
}
