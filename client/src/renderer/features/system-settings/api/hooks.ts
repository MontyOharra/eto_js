/**
 * System Settings API Hooks
 * API implementation for system settings endpoints
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type { EmailSettingsResponse, UpdateEmailSettingsRequest } from './types';

interface UseSystemSettingsApiResult {
  // State
  isLoading: boolean;
  error: string | null;

  // Email settings operations
  getEmailSettings: () => Promise<EmailSettingsResponse>;
  updateEmailSettings: (data: UpdateEmailSettingsRequest) => Promise<EmailSettingsResponse>;
}

export function useSystemSettingsApi(): UseSystemSettingsApiResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.SYSTEM_SETTINGS;

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
   * GET /api/settings/email
   * Get email settings including default sender account
   */
  const getEmailSettings = useCallback(async (): Promise<EmailSettingsResponse> => {
    return withLoadingAndError(async () => {
      const response = await apiClient.get<EmailSettingsResponse>(`${baseUrl}/email`);
      return response.data;
    });
  }, [baseUrl, withLoadingAndError]);

  /**
   * PUT /api/settings/email
   * Update email settings
   */
  const updateEmailSettings = useCallback(
    async (data: UpdateEmailSettingsRequest): Promise<EmailSettingsResponse> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.put<EmailSettingsResponse>(`${baseUrl}/email`, data);
        return response.data;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  return {
    isLoading,
    error,
    getEmailSettings,
    updateEmailSettings,
  };
}
