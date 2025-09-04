/**
 * React hook for managing transformation pipeline modules
 */

import { useState, useEffect, useCallback } from 'react';
import { BaseModuleTemplate, testModules } from '../data/testModules';

export interface UseTransformationModulesResult {
  modules: BaseModuleTemplate[];
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
  const [modules, setModules] = useState<BaseModuleTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadModules = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use test modules for now
      setModules(testModules);
      console.log(`Loaded ${testModules.length} test modules`);

    } catch (err) {
      console.error('Error loading modules:', err);
      setError('Failed to load modules');
      setModules([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshModules = useCallback(async () => {
    await loadModules();
  }, [loadModules]);

  useEffect(() => {
    loadModules();
  }, []);

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
    isLoading,
    error,
    refreshModules,
    extractedDataModules,
    processingModules,
    orderGenerationModule
  };
}