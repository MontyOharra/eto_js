/**
 * Modules API Hooks
 * TanStack Query hooks for fetching module catalog data
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';
import { API_CONFIG } from '../../../shared/api/config';
import type { ModuleTemplate } from '../types';
import type { Module, ModulesQueryParams } from './types';

/**
 * Convert backend Module to frontend ModuleTemplate
 */
function convertModuleToTemplate(dto: Module): ModuleTemplate {
  return {
    id: dto.id,
    version: dto.version,
    title: dto.name,
    description: dto.description || '',
    kind: dto.module_kind,
    color: dto.color,
    category: dto.category,
    meta: dto.meta,
    config_schema: dto.config_schema,
  };
}

/**
 * Fetch all modules from catalog with optional filters
 *
 * Query key: ['modules', filters]
 * Cache: 5 minutes stale time, 10 minutes garbage collection
 *
 * @param filters - Optional filters (module_kind, category, search)
 * @returns TanStack Query result with modules array
 *
 * @example
 * const { data: modules = [], isLoading } = useModules();
 * const { data: transformModules = [] } = useModules({ module_kind: 'transform' });
 */
export function useModules(filters?: ModulesQueryParams) {
  return useQuery({
    queryKey: ['modules', filters],
    queryFn: async (): Promise<ModuleTemplate[]> => {
      // Build query params for backend
      const params: Record<string, string> = {};
      if (filters?.module_kind) {
        params.kind = filters.module_kind;
      }

      // Fetch from backend
      const response = await apiClient.get<Module[]>(
        API_CONFIG.ENDPOINTS.MODULES,
        { params }
      );

      // Convert to frontend format
      let modules = response.data.map(convertModuleToTemplate);

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

      return modules;
    },
    staleTime: 0, // Always fetch fresh data (modules may be synced externally via curl)
    gcTime: 1000 * 60 * 10, // 10 minutes - keep in cache
  });
}

/**
 * Fetch a single module by ID
 *
 * Query key: ['module', moduleId]
 * Cache: 5 minutes stale time, 10 minutes garbage collection
 *
 * Note: Backend doesn't have a single module endpoint yet,
 * so we fetch all modules and filter client-side.
 *
 * @param moduleId - Module ID to fetch (null to disable query)
 * @returns TanStack Query result with module or null
 *
 * @example
 * const { data: module } = useModule('transform_add_v1');
 * const { data: module } = useModule(selectedId); // null if selectedId is null
 */
export function useModule(moduleId: string | null) {
  return useQuery({
    queryKey: ['module', moduleId],
    queryFn: async (): Promise<ModuleTemplate | null> => {
      if (!moduleId) return null;

      // Backend doesn't have single module endpoint, fetch all and filter
      const response = await apiClient.get<Module[]>(
        API_CONFIG.ENDPOINTS.MODULES
      );

      const modules = response.data.map(convertModuleToTemplate);
      const module = modules.find((m) => m.id === moduleId);

      if (!module) {
        throw new Error(`Module not found: ${moduleId}`);
      }

      return module;
    },
    enabled: !!moduleId, // Only run query if moduleId is provided
    staleTime: 0, // Always fetch fresh data (modules may be synced externally via curl)
    gcTime: 1000 * 60 * 10,
  });
}
