/**
 * React hook for managing transformation pipeline modules
 */

import { useState, useEffect, useCallback } from 'react';
import { BaseModuleTemplate } from '../types/modules';
import { fetchBaseModules } from '../services/transformationPipelineApi';
import { testModules } from '../data/testModules';

export interface UseTransformationModulesResult {
  modules: BaseModuleTemplate[];
  mockModules: BaseModuleTemplate[];
  backendModules: BaseModuleTemplate[];
  isLoading: boolean;
  error: string | null;
  refreshModules: () => Promise<void>;
  processingModules: BaseModuleTemplate[];
}

/**
 * Hook to fetch and manage transformation pipeline modules
 */
export function useTransformationModules(): UseTransformationModulesResult {
  const [backendModules, setBackendModules] = useState<BaseModuleTemplate[]>([]);
  const [mockModules] = useState<BaseModuleTemplate[]>(testModules);
  const [modules, setModules] = useState<BaseModuleTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadModules = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch modules from transformation pipeline backend
      const fetchedBackendModules = await fetchBaseModules();
      setBackendModules(fetchedBackendModules);
      
      // Use backend modules as the primary source (no mock modules for extraction/order generation)
      const backendModulesWithSource = fetchedBackendModules.map(module => ({
        ...module,
        id: `backend_${module.id}`,
        name: module.name,
        description: module.description
      }));
      
      setModules(backendModulesWithSource);
      
      console.log(`Loaded ${fetchedBackendModules.length} backend modules`);

    } catch (err) {
      console.error('Error loading backend modules:', err);
      setError(`Failed to load backend modules: ${err instanceof Error ? err.message : 'Unknown error'}`);
      
      // Set empty modules array if backend fails
      setModules([]);
      setBackendModules([]);
    } finally {
      setIsLoading(false);
    }
  }, [mockModules]);

  const refreshModules = useCallback(async () => {
    await loadModules();
  }, [loadModules]);

  useEffect(() => {
    loadModules();
  }, [loadModules]);

  // Categorize modules for easier use
  const processingModules = modules.filter(module => 
    module.category === 'Text Processing' || 
    module.category === 'Data Processing' || 
    module.category === 'Math'
  );

  return {
    modules,
    mockModules,
    backendModules,
    isLoading,
    error,
    refreshModules,
    processingModules
  };
}