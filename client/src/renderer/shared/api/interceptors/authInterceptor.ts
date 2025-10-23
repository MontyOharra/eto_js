/**
 * Authentication Interceptor
 * Adds authentication tokens to outgoing requests
 */

import type { InternalAxiosRequestConfig } from 'axios';

export function authRequestInterceptor(
  config: InternalAxiosRequestConfig
): InternalAxiosRequestConfig {
  // TODO: Add token retrieval logic when authentication is implemented
  // For now, this is a placeholder

  // Example:
  // const token = localStorage.getItem('auth_token');
  // if (token) {
  //   config.headers.Authorization = `Bearer ${token}`;
  // }

  return config;
}
