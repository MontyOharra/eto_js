/**
 * useOrderEvents Hook
 * Connects to Server-Sent Events (SSE) endpoint for real-time order management updates
 *
 * Automatically connects when component mounts and reconnects if connection drops.
 * Handles all event types: pending order and pending update create/update/delete events.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { API_CONFIG } from '../../../shared/api/config';
import { orderManagementQueryKeys } from '../api/hooks';

interface OrderEventData {
  // Common fields
  id?: number;
  status?: string;
  hawb?: string;
  customer_id?: number;
  htc_order_number?: number;
  // Action-specific fields
  action?: string;
  fields_changed?: string[];
  fields_updated?: string[];
  error_message?: string;
}

interface OrderEvent {
  type: string;
  data: OrderEventData;
  timestamp: string;
}

interface UseOrderEventsOptions {
  /** Called when SSE connection is established */
  onConnected?: () => void;
  /** Called when SSE connection is lost */
  onDisconnected?: () => void;
  /** Called on any event (for custom handling) */
  onEvent?: (event: OrderEvent) => void;
  /**
   * Fallback polling interval in milliseconds.
   * Periodically invalidates queries as backup in case SSE events are missed.
   * Set to 0 to disable. Default: 10000 (10 seconds)
   */
  fallbackPollingInterval?: number;
}

/**
 * Hook for connecting to order management SSE events with automatic query invalidation.
 *
 * Automatically invalidates TanStack Query caches when events are received,
 * causing affected queries to refetch with updated data.
 */
const DEFAULT_FALLBACK_POLLING_INTERVAL = 10000;

export function useOrderEvents(options: UseOrderEventsOptions = {}) {
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

  const handleEvent = useCallback((event: OrderEvent) => {
    // Call custom handler if provided
    onEvent?.(event);

    // Handle different event types
    switch (event.type) {
      case 'pending_order_created':
        // New pending order - invalidate lists
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingOrders() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        break;

      case 'pending_order_updated':
        // Pending order changed - invalidate lists and detail
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingOrders() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        if (event.data.id) {
          queryClient.invalidateQueries({
            queryKey: orderManagementQueryKeys.pendingOrderDetail(event.data.id)
          });
        }
        break;

      case 'pending_order_deleted':
        // Pending order deleted - invalidate lists and remove detail from cache
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingOrders() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        if (event.data.id) {
          queryClient.removeQueries({
            queryKey: orderManagementQueryKeys.pendingOrderDetail(event.data.id)
          });
        }
        break;

      case 'pending_update_created':
        // New pending update - invalidate lists
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        break;

      case 'pending_update_updated':
        // Pending update changed - invalidate lists and detail
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        if (event.data.id) {
          queryClient.invalidateQueries({
            queryKey: orderManagementQueryKeys.pendingUpdateDetail(event.data.id)
          });
        }
        break;

      case 'pending_update_resolved':
        // Pending update approved/rejected - invalidate lists and detail
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.pendingUpdates() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.orderHistory() });
        if (event.data.id) {
          queryClient.invalidateQueries({
            queryKey: orderManagementQueryKeys.pendingUpdateDetail(event.data.id)
          });
        }
        break;

      default:
        // Unknown event type - invalidate everything to be safe
        console.warn('[Order SSE] Unknown event type:', event.type);
        queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.all });
    }
  }, [queryClient, onEvent]);

  const connect = useCallback(() => {
    // Don't create duplicate connections
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    // Create EventSource connection
    const eventSource = new EventSource(
      `${API_CONFIG.BASE_URL}/api/order-management/events`,
      { withCredentials: false }
    );

    eventSource.onopen = () => {
      console.log('[Order SSE] Connected to order events stream');
      isConnectedRef.current = true;
      onConnected?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const payload: OrderEvent = JSON.parse(event.data);
        console.log('[Order SSE] Received event:', payload.type, payload.data);
        handleEvent(payload);
      } catch (err) {
        console.error('[Order SSE] Error parsing event:', err);
      }
    };

    eventSource.onerror = (error) => {
      console.log('[Order SSE] Connection error:', error);

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
        console.log('[Order SSE Fallback] Polling - invalidating order queries');
      }
      queryClient.invalidateQueries({ queryKey: orderManagementQueryKeys.unifiedActions() });
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
