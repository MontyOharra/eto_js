/**
 * React Hooks for ETO API Data Fetching
 * Provides loading states, error handling, and data caching
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, ApiError, type ApiEtoRunSummary } from '../services/api';
import type {
  EtoRun,
  EtoRunSummary,
  SystemStats,
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

      const response = await apiClient.getEtoRuns({
        eto_run_status: status,
        limit,
        order_by: 'created_at',
        order_direction: 'desc'
      });

      // Transform API data to frontend summary format
      const summaries = response.data.map((apiRunSummary: ApiEtoRunSummary) => {
        // Convert ApiEtoRunSummary to EtoRun format for transform function
        const etoRun: EtoRun = {
          id: apiRunSummary.id,
          email_id: apiRunSummary.email?.email_id || 0,
          pdf_file_id: apiRunSummary.pdf_file_id,
          status: apiRunSummary.status,
          processing_step: apiRunSummary.processing_step,
          pdf_filename: apiRunSummary.pdf_filename,
          email_subject: apiRunSummary.email?.subject || 'No Email Subject',
          sender_email: apiRunSummary.email?.sender_email || 'Unknown Sender',
          file_size: apiRunSummary.file_size,
          matched_template_id: apiRunSummary.matched_template_id,
          template_name: apiRunSummary.matched_template_name,
          processing_duration_ms: apiRunSummary.processing_duration_ms,
          error_message: apiRunSummary.error_message,
          created_at: apiRunSummary.created_at,
          started_at: apiRunSummary.started_at,
          completed_at: apiRunSummary.completed_at,
        };
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