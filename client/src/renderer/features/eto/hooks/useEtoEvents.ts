/**
 * useEtoEvents Hook
 * Connects to Server-Sent Events (SSE) endpoint for real-time ETO run updates
 *
 * Automatically connects when component mounts and reconnects if connection drops.
 * Handles all event types: run and sub-run create/update/delete events.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { API_CONFIG } from '../../../shared/api/config';
import { etoRunsQueryKeys } from '../api/hooks';

interface EtoEventData {
  // Run-level fields
  id?: number;
  run_id?: number;
  pdf_file_id?: number;
  status?: string;
  processing_step?: string | null;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  error_type?: string | null;
  error_message?: string | null;
  // Sub-run fields
  eto_run_id?: number;
  new_sub_run_id?: number | null;
  old_sub_run_id?: number;
  pages_count?: number;
  deleted_sub_run_count?: number;
}

interface EtoEvent {
  type: string;
  data: EtoEventData;
  timestamp: string;
}

interface UseEtoEventsOptions {
  /** Called when SSE connection is established */
  onConnected?: () => void;
  /** Called when SSE connection is lost */
  onDisconnected?: () => void;
  /** Called on any event (for custom handling) */
  onEvent?: (event: EtoEvent) => void;
  /**
   * Fallback polling interval in milliseconds.
   * Periodically invalidates queries as backup in case SSE events are missed.
   * Set to 0 to disable. Default: 30000 (30 seconds)
   */
  fallbackPollingInterval?: number;
}

/**
 * Hook for connecting to ETO run SSE events with automatic query invalidation.
 *
 * Automatically invalidates TanStack Query caches when events are received,
 * causing affected queries to refetch with updated data.
 */
// Default fallback polling interval: 30 seconds
const DEFAULT_FALLBACK_POLLING_INTERVAL = 10000;

export function useEtoEvents(options: UseEtoEventsOptions = {}) {
  const {
    onConnected,
    onDisconnected,
    onEvent,
    fallbackPollingInterval = DEFAULT_FALLBACK_POLLING_INTERVAL
  } = options;
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectedRef = useRef(false);

  const handleEvent = useCallback((event: EtoEvent) => {
    // Call custom handler if provided
    onEvent?.(event);

    // Determine which run ID to invalidate
    const runId = event.data.id || event.data.run_id || event.data.eto_run_id;

    // Handle different event types
    switch (event.type) {
      case 'run_created':
        // New run - invalidate list
        queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
        break;

      case 'run_updated':
      case 'run_reprocessed':
      case 'run_skipped':
        // Run changed - invalidate list and detail
        queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
        if (runId) {
          queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(runId) });
        }
        break;

      case 'run_deleted':
        // Run deleted - invalidate list and remove detail from cache
        queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
        if (runId) {
          queryClient.removeQueries({ queryKey: etoRunsQueryKeys.detail(runId) });
        }
        break;

      case 'sub_run_updated':
      case 'sub_run_reprocessed':
      case 'sub_run_skipped':
        // Sub-run changed - invalidate parent run detail and list
        queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
        if (runId) {
          queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.detail(runId) });
        }
        break;

      default:
        // Unknown event type - invalidate everything to be safe
        console.warn('[SSE] Unknown event type:', event.type);
        queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.all });
    }
  }, [queryClient, onEvent]);

  const connect = useCallback(() => {
    // Don't create duplicate connections
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    // Create EventSource connection
    const eventSource = new EventSource(
      `${API_CONFIG.BASE_URL}/api/eto-runs/events`,
      { withCredentials: false }
    );

    eventSource.onopen = () => {
      console.log('[SSE] Connected to ETO events stream');
      isConnectedRef.current = true;
      onConnected?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const payload: EtoEvent = JSON.parse(event.data);
        console.log('[SSE] Received event:', payload.type, payload.data);
        handleEvent(payload);
      } catch (err) {
        console.error('[SSE] Error parsing event:', err);
      }
    };

    eventSource.onerror = (error) => {
      console.log('[SSE] Connection error:', error);

      if (isConnectedRef.current) {
        isConnectedRef.current = false;
        onDisconnected?.();
      }

      // Close current connection
      eventSource.close();

      // Attempt reconnect after delay
      if (!reconnectTimeoutRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          connect();
        }, 3000);
      }
    };

    eventSourceRef.current = eventSource;
  }, [handleEvent, onConnected, onDisconnected]);

  // Connect on mount, disconnect on unmount
  // Note: Empty dependency array - we only want to connect once on mount
  // The connect function uses refs for callbacks so it always has the latest values
  useEffect(() => {
    connect();

    return () => {
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      isConnectedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fallback polling - periodically invalidate queries in case SSE events are missed
  useEffect(() => {
    if (fallbackPollingInterval <= 0) {
      return; // Polling disabled
    }

    const poll = () => {
      // Only log in development to avoid console spam
      if (process.env.NODE_ENV === 'development') {
        console.log('[SSE Fallback] Polling - invalidating ETO queries');
      }
      queryClient.invalidateQueries({ queryKey: etoRunsQueryKeys.lists() });
    };

    // Start polling interval
    pollingIntervalRef.current = setInterval(poll, fallbackPollingInterval);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [fallbackPollingInterval, queryClient]);

  return {
    isConnected: isConnectedRef.current,
  };
}
