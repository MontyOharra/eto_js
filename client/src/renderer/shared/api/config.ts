/**
 * API Configuration
 * Centralized configuration for API endpoints and environment settings
 */

export const API_CONFIG = {
  // Base URL for the API - can be overridden by environment variable
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

  // Request timeout in milliseconds
  TIMEOUT: 30000,

  // API endpoints (all backend routes are prefixed with /api)
  ENDPOINTS: {
    EMAIL_CONFIGS: '/api/email-configs',
    TEMPLATES: '/api/pdf-templates',
    PIPELINES: '/api/pipelines',
    PDF_FILES: '/api/pdf-files',
    ETO_RUNS: '/api/eto-runs',
    MODULES: '/api/modules',
  },
} as const;

export type ApiEndpoint = keyof typeof API_CONFIG.ENDPOINTS;
