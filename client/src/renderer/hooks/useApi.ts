/**
 * React Hooks for ETO API Data Fetching
 * Provides loading states, error handling, and data caching
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, ApiError } from '../services/api';
import type {
  EtoRun,
  EtoRunSummary,
  SystemStats,
  EmailServiceStatus,
  TemplateSummary
} from '../types/eto';
import { EtoDataTransforms } from '../types/eto';

// Generic API hook state
interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastFetch: Date | null;
}

// Hook for fetching ETO runs
export function useEtoRuns(params?: {
  status?: string;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}) {
  const [state, setState] = useState<ApiState<EtoRunSummary[]>>({
    data: null,
    loading: true,
    error: null,
    lastFetch: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const { status, limit, autoRefresh = false, refreshInterval = 30000 } = params || {};

  const fetchEtoRuns = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      const response = await apiClient.getEtoRuns({ status, limit });

      // Transform API data to frontend summary format
      const summaries = response.data.map(apiRun => {
        // Convert ApiEtoRun to EtoRun (they have the same structure)
        const etoRun: EtoRun = apiRun as EtoRun;
        return EtoDataTransforms.toSummary(etoRun);
      });

      setState({
        data: summaries,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  }, [status, limit]);

  // Initial fetch
  useEffect(() => {
    fetchEtoRuns();
  }, [fetchEtoRuns]);

  // Auto refresh setup
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(fetchEtoRuns, refreshInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchEtoRuns]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    ...state,
    refetch: fetchEtoRuns,
  };
}

// Hook for system statistics
export function useSystemStats(autoRefresh: boolean = false, refreshInterval: number = 60000) {
  const [state, setState] = useState<ApiState<SystemStats>>({
    data: null,
    loading: true,
    error: null,
    lastFetch: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const fetchStats = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const stats = await apiClient.getSystemStats();
      
      setState({
        data: stats,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Auto refresh setup
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(fetchStats, refreshInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchStats]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    ...state,
    refetch: fetchStats,
  };
}

// Hook for email service status
export function useEmailStatus(autoRefresh: boolean = true, refreshInterval: number = 10000) {
  const [state, setState] = useState<ApiState<EmailServiceStatus>>({
    data: null,
    loading: true,
    error: null,
    lastFetch: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const fetchStatus = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: prev.data === null, error: null }));
      
      const status = await apiClient.getEmailStatus();
      
      setState({
        data: status,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Auto refresh setup
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(fetchStatus, refreshInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    ...state,
    refetch: fetchStatus,
  };
}

// Hook for email service control actions
export function useEmailServiceActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startMonitoring = useCallback(async (params?: {
    email_address?: string;
    folder_name?: string;
  }) => {
    try {
      setLoading(true);
      setError(null);
      
      await apiClient.startEmailMonitoring(params);
      return true;
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const stopMonitoring = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      await apiClient.stopEmailMonitoring();
      return true;
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    startMonitoring,
    stopMonitoring,
    loading,
    error,
    clearError: () => setError(null),
  };
}

// Hook for server health check
export function useServerHealth(autoCheck: boolean = true, checkInterval: number = 30000) {
  const [state, setState] = useState<ApiState<{ status: string; timestamp: string }>>({
    data: null,
    loading: true,
    error: null,
    lastFetch: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const checkHealth = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: prev.data === null, error: null }));
      
      const health = await apiClient.healthCheck();
      
      setState({
        data: health,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Server unavailable';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  }, []);

  // Initial check
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Auto check setup
  useEffect(() => {
    if (autoCheck && checkInterval > 0) {
      intervalRef.current = setInterval(checkHealth, checkInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoCheck, checkInterval, checkHealth]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const isServerOnline = (state.data?.status === 'ok' || state.data?.status === 'healthy') && !state.error;

  return {
    ...state,
    isServerOnline,
    refetch: checkHealth,
  };
}

// Hook for fetching templates
export function useTemplates(params?: {
  status?: string;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}) {
  const [state, setState] = useState<ApiState<TemplateSummary[]>>({
    data: null,
    loading: true,
    error: null,
    lastFetch: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const { status, limit, autoRefresh = false, refreshInterval = 60000 } = params || {};

  const fetchTemplates = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const response = await apiClient.getTemplates({ status, limit });
      
      // Transform API data to frontend format
      const templates = response.templates.map(template => {
        const fullTemplate = EtoDataTransforms.templateApiToFrontend(template);
        return EtoDataTransforms.templateToSummary(fullTemplate);
      });
      
      setState({
        data: templates,
        loading: false,
        error: null,
        lastFetch: new Date(),
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError ? error.message : 'Unknown error occurred';
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
    }
  }, [status, limit]);

  // Initial fetch
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Auto refresh setup
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(fetchTemplates, refreshInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchTemplates]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    ...state,
    refetch: fetchTemplates,
  };
}