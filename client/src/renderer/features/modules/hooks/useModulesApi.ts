/**
 * Modules API Hook
 * Real API integration for /api/modules endpoint
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type { ModuleTemplate } from '../../../types/moduleTypes';
import type { ModuleCatalogResponse, ModulesQueryParams } from '../api/types';

/**
 * Backend API response type (matches server-new/src/api/schemas/modules.py)
 */
interface ModulesListResponse {
  items: ModuleCatalogDTO[];
  total: number;
}

interface ModuleCatalogDTO {
  id: string;
  version: string;
  name: string;
  description: string | null;
  module_kind: string;
  meta: any;
  config_schema: any;
  handler_name: string;
  color: string;
  category: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Convert backend ModuleCatalogDTO to frontend ModuleTemplate
 */
function convertModuleCatalogToTemplate(dto: ModuleCatalogDTO): ModuleTemplate {
  return {
    id: dto.id,
    version: dto.version,
    title: dto.name,
    description: dto.description || '',
    kind: dto.module_kind,
    color: dto.color,
    meta: dto.meta,
    config_schema: dto.config_schema,
  };
}

/**
 * Real Modules API Hook
 * Fetches modules from /api/modules endpoint
 */
export function useModulesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = API_CONFIG.ENDPOINTS.MODULES;

  /**
   * Wrapper for API calls with loading and error handling
   */
  const withLoadingAndError = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiCall();
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An error occurred';
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Get module catalog
   * Endpoint: GET /api/modules
   *
   * @param filters - Optional filters for module kind, category, or search
   * @returns Promise resolving to module catalog response
   */
  const getModules = useCallback(
    async (filters?: ModulesQueryParams): Promise<ModuleCatalogResponse> => {
      return withLoadingAndError(async () => {
        // Build query params
        const params: Record<string, string> = {};

        if (filters?.module_kind) {
          params.kind = filters.module_kind;
        }

        // Note: Backend uses 'only_active' param, defaults to true
        // Frontend filters for category and search are client-side for now

        const response = await apiClient.get<ModulesListResponse>(baseUrl, { params });

        // Convert backend DTOs to frontend ModuleTemplate format
        let modules = response.data.items.map(convertModuleCatalogToTemplate);

        // Apply client-side filters
        if (filters?.category) {
          modules = modules.filter((m) => m.category === filters.category);
        }

        if (filters?.search) {
          const searchLower = filters.search.toLowerCase();
          modules = modules.filter(
            (m) =>
              m.title.toLowerCase().includes(searchLower) ||
              m.description?.toLowerCase().includes(searchLower)
          );
        }

        console.log(`[API] Loaded ${modules.length} modules from ${baseUrl}`);

        return { modules };
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * Get a single module by ID
   * Note: Backend doesn't have a single module endpoint yet,
   * so we fetch all and filter client-side
   *
   * @param moduleId - Module ID to fetch
   * @returns Promise resolving to module template
   */
  const getModuleById = useCallback(
    async (moduleId: string): Promise<ModuleTemplate | null> => {
      return withLoadingAndError(async () => {
        const response = await apiClient.get<ModulesListResponse>(baseUrl);
        const modules = response.data.items.map(convertModuleCatalogToTemplate);
        const module = modules.find((m) => m.id === moduleId);

        if (!module) {
          throw new Error(`Module not found: ${moduleId}`);
        }

        console.log(`[API] Loaded module: ${moduleId}`);
        return module;
      });
    },
    [baseUrl, withLoadingAndError]
  );

  /**
   * Get all available module IDs
   * Utility method for testing/debugging
   */
  const getAvailableModuleIds = useCallback(async (): Promise<string[]> => {
    const result = await getModules();
    return result.modules.map((m) => m.id);
  }, [getModules]);

  /**
   * Get modules grouped by category
   * Utility method for UI organization
   */
  const getModulesByCategory = useCallback(async (): Promise<Record<string, ModuleTemplate[]>> => {
    const result = await getModules();
    const grouped: Record<string, ModuleTemplate[]> = {};

    for (const module of result.modules) {
      const category = module.category || 'Uncategorized';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(module);
    }

    return grouped;
  }, [getModules]);

  /**
   * Get modules grouped by kind
   * Utility method for UI organization
   */
  const getModulesByKind = useCallback(async (): Promise<Record<string, ModuleTemplate[]>> => {
    const result = await getModules();
    const grouped: Record<string, ModuleTemplate[]> = {};

    for (const module of result.modules) {
      const kind = module.kind;
      if (!grouped[kind]) {
        grouped[kind] = [];
      }
      grouped[kind].push(module);
    }

    return grouped;
  }, [getModules]);

  return {
    // Primary API methods
    getModules,
    getModuleById,

    // Utility methods
    getAvailableModuleIds,
    getModulesByCategory,
    getModulesByKind,

    // State
    isLoading,
    error,
  };
}

export default useModulesApi;
