/**
 * Mock Modules API Hook
 * Simulates the /api/modules endpoint with in-memory module catalog data
 */

import { useState } from 'react';
import type { ModuleTemplate } from '../../../types/moduleTypes';
import type { ModuleCatalogResponse, ModulesQueryParams } from '../api/types';

// Import mock module catalog data
import mockModulesData from './data/modules.json';

/**
 * Simulated network delay (in milliseconds)
 */
const MOCK_DELAY_MS = 200;

/**
 * Mock Modules API Hook
 * Provides the same interface as the real API but uses local mock data
 */
export function useMockModulesApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Simulate network delay
   */
  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  /**
   * Get module catalog
   * Endpoint: GET /api/modules
   *
   * @param filters - Optional filters for module kind, category, or search
   * @returns Promise resolving to module catalog response
   */
  const getModules = async (
    filters?: ModulesQueryParams
  ): Promise<ModuleCatalogResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      // Simulate network delay
      await delay(MOCK_DELAY_MS);

      // Start with all modules
      let modules: ModuleTemplate[] = [...mockModulesData.modules];

      // Apply filters if provided
      if (filters) {
        // Filter by module kind
        if (filters.module_kind) {
          modules = modules.filter((m) => m.kind === filters.module_kind);
        }

        // Filter by category
        if (filters.category) {
          modules = modules.filter((m) => m.category === filters.category);
        }

        // Filter by search text (searches title and description)
        if (filters.search) {
          const searchLower = filters.search.toLowerCase();
          modules = modules.filter(
            (m) =>
              m.title.toLowerCase().includes(searchLower) ||
              m.description?.toLowerCase().includes(searchLower)
          );
        }
      }

      console.log(
        `[Mock API] Loaded ${modules.length} modules` +
          (filters ? ` (filtered from ${mockModulesData.modules.length} total)` : '')
      );

      return { modules };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load modules';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get a single module by ID
   * Endpoint: GET /api/modules/{id}
   *
   * @param moduleId - Module ID to fetch
   * @returns Promise resolving to module template
   */
  const getModuleById = async (moduleId: string): Promise<ModuleTemplate | null> => {
    setIsLoading(true);
    setError(null);

    try {
      await delay(MOCK_DELAY_MS);

      const module = mockModulesData.modules.find((m) => m.id === moduleId);

      if (!module) {
        throw new Error(`Module not found: ${moduleId}`);
      }

      console.log(`[Mock API] Loaded module: ${moduleId}`);

      return module;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load module';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get all available module IDs
   * Utility method for testing/debugging
   */
  const getAvailableModuleIds = (): string[] => {
    return mockModulesData.modules.map((m) => m.id);
  };

  /**
   * Get modules grouped by category
   * Utility method for UI organization
   */
  const getModulesByCategory = (): Record<string, ModuleTemplate[]> => {
    const grouped: Record<string, ModuleTemplate[]> = {};

    for (const module of mockModulesData.modules) {
      const category = module.category || 'Uncategorized';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(module);
    }

    return grouped;
  };

  /**
   * Get modules grouped by kind
   * Utility method for UI organization
   */
  const getModulesByKind = (): Record<string, ModuleTemplate[]> => {
    const grouped: Record<string, ModuleTemplate[]> = {};

    for (const module of mockModulesData.modules) {
      const kind = module.kind;
      if (!grouped[kind]) {
        grouped[kind] = [];
      }
      grouped[kind].push(module);
    }

    return grouped;
  };

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

export default useMockModulesApi;
