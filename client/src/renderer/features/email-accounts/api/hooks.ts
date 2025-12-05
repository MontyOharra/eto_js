/**
 * Email Accounts API Hooks
 * API implementation for email-accounts endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type {
  EmailAccountSummary,
  EmailAccountResponse,
  EmailAccountListResponse,
  CreateEmailAccountRequest,
  UpdateEmailAccountRequest,
  ValidateConnectionRequest,
  ValidationResultResponse,
  EmailAccountsListQueryParams,
  FolderListResponse,
} from './types';

interface UseEmailAccountsApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // List operations
  getEmailAccounts: (params?: EmailAccountsListQueryParams) => Promise<EmailAccountSummary[]>;
  getEmailAccount: (id: number) => Promise<EmailAccountResponse>;
  getAccountFolders: (accountId: number) => Promise<string[]>;

  // CRUD operations
  createEmailAccount: (data: CreateEmailAccountRequest) => Promise<EmailAccountResponse>;
  updateEmailAccount: (id: number, data: UpdateEmailAccountRequest) => Promise<EmailAccountResponse>;
  deleteEmailAccount: (id: number) => Promise<EmailAccountResponse>;

  // Validation operations
  validateConnection: (data: ValidateConnectionRequest) => Promise<ValidationResultResponse>;
}

export function useEmailAccountsApi(): UseEmailAccountsApiResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.EMAIL_ACCOUNTS;

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
   * GET /api/email-accounts
   * List all email accounts as summaries (credentials excluded)
   */
  const getEmailAccounts = useCallback(
    async (params?: EmailAccountsListQueryParams): Promise<EmailAccountSummary[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailAccountListResponse>(baseUrl, { params });
        return response.data.accounts;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-accounts/{id}
   * Get a single email account by ID
   */
  const getEmailAccount = useCallback(
    async (id: number): Promise<EmailAccountResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<EmailAccountResponse>(`${baseUrl}/${id}`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * GET /api/email-accounts/{id}/folders
   * List available folders for an email account
   */
  const getAccountFolders = useCallback(
    async (accountId: number): Promise<string[]> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<FolderListResponse>(`${baseUrl}/${accountId}/folders`);
        return response.data.folders;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-accounts
   * Create a new email account
   */
  const createEmailAccount = useCallback(
    async (data: CreateEmailAccountRequest): Promise<EmailAccountResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<EmailAccountResponse>(baseUrl, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * PATCH /api/email-accounts/{id}
   * Update an email account
   */
  const updateEmailAccount = useCallback(
    async (id: number, data: UpdateEmailAccountRequest): Promise<EmailAccountResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.patch<EmailAccountResponse>(`${baseUrl}/${id}`, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * DELETE /api/email-accounts/{id}
   * Delete an email account
   */
  const deleteEmailAccount = useCallback(
    async (id: number): Promise<EmailAccountResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.delete<EmailAccountResponse>(`${baseUrl}/${id}`);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * POST /api/email-accounts/validate
   * Test email connection with provided credentials
   */
  const validateConnection = useCallback(
    async (data: ValidateConnectionRequest): Promise<ValidationResultResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.post<ValidationResultResponse>(
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
    getEmailAccounts,
    getEmailAccount,
    getAccountFolders,
    createEmailAccount,
    updateEmailAccount,
    deleteEmailAccount,
    validateConnection,
  };
}
