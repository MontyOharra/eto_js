/**
 * Email Configs Hooks - Conditional Export
 * Exports either mock or real API hook based on environment configuration
 */

import { API_CONFIG } from '@renderer/shared/api/config';
import { useMockEmailConfigsApi } from './useMockEmailConfigsApi';
import { useEmailConfigsApi } from './useEmailConfigsApi';

/**
 * Export the appropriate API hook based on configuration
 *
 * Set VITE_USE_MOCK_API=true to use mock data (development)
 * Set VITE_USE_MOCK_API=false or omit to use real API (production)
 */
export const useEmailConfigsApiHook = API_CONFIG.USE_MOCK_API
  ? useMockEmailConfigsApi
  : useEmailConfigsApi;

// Also export individual hooks for explicit usage
export { useMockEmailConfigsApi } from './useMockEmailConfigsApi';
export { useEmailConfigsApi } from './useEmailConfigsApi';
