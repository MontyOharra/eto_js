/**
 * Logging Interceptor
 * Logs API requests and responses in development mode
 */

import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';

export function loggingRequestInterceptor(
  config: InternalAxiosRequestConfig
): InternalAxiosRequestConfig {
  if (import.meta.env.DEV) {
    console.log('[API Request]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      params: config.params,
      data: config.data,
    });
  }
  return config;
}

export function loggingResponseInterceptor(
  response: AxiosResponse
): AxiosResponse {
  if (import.meta.env.DEV) {
    console.log('[API Response]', {
      status: response.status,
      url: response.config.url,
      data: response.data,
    });
  }
  return response;
}
