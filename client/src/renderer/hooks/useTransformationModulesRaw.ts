/**
 * React hook for managing transformation pipeline modules with raw API format
 */

import { useState, useEffect, useCallback } from 'react';

// Raw module format from API
export interface RawModuleTemplate {
  module_ref: string;
  id: string;
  version: string;
  title: string;
  description: string;
  kind: string;
  meta: {
    inputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string | { mode: 'variable'; allowed: string[] };
    };
    outputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string | { mode: 'variable'; allowed: string[] };
    };
  };
  config_schema: any;
  category: string;
  color: string;
}

export interface UseRawModulesResult {
  modules: RawModuleTemplate[];
  isLoading: boolean;
  error: string | null;
  refreshModules: () => Promise<void>;
}

/**
 * Hook to fetch and manage transformation pipeline modules in raw API format
 */
export function useTransformationModulesRaw(): UseRawModulesResult {
  const [modules, setModules] = useState<RawModuleTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadModules = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch modules directly from API without conversion
      const response = await fetch('http://localhost:8090/api/modules');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data.modules) {
        throw new Error('No modules found in response');
      }

      setModules(data.modules);
      console.log(`Loaded ${data.modules.length} raw modules from API`);

    } catch (err) {
      console.error('Error loading raw modules:', err);
      setError(`Failed to load modules: ${err instanceof Error ? err.message : 'Unknown error'}`);
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
  }, [loadModules]);

  return {
    modules,
    isLoading,
    error,
    refreshModules
  };
}