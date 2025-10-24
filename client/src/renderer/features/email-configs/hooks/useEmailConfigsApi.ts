/**
 * Email Configs API Hook
 * Real API implementation for email-configs endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  EmailConfigSummaryDTO,
  EmailConfigDetailDTO,
  CreateEmailConfigRequestDTO,
  UpdateEmailConfigRequestDTO,
  EmailAccountDTO,
  EmailFolderDTO,
  ValidateEmailConfigRequestDTO,
  ValidateEmailConfigResponseDTO,
  EmailConfigsListQueryParams,
  EmailFoldersQueryParams,
} from '../api/types';

interface UseEmailConfigsApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // List operations
  getEmailConfigs: (params?: EmailConfigsListQueryParams) => Promise<EmailConfigSummaryDTO[]>;
  getEmailConfigDetail: (id: number) => Promise<EmailConfigDetailDTO>;

  // CRUD operations
  createEmailConfig: (data: CreateEmailConfigRequestDTO) => Promise<EmailConfigDetailDTO>;
  updateEmailConfig: (id: number, data: UpdateEmailConfigRequestDTO) => Promise<EmailConfigDetailDTO>;
  deleteEmailConfig: (id: number) => Promise<void>;

  // Activation operations
  activateEmailConfig: (id: number) => Promise<EmailConfigDetailDTO>;
  deactivateEmailConfig: (id: number) => Promise<EmailConfigDetailDTO>;

  // Discovery operations
  getEmailAccounts: () => Promise<EmailAccountDTO[]>;
  getEmailFolders: (params: EmailFoldersQueryParams) => Promise<EmailFolderDTO[]>;

  // Validation operations
  validateEmailConfig: (data: ValidateEmailConfigRequestDTO) => Promise<ValidateEmailConfigResponseDTO>;
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
    async (params?: EmailConfigsListQueryParams): Promise<EmailConfigSummaryDTO[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailConfigSummaryDTO[]>(baseUrl, { params });
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
    async (id: number): Promise<EmailConfigDetailDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailConfigDetailDTO>(`${baseUrl}/${id}`);
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
    async (data: CreateEmailConfigRequestDTO): Promise<EmailConfigDetailDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetailDTO>(baseUrl, data);
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
    async (id: number, data: UpdateEmailConfigRequestDTO): Promise<EmailConfigDetailDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.put<EmailConfigDetailDTO>(`${baseUrl}/${id}`, data);
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
    async (id: number): Promise<EmailConfigDetailDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetailDTO>(`${baseUrl}/${id}/activate`);
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
    async (id: number): Promise<EmailConfigDetailDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailConfigDetailDTO>(`${baseUrl}/${id}/deactivate`);
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
    async (): Promise<EmailAccountDTO[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailAccountDTO[]>(`${baseUrl}/discovery/accounts`);
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
    async (params: EmailFoldersQueryParams): Promise<EmailFolderDTO[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailFolderDTO[]>(`${baseUrl}/discovery/folders`, {
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
    async (data: ValidateEmailConfigRequestDTO): Promise<ValidateEmailConfigResponseDTO> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<ValidateEmailConfigResponseDTO>(
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
