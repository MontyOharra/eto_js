/**
 * API Configuration
 * Centralized configuration for API endpoints and environment settings
 */

export const API_CONFIG = {
  // Base URL for the API - can be overridden by environment variable
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

  // Use mock API for development (set VITE_USE_MOCK_API=true to enable)
  USE_MOCK_API: import.meta.env.VITE_USE_MOCK_API === 'true',

  // Request timeout in milliseconds
  TIMEOUT: 30000,

  // API endpoints
  ENDPOINTS: {
    EMAIL_CONFIGS: '/email-configs',
    TEMPLATES: '/pdf-templates',
    PIPELINES: '/pipelines',
    PDF_FILES: '/pdf-files',
    ETO_RUNS: '/eto-runs',
    MODULES: '/modules',
  },
} as const;

export type ApiEndpoint = keyof typeof API_CONFIG.ENDPOINTS;
