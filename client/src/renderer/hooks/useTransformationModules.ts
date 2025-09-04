/**
 * React hook for managing transformation pipeline modules
 */

import { useState, useEffect, useCallback } from 'react';
import { BaseModuleTemplate, testBaseModules } from '../data/testModules';
import { fetchBaseModules } from '../services/transformationPipelineApi';

export interface UseTransformationModulesResult {
  modules: BaseModuleTemplate[];
  mockModules: BaseModuleTemplate[];
  backendModules: BaseModuleTemplate[];
  isLoading: boolean;
  error: string | null;
  refreshModules: () => Promise<void>;
  extractedDataModules: BaseModuleTemplate[];
  processingModules: BaseModuleTemplate[];
  orderGenerationModule: BaseModuleTemplate | null;
}

/**
 * Hook to fetch and manage transformation pipeline modules
 */
export function useTransformationModules(): UseTransformationModulesResult {
  const [backendModules, setBackendModules] = useState<BaseModuleTemplate[]>([]);
  const [mockModules] = useState<BaseModuleTemplate[]>(testBaseModules);
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
      
      // Keep only specific mock modules for testing (extracted data and order creation)
      const testingOnlyModules = mockModules.filter(module => 
        module.category === 'Extracted Data' || 
        module.id === 'order_generation'
      ).map(module => ({
        ...module,
        id: `mock_${module.id}`,
        name: module.name, // Keep original name for these testing modules
        description: module.description
      }));
      
      // Use backend modules as-is (no prefix needed since they're the real modules)
      const backendModulesWithSource = fetchedBackendModules.map(module => ({
        ...module,
        id: `backend_${module.id}`,
        name: module.name, // Keep original name
        description: module.description
      }));
      
      const allModules = [...testingOnlyModules, ...backendModulesWithSource];
      setModules(allModules);
      
      console.log(`Loaded ${fetchedBackendModules.length} backend modules + ${testingOnlyModules.length} testing modules`);

    } catch (err) {
      console.error('Error loading backend modules:', err);
      setError(`Failed to load backend modules: ${err instanceof Error ? err.message : 'Unknown error'}`);
      
      // Fall back to just testing modules if backend fails
      const testingOnlyModules = mockModules.filter(module => 
        module.category === 'Extracted Data' || 
        module.id === 'order_generation'
      ).map(module => ({
        ...module,
        id: `mock_${module.id}`,
        name: module.name,
        description: `${module.description} (Backend Unavailable)`
      }));
      setModules(testingOnlyModules);
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
  const extractedDataModules = modules.filter(module => module.category === 'Extracted Data');
  const processingModules = modules.filter(module => 
    module.category === 'Text Processing' || 
    module.category === 'Data Processing' || 
    module.category === 'Math'
  );
  const orderGenerationModule = modules.find(module => module.id === 'order_generation') || null;

  return {
    modules,
    mockModules,
    backendModules,
    isLoading,
    error,
    refreshModules,
    extractedDataModules,
    processingModules,
    orderGenerationModule
  };
}