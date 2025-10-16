/**
 * Error Interceptor
 * Handles API errors and provides consistent error formatting
 */

import type { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  detail?: unknown;
}

export function errorResponseInterceptor(error: AxiosError): Promise<never> {
  const apiError: ApiError = {
    message: 'An unexpected error occurred',
    status: error.response?.status,
  };

  if (error.response) {
    // Server responded with error status
    const data = error.response.data as any;
    apiError.message = data?.message || data?.detail || error.message;
    apiError.detail = data;
  } else if (error.request) {
    // Request made but no response received
    apiError.message = 'No response from server. Please check your connection.';
  } else {
    // Error in request setup
    apiError.message = error.message;
  }

  // Log error in development
  if (import.meta.env.DEV) {
    console.error('[API Error]', apiError);
  }

  return Promise.reject(apiError);
}
